import json
import logging
import uuid
from datetime import timedelta

from app.config import settings
from app.models.test_scene import TestScene
from app.models.test_report import TestReport

logger = logging.getLogger("seed")

DEMO_PROJECT_NAME = "电商平台演示项目"

_base_url = f"http://{settings.API_HOST}:{settings.API_PORT}"

# 注意：以下密码为演示数据，仅用于开发/测试环境，生产环境请勿使用明文密码


def _uid():
    """生成短 UUID 用作 node_id / edge_id"""
    return uuid.uuid4().hex[:12]


# ── 公共 Headers ──
COMMON_HEADERS = json.dumps([
    {"key": "Content-Type", "value": "application/json", "enabled": True}
], ensure_ascii=False)

AUTH_HEADER = json.dumps([
    {"key": "Content-Type", "value": "application/json", "enabled": True},
    {"key": "Authorization", "value": "Bearer {{token}}", "enabled": True},
], ensure_ascii=False)


def _body(content: str) -> str:
    """快捷创建 JSON body"""
    return json.dumps({"type": "json", "content": content}, ensure_ascii=False)


def _no_body() -> str:
    return json.dumps({"type": "none", "content": ""}, ensure_ascii=False)


def _assertions(*items) -> str:
    """快捷创建断言列表"""
    return json.dumps(items, ensure_ascii=False)


def _extract(*items) -> str:
    """快捷创建变量提取列表"""
    return json.dumps(items, ensure_ascii=False)


def _vars(**kwargs) -> str:
    """创建变量列表"""
    return json.dumps([{"key": k, "value": v, "enabled": True} for k, v in kwargs.items()], ensure_ascii=False)


# ── 响应示例快捷 ──
def _resp(code: int, message: str = "ok", data=None) -> str:
    obj = {"code": code, "message": message}
    if data is not None:
        obj["data"] = data
    return json.dumps(obj, ensure_ascii=False)


