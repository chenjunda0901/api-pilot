# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Backend (Python/FastAPI)
```bash
# Install dependencies
cd backend && pip install -r requirements.txt -r requirements-dev.txt

# Run dev server (auto-reload, port auto-detection from 5000)
cd backend && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 5000

# Run via python main block (also works)
cd backend && python -m app.main

# Run tests
cd backend && pytest tests/ -v --cov=app --cov-report=term

# Lint (ruff)
cd backend && ruff check app/

# Database migrations
cd backend && alembic upgrade head    # Apply pending
cd backend && alembic revision --autogenerate -m "description"  # New migration
cd backend && alembic downgrade -1    # Rollback one step

# Cleanup scripts
cd backend && python scripts/cleanup_admin_private.py
cd backend && python scripts/cleanup_db.py
```

### Frontend (Vue 3 / TypeScript / Vite)
```bash
# Install dependencies
cd frontend && pnpm install

# Dev server (port 8080)
cd frontend && pnpm dev

# Type check
cd frontend && pnpm typecheck

# Lint
cd frontend && pnpm lint
cd frontend && pnpm lint:fix

# Run vitest unit tests
cd frontend && pnpm test
cd frontend && pnpm test:watch       # Watch mode
cd frontend && pnpm test:coverage    # With coverage

# E2E tests (Playwright)
cd frontend && pnpm exec playwright test
cd frontend && pnpm exec playwright test --ui  # UI mode

# Build for production
cd frontend && pnpm build
```

### Docker (full stack)
```bash
# Development
docker compose up --build

# Production
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build
```

### CI pipelines
- Backend CI: `.github/workflows/backend-ci.yml` — lint (ruff), security audit (pip-audit), pytest with coverage
- Frontend CI: `.github/workflows/frontend-ci.yml` — typecheck, lint, build, E2E tests (Playwright)

## Project Structure

