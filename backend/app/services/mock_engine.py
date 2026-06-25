"""智能 Mock 引擎。

在 ``app.services.mock_service.MockService`` 基础上扩展：按 JSON Schema 自动生成数据、
按 header / query 路由、期望断言、中文数据生成器、字段名智能推断、
Faker 模板变量解析。
保留原接口，向上兼容。

典型用法::

    # 纯 Python Schema 生成（无第三方依赖）
    generator = SchemaMockGenerator()
    data = generator.generate({"type": "object", "properties": {"id": {"type": "integer"}}})

    # Faker 模板变量
    body = resolve_faker_templates('{"name": "{{faker.name}}"}')

    # SmartMockEngine（需要 faker 库）
    engine = SmartMockEngine()
    data = engine.generate_from_schema(schema)
    payload = engine.route(api_id=1, request={"headers": {...}})
    cn_data = engine.generate_chinese_data("name")  # -> "张伟"
"""

from __future__ import annotations

import logging
import random
import re
import string
import threading
import time
import uuid as _uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger("service.mock_engine")


# ── 异常 ────────────────────────────────────────────────────────────────


class MockEngineError(Exception):
    """Mock 引擎错误。"""


# ── 中文数据生成器 ──────────────────────────────────────────────────────


class ChineseDataGenerator:
    """中文拟真数据生成器，无第三方依赖。"""

    # 常见姓氏（前 100 姓）
    SURNAMES = [
        "王", "李", "张", "刘", "陈", "杨", "赵", "黄", "周", "吴",
        "徐", "孙", "胡", "朱", "高", "林", "何", "郭", "马", "罗",
        "梁", "宋", "郑", "谢", "韩", "唐", "冯", "于", "董", "萧",
        "程", "曹", "袁", "邓", "许", "傅", "沈", "曾", "彭", "吕",
        "苏", "卢", "蒋", "蔡", "贾", "丁", "魏", "薛", "叶", "阎",
        "余", "潘", "杜", "戴", "夏", "钟", "汪", "田", "任", "姜",
        "范", "方", "石", "姚", "谭", "廖", "邹", "熊", "金", "陆",
        "郝", "孔", "白", "崔", "康", "毛", "邱", "秦", "江", "史",
        "顾", "侯", "邵", "孟", "龙", "万", "段", "雷", "钱", "汤",
        "尹", "黎", "易", "常", "武", "乔", "贺", "赖", "龚", "文",
    ]

    # 常见名字用字
    GIVEN_NAMES = [
        "伟", "芳", "娜", "敏", "静", "丽", "强", "磊", "洋", "勇",
        "艳", "杰", "军", "秀英", "明", "华", "慧", "建", "国", "玲",
        "桂英", "飞", "平", "秀兰", "鑫", "桂兰", "素芬", "玉梅", "翔", "涛",
        "超", "志强", "俊", "浩", "宇", "婷", "雪", "萍", "红", "梅",
        "文", "博", "天", "子", "一", "思", "梦", "佳", "欣", "怡",
    ]

    # 省份
    PROVINCES = [
        "北京市", "上海市", "广东省", "江苏省", "浙江省", "山东省", "河南省",
        "四川省", "湖北省", "湖南省", "福建省", "安徽省", "河北省", "陕西省",
        "江西省", "重庆市", "辽宁省", "云南省", "广西壮族自治区", "山西省",
    ]

    # 城市（与省份对应简化）
    CITIES = [
        "朝阳区", "浦东新区", "深圳市", "南京市", "杭州市", "济南市", "郑州市",
        "成都市", "武汉市", "长沙市", "福州市", "合肥市", "石家庄市", "西安市",
        "南昌市", "渝中区", "沈阳市", "昆明市", "南宁市", "太原市",
    ]

    # 街道
    STREETS = [
        "中山路", "人民路", "解放路", "建设路", "和平路", "长安路",
        "文化路", "民主路", "新华路", "光明路", "幸福路", "科技路",
    ]

    # 行业
    INDUSTRIES = [
        "科技", "信息", "网络", "数据", "智能", "云计算", "软件",
        "电子商务", "金融", "教育", "医疗", "物流", "传媒", "贸易",
    ]

    # 公司类型
    COMPANY_TYPES = [
        "有限公司", "科技有限公司", "信息技术有限公司", "网络科技有限公司",
        "数据服务有限公司", "智能科技有限公司", "集团有限公司",
    ]

    # 常见邮箱域名
    EMAIL_DOMAINS = [
        "qq.com", "163.com", "126.com", "gmail.com", "outlook.com",
        "sina.com", "foxmail.com", "hotmail.com",
    ]

    # 拼音姓（与 SURNAMES 对应简化）
    PINYIN_SURNAMES = [
        "wang", "li", "zhang", "liu", "chen", "yang", "zhao", "huang",
        "zhou", "wu", "xu", "sun", "hu", "zhu", "gao", "lin", "he",
        "guo", "ma", "luo",
    ]

    # 字段名 → 生成器映射
    FIELD_INFERENCE: dict[str, str] = {
        # 姓名
        "name": "chinese_name", "姓名": "chinese_name", "username": "chinese_name",
        "user_name": "chinese_name",
        "realname": "chinese_name",
        "real_name": "chinese_name",
        "nick": "chinese_name", "nickname": "chinese_name", "author": "chinese_name",
        # 手机
        "phone": "phone", "手机": "phone", "手机号": "phone", "mobile": "phone",
        "telephone": "phone", "tel": "phone", "phone_number": "phone",
        # 邮箱
        "email": "email", "邮箱": "email", "mail": "email",
        # 地址
        "address": "address", "地址": "address", "addr": "address",
        "location": "address", "住址": "address",
        # 公司
        "company": "company", "公司": "company", "company_name": "company",
        "org": "company", "organization": "company",
        # ID
        "id": "auto_id", "编号": "auto_id", "uid": "auto_id",
        "user_id": "auto_id", "order_id": "auto_id",
        # 价格
        "price": "price", "价格": "price", "amount": "price",
        "fee": "price", "cost": "price", "money": "price",
        # 日期
        "date": "date", "日期": "date", "birthday": "date",
        "created_at": "date", "updated_at": "date",
        # URL
        "url": "url", "link": "url", "website": "url",
        "href": "url", "avatar": "url", "image": "url", "img": "url",
        "logo": "url", "photo": "url", "picture": "url",
    }

    _auto_id_counter = 0

    def generate(self, field_name: str) -> Any:
        """根据字段名智能推断并生成中文拟真数据。"""
        key = field_name.lower().strip()
        gen_type = self.FIELD_INFERENCE.get(key)
        if gen_type:
            return getattr(self, f"_gen_{gen_type}")()
        # 模糊匹配
        for pattern, gen_type in self.FIELD_INFERENCE.items():
            if pattern in key or key in pattern:
                return getattr(self, f"_gen_{gen_type}")()
        return None

    def _gen_chinese_name(self) -> str:
        return random.choice(self.SURNAMES) + random.choice(self.GIVEN_NAMES)

    def _gen_phone(self) -> str:
        prefix = random.choice(["13", "14", "15", "16", "17", "18", "19"])
        return prefix + "".join([str(random.randint(0, 9)) for _ in range(9)])

    def _gen_email(self) -> str:
        pinyin = random.choice(self.PINYIN_SURNAMES)
        num = random.randint(10, 9999)
        domain = random.choice(self.EMAIL_DOMAINS)
        return f"{pinyin}{num}@{domain}"

    def _gen_address(self) -> str:
        idx = random.randint(0, len(self.PROVINCES) - 1)
        province = self.PROVINCES[idx]
        city = self.CITIES[idx]
        street = random.choice(self.STREETS)
        number = random.randint(1, 999)
        return f"{province}{city}{street}{number}号"

    def _gen_company(self) -> str:
        region = random.choice(self.PROVINCES).replace("市", "").replace("省", "")
        industry = random.choice(self.INDUSTRIES)
        company_type = random.choice(self.COMPANY_TYPES)
        return f"{region}{industry}{company_type}"

    def _gen_auto_id(self) -> int:
        self._auto_id_counter += 1
        return self._auto_id_counter

    def _gen_price(self) -> float:
        return round(random.uniform(10, 9999.99), 2)

    def _gen_date(self) -> str:
        year = random.randint(2020, 2026)
        month = random.randint(1, 12)
        day = random.randint(1, 28)
        return f"{year}-{month:02d}-{day:02d}"

    def _gen_url(self) -> str:
        domain = random.choice(["example", "demo", "api", "cdn", "static"])
        tld = random.choice(["com", "cn", "io", "net"])
        return f"https://{domain}.{tld}/{random.randint(1000, 9999)}"