def _build_api_definitions(pid: int, cat_map: dict) -> list:
    """构建演示接口定义"""

    return [
        # ══════════ 用户与认证（2 个）══════════
        {
            "project_id": pid, "category_id": cat_map["用户与认证"],
            "name": "商户登录", "method": "POST", "path": "/auth/merchant/login",
            "description": "商户账号登录，返回访问令牌和刷新令牌。是后续所有需要鉴权接口的前置步骤",
            "headers": COMMON_HEADERS, "params": json.dumps([], ensure_ascii=False),
            "body": _body('{"username":"demo_merchant","password":"Demo@2026"}'),
            "auth_type": "none",
            "response_examples": _resp(200, "登录成功", data={
                "merchant_id": 10086, "username": "demo_merchant", "nickname": "演示商户",
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.demo_token_string_here",
                "token_type": "Bearer", "expires_in": 7200,
            }),
        },
        {
            "project_id": pid, "category_id": cat_map["用户与认证"],
            "name": "获取用户信息", "method": "GET", "path": "/auth/merchant/profile",
            "description": "获取当前登录商户的详细信息，需要携带有效的 Authorization 令牌",
            "headers": AUTH_HEADER, "params": json.dumps([], ensure_ascii=False),
            "body": _no_body(), "auth_type": "bearer",
            "response_examples": _resp(200, "获取成功", data={
                "merchant_id": 10086, "username": "demo_merchant", "nickname": "演示商户",
                "shop_name": "API Pilot 数码旗舰店", "email": "merchant@apipilot.dev", "points": 3280,
            }),
        },

        # ══════════ 商品管理（4 个）══════════
        {
            "project_id": pid, "category_id": cat_map["商品管理"],
            "name": "获取商品列表", "method": "GET", "path": "/api/v1/products",
            "description": "分页获取商品列表，支持按关键词搜索和目录筛选",
            "headers": COMMON_HEADERS,
            "params": json.dumps([
                {"key": "page", "value": "1", "enabled": True, "description": "页码"},
                {"key": "page_size", "value": "20", "enabled": True, "description": "每页数量"},
                {"key": "keyword", "value": "", "enabled": False, "description": "搜索关键词"},
                {"key": "category_id", "value": "", "enabled": False, "description": "接口目录ID筛选"},
            ], ensure_ascii=False),
            "body": _no_body(), "auth_type": "none",
            "response_examples": _resp(200, data={
                "list": [
                    {"id": 1, "name": "智能蓝牙耳机 Pro", "price": 299.00, "stock": 1200, "category": "数码", "status": "online"},
                    {"id": 2, "name": "4K 高清投影仪", "price": 2499.00, "stock": 320, "category": "数码", "status": "online"},
                    {"id": 3, "name": "机械键盘 87键 青轴", "price": 459.00, "stock": 850, "category": "数码", "status": "online"},
                ],
                "total": 3, "page": 1, "page_size": 20,
            }),
        },
        {
            "project_id": pid, "category_id": cat_map["商品管理"],
            "name": "获取商品详情", "method": "GET", "path": "/api/v1/products/{id}",
            "description": "根据商品 ID 获取商品详情，包含 SKU 规格和库存",
            "headers": COMMON_HEADERS, "params": json.dumps([], ensure_ascii=False),
            "body": _no_body(), "auth_type": "none",
            "response_examples": _resp(200, data={
                "id": 1, "name": "智能蓝牙耳机 Pro", "price": 299.00, "stock": 1200,
                "category": "数码", "description": "蓝牙 5.3 主动降噪，续航 30 小时",
                "skus": [{"sku_id": "S001", "spec": "黑色", "price": 299.00, "stock": 500}],
                "status": "online", "created_at": "2026-01-15T10:00:00Z",
            }),
        },
        {
            "project_id": pid, "category_id": cat_map["商品管理"],
            "name": "创建商品", "method": "POST", "path": "/api/v1/products",
            "description": "创建商品，展示 POST 请求与表单参数保存能力",
            "headers": AUTH_HEADER, "params": json.dumps([], ensure_ascii=False),
            "body": _body('{"name":"无线鼠标","price":99.00,"stock":{{$randomInt}},"category":"数码","sku_id":"{{$uuid}}"}'),
            "auth_type": "bearer",
            "response_examples": _resp(200, "创建成功", data={
                "id": 4, "name": "无线鼠标", "price": 99.00, "stock": 200, "status": "online",
            }),
        },

        # ══════════ 订单管理（3 个）══════════
        {
            "project_id": pid, "category_id": cat_map["订单管理"],
            "name": "创建订单", "method": "POST", "path": "/api/v1/orders",
            "description": "提交订单，返回订单号用于后续支付和物流查询",
            "headers": AUTH_HEADER, "params": json.dumps([], ensure_ascii=False),
            "body": _body('{"product_id":1,"quantity":2,"address_id":1,"receiver_name":"张三","receiver_phone":"13800138000","receiver_address":"浙江省杭州市西湖区","timestamp":"{{$timestamp}}"}'),
            "auth_type": "bearer",
            "response_examples": _resp(200, "订单创建成功", data={
                "order_no": "ORD202605130001", "total_amount": 598.00, "pay_amount": 598.00,
                "discount_amount": 0, "status": "pending_pay",
                "expire_time": "2026-05-13T16:52:44", "items_count": 2,
            }),
        },
        {
            "project_id": pid, "category_id": cat_map["订单管理"],
            "name": "订单详情", "method": "GET", "path": "/api/v1/orders/{id}",
            "description": "获取订单完整详情，包含商品明细、收货地址和物流信息",
            "headers": AUTH_HEADER, "params": json.dumps([], ensure_ascii=False),
            "body": _no_body(), "auth_type": "bearer",
            "response_examples": _resp(200, "获取成功", data={
                "id": 1001, "order_no": "ORD20260510001", "status": "paid", "total": 299.00,
                "items": [{"product_id": 1, "name": "智能蓝牙耳机 Pro", "quantity": 1, "price": 299.00}],
                "address": "北京市朝阳区建国路88号", "created_at": "2026-05-10T10:30:00",
            }),
        },
        {
            "project_id": pid, "category_id": cat_map["订单管理"],
            "name": "取消订单", "method": "DELETE", "path": "/api/v1/orders/{id}",
            "description": "取消未支付订单，展示 DELETE 请求与异常流程",
            "headers": AUTH_HEADER, "params": json.dumps([], ensure_ascii=False),
            "body": _no_body(), "auth_type": "bearer",
            "response_examples": _resp(200, "取消成功", data={"order_no": "ORD202605130001", "status": "cancelled"}),
        },

        # ══════════ 支付与退款（1 个）══════════
        {
            "project_id": pid, "category_id": cat_map["支付与退款"],
            "name": "创建支付", "method": "POST", "path": "/api/v1/payments",
            "description": "为订单创建支付单，展示 POST 支付流程",
            "headers": AUTH_HEADER, "params": json.dumps([], ensure_ascii=False),
            "body": _body('{"order_no":"ORD202605130001","payment_method":"alipay"}'),
            "auth_type": "bearer",
            "response_examples": _resp(200, "支付单创建成功", data={
                "payment_no": "PAY202605130001", "order_no": "ORD202605130001", "amount": 598.00, "status": "created",
            }),
        },
        {
            "project_id": pid, "category_id": cat_map["支付与退款"],
            "name": "申请退款", "method": "POST", "path": "/api/v1/refunds",
            "description": "对已支付订单申请退款，展示售后异常流程",
            "headers": AUTH_HEADER, "params": json.dumps([], ensure_ascii=False),
            "body": _body('{"order_no":"ORD20260510001","reason":"商品破损"}'),
            "auth_type": "bearer",
            "response_examples": _resp(200, "退款申请已提交", data={
                "refund_no": "REF202605130001", "order_no": "ORD20260510001", "status": "reviewing",
            }),
        },

        # ══════════ 物流配送（2 个）══════════
        {
            "project_id": pid, "category_id": cat_map["物流配送"],
            "name": "查询物流", "method": "GET", "path": "/api/v1/logistics/{order_no}",
            "description": "查询订单物流轨迹，展示 GET 查询能力",
            "headers": AUTH_HEADER, "params": json.dumps([], ensure_ascii=False),
            "body": _no_body(), "auth_type": "bearer",
            "response_examples": _resp(200, "获取成功", data={
                "order_no": "ORD20260510001", "carrier": "顺丰速运", "status": "in_transit",
                "trace": [{"time": "2026-05-10 12:00:00", "desc": "已揽收"}, {"time": "2026-05-10 18:00:00", "desc": "运输中"}],
            }),
        },
        {
            "project_id": pid, "category_id": cat_map["物流配送"],
            "name": "确认收货", "method": "POST", "path": "/api/v1/logistics/confirm",
            "description": "确认收货，展示最终态写操作",
            "headers": AUTH_HEADER, "params": json.dumps([], ensure_ascii=False),
            "body": _body('{"order_no":"ORD20260510001"}'),
            "auth_type": "bearer",
            "response_examples": _resp(200, "已确认收货", data={"order_no": "ORD20260510001", "status": "finished"}),
        },

        # ══════════ 数据统计（2 个）══════════
        {
            "project_id": pid, "category_id": cat_map["数据统计"],
            "name": "销售概览", "method": "GET", "path": "/api/v1/stats/overview",
            "description": "获取平台销售概览",
            "headers": AUTH_HEADER, "params": json.dumps([], ensure_ascii=False),
            "body": _no_body(), "auth_type": "bearer",
            "response_examples": _resp(200, "获取成功", data={
                "today_orders": 128, "today_revenue": 32880.50, "yesterday_revenue": 29700.00, "growth_rate": 10.7,
            }),
        },
        {
            "project_id": pid, "category_id": cat_map["数据统计"],
            "name": "热销商品", "method": "GET", "path": "/api/v1/stats/top-products",
            "description": "获取热销商品排行",
            "headers": AUTH_HEADER, "params": json.dumps([], ensure_ascii=False),
            "body": _no_body(), "auth_type": "bearer",
            "response_examples": _resp(200, "获取成功", data={
                "items": [
                    {"name": "智能蓝牙耳机 Pro", "sales": 2300},
                    {"name": "4K 高清投影仪", "sales": 180},
                ],
            }),
        },

        # ══════════ 商品管理 - 更新（PUT）══════════
        {
            "project_id": pid, "category_id": cat_map["商品管理"],
            "name": "更新商品", "method": "PUT", "path": "/api/v1/products/{id}",
            "description": "更新商品信息（名称、价格、库存等），展示 PUT 全量更新能力",
            "headers": AUTH_HEADER, "params": json.dumps([], ensure_ascii=False),
            "body": _body('{"name":"智能蓝牙耳机 Pro Max","price":349.00,"stock":1000,"description":"升级版蓝牙5.3"}'),
            "auth_type": "bearer",
            "response_examples": _resp(200, "更新成功", data={
                "id": 1, "name": "智能蓝牙耳机 Pro Max", "price": 349.00,
                "stock": 1000, "status": "online", "updated_at": "2026-06-11T10:00:00Z",
            }),
        },

        # ══════════ 订单管理 - 更新状态（PATCH）══════════
        {
            "project_id": pid, "category_id": cat_map["订单管理"],
            "name": "更新订单状态", "method": "PATCH", "path": "/api/v1/orders/{id}/status",
            "description": "部分更新订单状态（如确认发货），展示 PATCH 部分更新能力",
            "headers": AUTH_HEADER, "params": json.dumps([], ensure_ascii=False),
            "body": _body('{"status":"shipped","carrier":"顺丰速运","tracking_no":"SF1234567890"}'),
            "auth_type": "bearer",
            "response_examples": _resp(200, "状态已更新", data={
                "id": 1001, "order_no": "ORD20260510001", "status": "shipped",
                "carrier": "顺丰速运", "tracking_no": "SF1234567890",
            }),
        },
    ]


