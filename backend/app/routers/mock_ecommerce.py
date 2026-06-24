# Mock 电商接口 — 设计为公开测试端点（无用户隐私数据）。
# 所有数据均为硬编码模拟商品/订单，不涉及真实业务。
# 生产环境通过 main.py 中环境变量 API_PILOT_MOCK_ENABLED 控制是否注册此路由。
import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter
import asyncio
from app.utils.response import success, fail

router = APIRouter(tags=["电商 Mock"])

# ── 已支付订单记录（防重复支付）──
PAID_ORDERS: dict[int, bool] = {}
PAY_LOCK = asyncio.Lock()
_order_counter = [0]  # 订单自增计数器

# ── 商品数据 ──
PRODUCTS = [
    {"id": 1, "name": "智能蓝牙耳机 Pro", "price": 299.00, "stock": 1200, "category_id": 1,
     "skus": [{"sku_id": "S001", "spec": "黑色", "price": 299.00, "stock": 500},
              {"sku_id": "S002", "spec": "白色", "price": 299.00, "stock": 400},
              {"sku_id": "S003", "spec": "蓝色", "price": 319.00, "stock": 300}],
     "specs": {"品牌": "TechSound", "连接": "蓝牙 5.3", "续航": "30h"},
     "description": "蓝牙 5.3 主动降噪，续航 30 小时",
     "images": ["https://example.com/images/1.jpg"], "status": "online", "created_at": "2026-01-15T10:00:00"},
    {"id": 2, "name": "4K 高清投影仪", "price": 2499.00, "stock": 320, "category_id": 1,
     "skus": [{"sku_id": "S004", "spec": "标准版", "price": 2499.00, "stock": 200},
              {"sku_id": "S005", "spec": "尊享版", "price": 2999.00, "stock": 120}],
     "specs": {"分辨率": "3840x2160", "亮度": "3000 ANSI", "系统": "Android 12"},
     "description": "4K 超高清家庭影院投影仪",
     "images": ["https://example.com/images/2.jpg"], "status": "online", "created_at": "2026-02-01T14:00:00"},
    {"id": 3, "name": "机械键盘 87键 青轴", "price": 459.00, "stock": 850, "category_id": 1,
     "skus": [{"sku_id": "S006", "spec": "黑色青轴", "price": 459.00, "stock": 400},
              {"sku_id": "S007", "spec": "白色红轴", "price": 479.00, "stock": 300},
              {"sku_id": "S008", "spec": "RGB 茶轴", "price": 529.00, "stock": 150}],
     "specs": {"布局": "87键", "轴体": "Cherry MX", "背光": "RGB"},
     "description": "Cherry MX 青轴，RGB 全彩背光",
     "images": ["https://example.com/images/3.jpg"], "status": "online", "created_at": "2026-01-20T09:00:00"},
    {"id": 4, "name": "USB-C 扩展坞 12合1", "price": 189.00, "stock": 2000, "category_id": 1,
     "skus": [{"sku_id": "S009", "spec": "HDMI版", "price": 189.00, "stock": 1000},
              {"sku_id": "S010", "spec": "DP版", "price": 219.00, "stock": 1000}],
     "specs": {"接口": "HDMI+USB3.0+PD", "供电": "100W PD"},
     "description": "12 合 1 高速扩展坞，100W PD 充电",
     "images": ["https://example.com/images/4.jpg"], "status": "online", "created_at": "2026-03-01T11:00:00"},
    {"id": 5, "name": "无线充电器 15W 快充", "price": 79.00, "stock": 5000, "category_id": 1,
     "skus": [{"sku_id": "S011", "spec": "黑色", "price": 79.00, "stock": 2000},
              {"sku_id": "S012", "spec": "白色", "price": 79.00, "stock": 2000},
              {"sku_id": "S013", "spec": "车载版", "price": 99.00, "stock": 1000}],
     "specs": {"功率": "15W", "协议": "Qi"},
     "description": "Qi 协议 15W 快充，兼容主流手机",
     "status": "online", "created_at": "2026-03-10T08:00:00"},
]