# ── 纯 Python Schema Mock 生成器（无第三方依赖）─────────────────────────


class SchemaMockGenerator:
    """按 JSON Schema 生成 Mock 数据，纯 Python 实现，无第三方依赖。

    支持：
      - 类型：string / number / integer / boolean / array / object / null
      - string format：email / date / date-time / uuid / uri / url / hostname / ipv4 / ipv6 / phone
      - 约束：enum / const / minLength / maxLength / minimum / maximum / minItems / maxItems / pattern / required
      - 字段名智能推断（复用 ChineseDataGenerator）
    """

    def __init__(self) -> None:
        self._cn_gen = ChineseDataGenerator()
        self._id_counter = 0

    def generate(self, schema: dict[str, Any] | Any) -> Any:
        """按 JSON Schema 生成 Mock 数据。"""
        if not isinstance(schema, dict):
            return None
        # const 优先
        if "const" in schema:
            return schema["const"]
        # enum 随机选一个
        if "enum" in schema and isinstance(schema["enum"], list) and schema["enum"]:
            return random.choice(schema["enum"])

        t = schema.get("type")
        # 推断类型
        if t is None and "properties" in schema:
            t = "object"
        if t is None:
            return None

        handlers = {
            "object": self._gen_object,
            "array": self._gen_array,
            "string": self._gen_string,
            "integer": self._gen_integer,
            "number": self._gen_number,
            "boolean": self._gen_boolean,
            "null": lambda _: None,
        }
        handler = handlers.get(t)
        return handler(schema) if handler else None

    def _gen_object(self, schema: dict[str, Any]) -> dict[str, Any]:
        props: dict[str, Any] = schema.get("properties", {}) or {}
        required = set(schema.get("required", []) or [])
        out: dict[str, Any] = {}
        for name, sub in props.items():
            try:
                # 先尝试中文智能推断（仅 string 类型）
                if isinstance(sub, dict) and sub.get("type") == "string" and "enum" not in sub and "const" not in sub and "format" not in sub:
                    cn_val = self._cn_gen.generate(name)
                    if cn_val is not None:
                        out[name] = cn_val
                        continue
                out[name] = self.generate(sub)
            except Exception:
                out[name] = None
        # 确保必填字段存在
        for r in required:
            out.setdefault(r, None)
        return out

    def _gen_array(self, schema: dict[str, Any]) -> list[Any]:
        items_schema = schema.get("items", {"type": "string"})
        min_items = int(schema.get("minItems", 1))
        max_items = int(schema.get("maxItems", max(min_items, 3)))
        size = random.randint(min_items, max(min_items, max_items))
        return [self.generate(items_schema) for _ in range(size)]

    def _gen_string(self, schema: dict[str, Any]) -> str:
        fmt = (schema.get("format") or "").lower()
        # format 映射
        if fmt == "email":
            return self._fake_email()
        if fmt in ("uri", "url"):
            return self._fake_url()
        if fmt == "uuid":
            return str(_uuid.uuid4())
        if fmt == "date":
            return self._fake_date()
        if fmt in ("date-time", "datetime"):
            return self._fake_datetime()
        if fmt == "hostname":
            return self._fake_hostname()
        if fmt == "ipv4":
            return self._fake_ipv4()
        if fmt == "ipv6":
            return self._fake_ipv6()
        if fmt == "phone":
            return self._cn_gen._gen_phone()

        # pattern 约束：尽力生成匹配的字符串
        if "pattern" in schema:
            return self._gen_from_pattern(schema["pattern"])

        min_len = int(schema.get("minLength", 1))
        max_len = max(min_len, int(schema.get("maxLength", 16)))
        length = random.randint(min_len, max_len)
        return "".join(random.choices(string.ascii_letters + string.digits, k=length))

    def _gen_integer(self, schema: dict[str, Any]) -> int:
        minimum = int(schema.get("minimum", 0))
        maximum = max(minimum + 1, int(schema.get("maximum", 1000)))
        exclusive_min = schema.get("exclusiveMinimum", False)
        exclusive_max = schema.get("exclusiveMaximum", False)
        if exclusive_min:
            minimum += 1
        if exclusive_max:
            maximum -= 1
        if minimum > maximum:
            minimum = maximum - 1
        return random.randint(minimum, maximum)

    def _gen_number(self, schema: dict[str, Any]) -> float:
        minimum = float(schema.get("minimum", 0.0))
        maximum = max(minimum + 1.0, float(schema.get("maximum", 1000.0)))
        exclusive_min = schema.get("exclusiveMinimum", False)
        exclusive_max = schema.get("exclusiveMaximum", False)
        if exclusive_min:
            minimum += 0.001
        if exclusive_max:
            maximum -= 0.001
        return round(random.uniform(minimum, maximum), 2)

    def _gen_boolean(self, _schema: dict[str, Any]) -> bool:
        return random.choice([True, False])

    # ── 辅助方法：纯 Python 伪数据生成 ──────────────────────────────

    def _fake_email(self) -> str:
        user = "".join(random.choices(string.ascii_lowercase, k=random.randint(3, 8)))
        domain = random.choice(["gmail.com", "outlook.com", "qq.com", "163.com", "example.com"])
        return f"{user}@{domain}"

    def _fake_url(self) -> str:
        domain = "".join(random.choices(string.ascii_lowercase, k=random.randint(4, 10)))
        tld = random.choice(["com", "cn", "io", "net", "org"])
        path = "".join(random.choices(string.ascii_lowercase + string.digits, k=random.randint(3, 8)))
        return f"https://{domain}.{tld}/{path}"

    def _fake_date(self) -> str:
        d = datetime.now() - timedelta(days=random.randint(0, 3650))
        return d.strftime("%Y-%m-%d")

    def _fake_datetime(self) -> str:
        d = datetime.now() - timedelta(days=random.randint(0, 3650), hours=random.randint(0, 23))
        return d.strftime("%Y-%m-%dT%H:%M:%SZ")

    def _fake_hostname(self) -> str:
        name = "".join(random.choices(string.ascii_lowercase, k=random.randint(4, 10)))
        tld = random.choice(["com", "cn", "io", "net"])
        return f"{name}.{tld}"

    def _fake_ipv4(self) -> str:
        return f"{random.randint(1, 223)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"

    def _fake_ipv6(self) -> str:
        parts = [format(random.randint(0, 0xFFFF), 'x') for _ in range(8)]
        return ":".join(parts)

    def _gen_from_pattern(self, pattern: str) -> str:
        """尽力根据正则 pattern 生成匹配字符串。简化实现，覆盖常见模式。"""
        # 常见模式快速映射
        quick_map = {
            r"^\d{4}-\d{2}-\d{2}$": lambda: self._fake_date(),
            r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$": lambda: self._fake_email(),
            r"^https?://.+$": lambda: self._fake_url(),
        }
        for p, gen in quick_map.items():
            if pattern.strip() == p:
                return gen()
        # 兜底：生成随机字符串
        length = random.randint(4, 16)
        return "".join(random.choices(string.ascii_letters + string.digits, k=length))