def _build_test_cases(pid: int, api_map: dict) -> list:
    """构建接口测试用例"""

    cases = []

    def add_case(api_name: str, name: str, description: str, priority: str, tags: str, assertions, extract_vars="[]"):
        cases.append({
            "project_id": pid,
            "api_id": api_map[api_name],
            "name": name,
            "description": description,
            "priority": priority,
            "status": "active",
            "tags": tags,
            "request_body": None,
            "assertions": _assertions(*assertions),
            "extract_vars": extract_vars,
        })

    # 登录链路
    add_case(
        "商户登录", "正确账号密码登录", "使用正确的商户凭据登录", "P0", "正常流程,认证",
        [
            {"type": "status", "operator": "eq", "value": 200, "passed": True},
            {"type": "json", "operator": "eq", "path": "$.code", "value": 0, "passed": True},
            {"type": "json", "operator": "is_not_null", "path": "$.data.access_token", "passed": True},
        ],
        _extract({"var_name": "token", "path": "$.data.access_token"}),
    )
    add_case(
        "商户登录", "错误密码登录", "使用错误密码应返回 401", "P0", "异常,认证",
        [
            {"type": "status", "operator": "eq", "value": 401, "passed": True},
            {"type": "json", "operator": "contains", "path": "$.message", "value": "密码错误", "passed": True},
        ],
    )
    add_case(
        "获取用户信息", "获取当前用户信息", "携带有效 Token 获取用户信息", "P0", "正常流程,认证",
        [
            {"type": "status", "operator": "eq", "value": 200, "passed": True},
            {"type": "json", "operator": "eq", "path": "$.data.username", "value": "demo_merchant", "passed": True},
        ],
    )

    # 商品链路
    add_case(
        "获取商品列表", "正常分页查询", "默认参数分页获取商品列表", "P0", "正常流程",
        [
            {"type": "status", "operator": "eq", "value": 200, "passed": True},
            {"type": "json", "operator": "gt", "path": "$.data.total", "value": 0, "passed": True},
        ],
    )
    add_case(
        "获取商品列表", "空结果集", "搜索不存在的关键词应返回空列表", "P2", "边界",
        [
            {"type": "status", "operator": "eq", "value": 200, "passed": True},
            {"type": "json", "operator": "eq", "path": "$.data.list.length()", "value": 0, "passed": True},
        ],
    )
    add_case(
        "获取商品详情", "获取指定商品详情", "查询 id=1 的商品详情", "P0", "正常流程",
        [
            {"type": "status", "operator": "eq", "value": 200, "passed": True},
            {"type": "json", "operator": "eq", "path": "$.data.id", "value": 1, "passed": True},
        ],
    )
    add_case(
        "获取商品详情", "商品不存在", "查询不存在的商品 ID 应返回 404", "P1", "异常,边界",
        [{"type": "status", "operator": "eq", "value": 404, "passed": True}],
    )
    add_case(
        "创建商品", "创建新商品", "创建新的商品信息", "P1", "正常流程",
        [
            {"type": "status", "operator": "eq", "value": 200, "passed": True},
            {"type": "json", "operator": "eq", "path": "$.data.status", "value": "online", "passed": True},
        ],
    )

    # 订单链路
    add_case(
        "创建订单", "正常创建订单", "携带 Token 提交订单", "P0", "正常流程,核心",
        [
            {"type": "status", "operator": "eq", "value": 200, "passed": True},
            {"type": "json", "operator": "eq", "path": "$.data.status", "value": "pending_pay", "passed": True},
        ],
        _extract({"var_name": "order_no", "path": "$.data.order_no"}),
    )
    add_case(
        "创建订单", "未登录创建订单", "不携带 Authorization 应返回 401", "P0", "异常,认证",
        [{"type": "status", "operator": "eq", "value": 401, "passed": True}],
    )
    add_case(
        "订单详情", "获取指定订单详情", "根据订单ID查询订单详细信息", "P0", "正常流程",
        [
            {"type": "status", "operator": "eq", "value": 200, "passed": True},
            {"type": "json", "operator": "is_not_null", "path": "$.data.order_no", "passed": True},
        ],
    )
    add_case(
        "取消订单", "取消未支付订单", "取消未支付订单并返回取消状态", "P1", "异常,流程",
        [
            {"type": "status", "operator": "eq", "value": 200, "passed": True},
            {"type": "json", "operator": "eq", "path": "$.data.status", "value": "cancelled", "passed": True},
        ],
    )

    # 支付/退款/物流/统计链路
    add_case(
        "创建支付", "创建支付单", "为订单创建支付单", "P1", "正常流程",
        [
            {"type": "status", "operator": "eq", "value": 200, "passed": True},
            {"type": "json", "operator": "is_not_null", "path": "$.data.payment_no", "passed": True},
        ],
    )
    add_case(
        "申请退款", "申请退款", "对已支付订单申请退款", "P1", "异常,售后",
        [{"type": "status", "operator": "eq", "value": 200, "passed": True}],
    )
    add_case(
        "查询物流", "查询物流轨迹", "查询订单物流轨迹", "P1", "正常流程",
        [
            {"type": "status", "operator": "eq", "value": 200, "passed": True},
            {"type": "json", "operator": "is_not_null", "path": "$.data.trace", "passed": True},
        ],
    )
    add_case(
        "确认收货", "确认收货", "确认订单收货并关闭流程", "P2", "正常流程",
        [
            {"type": "status", "operator": "eq", "value": 200, "passed": True},
            {"type": "json", "operator": "eq", "path": "$.data.status", "value": "finished", "passed": True},
        ],
    )

    # 数据统计链路
    add_case(
        "销售概览", "获取销售概览", "查询平台销售概览数据", "P2", "报表",
        [{"type": "status", "operator": "eq", "value": 200, "passed": True}],
    )
    add_case(
        "热销商品", "获取热销商品", "查询热销商品排行", "P2", "报表",
        [{"type": "status", "operator": "eq", "value": 200, "passed": True}],
    )

    # ── 补充：之前缺失的接口用例 ──
    add_case(
        "创建商品", "创建新商品", "创建新的商品信息并验证返回状态", "P1", "正常流程",
        [
            {"type": "status", "operator": "eq", "value": 200, "passed": True},
            {"type": "json", "operator": "eq", "path": "$.data.status", "value": "online", "passed": True},
        ],
    )
    add_case(
        "取消订单", "取消未支付订单", "取消未支付订单验证状态变更", "P1", "异常,流程",
        [
            {"type": "status", "operator": "eq", "value": 200, "passed": True},
            {"type": "json", "operator": "eq", "path": "$.data.status", "value": "cancelled", "passed": True},
        ],
    )

    # ── 新增：PUT / PATCH 接口用例 ──
    add_case(
        "更新商品", "更新商品价格和库存", "PUT 全量更新商品信息", "P1", "正常流程",
        [
            {"type": "status", "operator": "eq", "value": 200, "passed": True},
            {"type": "json", "operator": "eq", "path": "$.data.price", "value": 349.00, "passed": True},
            {"type": "json", "operator": "eq", "path": "$.data.stock", "value": 1000, "passed": True},
        ],
    )
    add_case(
        "更新订单状态", "确认发货", "PATCH 部分更新订单为已发货", "P1", "正常流程",
        [
            {"type": "status", "operator": "eq", "value": 200, "passed": True},
            {"type": "json", "operator": "eq", "path": "$.data.status", "value": "shipped", "passed": True},
            {"type": "json", "operator": "is_not_null", "path": "$.data.tracking_no", "passed": True},
        ],
    )

    return cases