ORDERS = [
    {"id": 1001, "user_id": 1, "status": "paid", "total": 299.00,
     "items": [{"product_id": 1, "name": "智能蓝牙耳机 Pro", "quantity": 1, "price": 299.00}],
     "address": "北京市朝阳区建国路88号", "express": "SF1234567890", "created_at": "2026-05-10T10:30:00"},
    {"id": 1002, "user_id": 1, "status": "shipped", "total": 2958.00,
     "items": [{"product_id": 2, "name": "4K 高清投影仪", "quantity": 1, "price": 2499.00},
               {"product_id": 4, "name": "USB-C 扩展坞 12合1", "quantity": 1, "price": 189.00},
               {"product_id": 5, "name": "无线充电器 15W 快充", "quantity": 2, "price": 79.00}],
     "address": "上海市浦东新区张江高科技园区", "express": "SF9876543210", "created_at": "2026-05-11T14:00:00"},
    {"id": 1003, "user_id": 1, "status": "pending", "total": 459.00,
     "items": [{"product_id": 3, "name": "机械键盘 87键 青轴", "quantity": 1, "price": 459.00}],
     "address": "广东省深圳市南山区科技园", "express": "", "created_at": "2026-05-12T09:00:00"},
]

TRACKING = {
    "SF1234567890": [
        {"time": "2026-05-10 14:00", "desc": "已揽收"},
        {"time": "2026-05-10 22:00", "desc": "已到达北京分拣中心"},
        {"time": "2026-05-11 08:00", "desc": "已发出，正在派送"},
        {"time": "2026-05-11 14:30", "desc": "已签收"},
    ],
    "SF9876543210": [
        {"time": "2026-05-11 16:00", "desc": "已揽收"},
        {"time": "2026-05-12 02:00", "desc": "已到达上海分拣中心"},
        {"time": "2026-05-12 09:00", "desc": "正在派送中"},
    ],
}

# ════════════════════════════════════════
# 商品接口
# ════════════════════════════════════════

@router.get("/api/v1/products")
async def list_products(page: int = 1, page_size: int = 10, category_id: int = None, keyword: str = ""):
    filtered = PRODUCTS
    if category_id:
        filtered = [p for p in PRODUCTS if p["category_id"] == category_id]
    if keyword:
        filtered = [p for p in filtered if keyword.lower() in p["name"].lower()]
    start = (page - 1) * page_size
    end = start + page_size
    return {"code": 200, "data": {"items": filtered[start:end], "total": len(filtered), "page": page, "page_size": page_size}}


@router.get("/api/v1/products/{product_id}")
async def get_product(product_id: int):
    for p in PRODUCTS:
        if p["id"] == product_id:
            return {"code": 200, "data": p}
    return {"code": 404, "message": "商品不存在", "data": None}


@router.post("/api/v1/products")
async def create_product():
    return success({"id": 6, "name": "新建商品", "status": "draft"}, message="创建成功")


@router.put("/api/v1/products/{product_id}")
async def update_product(product_id: int):
    return {"code": 200, "data": {"id": product_id, "status": "updated"}, "message": "更新成功"}


@router.delete("/api/v1/products/{product_id}")
async def delete_product(product_id: int):
    return {"code": 200, "message": "下架成功", "data": None}


# ════════════════════════════════════════
# 订单接口
# ════════════════════════════════════════

@router.get("/api/v1/orders")
async def list_orders(status: str = None, page: int = 1, page_size: int = 10):
    filtered = ORDERS
    if status:
        filtered = [o for o in ORDERS if o["status"] == status]
    start = (page - 1) * page_size
    end = start + page_size
    return {"code": 0, "message": "获取成功", "data": {
        "items": filtered[start:end], "total": len(filtered), "page": page, "page_size": page_size}}


@router.get("/api/v1/orders/{order_id}")
async def get_order(order_id: int):
    for o in ORDERS:
        if o["id"] == order_id:
            return {"code": 0, "message": "获取成功", "data": o}
    return {"code": 404, "message": "订单不存在", "data": None}


@router.post("/api/v1/orders")
async def create_order(body: dict = {}):
    _order_counter[0] += 1
    order_id = _order_counter[0]
    order_no = f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:4].upper()}"
    return {
        "code": 0, "message": "订单创建成功",
        "data": {
            "id": order_id, "order_no": order_no, "total_amount": 598.00, "pay_amount": 598.00,
            "discount_amount": 0, "status": "pending_pay",
            "expire_time": (datetime.now() + timedelta(minutes=30)).isoformat(),
            "items_count": 2,
        },
    }