# ── Faker 模板变量解析器 ──────────────────────────────────────────────


# 英文 Faker 数据池（纯 Python，无第三方依赖）
_EN_FIRST_NAMES = [
    "James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda",
    "David", "Elizabeth", "William", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Christopher", "Karen", "Charles", "Lisa", "Daniel", "Nancy",
    "Matthew", "Betty", "Anthony", "Margaret", "Mark", "Sandra", "Steven", "Ashley",
]

_EN_LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson",
]

_EN_CITIES = [
    "New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia",
    "San Antonio", "San Diego", "Dallas", "San Jose", "Austin", "Jacksonville",
    "Fort Worth", "Columbus", "Charlotte", "San Francisco", "Indianapolis", "Seattle",
    "Denver", "Washington",
]

_EN_COUNTRIES = [
    "United States", "United Kingdom", "Canada", "Australia", "Germany", "France",
    "Japan", "Brazil", "India", "China", "Italy", "Spain", "Mexico", "South Korea",
    "Netherlands", "Sweden", "Norway", "Switzerland", "Singapore", "New Zealand",
]

_EN_WORDS = [
    "adventure", "algorithm", "benchmark", "capacity", "dynamic", "element",
    "framework", "gateway", "harmony", "interface", "junction", "keyword",
    "landscape", "mechanism", "network", "optimize", "paradigm", "quantum",
    "resonance", "spectrum", "threshold", "universe", "velocity", "workflow",
]