def _build_environments(pid: int) -> list:
    """构建 3 个环境配置"""

    return [
        {
            "project_id": pid,
            "name": "开发环境 (Dev)",
            "services": json.dumps([
                {"name": "API 服务", "url": "{{base_url}}"},
                {"name": "认证服务", "url": "{{base_url}}/auth"},
                {"name": "文件服务", "url": "{{base_url}}/files"},
            ], ensure_ascii=False),
            "variables": _vars(base_url=_base_url, auth_url=f"{_base_url}/auth", timeout="5000", debug="true"),
            "headers": json.dumps([], ensure_ascii=False),
        },
        {
            "project_id": pid,
            "name": "测试环境 (Mock)",
            "services": json.dumps([
                {"name": "API 服务", "url": "{{base_url}}"},
            ], ensure_ascii=False),
            "variables": _vars(base_url=_base_url, mock_mode="true"),
            "headers": json.dumps([], ensure_ascii=False),
        },
        {
            "project_id": pid,
            "name": "预发布环境 (Staging)",
            "services": json.dumps([
                {"name": "API 服务", "url": "http://staging-api.example.com"},
                {"name": "认证服务", "url": "http://staging-auth.example.com"},
            ], ensure_ascii=False),
            "variables": _vars(base_url="http://staging-api.example.com", timeout="10000", debug="false"),
            "headers": json.dumps([], ensure_ascii=False),
        },
    ]


