"""Jinja2 模板渲染引擎。

为飞书 / 钉钉 / 企业微信 / Slack / Email 五个渠道提供默认模板，
支持 ``render(template_str, vars)`` 与 ``render_default(channel, event, payload)``。

典型用法::

    engine = TemplateEngine()
    body = engine.render_default("feishu", "plan.run.failed", payload)
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("service.template")


class TemplateError(Exception):
    """模板渲染错误。"""


# ── 默认模板 ────────────────────────────────────────────────────────────


DEFAULT_TEMPLATES: dict[str, dict[str, str]] = {
    "feishu": {
        "plan.run.completed": (
            '{% set status_emoji = "✅" if status == "passed" else "❌" %}'
            '{"msg_type": "interactive", "card": {'
            '"header": {"title": {"tag": "plain_text", '
            '"content": "{{ status_emoji }} 计划执行完成: {{ plan_id }}"}}, '
            '"elements": [{"tag": "div", "text": {"tag": "lark_md", '
            '"content": "**状态**: {{ status }}\\n**通过**: {{ pass_count }} '
            '\\n**失败**: {{ fail_count }}\\n**耗时**: {{ duration_ms }}ms"}}, '
            '{"tag": "note", "elements": [{"tag": "plain_text", '
            '"content": "API Pilot 自动化通知"}]}]}}'
        ),
    },
    "dingtalk": {
        "plan.run.completed": (
            "# 计划执行{{ '成功' if status == 'passed' else '失败' }}: 计划 #{{ plan_id }}\n\n"
            "- 状态: **{{ status }}**\n"
            "- 通过: {{ pass_count }}  失败: {{ fail_count }}  跳过: {{ skip_count }}\n"
            "- 耗时: {{ duration_ms }}ms"
        ),
    },
    "wechat": {
        "plan.run.completed": (
            "## 计划执行完成: 计划 #{{ plan_id }}\n"
            "> 状态: <font color=\"{{ 'info' if status == 'passed' else 'warning' }}\">{{ status }}</font>\n"
            "> 通过: {{ pass_count }}  失败: {{ fail_count }}\n"
            "> 耗时: {{ duration_ms }}ms"
        ),
    },
    "slack": {
        "plan.run.completed": (
            '{"blocks": ['
            '{"type": "header", "text": {"type": "plain_text", '
            '"text": "Plan #{{ plan_id }} {{ status }}"}}, '
            '{"type": "section", "fields": ['
            '{"type": "mrkdwn", "text": "*Passed*\n{{ pass_count }}"}, '
            '{"type": "mrkdwn", "text": "*Failed*\n{{ fail_count }}"}, '
            '{"type": "mrkdwn", "text": "*Duration*\n{{ duration_ms }}ms"}]}'
            ']}'
        ),
    },
    "email": {
        "plan.run.completed": (
            "<h2>计划执行{{ '成功' if status == 'passed' else '失败' }}: 计划 #{{ plan_id }}</h2>"
            "<table border=\"1\" cellpadding=\"6\" cellspacing=\"0\">"
            "<tr><th>状态</th><td>{{ status }}</td></tr>"
            "<tr><th>通过</th><td>{{ pass_count }}</td></tr>"
            "<tr><th>失败</th><td>{{ fail_count }}</td></tr>"
            "<tr><th>跳过</th><td>{{ skip_count }}</td></tr>"
            "<tr><th>耗时</th><td>{{ duration_ms }}ms</td></tr>"
            "</table>"
        ),
    },
}


# ── 引擎实现 ────────────────────────────────────────────────────────────


class TemplateEngine:
    """Jinja2 渲染器（独立 Environment，不与全局共享）。"""

    def __init__(self, autoescape: bool = False, enable_async: bool = False) -> None:
        try:
            from jinja2 import Environment, StrictUndefined
        except ImportError as exc:  # pragma: no cover
            raise TemplateError("未安装 jinja2") from exc
        self.env = Environment(
            autoescape=autoescape,
            undefined=StrictUndefined,
            enable_async=enable_async,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render(self, template_str: str, vars: dict[str, Any]) -> str:
        """渲染单条模板字符串。"""
        if not isinstance(template_str, str):
            raise TemplateError("template_str 必须是字符串")
        try:
            tmpl = self.env.from_string(template_str)
            return tmpl.render(**vars)
        except Exception as exc:
            raise TemplateError(f"模板渲染失败: {exc}") from exc

    def render_default(self, channel: str, event: str, payload: dict[str, Any]) -> str:
        """按 channel + event 查默认模板，缺省走 ``generic`` 简易模板。"""
        channel_tmpls = DEFAULT_TEMPLATES.get(channel, {})
        tmpl_str = channel_tmpls.get(event) or channel_tmpls.get("plan.run.completed")
        if tmpl_str is None:
            tmpl_str = (
                "事件: {{ event }}\n"
                "状态: {{ status | default('unknown') }}\n"
                "载荷: {{ payload | default('{}') }}"
            )
            vars_: dict[str, Any] = {**payload, "event": event, "payload": payload}
        else:
            vars_ = {**payload, "event": event}
        return self.render(tmpl_str, vars_)

    @staticmethod
    def supported_channels() -> list[str]:
        return list(DEFAULT_TEMPLATES.keys())


default_engine = TemplateEngine()


def render(template_str: str, vars: dict[str, Any]) -> str:
    return default_engine.render(template_str, vars)