_EN_SENTENCES = [
    "The quick brown fox jumps over the lazy dog.",
    "A journey of a thousand miles begins with a single step.",
    "To be or not to be, that is the question.",
    "All that glitters is not gold.",
    "The only thing we have to fear is fear itself.",
]

_EN_PARAGRAPHS = [
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
    "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.",
    "Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.",
]

_EN_COMPANIES = [
    "Acme Corp", "Globex Inc", "Initech", "Umbrella Corp", "Wayne Enterprises",
    "Stark Industries", "Cyberdyne Systems", "Soylent Corp", "Wonka Industries",
    "Aperture Science", "Massive Dynamic", "Oscorp", "Tyrell Corp", "Weyland-Yutani",
]


def _faker_generate(faker_type: str) -> str:
    """根据 faker 类型生成伪数据（纯 Python 实现，无第三方依赖）。"""
    generators = {
        "name": lambda: f"{random.choice(_EN_FIRST_NAMES)} {random.choice(_EN_LAST_NAMES)}",
        "email": lambda: f"{''.join(random.choices(string.ascii_lowercase, k=random.randint(3, 8)))}@{random.choice(['gmail.com', 'outlook.com', 'example.com'])}",
        "phone": lambda: f"+1-{random.randint(200, 999)}-{random.randint(100, 999)}-{random.randint(1000, 9999)}",
        "address": lambda: f"{random.randint(100, 9999)} {random.choice(_EN_WORDS).title()} St, {random.choice(_EN_CITIES)}",
        "company": lambda: random.choice(_EN_COMPANIES),
        "date": lambda: (datetime.now() - timedelta(days=random.randint(0, 3650))).strftime("%Y-%m-%d"),
        "number": lambda: str(random.randint(1, 9999)),
        "uuid": lambda: str(_uuid.uuid4()),
        "url": lambda: f"https://{''.join(random.choices(string.ascii_lowercase, k=random.randint(4, 10)))}.{random.choice(['com', 'io', 'net'])}/",
        "username": lambda: f"{random.choice(_EN_FIRST_NAMES).lower()}{random.randint(1, 9999)}",
        "firstName": lambda: random.choice(_EN_FIRST_NAMES),
        "lastname": lambda: random.choice(_EN_LAST_NAMES),
        "city": lambda: random.choice(_EN_CITIES),
        "country": lambda: random.choice(_EN_COUNTRIES),
        "zipCode": lambda: f"{random.randint(10000, 99999)}",
        "sentence": lambda: random.choice(_EN_SENTENCES),
        "paragraph": lambda: random.choice(_EN_PARAGRAPHS),
        "word": lambda: random.choice(_EN_WORDS),
        "boolean": lambda: random.choice(["true", "false"]),
        "float": lambda: str(round(random.uniform(0, 1000), 2)),
        "hex": lambda: ''.join(random.choices('0123456789abcdef', k=8)),
        "color": lambda: f"#{''.join(random.choices('0123456789abcdef', k=6))}",
    }
    gen = generators.get(faker_type)
    if gen:
        try:
            return gen()
        except Exception:
            return f"{{{{faker.{faker_type}}}}}"
    return f"{{{{faker.{faker_type}}}}}"