def _build_scenes(pid, scat_map, env_map, api_map):
    """构建场景测试（场景元数据 + 步骤 + 连线）

    返回 [(scene, steps, edges), ...]，用于一次性落库。
    """

    scenes = []

    # ── 场景1：用户下单全流程（5 步）──
    n1 = [_uid() for _ in range(5)]
    s1 = TestScene(
        project_id=pid, category_id=scat_map["端到端流程"],
        name="用户下单全流程",
        description="登录 → 浏览商品 → 查看详情 → 下单 → 查询订单。完整展示变量传递和业务链路",
        env_id=env_map["测试环境 (Mock)"],
        loop_count=1, thread_count=1, delay=0,
        on_failure="stop", on_error="stop",
        save_detail="all", save_vars=1,
        global_cookie=0, retry_count=0, save_cookie_to_global=0,
    )
    s1_steps = [
        {"node_id": n1[0], "node_type": "request", "label": "商户登录",
         "position_x": 80, "position_y": 200, "api_id": api_map["商户登录"], "sort_order": 0,
         "headers": None, "query_params": None,
         "request_body": '{"username":"demo_merchant","password":"Demo@2026"}',
         "assertions": _assertions(
             {"type": "status", "operator": "eq", "value": 200, "passed": True},
             {"type": "json", "operator": "eq", "path": "$.code", "value": 0, "passed": True},
             {"type": "json", "operator": "is_not_null", "path": "$.data.access_token", "passed": True},
         ),
         "extract_vars": _extract({"var_name": "token", "path": "$.data.access_token"}),
         "enabled": 1, "timeout": 30000, "retry_count": 0},
        {"node_id": n1[1], "node_type": "request", "label": "获取商品列表",
         "position_x": 260, "position_y": 200, "api_id": api_map["获取商品列表"], "sort_order": 1,
         "headers": AUTH_HEADER,
         "query_params": json.dumps([{"key": "page", "value": "1", "enabled": True}, {"key": "page_size", "value": "10", "enabled": True}]),
         "request_body": None,
         "assertions": _assertions(
             {"type": "status", "operator": "eq", "value": 200, "passed": True},
             {"type": "json", "operator": "gt", "path": "$.data.total", "value": 0, "passed": True},
         ),
         "extract_vars": "[]",
         "enabled": 1, "timeout": 30000, "retry_count": 0},
        {"node_id": n1[2], "node_type": "request", "label": "获取商品详情",
         "position_x": 440, "position_y": 200, "api_id": api_map["获取商品详情"], "sort_order": 2,
         "headers": AUTH_HEADER, "query_params": None,
         "request_body": None,
         "assertions": _assertions(
             {"type": "status", "operator": "eq", "value": 200, "passed": True},
             {"type": "json", "operator": "gt", "path": "$.data.price", "value": 0, "passed": True},
         ),
         "extract_vars": "[]",
         "enabled": 1, "timeout": 30000, "retry_count": 0},
        {"node_id": n1[3], "node_type": "request", "label": "创建订单",
         "position_x": 620, "position_y": 200, "api_id": api_map["创建订单"], "sort_order": 3,
         "headers": AUTH_HEADER, "query_params": None,
         "request_body": '{"product_id":1,"quantity":1,"address_id":1}',
         "assertions": _assertions(
             {"type": "status", "operator": "eq", "value": 200, "passed": True},
             {"type": "json", "operator": "eq", "path": "$.data.status", "value": "pending_pay", "passed": True},
         ),
         "extract_vars": _extract({"var_name": "order_no", "path": "$.data.order_no"}),
         "enabled": 1, "timeout": 30000, "retry_count": 0},
        {"node_id": n1[4], "node_type": "request", "label": "订单详情",
         "position_x": 800, "position_y": 200, "api_id": api_map["订单详情"], "sort_order": 4,
         "headers": AUTH_HEADER,
         "query_params": json.dumps([{"key": "order_no", "value": "{{order_no}}", "enabled": True}]),
         "request_body": None,
         "assertions": _assertions(
             {"type": "status", "operator": "eq", "value": 200, "passed": True},
             {"type": "json", "operator": "is_not_null", "path": "$.data.order_no", "passed": True},
         ),
         "extract_vars": "[]",
         "enabled": 1, "timeout": 30000, "retry_count": 0},
    ]
    s1_edges = [
        {"edge_id": _uid(), "source_node_id": n1[0], "target_node_id": n1[1], "label": ""},
        {"edge_id": _uid(), "source_node_id": n1[1], "target_node_id": n1[2], "label": ""},
        {"edge_id": _uid(), "source_node_id": n1[2], "target_node_id": n1[3], "label": ""},
        {"edge_id": _uid(), "source_node_id": n1[3], "target_node_id": n1[4], "label": ""},
    ]
    scenes.append((s1, s1_steps, s1_edges))

    # ── 场景2：下单异常链路（4 步）──
    n2 = [_uid() for _ in range(4)]
    s2 = TestScene(
        project_id=pid, category_id=scat_map["异常场景"],
        name="下单异常链路",
        description="错误密码登录 → 获取商品详情失败 → 创建订单未授权 → 取消订单异常流程",
        env_id=env_map["测试环境 (Mock)"],
        loop_count=1, thread_count=1, delay=0,
        on_failure="continue", on_error="continue",
        save_detail="failed", save_vars=1,
        global_cookie=0, retry_count=0, save_cookie_to_global=0,
    )
    s2_steps = [
        {"node_id": n2[0], "node_type": "request", "label": "错误密码登录", "position_x": 100, "position_y": 120, "api_id": api_map["商户登录"], "sort_order": 0,
         "headers": None, "query_params": None, "request_body": '{"username":"demo_merchant","password":"wrong"}',
         "assertions": _assertions({"type": "status", "operator": "eq", "value": 401, "passed": True}),
         "extract_vars": "[]", "enabled": 1, "timeout": 30000, "retry_count": 0},
        {"node_id": n2[1], "node_type": "request", "label": "商品不存在", "position_x": 300, "position_y": 120, "api_id": api_map["获取商品详情"], "sort_order": 1,
         "headers": COMMON_HEADERS, "query_params": None, "request_body": None,
         "assertions": _assertions({"type": "status", "operator": "eq", "value": 404, "passed": True}),
         "extract_vars": "[]", "enabled": 1, "timeout": 30000, "retry_count": 0},
        {"node_id": n2[2], "node_type": "request", "label": "未登录下单", "position_x": 500, "position_y": 120, "api_id": api_map["创建订单"], "sort_order": 2,
         "headers": COMMON_HEADERS, "query_params": None, "request_body": '{"product_id":1,"quantity":1,"address_id":1}',
         "assertions": _assertions({"type": "status", "operator": "eq", "value": 401, "passed": True}),
         "extract_vars": "[]", "enabled": 1, "timeout": 30000, "retry_count": 0},
        {"node_id": n2[3], "node_type": "request", "label": "取消订单", "position_x": 700, "position_y": 120, "api_id": api_map["取消订单"], "sort_order": 3,
         "headers": AUTH_HEADER, "query_params": None, "request_body": None,
         "assertions": _assertions({"type": "status", "operator": "eq", "value": 200, "passed": True}),
         "extract_vars": "[]", "enabled": 1, "timeout": 30000, "retry_count": 0},
    ]
    s2_edges = [
        {"edge_id": _uid(), "source_node_id": n2[0], "target_node_id": n2[1], "label": ""},
        {"edge_id": _uid(), "source_node_id": n2[1], "target_node_id": n2[2], "label": ""},
        {"edge_id": _uid(), "source_node_id": n2[2], "target_node_id": n2[3], "label": ""},
    ]
    scenes.append((s2, s2_steps, s2_edges))

    # ── 场景3：运营看板（3 步）──
    n3 = [_uid() for _ in range(3)]
    s3 = TestScene(
        project_id=pid, category_id=scat_map["功能验证"],
        name="运营看板快速验证",
        description="登录后查看销售概览、热销商品和创建支付单",
        env_id=env_map["开发环境 (Dev)"],
        loop_count=1, thread_count=1, delay=0,
        on_failure="stop", on_error="stop",
        save_detail="all", save_vars=0,
        global_cookie=0, retry_count=0, save_cookie_to_global=0,
    )
    s3_steps = [
        {"node_id": n3[0], "node_type": "request", "label": "销售概览", "position_x": 120, "position_y": 80, "api_id": api_map["销售概览"], "sort_order": 0,
         "headers": AUTH_HEADER, "query_params": None, "request_body": None,
         "assertions": _assertions({"type": "status", "operator": "eq", "value": 200, "passed": True}),
         "extract_vars": "[]", "enabled": 1, "timeout": 30000, "retry_count": 0},
        {"node_id": n3[1], "node_type": "request", "label": "热销商品", "position_x": 360, "position_y": 80, "api_id": api_map["热销商品"], "sort_order": 1,
         "headers": AUTH_HEADER, "query_params": None, "request_body": None,
         "assertions": _assertions({"type": "status", "operator": "eq", "value": 200, "passed": True}),
         "extract_vars": "[]", "enabled": 1, "timeout": 30000, "retry_count": 0},
        {"node_id": n3[2], "node_type": "request", "label": "创建支付", "position_x": 600, "position_y": 80, "api_id": api_map["创建支付"], "sort_order": 2,
         "headers": AUTH_HEADER, "query_params": None, "request_body": '{"order_no":"ORD202605130001","payment_method":"alipay"}',
         "assertions": _assertions({"type": "status", "operator": "eq", "value": 200, "passed": True}),
         "extract_vars": "[]", "enabled": 1, "timeout": 30000, "retry_count": 0},
    ]
    s3_edges = [
        {"edge_id": _uid(), "source_node_id": n3[0], "target_node_id": n3[1], "label": ""},
        {"edge_id": _uid(), "source_node_id": n3[1], "target_node_id": n3[2], "label": ""},
    ]
    scenes.append((s3, s3_steps, s3_edges))

    # ── 场景4：条件与循环 — 批量商品巡检（4 步，含循环）──
    n4 = [_uid() for _ in range(4)]
    s4 = TestScene(
        project_id=pid, category_id=scat_map["条件与循环"],
        name="批量商品巡检",
        description="登录 → 循环检查各商品库存（loop=3）→ 条件判断低库存告警。展示循环执行和条件分支能力",
        env_id=env_map["测试环境 (Mock)"],
        loop_count=3, thread_count=1, delay=200,
        on_failure="continue", on_error="continue",
        save_detail="all", save_vars=1,
        global_cookie=0, retry_count=0, save_cookie_to_global=0,
    )
    s4_steps = [
        {"node_id": n4[0], "node_type": "request", "label": "商户登录",
         "position_x": 80, "position_y": 200, "api_id": api_map["商户登录"], "sort_order": 0,
         "headers": None, "query_params": None,
         "request_body": '{"username":"demo_merchant","password":"Demo@2026"}',
         "assertions": _assertions(
             {"type": "status", "operator": "eq", "value": 200, "passed": True},
             {"type": "json", "operator": "is_not_null", "path": "$.data.access_token", "passed": True},
         ),
         "extract_vars": _extract({"var_name": "token", "path": "$.data.access_token"}),
         "enabled": 1, "timeout": 30000, "retry_count": 0},
        {"node_id": n4[1], "node_type": "request", "label": "获取商品列表",
         "position_x": 280, "position_y": 200, "api_id": api_map["获取商品列表"], "sort_order": 1,
         "headers": AUTH_HEADER,
         "query_params": json.dumps([{"key": "page", "value": "1", "enabled": True}, {"key": "page_size", "value": "10", "enabled": True}]),
         "request_body": None,
         "assertions": _assertions(
             {"type": "status", "operator": "eq", "value": 200, "passed": True},
             {"type": "json", "operator": "gt", "path": "$.data.total", "value": 0, "passed": True},
         ),
         "extract_vars": _extract({"var_name": "total_products", "path": "$.data.total"}),
         "enabled": 1, "timeout": 30000, "retry_count": 0,
         "condition_expression": "{{total_products}} > 0",
         "loop_count": 1,
         "loop_variable": "product_index",
         "wait_duration": 100},
        {"node_id": n4[2], "node_type": "request", "label": "获取商品详情(循环)",
         "position_x": 480, "position_y": 200, "api_id": api_map["获取商品详情"], "sort_order": 2,
         "headers": AUTH_HEADER, "query_params": None,
         "request_body": None,
         "assertions": _assertions(
             {"type": "status", "operator": "eq", "value": 200, "passed": True},
             {"type": "json", "operator": "gt", "path": "$.data.stock", "value": 0, "passed": True},
         ),
         "extract_vars": _extract({"var_name": "stock_level", "path": "$.data.stock"}),
         "enabled": 1, "timeout": 30000, "retry_count": 2,
         "loop_count": 3,
         "loop_variable": "product_id"},
        {"node_id": n4[3], "node_type": "condition", "label": "低库存告警?",
         "position_x": 680, "position_y": 200, "api_id": None, "test_case_id": None, "sort_order": 3,
         "headers": None, "query_params": None, "request_body": None,
         "assertions": _assertions(
             {"type": "expression", "operator": "lt", "value": "{{stock_level}}", "expected": "100", "passed": False},
         ),
         "extract_vars": "[]", "enabled": 1, "timeout": 5000, "retry_count": 0,
         "condition_expression": "{{stock_level}} < 100",
        },
    ]
    s4_edges = [
        {"edge_id": _uid(), "source_node_id": n4[0], "target_node_id": n4[1], "label": ""},
        {"edge_id": _uid(), "source_node_id": n4[1], "target_node_id": n4[2], "label": "循环巡检"},
        {"edge_id": _uid(), "source_node_id": n4[2], "target_node_id": n4[3], "label": "条件判断"},
    ]
    scenes.append((s4, s4_steps, s4_edges))

    return scenes


