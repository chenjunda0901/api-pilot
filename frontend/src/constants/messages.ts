/**
 * 全局消息常量
 *
 * 分工说明：
 * - MSG：一次性 toast/snackbar 消息（成功、错误、提示），调用后自动消失
 * - CONFIRM：需要用户确认的操作弹窗（标题 + 正文 + 确认/取消按钮）
 */
export const MSG = {
  // ===== 错误提示 =====
  UNKNOWN_ERROR: "出了点问题，请稍后重试",
  NETWORK_ERROR: "网络连接异常，请检查网络或代理设置",
  UPLOAD_FAILED: "文件上传失败，请重试",
  DUPLICATE_NAME: "名称已存在，请使用其他名称",

  // ===== 成功提示 =====
  LOGIN_SUCCESS: "登录成功，欢迎回来",
  REGISTER_SUCCESS: "注册成功，已自动登录",
  CREATE_SCENE: "场景创建成功",
  CREATE_CASE: "用例创建成功",
  SAVE_SUCCESS: "修改已安全落库，环境随时可用",
  OPERATION_SUCCESS: "操作完成",
  DELETE_SUCCESS: "已成功移除",
  COPY_SUCCESS: "已复制到剪贴板",

  // ===== 导入导出 =====
  IMPORT_SINGLE_FILE: "请选择 Apifox 导出的 JSON 文件",
  IMPORT_FILE_INVALID: "文件格式无效，请选择 Apifox 导出的 JSON 文件",
  IMPORT_EXECUTE_DONE: (count: number) => `导入完成，共导入 ${count} 个接口`,

  // ===== 删除确认 =====
  DELETE_CATEGORY_CONFIRM: (name: string) => `确定要移除接口目录「${name}」吗？目录下的所有场景和接口将一并删除。`,
  DELETE_SCENE_CONFIRM: (name: string) => `确定要移除场景「${name}」吗？删除后关联的步骤和执行记录将无法恢复。`,

  // ===== 空状态提示 =====
  EMPTY_PROJECTS: "暂无项目，点击右上角创建一个吧",
  EMPTY_APIS: "暂无接口，在项目中添加第一个接口",
  EMPTY_CATEGORIES: "暂无接口目录，创建接口目录来组织接口",
  EMPTY_SCENES: "暂无测试场景，创建场景开始测试",
  EMPTY_CASES: "暂无测试用例，为接口添加测试用例",
  EMPTY_REPORTS: "暂无测试报告，运行场景后可查看报告",
  EMPTY_MOCK_RULES: "暂无 Mock 规则，添加规则来自定义响应",
} as const

export const CONFIRM = {
  DELETE_API: {
    title: '移除接口',
    message: (name: string) => `确定要移除接口「${name}」吗？关联场景中的执行步骤将被同步取消。`,
    confirmText: '确认移除',
    cancelText: '取消',
  },
  DELETE_CATEGORY: {
    title: '移除接口目录',
    message: (name: string) => `确定要移除接口目录「${name}」吗？目录下的接口不会被删除。`,
    confirmText: '确认移除',
    cancelText: '取消',
  },
  DELETE_SCENE: {
    title: '移除场景',
    message: (name: string) => `确定要移除场景「${name}」吗？相关测试报告不受影响。`,
    confirmText: '确认移除',
    cancelText: '取消',
  },
  DELETE_CASE: {
    title: '移除用例',
    message: (name: string) => `确定要移除用例「${name}」吗？此操作不可恢复。`,
    confirmText: '确认移除',
    cancelText: '取消',
  },
  DELETE_ENV: {
    title: '移除环境',
    message: (name: string) => `确定要移除环境「${name}」吗？使用该环境的场景需要重新配置。`,
    confirmText: '确认移除',
    cancelText: '取消',
  },
  DELETE_MOCK_RULE: {
    title: '移除 Mock 规则',
    message: (name: string) => `确定要移除 Mock 规则「${name}」吗？匹配该规则的请求将使用默认响应。`,
    confirmText: '确认移除',
    cancelText: '取消',
  },
  DISCARD_CHANGES: {
    title: '放弃更改',
    message: '有未保存的更改，确定要放弃吗？',
    confirmText: '放弃',
    cancelText: '继续编辑',
  },
} as const