def resolve_faker_templates(body: str) -> str:
    """解析响应体中的 ``{{faker.TYPE}}`` 模板变量。

    支持的类型：name, email, phone, address, company, date, number, uuid,
    url, username, firstName, lastName, city, country, zipCode, sentence,
    paragraph, word, boolean, float, hex, color

    每次请求时调用，生成不同数据。
    """
    def _replace_faker(match: re.Match) -> str:
        faker_type = match.group(1).strip()
        return _faker_generate(faker_type)

    return re.sub(r"\{\{faker\.(\w+)\}\}", _replace_faker, body)


# ── Mock 函数处理器 ────────────────────────────────────────────────────


def process_mock_functions(body: str) -> str:
    """处理响应体中的 $randomXxx()、{{variable}} 和 {{faker.TYPE}} 占位符。"""
    # ReDoS 防护：拒绝超长 body（>1MB）
    if len(body) > 1_000_000:
        logger.warning("mock body 超过 1MB，跳过模板替换")
        return body
    cn_gen = ChineseDataGenerator()

    def _replace_fn(match: re.Match) -> str:
        fn_name = match.group(1)
        fn_map = {
            "randomInt": lambda: str(random.randint(1, 9999)),
            "randomName": cn_gen._gen_chinese_name,
            "randomEmail": cn_gen._gen_email,
            "randomPhone": cn_gen._gen_phone,
            "randomAddress": cn_gen._gen_address,
            "randomCompany": cn_gen._gen_company,
            "randomDate": cn_gen._gen_date,
            "randomUrl": cn_gen._gen_url,
            "randomPrice": lambda: str(cn_gen._gen_price()),
            "randomId": lambda: str(cn_gen._gen_auto_id()),
        }
        handler = fn_map.get(fn_name)
        if handler:
            try:
                return handler()
            except Exception:
                return match.group(0)
        return match.group(0)

    # 替换 $functionName()
    result = re.sub(r"\$(\w+)\(\)", _replace_fn, body)

    # 替换 {{faker.TYPE}} 模板变量
    result = resolve_faker_templates(result)

    # 替换 {{variable}} 占位符
    def _replace_var(match: re.Match) -> str:
        var_name = match.group(1).strip()
        var_map = {
            "timestamp": str(int(time.time())),
            "random_string": "".join(
                random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=8)
            ),
            "project_id": "",  # 需要上下文注入
            "base_url": "",    # 需要上下文注入
        }
        return var_map.get(var_name, match.group(0))

    result = re.sub(r"\{\{(\w+)\}\}", _replace_var, result)
    return result