def _build_mock_rules(pid: int) -> list:
    """构建 Mock 规则 — 精简版：3 个核心 + 1 个兜底"""

    return [
        # 核心1：商户登录 Mock
        {"project_id": pid, "name": "商户登录 Mock", "enabled": 1, "priority": 10,
         "match_method": "POST", "match_path": "/auth/merchant/login",
         "response_status": 200, "response_headers": json.dumps({"Content-Type": "application/json"}),
         "response_body": json.dumps({"code": 200, "message": "登录成功", "data": {
             "merchant_id": 10086, "username": "demo_merchant", "nickname": "演示商户",
             "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.mock_token_static",
             "token_type": "Bearer", "expires_in": 7200,
         }}),
         "response_delay": 100},

        # 核心2：获取商品列表 Mock
        {"project_id": pid, "name": "获取商品列表 Mock", "enabled": 1, "priority": 10,
         "match_method": "GET", "match_path": "/api/v1/products",
         "response_status": 200, "response_headers": json.dumps({"Content-Type": "application/json"}),
         "response_body": json.dumps({"code": 200, "message": "获取成功", "data": {"list": [
             {"id": 1, "name": "智能蓝牙耳机 Pro", "price": 299.00, "stock": 1200, "category": "数码", "status": "online"},
             {"id": 2, "name": "4K 高清投影仪", "price": 2499.00, "stock": 320, "category": "数码", "status": "online"},
             {"id": 3, "name": "机械键盘 87键 青轴", "price": 459.00, "stock": 850, "category": "数码", "status": "online"},
         ], "total": 3, "page": 1, "page_size": 20}}),
         "response_delay": 50},

        # 核心3：创建订单 Mock
        {"project_id": pid, "name": "创建订单 Mock", "enabled": 1, "priority": 10,
         "match_method": "POST", "match_path": "/api/v1/orders",
         "response_status": 200, "response_headers": json.dumps({"Content-Type": "application/json"}),
         "response_body": json.dumps({"code": 200, "message": "订单创建成功", "data": {
             "order_no": "ORD202605150001", "total_amount": 598.00, "pay_amount": 598.00,
             "discount_amount": 0, "status": "pending_pay",
             "expire_time": "2026-05-15T16:52:44", "items_count": 2,
         }}),
         "response_delay": 200},

        # 兜底：未匹配任何 Mock 规则的请求返回 401
        {"project_id": pid, "name": "未授权访问兜底", "enabled": 1, "priority": -1,
         "match_method": "*", "match_path": "*",
         "response_status": 401, "response_headers": json.dumps({"Content-Type": "application/json"}),
         "response_body": json.dumps({"code": 401, "message": "未登录或登录已过期", "data": None}),
         "response_delay": 0},
    ]


