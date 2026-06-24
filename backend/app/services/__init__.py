"""Service 层统一导出。

按特性分组导入并 re-export，便于 router 层 ``from app.services import X``。
"""

# ── 阶段 2 新增服务（production-grade optimization） ──
from app.services.scheduler import (
    SchedulerService,
    SchedulerError,
    InvalidCronError,
    InvalidTimezoneError,
    JobNotFoundError,
    JobInfo,
)
from app.services.test_runner import (
    TestRunner,
    TestRunnerError,
    PlanNotFoundError,
    TestReport,
    StepResult,
)
from app.services.jsonpath import (
    JSONPathService,
    JSONPathError,
    extract as jsonpath_extract,
    set_value as jsonpath_set_value,
)
from app.services.json_schema_validator import (
    JSONSchemaValidator,
    JSONSchemaError,
    ValidationResult,
    ValidationError,
    validate as schema_validate,
)
from app.services.diff import (
    JSONDiffer,
    DiffOp,
    diff as json_diff,
)
from app.services.notifier import (
    NotifierDispatcher,
    BaseNotifier,
    FeishuNotifier,
    DingTalkNotifier,
    WeChatNotifier,
    SlackNotifier,
    EmailNotifier,
    CustomWebhookNotifier,
    NotifierError,
    SendResult,
)
from app.services.template import (
    TemplateEngine,
    TemplateError,
    render as template_render,
    DEFAULT_TEMPLATES,
)
from app.services.variable_resolver import (
    VariableResolver,
    VariableResolverError,
    CryptoError,
    generate_key,
    encrypt as var_encrypt,
    decrypt as var_decrypt,
)
from app.services.mock_engine import (
    SmartMockEngine,
    MockEngineError,
    MockScenario,
    get_default_engine,
)
from app.services.metrics import (
    MetricsCollector,
    MetricsError,
    PercentileResult,
    Alert,
    SlowRequest,
)
from app.services.assertion_runner import (
    AssertionRunner,
    AssertionResult,
)
from app.services.trace import (
    TraceContext,
    default_context as default_trace_context,
)
from app.services.health import (
    HealthChecker,
    ComponentStatus,
)
from app.services.stream import (
    StreamProcessor,
    StreamError,
    StreamSizeLimitExceeded,
)
from app.services.idempotency import (
    IdempotencyStore,
    IdempotencyError,
    default_store as default_idempotency_store,
)

__all__ = [
    # scheduler
    "SchedulerService", "SchedulerError", "InvalidCronError", "InvalidTimezoneError",
    "JobNotFoundError", "JobInfo",
    # test_runner
    "TestRunner", "TestRunnerError", "PlanNotFoundError", "TestReport", "StepResult",
    # jsonpath
    "JSONPathService", "JSONPathError", "jsonpath_extract", "jsonpath_set_value",
    # json_schema_validator
    "JSONSchemaValidator", "JSONSchemaError", "ValidationResult", "ValidationError", "schema_validate",
    # diff
    "JSONDiffer", "DiffOp", "json_diff",
    # notifier
    "NotifierDispatcher", "BaseNotifier", "FeishuNotifier", "DingTalkNotifier",
    "WeChatNotifier", "SlackNotifier", "EmailNotifier", "CustomWebhookNotifier",
    "NotifierError", "SendResult",
    # template
    "TemplateEngine", "TemplateError", "template_render", "DEFAULT_TEMPLATES",
    # variable_resolver
    "VariableResolver", "VariableResolverError", "CryptoError",
    "generate_key", "var_encrypt", "var_decrypt",
    # mock_engine
    "SmartMockEngine", "MockEngineError", "MockScenario", "get_default_engine",
    # metrics
    "MetricsCollector", "MetricsError", "PercentileResult", "Alert", "SlowRequest",
    # assertion_runner
    "AssertionRunner", "AssertionResult",
    # trace
    "TraceContext", "default_trace_context",
    # health
    "HealthChecker", "ComponentStatus",
    # stream
    "StreamProcessor", "StreamError", "StreamSizeLimitExceeded",
    # idempotency
    "IdempotencyStore", "IdempotencyError", "default_idempotency_store",
]
