// Route path builders — type-safe, avoids hardcoded string typos.
// Patterns mirror the route definitions in ./index.ts.
export const RoutePaths = {
  login: '/login',
  register: '/register',
  dashboard: '/dashboard',
  // 分享相关（无需登录）
  shared: (token: string | number) => `/shared/${token}`,
  sharedDocs: (token: string | number) => `/shared-docs/${token}`,
  // 项目内路由
  apiList: (projectId: string | number) => `/projects/${projectId}/apis`,
  apiTestTool: (projectId: string | number) => `/projects/${projectId}/apis/test-tool`,
  apiDetail: (projectId: string | number, apiId: string | number) =>
    `/projects/${projectId}/apis/detail/${apiId}`,
  // 新建接口：实际路由为 /apis/detail/new（非 /apis/new）
  apisNew: (projectId: string | number) => `/projects/${projectId}/apis/detail/new`,
  // 接口测试历史
  apiTestHistory: (projectId: string | number, apiId: string | number) =>
    `/projects/${projectId}/apis/${apiId}/test-history`,
  caseDetail: (projectId: string | number, caseId: string | number) =>
    `/projects/${projectId}/apis/case/${caseId}`,
  scenes: (projectId: string | number) => `/projects/${projectId}/scenes`,
  reports: (projectId: string | number) => `/projects/${projectId}/reports`,
  reportDetail: (projectId: string | number, reportId: string | number) =>
    `/projects/${projectId}/reports/${reportId}`,
  mockRules: (projectId: string | number) => `/projects/${projectId}/mock-rules`,
  settings: (projectId: string | number) => `/projects/${projectId}/settings`,
  recycleBin: (projectId: string | number) => `/projects/${projectId}/recycle-bin`,
} as const;