# ── 数据结构 ────────────────────────────────────────────────────────────


@dataclass
class MockScenario:
    """场景路由条目。"""

    name: str
    match: dict[str, Any] = field(default_factory=dict)
    response_status: int = 200
    response_headers: dict[str, str] = field(default_factory=dict)
    response_body: Any = None
    weight: int = 1
    priority: int = 0
    enabled: bool = True


# ── 引擎实现 ────────────────────────────────────────────────────────────


class SmartMockEngine:
    """智能 Mock 引擎。

    设计要点：
      - 全部能力为纯函数 / 实例方法，无 DB 依赖
      - ``faker`` 用于按字段名/格式生成拟真数据（如 ``name`` -> 人名）
      - 中文数据生成器：按字段名智能推断生成中文拟真数据
      - 路由按 ``header.*`` / ``query.*`` / ``body.*`` 做精确匹配
      - 场景路由支持 priority 优先级排序
    """

    def __init__(self, locale: str = "zh_CN", seed: int | None = None) -> None:
        try:
            from faker import Faker
        except ImportError as exc:  # pragma: no cover
            raise MockEngineError("未安装 faker") from exc
        self.faker = Faker(locale)
        if seed is not None:
            self.faker.seed_instance(seed)
        self._faker_available = True
        self.scenarios: list[MockScenario] = []
        self.cn_generator = ChineseDataGenerator()

    # ── 中文数据生成 ──────────────────────────────────────────────

    def generate_chinese_data(self, field_name: str) -> Any:
        """根据字段名智能推断并生成中文拟真数据。"""
        return self.cn_generator.generate(field_name)

    # ── JSON Schema → 数据 ──────────────────────────────────────

    def generate_from_schema(self, schema: Any) -> Any:
        """按 JSON Schema 生成数据。

        支持：``type``（object / array / string / integer / number / boolean / null）、
        ``format``（email / uri / uuid / date-time 等常见格式）、
        ``enum`` / ``const``、``items``、``properties``、``required``、
        ``minLength`` / ``maxLength`` / ``minimum`` / ``maximum`` 等约束。
        """
        if not isinstance(schema, dict):
            return None
        # enum / const 优先
        if "const" in schema:
            return schema["const"]
        if "enum" in schema and isinstance(schema["enum"], list) and schema["enum"]:
            return schema["enum"][0]

        t = schema.get("type")
        # 推断类型
        if t is None and "properties" in schema:
            t = "object"
        if t == "object":
            return self._gen_object(schema)
        if t == "array":
            return self._gen_array(schema)
        if t == "string":
            return self._gen_string(schema)
        if t == "integer":
            return self._gen_integer(schema)
        if t == "number":
            return self._gen_number(schema)
        if t == "boolean":
            return self.faker.boolean()
        if t == "null":
            return None
        # 未知：兜底
        return None

    def _gen_object(self, schema: dict[str, Any]) -> dict[str, Any]:
        props: dict[str, Any] = schema.get("properties", {}) or {}
        required = schema.get("required", []) or []
        out: dict[str, Any] = {}
        for name, sub in props.items():
            try:
                # 先尝试中文智能推断
                cn_val = self.cn_generator.generate(name)
                if cn_val is not None and sub.get("type") == "string":
                    out[name] = cn_val
                    continue
                val = self.generate_from_schema(sub)
            except Exception as exc:  # noqa: BLE001
                logger.debug("generate %s failed: %s", name, exc)
                val = None
            out[name] = val
        # 必填缺失时再次确认
        for r in required:
            out.setdefault(r, None)
        return out

    def _gen_array(self, schema: dict[str, Any]) -> list[Any]:
        items_schema = schema.get("items", {"type": "string"})
        min_items = int(schema.get("minItems", 1))
        max_items = int(schema.get("maxItems", max(min_items, 3)))
        size = self.faker.random_int(min=min_items, max=max(max_items, min_items))
        return [self.generate_from_schema(items_schema) for _ in range(size)]

    def _gen_string(self, schema: dict[str, Any]) -> str:
        # 字段名启发式
        fmt = (schema.get("format") or "").lower()
        if fmt in ("email",):
            return self.faker.email()
        if fmt in ("uri", "url"):
            return self.faker.url()
        if fmt in ("uuid",):
            return self.faker.uuid4()
        if fmt in ("date",):
            return self.faker.date()
        if fmt in ("date-time", "datetime"):
            return self.faker.iso8601()
        if fmt in ("ipv4",):
            return self.faker.ipv4()
        if fmt in ("ipv6",):
            return self.faker.ipv6()
        if fmt in ("hostname",):
            return self.faker.hostname()
        if fmt in ("phone",):
            return self.faker.phone_number()

        min_len = int(schema.get("minLength", 1))
        max_len = max(min_len, int(schema.get("maxLength", 16)))
        length = self.faker.random_int(min=min_len, max=max_len)
        if "pattern" in schema:
            return self.faker.pystr(min_chars=length, max_chars=length)
        return self.faker.pystr(min_chars=length, max_chars=length)

    def _gen_integer(self, schema: dict[str, Any]) -> int:
        minimum = int(schema.get("minimum", 0))
        maximum = max(minimum + 1, int(schema.get("maximum", 1000)))
        return self.faker.random_int(min=minimum, max=maximum)

    def _gen_number(self, schema: dict[str, Any]) -> float:
        minimum = float(schema.get("minimum", 0.0))
        maximum = max(minimum + 1.0, float(schema.get("maximum", 1000.0)))
        return self.faker.pyfloat(min_value=minimum, max_value=maximum)

    # ── 场景路由 ────────────────────────────────────────────────

    def add_scenario(self, scenario: MockScenario) -> None:
        """注册场景（按 ``priority`` 降序匹配，priority 相同时按 ``weight`` 降序）。"""
        self.scenarios.append(scenario)
        self.scenarios.sort(key=lambda s: (s.priority, s.weight), reverse=True)

    def route(
        self,
        api_id: int,
        request: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """按请求上下文选择场景，返回 ``{status, headers, body}``。

        ``request`` 形如 ``{"headers": {...}, "query": {...}, "body": {...}}``。
        """
        request = request or {}
        for sc in self.scenarios:
            if not sc.enabled:
                continue
            if self._match_scenario(sc, request):
                return {
                    "matched": sc.name,
                    "status": sc.response_status,
                    "headers": sc.response_headers,
                    "body": sc.response_body,
                }
        # 默认空
        return {"matched": None, "status": 200, "headers": {}, "body": None}

    def _match_scenario(self, sc: MockScenario, request: dict[str, Any]) -> bool:
        match = sc.match or {}
        for path, expected in match.items():
            actual = self._resolve_request_path(path, request)
            if isinstance(expected, list):
                if actual not in expected:
                    return False
            else:
                if actual != expected:
                    return False
        return True

    @staticmethod
    def _resolve_request_path(path: str, request: dict[str, Any]) -> Any:
        """解析 ``header.x-token`` / ``query.id`` / ``body.user.name``。"""
        if "." not in path:
            return None
        source, rest = path.split(".", 1)
        root = request.get(source, {}) or {}
        cur: Any = root
        for p in rest.split("."):
            if isinstance(cur, dict):
                cur = cur.get(p)
            else:
                return None
        return cur

    # ── 期望断言 ────────────────────────────────────────────────

    def validate_expectation(
        self,
        expectation: dict[str, Any],
        actual_request: dict[str, Any],
    ) -> bool:
        """断言请求是否符合期望。返回 True / False。"""
        return self._match_scenario(
            MockScenario(name="expectation", match=expectation),
            actual_request,
        )

    # ── 工具：与现有 MockService 对接 ─────────────────────────────

    def build_response_from_scenario(
        self,
        sc: MockScenario,
    ) -> dict[str, Any]:
        """当 scenario.response_body 为 schema dict 时自动生成数据。"""
        body = sc.response_body
        if isinstance(body, dict) and ("type" in body or "properties" in body):
            return self.generate_from_schema(body)
        return body


_default_engine: SmartMockEngine | None = None
_default_engine_lock = threading.Lock()


def get_default_engine() -> SmartMockEngine:
    global _default_engine
    if _default_engine is None:
        with _default_engine_lock:
            # 双检锁：第二个协程在获取锁后需再次检查
            if _default_engine is None:
                _default_engine = SmartMockEngine()
    return _default_engine
