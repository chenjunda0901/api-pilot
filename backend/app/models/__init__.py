from app.models.base import Base
from app.models.user import User
from app.models.project import Project
from app.models.api_category import ApiCategory
from app.models.api_definition import ApiDefinition
from app.models.test_case import TestCase
from app.models.test_scene import TestScene
from app.models.scene_step import SceneStep
from app.models.scene_edge import SceneEdge
from app.models.environment import Environment
from app.models.test_report import TestReport
from app.models.report_step import ReportStep
from app.models.mock_rule import MockRule
from app.models.project_member import ProjectMember
from app.models.scene_category import SceneCategory
from app.models.debug_history import DebugHistory
from app.models.revoked_token import RevokedToken
from app.models.refresh_token import RefreshToken
from app.models.test_dataset import TestDataset, TestDatasetRow
from app.models.mock_hit_log import MockHitLog
from app.models.notification import Notification

# 阶段 1 新增：生产级特性模型
from app.models.api_test_plan import ApiTestPlan, ApiTestPlanStep
from app.models.schedule import Schedule
from app.models.data_schema import DataSchema
from app.models.mock_expectation import MockExpectation
from app.models.mock_recording import MockRecording
from app.models.api_snapshot import ApiSnapshot
from app.models.comment import Comment
from app.models.subscription import Subscription
from app.models.webhook import Webhook
from app.models.notification_dispatch import NotificationDispatch
from app.models.metrics_snapshot import MetricsSnapshot
from app.models.api_assertion import ApiAssertion
from app.models.variable import Variable
from app.models.api_tag import ApiTag, ApiTagRelation
from app.models.scene_dataset import SceneDataset
from app.models.mock_call_log import MockCallLog
from app.models.search_history import SearchHistory
from app.models.doc_version import DocVersion
from app.models.ci_config import CiConfig
from app.models.notification_preference import NotificationPreference
from app.models.api_test_history import ApiTestHistory

__all__ = [
    "Base",
    "User",
    "Project",
    "ApiCategory",
    "ApiDefinition",
    "TestCase",
    "TestScene",
    "SceneStep",
    "SceneEdge",
    "Environment",
    "TestReport",
    "ReportStep",
    "MockRule",
    "ProjectMember",
    "SceneCategory",
    "DebugHistory",
    "ApiTestHistory",
    "RevokedToken",
    "RefreshToken",
    "TestDataset",
    "TestDatasetRow",
    "MockHitLog",
    "Notification",
    # 阶段 1 新增
    "ApiTestPlan",
    "ApiTestPlanStep",
    "Schedule",
    "DataSchema",
    "MockExpectation",
    "MockRecording",
    "ApiSnapshot",
    "Comment",
    "Subscription",
    "Webhook",
    "NotificationDispatch",
    "MetricsSnapshot",
    "ApiAssertion",
    "Variable",
    "ApiTag",
    "ApiTagRelation",
    "SceneDataset",
    # Mock 智能化
    "MockCallLog",
    # 搜索历史
    "SearchHistory",
    # 新增模型
    "DocVersion",
    "CiConfig",
    "NotificationPreference",
]