```
├── backend/                    # FastAPI backend (Python 3.12)
│   ├── app/
│   │   ├── main.py            # FastAPI entry: lifespan, CORS, middleware stack, exception handlers, router registration
│   │   ├── config.py          # Settings (env-based): DB URL, SECRET_KEY, CORS, rate limit, SSRF, Fernet encryption
│   │   ├── database.py        # Async SQLAlchemy engine: connection pooling, exponential-backoff retry, N+1 detection, slow query logging
│   │   ├── limiter.py         # Rate limiter (slowapi)
│   │   ├── migration.py       # Alembic migration runner
│   │   ├── models/            # SQLAlchemy ORM models (~40+ models)
│   │   │   ├── base.py        # Declarative base with shared mixins (timestamps, soft-delete)
│   │   │   ├── project.py, user.py, environment.py  # Core domain models
│   │   │   ├── api_definition.py, api_assertion.py, api_category.py  # API management
│   │   │   ├── test_case.py, test_scene.py, test_report.py  # Testing domain
│   │   │   ├── scene_edge.py, scene_step.py, scene_dataset.py  # Scene graph
│   │   │   ├── mock_rule.py, mock_expectation.py, mock_recording.py  # Mock server
│   │   │   ├── variable.py   # Variable system (5 layers)
│   │   │   └── project_member.py, permission models
│   │   ├── routers/           # API route handlers (one per domain)
│   │   │   ├── auth.py, projects.py, members.py, system.py  # Core
│   │   │   ├── apis.py, categories.py, environments.py       # API management
│   │   │   ├── cases.py, scenes.py, scene_categories.py       # Test cases & scenes
│   │   │   ├── reports.py, run.py                            # Execution & reporting
│   │   │   ├── mock.py, mock_ecommerce.py                    # Mock server
│   │   │   ├── variables.py, assertions.py, tags.py           # Enterprise features
│   │   │   ├── docs.py, data_schemas.py, code_snippet.py      # Documentation & schemas
│   │   │   ├── debug.py, debug_history.py                     # Debugging
│   │   │   ├── import_export/                                # Apifox/OpenAPI import
│   │   │   ├── notifications.py, notifications_v2.py, subscriptions.py
│   │   │   ├── search.py, comments.py, fine_permissions.py
│   │   │   └── health.py, ws.py                              # Health & WebSocket
│   │   ├── services/          # Business logic layer
│   │   │   ├── executor/      # Test execution pipeline
│   │   │   │   ├── linear_executor.py     # Step-by-step scene runner
│   │   │   │   ├── request_builder.py     # Build HTTP requests from definition + variables
│   │   │   │   ├── assertion_engine.py    # Assertion evaluation engine
│   │   │   │   ├── script_executor.py     # Pre/post script execution (JS sandbox via quickjs/js2py)
│   │   │   │   └── variable_renderer.py   # 5-layer variable resolution & template rendering
│   │   │   ├── mock_engine.py, mock_service.py  # Mock server logic
│   │   │   ├── test_runner.py, report_service.py  # Test execution & reporting
│   │   │   ├── auth_service.py, permission_service.py  # Auth & RBAC
│   │   │   ├── api_service.py, scene_service.py, case_service.py
│   │   │   ├── variable_resolver.py, assertion_runner.py
│   │   │   ├── scheduler.py, sse_manager.py, ws_manager.py  # Async event streams
│   │   │   ├── importers/, apifox_importer.py, uni_importer.py  # Import handlers
│   │   │   └── ... (env_service, doc_service, export_service, etc.)
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   ├── middleware/        # FastAPI middleware stack
│   │   │   ├── auth.py                    # JWT access/refresh token auth
│   │   │   ├── request_tracking.py        # Performance monitoring & slow request alerts
│   │   │   ├── request_logging.py         # Structured JSON logging with trace_id
│   │   │   ├── idempotency.py             # Idempotency for POST/PUT/PATCH/DELETE
│   │   │   └── timeout.py                 # Request-level timeout (default 30s)
│   │   ├── core/             # Exceptions, error codes
│   │   └── utils/            # HTTP client, password, logging, scheduler, seed data, validators
│   ├── alembic/              # Database migrations (versioned, ~30 migration files)
│   └── scripts/              # DB cleanup & admin helper scripts
│
├── frontend/                   # Vue 3 SPA (pnpm, Vite 8)
│   ├── src/
│   │   ├── main.ts           # App bootstrap: Pinia, i18n, router, directives, Element Plus
│   │   ├── App.vue           # Root component: Suspense + KeepAlive + transition orchestrator
│   │   ├── api/              # Axios API layer (one module per domain: auth, projects, apis, etc.)
│   │   │   ├── apis.ts, auth.ts, cases.ts, scenes.ts, reports.ts, mock.ts, ...
│   │   │   └── request.ts   # Axios instance: interceptors, auto-retry, deduplication, SWR cache
│   │   ├── stores/           # Pinia stores
│   │   │   ├── userStore.ts, projectStore.ts, envStore.ts  # Core state
│   │   │   ├── apiStore.ts, editorStore.ts, tabsStore.ts    # Editor & UI state
│   │   │   ├── pendingApiStore.ts, hintBarStore.ts          # Utility stores
│   │   │   └── index.ts     # Pinia instance
│   │   ├── router/           # Vue Router
│   │   │   ├── index.ts     # Route definitions (lazy-loaded views)
│   │   │   └── paths.ts     # Type-safe route path builders (RoutePaths object)
│   │   ├── composables/     # ~40 Vue composables (hooks)
│   │   │   ├── useSWR.ts, useRequestDeduplicator.ts     # Network resilience
│   │   │   ├── useNetworkDetector.ts, useOptimisticUpdate.ts
│   │   │   ├── useToastManager.ts, useEventBus.ts       # UI patterns
│   │   │   ├── useKeyboardShortcuts.ts, useHotkeys.ts   # Keyboard
│   │   │   ├── useUndoManager.ts, useAutoSave.ts        # Editor UX
│   │   │   ├── useAsync.ts, useDebounce.ts, useLoading.ts # Utilities
│   │   │   ├── useTransitionOrchestrator.ts, useRoutePrefetcher.ts  # Performance
│   │   │   └── useWebSocket.ts, useReentrancyGuard.ts   # Async safety
│   │   ├── views/           # Page-level components (~17 views)
│   │   ├── components/      # Reusable components (~80+ components)
│   │   │   ├── common/      # SkeletonCard, EmptyState, ConfirmDialog, SearchDialog, etc.
│   │   │   ├── scene/       # StepConfigPanel, DatasetManager, DatasetSelector
│   │   │   ├── report/      # ReportCompare, ReportTrend, ResponseBodyViewer
│   │   │   ├── mock/        # MockRuleEditor, MockStatistics
│   │   │   ├── dashboard/   # Stats, TrendChart, QuickActions
│   │   │   ├── environment/ # EnvSwitcher, EnvironmentManager
│   │   │   ├── api/         # Sub-components for the API editor
│   │   │   └── tree/        # SidebarTree, CategoryTreeNode, etc.
│   │   ├── layout/          # AppLayout, Sidebar, TopBar, StatusBar, AppTabs
│   │   ├── directives/      # Custom directives (v-ripple)
│   │   ├── styles/          # CSS (animations, dark-mode, tokens, responsive, etc.)
│   │   ├── i18n/            # Localization (locales/)
│   │   ├── types/           # TypeScript type definitions
│   │   └── utils/           # Utility functions (JSON, deepEqual, retry, theme, toast, etc.)
│   ├── e2e/                 # Playwright E2E tests
│   └── vite.config.ts       # Vite config with auto-import, component resolver, Monaco, etc.
│
├── docker-compose.yml        # Dev stack (backend + frontend)
├── docker-compose.prod.yml   # Production overrides
├── Dockerfile.backend        # Multi-stage Python build
├── Dockerfile.frontend       # Nginx-served static build
└── .github/workflows/        # CI pipelines
```

