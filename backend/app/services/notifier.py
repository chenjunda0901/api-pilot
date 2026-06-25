"""5 渠道通知服务。

提供 ``FeishuNotifier`` / ``DingTalkNotifier`` / ``WeChatNotifier`` / ``SlackNotifier``
/ ``EmailNotifier`` / ``CustomWebhookNotifier``，统一 ``async send(payload, template_vars) -> SendResult``。
所有失败均不抛异常，只在 ``SendResult.error`` 写入错误。

典型用法::

    notifier = FeishuNotifier(url="https://open.feishu.cn/...")
    result = await notifier.send({"title": "Hi"}, {"name": "API Pilot"})
    assert result.success
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import time
from dataclasses import dataclass, field
from email.message import EmailMessage
from typing import Any, ClassVar

logger = logging.getLogger("service.notifier")


# ── 数据结构 ────────────────────────────────────────────────────────────


@dataclass
class SendResult:
    """发送结果。"""

    success: bool
    channel: str
    status_code: int = 0
    response: str = ""
    error: str = ""
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class NotifierError(Exception):
    """通知器配置或调用错误。"""


# ── 抽象基类 ────────────────────────────────────────────────────────────


class BaseNotifier:
    """所有渠道的抽象基类。"""

    channel: ClassVar[str] = "base"
    DEFAULT_TIMEOUT: ClassVar[float] = 10.0

    def __init__(self, url: str = "", secret: str | None = None, **kwargs: Any) -> None:
        self.url = url
        self.secret = secret
        self.extra: dict[str, Any] = kwargs

    async def send(
        self, payload: dict[str, Any], template_vars: dict[str, Any]
    ) -> SendResult:
        """派发方法：子类一般只重写 ``_build_request``。"""
        start = time.perf_counter()
        try:
            method, url, headers, body = self._build_request(payload, template_vars)
        except NotifierError as exc:
            return self._fail(str(exc), start)
        except Exception as exc:  # noqa: BLE001
            return self._fail(f"build request failed: {exc}", start)

        try:
            import httpx
        except ImportError:  # pragma: no cover
            return self._fail("未安装 httpx", start)

        try:
            async with httpx.AsyncClient(timeout=self.DEFAULT_TIMEOUT) as client:
                resp = await client.request(method, url, headers=headers, content=body)
        except asyncio.TimeoutError:
            return self._fail("请求超时", start)
        except Exception as exc:  # noqa: BLE001
            return self._fail(f"请求失败: {exc}", start)

        elapsed = (time.perf_counter() - start) * 1000
        ok = 200 <= resp.status_code < 300
        return SendResult(
            success=ok,
            channel=self.channel,
            status_code=resp.status_code,
            response=resp.text[:1000],
            error="" if ok else f"HTTP {resp.status_code}",
            duration_ms=elapsed,
        )

    def _build_request(
        self,
        payload: dict[str, Any],
        template_vars: dict[str, Any],
    ) -> tuple[str, str, dict[str, str], str | bytes]:
        raise NotImplementedError

    def _fail(self, msg: str, start: float) -> SendResult:
        return SendResult(
            success=False,
            channel=self.channel,
            error=msg,
            duration_ms=(time.perf_counter() - start) * 1000,
        )


# ── 飞书 ────────────────────────────────────────────────────────────────


class FeishuNotifier(BaseNotifier):
    """飞书自定义机器人。

    支持签名校验（secret 非空时启用）。
    """

    channel = "feishu"

    def _build_request(
        self,
        payload: dict[str, Any],
        template_vars: dict[str, Any],
    ) -> tuple[str, str, dict[str, str], str]:
        if not self.url:
            raise NotifierError("FeishuNotifier.url 不能为空")
        body: dict[str, Any] = dict(payload)
        # 签名
        if self.secret:
            ts = str(int(time.time()))
            string_to_sign = f"{ts}\n{self.secret}"
            digest = hmac.new(
                string_to_sign.encode("utf-8"), b"", hashlib.sha256
            ).digest()
            body["timestamp"] = ts
            body["sign"] = base64.b64encode(digest).decode("utf-8")
        return (
            "POST",
            self.url,
            {"Content-Type": "application/json"},
            json.dumps(body, ensure_ascii=False),
        )


# ── 钉钉 ────────────────────────────────────────────────────────────────


class DingTalkNotifier(BaseNotifier):
    """钉钉自定义机器人（加签 + 关键词可选）。"""

    channel = "dingtalk"

    def _build_request(
        self,
        payload: dict[str, Any],
        template_vars: dict[str, Any],
    ) -> tuple[str, str, dict[str, str], str]:
        if not self.url:
            raise NotifierError("DingTalkNotifier.url 不能为空")
        body = dict(payload)
        if self.secret:
            ts = str(round(time.time() * 1000))
            string_to_sign = f"{ts}\n{self.secret}"
            digest = hmac.new(
                self.secret.encode("utf-8"),
                string_to_sign.encode("utf-8"),
                hashlib.sha256,
            ).digest()
            b64_sig = base64.b64encode(digest).decode("utf-8")
            import urllib.parse

            body["timestamp"] = ts
            body["sign"] = urllib.parse.quote_plus(b64_sig)
        return (
            "POST",
            self.url,
            {"Content-Type": "application/json"},
            json.dumps(body, ensure_ascii=False),
        )


# ── 企业微信 ────────────────────────────────────────────────────────────


class WeChatNotifier(BaseNotifier):
    """企业微信群机器人（markdown 类型）。"""

    channel = "wechat"

    def _build_request(
        self,
        payload: dict[str, Any],
        template_vars: dict[str, Any],
    ) -> tuple[str, str, dict[str, str], str]:
        if not self.url:
            raise NotifierError("WeChatNotifier.url 不能为空")
        body = {"msgtype": payload.get("msgtype", "markdown")}
        if body["msgtype"] == "markdown":
            body["markdown"] = payload.get(
                "markdown", {"content": payload.get("content", "")}
            )
        else:
            body["text"] = payload.get("text", {"content": payload.get("content", "")})
        return (
            "POST",
            self.url,
            {"Content-Type": "application/json"},
            json.dumps(body, ensure_ascii=False),
        )


# ── Slack ───────────────────────────────────────────────────────────────


class SlackNotifier(BaseNotifier):
    """Slack Incoming Webhook。"""

    channel = "slack"

    def _build_request(
        self,
        payload: dict[str, Any],
        template_vars: dict[str, Any],
    ) -> tuple[str, str, dict[str, str], str]:
        if not self.url:
            raise NotifierError("SlackNotifier.url 不能为空")
        return (
            "POST",
            self.url,
            {"Content-Type": "application/json"},
            json.dumps(payload, ensure_ascii=False),
        )


# ── 自定义 Webhook ──────────────────────────────────────────────────────


class CustomWebhookNotifier(BaseNotifier):
    """通用 Webhook（透传 payload）。"""

    channel = "custom"

    def _build_request(
        self,
        payload: dict[str, Any],
        template_vars: dict[str, Any],
    ) -> tuple[str, str, dict[str, str], str]:
        if not self.url:
            raise NotifierError("CustomWebhookNotifier.url 不能为空")
        headers = {"Content-Type": "application/json"}
        # HMAC 签名头
        if self.secret:
            sig = hmac.new(
                self.secret.encode("utf-8"),
                json.dumps(payload, sort_keys=True).encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            headers["X-Webhook-Signature"] = f"sha256={sig}"
        return "POST", self.url, headers, json.dumps(payload, ensure_ascii=False)


# ── 邮件 ────────────────────────────────────────────────────────────────


class EmailNotifier(BaseNotifier):
    """SMTP 邮件通知（异步 + 线程池 fallback）。

    通过 ``smtp_host`` / ``smtp_port`` / ``username`` / ``password`` / ``to_addrs`` 等关键字参数注入。
    """

    channel = "email"
    DEFAULT_TIMEOUT = 30.0  # SMTP 握手可能慢一些

    def __init__(
        self,
        url: str = "",  # noqa: ARG003 —— 保持接口一致但不使用
        secret: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(url=url, secret=secret, **kwargs)
        self.smtp_host: str = kwargs.get("smtp_host", "")
        self.smtp_port: int = int(kwargs.get("smtp_port", 465))
        self.username: str = kwargs.get("username", "")
        self.password: str = kwargs.get("password", "")
        self.from_addr: str = kwargs.get("from_addr", self.username)
        self.to_addrs: list[str] = list(kwargs.get("to_addrs", []))
        self.use_ssl: bool = bool(kwargs.get("use_ssl", True))

    async def send(
        self, payload: dict[str, Any], template_vars: dict[str, Any]
    ) -> SendResult:
        start = time.perf_counter()
        if not self.smtp_host or not self.to_addrs or not self.from_addr:
            return self._fail("SMTP 配置缺失 (smtp_host/to_addrs/from_addr)", start)
        subject = payload.get("subject", template_vars.get("event", "Notification"))
        body = payload.get("body", json.dumps(payload, ensure_ascii=False))

        try:
            await self._send_email(subject, body, payload.get("html", False))
        except Exception as exc:  # noqa: BLE001
            return self._fail(f"邮件发送失败: {exc}", start)

        elapsed = (time.perf_counter() - start) * 1000
        return SendResult(success=True, channel=self.channel, duration_ms=elapsed)

    async def _send_email(self, subject: str, body: str, html: bool) -> None:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.from_addr
        msg["To"] = ", ".join(self.to_addrs)
        if html:
            msg.set_content("此邮件需 HTML 渲染查看")
            msg.add_alternative(body, subtype="html")
        else:
            msg.set_content(body)

        # 优先 aiosmtplib，缺失则回退到线程池 + smtplib
        try:
            import aiosmtplib  # type: ignore[import-not-found]

            if self.use_ssl:
                await aiosmtplib.send(
                    msg,
                    hostname=self.smtp_host,
                    port=self.smtp_port,
                    username=self.username or None,
                    password=self.password or None,
                    use_tls=True,
                    timeout=self.DEFAULT_TIMEOUT,
                )
            else:
                await aiosmtplib.send(
                    msg,
                    hostname=self.smtp_host,
                    port=self.smtp_port,
                    username=self.username or None,
                    password=self.password or None,
                    start_tls=True,
                    timeout=self.DEFAULT_TIMEOUT,
                )
        except ImportError:
            await asyncio.to_thread(self._send_email_sync, msg)

    def _send_email_sync(self, msg: EmailMessage) -> None:
        import smtplib

        if self.use_ssl:
            with smtplib.SMTP_SSL(
                self.smtp_host, self.smtp_port, timeout=self.DEFAULT_TIMEOUT
            ) as s:
                if self.username:
                    s.login(self.username, self.password)
                s.send_message(msg)
        else:
            with smtplib.SMTP(
                self.smtp_host, self.smtp_port, timeout=self.DEFAULT_TIMEOUT
            ) as s:
                if self.username:
                    s.starttls()
                    s.login(self.username, self.password)
                s.send_message(msg)


# ── 派发器 ──────────────────────────────────────────────────────────────


class NotifierDispatcher:
    """根据 channel 名称构造对应 notifier 并派发。"""

    _REGISTRY: ClassVar[dict[str, type[BaseNotifier]]] = {
        "feishu": FeishuNotifier,
        "dingtalk": DingTalkNotifier,
        "wechat": WeChatNotifier,
        "slack": SlackNotifier,
        "email": EmailNotifier,
        "custom": CustomWebhookNotifier,
    }

    def __init__(self, db: Any = None) -> None:
        self.db = db

    def create(self, channel: str, **kwargs: Any) -> BaseNotifier:
        cls = self._REGISTRY.get(channel)
        if cls is None:
            raise NotifierError(f"不支持的通知渠道: {channel}")
        return cls(**kwargs)

    async def dispatch(
        self,
        channel: str,
        payload: dict[str, Any],
        template_vars: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> SendResult:
        notifier = self.create(channel, **kwargs)
        return await notifier.send(payload, template_vars or {})

    async def dispatch_event(
        self,
        event_payload: dict[str, Any],
        db: Any = None,
    ) -> list[SendResult]:
        """从 ``webhooks`` 表加载订阅并派发。"""
        from sqlalchemy import select

        from app.models.webhook import Webhook

        db = db or self.db
        results: list[SendResult] = []
        if db is None:
            return results
        try:
            q = await db.execute(select(Webhook).where(Webhook.enabled == 1))  # type: ignore[arg-type]
            hooks = q.scalars().all()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Load webhooks failed: %s", exc)
            return results
        event = event_payload.get("event", "")
        for hook in hooks:
            try:
                events = json.loads(hook.events_json or "[]")
            except (TypeError, ValueError):
                events = []
            if events and event and event not in events:
                continue
            notifier = self.create(
                hook.channel,
                url=hook.url,
                secret=hook.secret,
            )
            try:
                result = await notifier.send(event_payload, event_payload)
            except Exception as exc:  # noqa: BLE001
                result = SendResult(success=False, channel=hook.channel, error=str(exc))
            results.append(result)
        return results
