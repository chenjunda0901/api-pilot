# API Pilot

> 企业级接口自动化测试平台 — 支持 API 管理、测试用例编写、场景编排、定时调度和测试报告分析

[Python](https://img.shields.io/badge/Python-3.12-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green) ![Vue](https://img.shields.io/badge/Vue-3.5-brightgreen) ![TypeScript](https://img.shields.io/badge/TypeScript-5.7-blue) ![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 目录

- [功能特性](#功能特性)
- [技术栈](#技术栈)
- [快速开始](#快速开始)
  - [本地开发启动](#本地开发启动)
  - [Docker 一键启动](#docker-一键启动)
- [目录结构](#目录结构)
- [API 概览](#api-概览)
- [执行引擎](#执行引擎)
- [测试](#测试)
  - [后端测试](#后端测试)
  - [前端 E2E 测试](#前端-e2e-测试)
  - [CI/CD](#cicd)
- [贡献指南](#贡献指南)
- [设计文档](#设计文档)
- [License](#license)

---

## 功能特性

- **项目管理** — 多项目支持，成员权限管理
- **接口管理** — 分类树结构，支持 Apifox / OpenAPI 导入
- **环境管理** — 多环境配置，变量替换
- **测试用例** — 参数化用例，自动断言
- **场景编排** — 线性 / 图结构场景，支持步骤依赖
- **执行引擎** — 支持单步 / 场景 / 全量执行，带变量提取和渲染
- **Mock 服务** — 灵活的 Mock 规则配置，支持延迟模拟和自定义响应头
- **定时调度** — Cron 表达式定时执行
- **报告系统** — 详细执行报告，支持分享

## 技术栈

### 后端

| 组件 | 技术选型 |
|------|---------|
| 框架 | FastAPI 0.115 |
| 数据库 | SQLite + SQLAlchemy (async, aiosqlite) |
| 迁移工具 | Alembic |
| 认证 | JWT |
| 任务调度 | APScheduler |
| 测试 | pytest + pytest-asyncio (asyncio_mode=auto) |
| 代码质量 | Ruff (lint + format) |

### 前端

| 组件 | 技术选型 |
|------|---------|
| 框架 | Vue 3.5 + TypeScript 5.7 |
| 构建工具 | Vite 6 |
| UI 组件 | Element Plus 2.9 |
| 状态管理 | Pinia |
| 路由 | Vue Router (Hash 模式) |
| 编辑器 | Monaco Editor |
| 测试 | Playwright 1.50 (chromium) |

### DevOps

| 组件 | 技术选型 |
|------|---------|
| 容器化 | Docker (多阶段构建) |
| 编排 | Docker Compose |
| CI | GitHub Actions (双 workflow) |
| 代码规范 | TypeScript Strict Mode + vue-tsc |

## 快速开始

### 本地开发启动

#### 后端

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --log-level debug
```

后端默认运行在 **`http://localhost:5000`**，API 文档地址 **`http://localhost:5000/docs`**

#### 前端

```bash
cd frontend
npm install
npm run dev
```

前端默认运行在 **`http://localhost:8080`**，开发模式下 `/api` 请求自动代理到后端 5000 端口。

#### 种子数据

系统启动时会自动创建演示账号和数据：

| 角色 | 用户名 | 密码 |
|------|--------|------|
| 管理员 | admin | admin123 |
| 演示用户 | demo | demo123 |

### Docker 一键启动

> 前提条件：已安装 Docker Engine 和 Docker Compose。

```bash
# 克隆项目
git clone http://gitee.com/Lucifer701/api-pilot.git
cd api-pilot

# 一键启动（后端 + 前端）
docker compose up -d

# 查看运行状态
docker compose ps

# 查看日志
docker compose logs -f
```

启动后访问：

| 服务 | 地址 |
|------|------|
| 前端页面 | http://localhost:8080 |
| API 文档 | http://localhost:5000/docs |
| 健康检查 | http://localhost:5000/api/health |

**Docker 架构说明：**

- **backend** — Python 3.12-slim，多阶段构建（builder 阶段预装依赖，运行阶段仅复制 site-packages 和代码），SQLite 数据通过命名卷 `api_pilot_data` 持久化
- **frontend** — Node 23-alpine 构建 + Nginx alpine 运行，SPA history 路由 fallback，`/api/` 反向代理到 backend 容器
- **启动顺序** — frontend 通过 `depends_on` + `condition: service_healthy` 确保 backend 就绪后再启动
- **健康检查** — backend 每 30 秒通过 `/api/health` 自检

```bash
# 停止服务
docker compose down

# 停止并删除数据卷
docker compose down -v
```

## 目录结构

```
api-pilot/
├── backend/
│   ├── app/
│   │   ├── config.py       # 应用配置（端口/数据库/密钥）
│   │   ├── main.py         # 应用入口
│   │   ├── core/           # 核心异常
│   │   ├── middleware/     # 中间件（认证）
│   │   ├── models/         # 数据模型（16 个）
│   │   ├── routers/        # API 路由（14 个模块，76 个端点）
│   │   ├── schemas/        # Pydantic 模型
│   │   ├── services/       # 业务逻辑
│   │   │   └── executor/   # 执行引擎（线性/图/断言/变量渲染）
│   │   └── utils/          # 工具函数
│   ├── alembic/            # 数据库迁移
│   ├── data/               # SQLite 数据文件
│   └── tests/              # 后端测试（18+ 测试用例）
├── frontend/
│   ├── src/
│   │   ├── api/            # API 请求封装
│   │   ├── components/     # Vue 组件
│   │   ├── composables/    # 组合式 API
│   │   ├── constants/      # 常量定义
│   │   ├── layouts/        # 布局组件
│   │   ├── router/         # 路由配置
│   │   ├── stores/         # Pinia Store
│   │   ├── styles/         # 全局样式
│   │   ├── types/          # TypeScript 类型定义
│   │   ├── utils/          # 工具函数
│   │   └── views/          # 页面视图
│   └── e2e/                # E2E 测试（10 个 spec，14+ 测试用例）
├── .github/workflows/
│   ├── backend-ci.yml      # 后端 CI：Ruff lint → pytest + coverage
│   └── frontend-ci.yml     # 前端 CI：vue-tsc → build → E2E
├── Dockerfile.backend      # 后端 Docker 多阶段构建
├── Dockerfile.frontend     # 前端 Docker 多阶段构建
├── docker-compose.yml      # Docker Compose 编排
├── .dockerignore           # Docker 构建忽略规则
└── docs/                   # 设计文档
```

## API 概览

所有 API 端点前缀为 `/api`，认证接口除外。认证方式为 JWT Bearer Token。

### 认证模块

| 端点 | 方法 | 功能 | 认证 |
|------|------|------|------|
| `/api/auth/register` | POST | 用户注册 | 否 |
| `/api/auth/login` | POST | 用户登录，返回 JWT Token | 否 |
| `/api/auth/refresh` | POST | 刷新 Token | 是 |
| `/api/auth/me` | GET | 获取当前用户信息 | 是 |

### 核心业务模块

| 路由前缀 | 功能 | 主要端点 |
|---------|------|---------|
| `/api/projects` | 项目管理 | CRUD + 成员管理 |
| `/api/categories` | 接口分类 | 分类树 CRUD |
| `/api/apis` | 接口定义 | CRUD + 导入（Apifox/OpenAPI） |
| `/api/environments` | 环境管理 | CRUD，多 Base URL 配置 |
| `/api/cases` | 测试用例 | CRUD，参数化配置 |
| `/api/scenes` | 场景管理 | CRUD，步骤编排 |
| `/api/scene-categories` | 场景分类 | 分类树 CRUD |
| `/api/run` | 测试执行 | 单步 / 场景 / 全量执行 |
| `/api/reports` | 测试报告 | 查询 / 详情 / 分享 |
| `/api/mock` | Mock 规则 | CRUD，启用/禁用切换 |
| `/api/import-export` | 导入导出 | 项目级导入导出 |
| `/api/search` | 全局搜索 | 跨模块全文搜索 |
| `/api/system` | 系统管理 | 健康检查 / 配置信息 |

### Mock 服务详情

Mock 服务支持灵活的规则配置，适用于前后端分离开发中的接口模拟：

- **匹配条件** — 按请求方法（GET/POST/PUT/DELETE）和路径匹配
- **响应配置** — 自定义状态码、响应头、响应体
- **延迟模拟** — 可配置响应延迟（毫秒），模拟真实网络环境
- **启用控制** — 每条规则可独立启用/禁用

## 执行引擎

| 组件 | 说明 |
|------|------|
| **LinearExecutor** | 线性执行器，按顺序执行步骤，支持变量提取和断言 |
| **ExecutionEngine** | 图执行器，支持步骤依赖和拓扑排序 |
| **AssertionEngine** | 断言引擎，支持 JSONPath 提取和多种比较操作 |
| **VariableRenderer** | 变量渲染器，支持 `{{variable}}` 模板语法 |

## 测试

### 后端测试

```bash
cd backend

# 运行全部测试
pytest

# 按模块运行
pytest tests/test_apis/
pytest tests/test_executor/

# 带覆盖率报告
pytest --cov=app --cov-report=term-missing
```

### 前端 E2E 测试

```bash
cd frontend

# 安装 Playwright 浏览器（首次）
npx playwright install chromium

# 启动后端（终端 1）
cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 5000

# 启动前端（终端 2）
cd frontend && npm run dev

# 运行 E2E 测试（终端 3）
npx playwright test

# 运行单个测试文件
npx playwright test e2e/mock-rules.spec.ts

# 查看 HTML 报告
npx playwright show-report
```

E2E 测试覆盖范围：

| 测试文件 | 覆盖场景 |
|---------|---------|
| `auth.spec.ts` | 登录 / 注册 / 登出 |
| `navigation.spec.ts` | 菜单导航 / 页面跳转 |
| `acceptance.spec.ts` | 核心业务流程验收 |
| `business-flow.spec.ts` | 业务流：创建项目 → 添加接口 → 编写用例 |
| `5user-business-flow.spec.ts` | 多用户协作业务流 |
| `complete-flow.spec.ts` | 完整端到端流程 |
| `mock-rules.spec.ts` | Mock 规则 CRUD + 启用切换 |
| `scene-categories.spec.ts` | 场景分类 CRUD |
| `environments.spec.ts` | 环境管理 CRUD |
| `error-scenarios.spec.ts` | 404 / 无权限 / 无效项目 / 控制台错误 |

### CI/CD

项目使用 GitHub Actions 进行持续集成，包含两个独立 workflow：

#### 后端 CI (`.github/workflows/backend-ci.yml`)

| 阶段 | 操作 |
|------|------|
| Lint | Ruff 代码规范检查 |
| Test | pytest 运行全部测试 + 覆盖率报告 |

触发条件：推送到 `master` 分支或针对 `master` 的 PR。

#### 前端 CI (`.github/workflows/frontend-ci.yml`)

| 阶段 | 操作 |
|------|------|
| Type Check | vue-tsc TypeScript 类型检查 |
| Build | Vite 生产构建 |
| E2E | 安装 Playwright 浏览器 → 启动后端 → 启动前端 → 运行 Playwright 测试 |

触发条件：推送到 `master` 分支或针对 `master` 的 PR。

## 贡献指南

欢迎贡献代码！请遵循以下流程：

1. **Fork 项目** 并创建你的特性分支
2. **开发前阅读设计文档** — 见 `docs/` 目录
3. **遵循代码规范**：
   - 后端：Ruff 规范（`ruff check backend/`）
   - 前端：TypeScript Strict Mode（`vue-tsc --noEmit`）
4. **编写测试** — 新功能需包含对应的后端测试或前端 E2E 测试
5. **提交前检查**：
   ```bash
   # 后端
   cd backend && ruff check . && pytest
   
   # 前端
   cd frontend && vue-tsc --noEmit && npm run build
   ```
6. **提交 PR** 到 `master` 分支，CI 自动运行

### 开发环境要求

| 工具 | 版本要求 |
|------|---------|
| Python | >= 3.12 |
| Node.js | >= 20 |
| npm | >= 10 |
| Docker (可选) | >= 24.0 |

## 设计文档

更多详细设计和实现计划见 `docs/` 目录：

- `docs/superpowers/specs/` — 设计规格说明
- `docs/superpowers/plans/` — 实现计划
- `docs/testing/` — 测试清单

## License

MIT