def _build_reports(pid, admin_id, scene_map, env_map, api_map, now):
    """构建历史测试报告"""

    mock_env_id = env_map.get("测试环境 (Mock)", 2)
    dev_env_id = env_map.get("开发环境 (Dev)", mock_env_id)
    base_url = _base_url

    reports = []

    def make_report(name, scene_name, environment_id, status, pass_count, fail_count, total_count, duration, created_at, steps_data, tags=""):
        report = TestReport(
            project_id=pid,
            scene_id=scene_map.get(scene_name),
            environment_id=environment_id,
            name=name,
            status=status,
            pass_count=pass_count,
            fail_count=fail_count,
            skip_count=0,
            total_count=total_count,
            duration=duration,
            executor_id=admin_id,
            share_token=uuid.uuid4().hex,
            share_enabled=1,
            tags=tags,
            created_at=created_at,
        )
        return report, steps_data

    reports.append(make_report(
        "用户下单全流程 - 成功",
        "用户下单全流程",
        mock_env_id,
        "success",
        5, 0, 5, 2.35,
        now - timedelta(hours=1),
        [
            {"sort_order": 0, "status": "success", "duration": 155, "request_method": "POST",
             "request_url": f"{base_url}/auth/merchant/login",
             "request_body": '{"username":"demo_merchant","password":"Demo@2026"}',
             "response_status": 200,
             "response_body": '{"code":200,"data":{"access_token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.latest"},"message":"登录成功"}',
             "assertions": _assertions(
                 {"type": "status", "operator": "eq", "value": 200, "passed": True},
                 {"type": "json", "operator": "eq", "path": "$.code", "value": 0, "passed": True},
                 {"type": "json", "operator": "is_not_null", "path": "$.data.access_token", "passed": True},
             )},
            {"sort_order": 1, "status": "success", "duration": 78,
             "request_method": "GET", "request_url": f"{base_url}/api/v1/products?page=1&page_size=5",
             "request_body": None, "response_status": 200,
             "response_body": '{"code":200,"data":{"total":3,"list":[{"id":1}]}}',
             "assertions": _assertions({"type": "status", "operator": "eq", "value": 200, "passed": True})},
            {"sort_order": 2, "status": "success", "duration": 55,
             "request_method": "GET", "request_url": f"{base_url}/api/v1/products/1",
             "request_body": None, "response_status": 200,
             "response_body": '{"code":200,"data":{"id":1,"price":299.00}}',
             "assertions": _assertions({"type": "status", "operator": "eq", "value": 200, "passed": True})},
            {"sort_order": 3, "status": "success", "duration": 225,
             "request_method": "POST", "request_url": f"{base_url}/api/v1/orders",
             "request_body": '{"product_id":1,"quantity":2,"address_id":1}',
             "response_status": 200,
             "response_body": '{"code":200,"data":{"order_no":"ORD202605150001","status":"pending_pay"}}',
             "assertions": _assertions({"type": "status", "operator": "eq", "value": 200, "passed": True})},
            {"sort_order": 4, "status": "success", "duration": 88,
             "request_method": "GET", "request_url": f"{base_url}/api/v1/orders/ORD202605150001",
             "request_body": None, "response_status": 200,
             "response_body": '{"code":200,"data":{"order_no":"ORD202605150001","status":"pending_pay"}}',
             "assertions": _assertions({"type": "status", "operator": "eq", "value": 200, "passed": True})},
        ],
        tags="正常流程",
    ))

    reports.append(make_report(
        "用户下单全流程 - 失败复盘",
        "用户下单全流程",
        mock_env_id,
        "failed",
        3, 2, 5, 3.15,
        now - timedelta(hours=25),
        [
            {"sort_order": 0, "status": "success", "duration": 180, "request_method": "POST",
             "request_url": f"{base_url}/auth/merchant/login",
             "request_body": '{"username":"demo_merchant","password":"Demo@2026"}',
             "response_status": 200,
             "response_body": '{"code":200,"data":{"access_token":"eyJ...older"},"message":"登录成功"}',
             "assertions": _assertions({"type": "status", "operator": "eq", "value": 200, "passed": True})},
            {"sort_order": 1, "status": "success", "duration": 230,
             "request_method": "GET", "request_url": f"{base_url}/api/v1/products?page=1&page_size=5",
             "request_body": None, "response_status": 200,
             "response_body": '{"code":200,"data":{"total":3}}',
             "assertions": _assertions({"type": "status", "operator": "eq", "value": 200, "passed": True})},
            {"sort_order": 2, "status": "failed", "duration": 195,
             "request_method": "GET", "request_url": f"{base_url}/api/v1/products/1",
             "request_body": None, "response_status": 404,
             "response_body": '{"code":404,"message":"Not Found"}',
             "assertions": _assertions({"type": "status", "operator": "eq", "value": 200, "passed": False}),
             "error_message": "预期状态码 200 但实际为 404：Mock 环境未配置商品详情接口"},
            {"sort_order": 3, "status": "success", "duration": 280,
             "request_method": "POST", "request_url": f"{base_url}/api/v1/orders",
             "request_body": '{"product_id":1,"quantity":2,"address_id":1}',
             "response_status": 200,
             "response_body": '{"code":200,"data":{"order_no":"ORD202605140001","status":"pending_pay"}}',
             "assertions": _assertions({"type": "status", "operator": "eq", "value": 200, "passed": True})},
            {"sort_order": 4, "status": "failed", "duration": 165,
             "request_method": "GET", "request_url": f"{base_url}/api/v1/orders/ORD202605140001",
             "request_body": None, "response_status": 404,
             "response_body": '{"code":404,"message":"Not Found"}',
             "assertions": _assertions({"type": "status", "operator": "eq", "value": 200, "passed": False}),
             "error_message": "预期状态码 200 但实际为 404：Mock 环境未配置订单详情接口"},
        ],
        tags="异常,复盘",
    ))

    reports.append(make_report(
        "运营看板快速验证",
        "运营看板快速验证",
        dev_env_id,
        "success",
        3, 0, 3, 1.42,
        now - timedelta(hours=6),
        [
            {"sort_order": 0, "status": "success", "duration": 110, "request_method": "GET", "request_url": f"{base_url}/api/v1/stats/overview",
             "request_body": None, "response_status": 200, "response_body": '{"code":200,"data":{"today_orders":128}}',
             "assertions": _assertions({"type": "status", "operator": "eq", "value": 200, "passed": True})},
            {"sort_order": 1, "status": "success", "duration": 125, "request_method": "GET", "request_url": f"{base_url}/api/v1/stats/top-products",
             "request_body": None, "response_status": 200, "response_body": '{"code":200,"data":{"items":[{"name":"智能蓝牙耳机 Pro","sales":2300}]}}',
             "assertions": _assertions({"type": "status", "operator": "eq", "value": 200, "passed": True})},
            {"sort_order": 2, "status": "success", "duration": 165, "request_method": "POST", "request_url": f"{base_url}/api/v1/payments",
             "request_body": '{"order_no":"ORD202605130001","payment_method":"alipay"}', "response_status": 200,
             "response_body": '{"code":200,"data":{"payment_no":"PAY202605130001","status":"created"}}',
             "assertions": _assertions({"type": "status", "operator": "eq", "value": 200, "passed": True})},
        ],
        tags="报表,正常流程",
    ))

    reports.append(make_report(
        "物流配送确认",
        "运营看板快速验证",
        mock_env_id,
        "success",
        2, 0, 2, 0.86,
        now - timedelta(days=1, hours=2),
        [
            {"sort_order": 0, "status": "success", "duration": 96, "request_method": "GET", "request_url": f"{base_url}/api/v1/logistics/ORD20260510001",
             "request_body": None, "response_status": 200, "response_body": '{"code":200,"data":{"status":"in_transit"}}',
             "assertions": _assertions({"type": "status", "operator": "eq", "value": 200, "passed": True})},
            {"sort_order": 1, "status": "success", "duration": 74, "request_method": "POST", "request_url": f"{base_url}/api/v1/logistics/confirm",
             "request_body": '{"order_no":"ORD20260510001"}', "response_status": 200, "response_body": '{"code":200,"data":{"status":"finished"}}',
             "assertions": _assertions({"type": "status", "operator": "eq", "value": 200, "passed": True})},
        ],
        tags="物流,正常流程",
    ))

    # ── 报告5：退款流程 ──
    reports.append(make_report(
        "退款申请流程",
        "下单异常链路",
        mock_env_id,
        "success",
        3, 0, 3, 1.88,
        now - timedelta(days=2, hours=5),
        [
            {"sort_order": 0, "status": "success", "duration": 160, "request_method": "POST",
             "request_url": f"{base_url}/auth/merchant/login",
             "request_body": '{"username":"demo_merchant","password":"Demo@2026"}',
             "response_status": 200,
             "response_body": '{"code":200,"data":{"access_token":"eyJ...token"}}',
             "assertions": _assertions({"type": "status", "operator": "eq", "value": 200, "passed": True})},
            {"sort_order": 1, "status": "success", "duration": 210, "request_method": "POST",
             "request_url": f"{base_url}/api/v1/orders",
             "request_body": '{"product_id":1,"quantity":1,"address_id":1}',
             "response_status": 200,
             "response_body": '{"code":200,"data":{"order_no":"ORD20260509001","status":"paid"}}',
             "assertions": _assertions({"type": "status", "operator": "eq", "value": 200, "passed": True})},
            {"sort_order": 2, "status": "success", "duration": 310, "request_method": "POST",
             "request_url": f"{base_url}/api/v1/refunds",
             "request_body": '{"order_no":"ORD20260509001","reason":"质量问题"}',
             "response_status": 200,
             "response_body": '{"code":200,"data":{"refund_no":"REF20260509001","status":"reviewing"}}',
             "assertions": _assertions({"type": "status", "operator": "eq", "value": 200, "passed": True})},
        ],
        tags="售后,正常流程",
    ))

    # ── 报告6：条件与循环场景 ──
    reports.append(make_report(
        "批量商品巡检",
        "批量商品巡检",
        dev_env_id,
        "success",
        4, 0, 4, 3.52,
        now - timedelta(hours=3),
        [
            {"sort_order": 0, "status": "success", "duration": 155, "request_method": "POST",
             "request_url": f"{base_url}/auth/merchant/login",
             "request_body": '{"username":"demo_merchant","password":"Demo@2026"}',
             "response_status": 200,
             "response_body": '{"code":200,"data":{"access_token":"eyJ...loop"}}',
             "assertions": _assertions({"type": "status", "operator": "eq", "value": 200, "passed": True})},
            {"sort_order": 1, "status": "success", "duration": 88, "request_method": "GET",
             "request_url": f"{base_url}/api/v1/products?page=1&page_size=10",
             "request_body": None, "response_status": 200,
             "response_body": '{"code":200,"data":{"total":3,"list":[{"id":1},{"id":2},{"id":3}]}}',
             "assertions": _assertions({"type": "status", "operator": "eq", "value": 200, "passed": True})},
            {"sort_order": 2, "status": "success", "duration": 320, "request_method": "GET",
             "request_url": f"{base_url}/api/v1/products/1",
             "request_body": None, "response_status": 200,
             "response_body": '{"code":200,"data":{"id":1,"stock":1200}}',
             "assertions": _assertions({"type": "status", "operator": "eq", "value": 200, "passed": True})},
            {"sort_order": 3, "status": "success", "duration": 45, "request_method": "condition",
             "request_url": "", "request_body": None, "response_status": 0,
             "response_body": "",
             "assertions": _assertions({"type": "expression", "operator": "lt", "value": "1200", "expected": "100", "passed": False})},
        ],
        tags="循环,条件,巡检",
    ))

    return reports