@router.put("/api/v1/orders/{order_id}/pay")
async def pay_order(order_id: int):
    async with PAY_LOCK:
        if PAID_ORDERS.get(order_id):
            return fail(code=400, message="该订单已支付，不可重复支付")
        PAID_ORDERS[order_id] = True
    return {
        "code": 0, "message": "支付成功",
        "data": {
            "order_no": f"ORD20260513{order_id:04d}",
            "trade_no": f"TP{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6]}",
            "status": "paid", "paid_at": datetime.now().isoformat(),
            "pay_channel": "alipay",
        },
    }


@router.post("/api/v1/orders/{order_id}/refund")
async def refund_order(order_id: int):
    return {
        "code": 0, "message": "退款申请已提交",
        "data": {"refund_id": f"RF{uuid.uuid4().hex[:12]}", "status": "processing", "amount": 299.00},
    }


@router.put("/api/v1/orders/{order_id}/address")
async def update_order_address(order_id: int):
    return {
        "code": 0, "message": "地址修改成功",
        "data": {"order_id": order_id, "status": "updated"},
    }


# ════════════════════════════════════════
# 支付接口
# ════════════════════════════════════════

@router.post("/api/v1/payments/create")
async def create_payment(body: dict = {}):
    order_no = body.get("order_no", "ORD202605130001")
    return {
        "code": 0, "message": "支付单创建成功",
        "data": {
            "pay_id": f"PAY{uuid.uuid4().hex[:12]}",
            "trade_no": f"TP{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6]}",
            "order_no": order_no, "amount": 598.00, "status": "pending",
            "qr_code_url": "https://pay.example.com/qr/abc123",
        },
    }


# ════════════════════════════════════════
# 物流接口
# ════════════════════════════════════════

@router.get("/api/v1/shipping/tracks")
async def get_shipping_tracks(order_no: str = ""):
    return {
        "code": 0, "message": "获取成功",
        "data": {
            "order_no": order_no or "ORD202605130001",
            "logistics_company": "顺丰速运",
            "tracking_no": "SF1234567890123",
            "tracks": [
                {"time": "2026-05-13 20:15:00", "status": "已签收", "location": "杭州西湖区菜鸟驿站"},
                {"time": "2026-05-13 08:30:00", "status": "派送中", "location": "杭州转运中心"},
                {"time": "2026-05-12 22:00:00", "status": "运输中", "location": "上海分拨中心"},
                {"time": "2026-05-12 14:00:00", "status": "已揽收", "location": "上海市浦东新区"},
            ],
        },
    }


# ════════════════════════════════════════
# 商户认证
# ════════════════════════════════════════

@router.post("/auth/merchant/login")
async def merchant_login():
    return {
        "code": 0, "message": "登录成功",
        "data": {
            "merchant_id": 10086,
            "username": "demo_merchant",
            "nickname": "演示商户",
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.demo_token_" + uuid.uuid4().hex[:8],
            "token_type": "Bearer",
            "expires_in": 7200,
        },
    }


@router.get("/auth/merchant/profile")
async def merchant_profile():
    return {
        "code": 0, "message": "获取成功",
        "data": {
            "merchant_id": 10086, "username": "demo_merchant",
            "nickname": "演示商户", "shop_name": "API Pilot 数码旗舰店",
            "email": "merchant@apipilot.dev", "points": 3280,
        },
    }


@router.put("/auth/merchant/password")
async def merchant_password():
    return {"code": 0, "message": "密码修改成功", "data": None}


@router.post("/auth/merchant/refresh")
async def merchant_refresh():
    return {
        "code": 0, "message": "刷新成功",
        "data": {"access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.new_token_" + uuid.uuid4().hex[:8], "expires_in": 7200},
    }


# ════════════════════════════════════════
# 数据统计
# ════════════════════════════════════════

@router.get("/api/v1/stats/dashboard")
async def stats_dashboard(date_range: str = "7d"):
    return {
        "code": 0, "message": "获取成功",
        "data": {
            "order_total": 1286, "order_growth": "+12.3%",
            "revenue": 458920.00, "revenue_growth": "+8.7%",
            "product_count": 256, "product_count_growth": "+5.2%",
            "user_count": 3842, "user_count_growth": "+15.1%",
            "top_products": [
                {"name": "iPhone 15 Pro", "sales": 320, "revenue": 2879680},
                {"name": "MacBook Pro 14寸", "sales": 156, "revenue": 2339844},
            ],
        },
    }