## Architecture Overview

### Request Flow
```
Browser → Nginx (in Docker) → Vue Router → Vue Component
  → Pinia Store → API Module (axios) → FastAPI Router
  → Service Layer → SQLAlchemy Model → SQLite/PostgreSQL
```

### Middleware Stack (ordered from outermost to innermost)
1. `CORS` — env-configured origins, credentials handling
2. `RequestTracking` — trace_id injection, timing, slow-request logging
3. `StructuredRequestLogging` — structured JSON request lifecycle logs
4. `Idempotency` — idempotency-key deduplication for mutations (POST/PUT/PATCH/DELETE)
5. `RequestTimeout` — per-request timeout (default 30s, overridable via header)
6. Route handlers with rate limiting (slowapi) and JWT auth

### Security Patterns
- JWT dual-token auth (15min access + 7-day refresh, httpOnly cookie)
- Turnstile CAPTCHA with test/production/disabled modes
- SSRF protection via `ALLOWED_API_HOSTS` whitelist
- Fernet encryption for stored variables (key derived from SECRET_KEY or env)
- Rate limiting per endpoint (login 10/min, register 5/min)
- Production startup enforces: strong SECRET_KEY (≥32 chars), restricted CORS, Turnstile config validation
- Variable content encrypted at rest with env-configurable key

### Test Execution Pipeline
```
Scene → LinearExecutor → resolve variables (5 layers: builtin/env/project/api/step)
  → build HTTP request (request_builder.py)
  → execute with script (script_executor.py, pre/post JS sandbox)
  → run assertions (assertion_engine.py, jsonpath/status/header/body checks)
  → extract variables for downstream steps
  → collect results → test_report
```

### Key Technical Decisions
- **SQLite default** (single-worker required), PostgreSQL available via env switch
- **5-layer variable system**: builtin → environment → project → api/scene → step-level overrides
- **JS sandboxing**: quickjs (primary) / js2py (fallback) for pre/post scripts
- **WebSocket** for real-time execution progress and SSE for event streams
- **APScheduler** for scheduled scene execution and report retention cleanup
- **Element Plus** auto-imported globally alongside auto-registered components
- **unplugin-auto-import** + **unplugin-vue-components**: no manual imports needed for common APIs and components
- **SWR cache** (stale-while-revalidate) in axios interceptors for fast re-renders
- **Optimistic updates** with rollback for instant UI feedback on mutations
