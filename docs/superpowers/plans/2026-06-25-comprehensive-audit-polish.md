# API Pilot Comprehensive Audit & Polish Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Analyze all business flows for bugs, score the project from expert perspectives, polish frontend styles for both light/dark modes, and run comprehensive E2E user simulations.

**Architecture:** Systematic bug analysis across the full business flow (register → login → project → API → case → scene → report), followed by targeted fixes, UI/UX polish, and comprehensive E2E testing with 10 simulated users.

**Tech Stack:** Vue 3.5 + TypeScript 5.7 + Element Plus 2.9 + FastAPI 0.115 + SQLite + Playwright 1.61

---

## Task 1: Bug Analysis — Registration & Login Flow

**Files:**
- Modify: `frontend/src/views/RegisterView.vue`
- Modify: `frontend/src/views/LoginView.vue`
- Modify: `frontend/src/views/RegisterView.css`
- Modify: `frontend/src/views/LoginView.css`
- Modify: `frontend/src/stores/userStore.ts`
- Modify: `frontend/src/router/index.ts`

- [ ] **Step 1: Analyze registration flow for bugs**

Key issues to check:
- Password validation: min 6 chars, confirm match, strength indicator
- Username validation: 4-20 chars, alphanumeric + underscore only
- Email validation: optional, format check
- Auto-login after registration
- Welcome dialog for new users
- Mobile keyboard handling
- AbortController timeout handling
- Form reset after successful registration

- [ ] **Step 2: Fix registration bugs**

Common bugs found:
1. `RegisterView.vue` — `form.nickname` is NOT in the `rules` object but has `prop="nickname"` on the form-item, causing Element Plus validation warning
2. `RegisterView.vue` — `isKeyboardVisible` class applied to `.register-page` but no CSS for it
3. `RegisterView.vue` — Missing `form-wrapper` wrapper div (unlike LoginView), causing inconsistent layout
4. `RegisterView.css` — Missing styles for `.mobile-keyboard-open` class
5. `RegisterView.vue` — Password strength bar uses `--color-success-*` colors but doesn't define the gradient for level-3 (strong)

- [ ] **Step 3: Fix login flow bugs**

Key issues to check:
- Remember username functionality
- Form validation on submit
- Timeout handling (30s abort)
- Redirect after login
- Error handling for locked accounts (AUTH_011)
- Error handling for wrong credentials (AUTH_003)
- Auto-focus on error fields

- [ ] **Step 4: Run typecheck and lint**

Run: `pnpm run typecheck` and `pnpm run lint` from `frontend/`

---

## Task 2: Bug Analysis — Project Management Flow

**Files:**
- Modify: `frontend/src/views/DashboardView.vue`
- Modify: `frontend/src/stores/projectStore.ts`
- Modify: `frontend/src/api/projects.ts`

- [ ] **Step 1: Analyze project creation flow**

Check:
- New project dialog opens correctly
- Project name validation (non-empty, length limits)
- Public/private toggle
- Description field
- After creation, project is selected and navigated to
- Demo project is not editable/deletable by non-admins
- Empty state when no projects exist

- [ ] **Step 2: Fix project management bugs**

Common issues:
1. `DashboardView.vue` — `handleCreateProject` uses `createLock` but may not handle concurrent clicks
2. `DashboardView.vue` — Stats cards may show 0 when project exists but has no data (should show empty state hint)
3. `projectStore.ts` — Project switching may not reset related stores (apiStore, envStore)
4. `DashboardView.vue` — `goTo(card.link)` may fail if link is undefined

- [ ] **Step 3: Run typecheck and lint**

---

## Task 3: Bug Analysis — API Management Flow

**Files:**
- Modify: `frontend/src/views/ApiListView.vue`
- Modify: `frontend/src/views/ApiDetail.vue`
- Modify: `frontend/src/components/SidebarTree.vue`
- Modify: `frontend/src/stores/apiStore.ts`

- [ ] **Step 1: Analyze API creation and management flow**

Check:
- Category tree CRUD (create, rename, delete, move)
- API creation with different HTTP methods
- API editing (name, URL, method, headers, params, body)
- API deletion (move to recycle bin)
- API import (Apifox, OpenAPI, cURL)
- API export
- Batch operations (select all, batch delete, batch move)
- Search and filter functionality
- Tag management

- [ ] **Step 2: Fix API management bugs**

Common issues:
1. `SidebarTree.vue` — Context menu may not close on outside click
2. `ApiListView.vue` — Category filter may not reset when switching projects
3. `ApiDetail.vue` — Unsaved changes warning may not trigger for all fields
4. `apiStore.ts` — API list may not refresh after batch operations
5. `ApiListView.vue` — Method filter chips may not sync with URL params

- [ ] **Step 3: Run typecheck and lint**

---

## Task 4: Bug Analysis — Test Case & Scene Flow

**Files:**
- Modify: `frontend/src/views/CaseDetail.vue`
- Modify: `frontend/src/views/ScenesView.vue`
- Modify: `frontend/src/components/CasesTab.vue`
- Modify: `frontend/src/components/SceneTree.vue`

- [ ] **Step 1: Analyze test case creation flow**

Check:
- Case creation from API detail
- Case parameter overrides
- Case assertions configuration
- Case execution (single case)
- Case save/update/delete
- Case list in API detail tab

- [ ] **Step 2: Analyze scene test flow**

Check:
- Scene creation and naming
- Scene step editor (add, remove, reorder)
- Step configuration (API, assertions, variables)
- Scene import (from API list, from cases)
- Scene execution (run all, run failed only, stress mode)
- Scene export (JSON, clipboard)
- Scene categories

- [ ] **Step 3: Fix scene and case bugs**

Common issues:
1. `ScenesView.vue` — Step reorder may not persist after save
2. `SceneTree.vue` — Scene deletion confirmation may be missing
3. `CasesTab.vue` — Case creation dialog may not reset form on close
4. `CaseDetail.vue` — Auto-save may conflict with manual save
5. `ScenesView.vue` — Execution progress may not update in real-time

- [ ] **Step 4: Run typecheck and lint**

---

## Task 5: Bug Analysis — Report & Export Flow

**Files:**
- Modify: `frontend/src/views/ReportsView.vue`
- Modify: `frontend/src/views/ReportDetailView.vue`
- Modify: `frontend/src/api/reports.ts`
- Modify: `frontend/src/utils/exporter.ts`

- [ ] **Step 1: Analyze report generation and viewing flow**

Check:
- Report list with pagination
- Report filtering (status, date range, search)
- Report detail view (summary, step details, assertions)
- Report sharing (generate share link)
- Report export (PDF, HTML, JSON)
- Real-time report updates during execution

- [ ] **Step 2: Fix report bugs**

Common issues:
1. `ReportsView.vue` — Pagination may not reset when filters change
2. `ReportDetailView.vue` — Large report detail may cause performance issues
3. `exporter.ts` — Export may fail silently for large reports
4. `ReportsView.vue` — Date range filter may not clear properly
5. `ReportDetailView.vue` — Step expand/collapse state may not persist

- [ ] **Step 3: Run typecheck and lint**

---

## Task 6: Bug Analysis — Mock, Environment & Settings

**Files:**
- Modify: `frontend/src/views/MockRulesView.vue`
- Modify: `frontend/src/components/environment/EnvironmentManager.vue`
- Modify: `frontend/src/views/SettingsView.vue`

- [ ] **Step 1: Analyze mock rules flow**

Check:
- Mock rule CRUD
- Enable/disable toggle
- Method and path matching
- Response configuration (status, headers, body)
- Delay simulation

- [ ] **Step 2: Analyze environment management flow**

Check:
- Environment CRUD
- Variable management within environments
- Environment switching in TopBar
- Variable interpolation in API requests
- Environment import/export

- [ ] **Step 3: Analyze settings flow**

Check:
- Project info editing
- Member management (invite, role change, remove)
- Project deletion (with confirmation)
- API documentation generation
- Project import/export

- [ ] **Step 4: Fix mock/environment/settings bugs**

- [ ] **Step 5: Run typecheck and lint**

---

## Task 7: Expert Scoring & Optimization Plan

**Files:**
- Modify: Various frontend files based on scoring

- [ ] **Step 1: Score as Senior Designer (UI/UX)**

Scoring dimensions (1-10):
- Visual hierarchy: Score and recommendations
- Color system: Score and recommendations
- Typography: Score and recommendations
- Spacing consistency: Score and recommendations
- Component states (hover, active, focus, disabled): Score and recommendations
- Animation & transitions: Score and recommendations
- Dark mode quality: Score and recommendations
- Accessibility (WCAG 2.1): Score and recommendations

- [ ] **Step 2: Score as Senior Product Manager**

Scoring dimensions (1-10):
- User flow completeness: Score and recommendations
- Error handling UX: Score and recommendations
- Empty states: Score and recommendations
- Loading states: Score and recommendations
- Onboarding experience: Score and recommendations
- Feature discoverability: Score and recommendations
- Performance perception: Score and recommendations

- [ ] **Step 3: Score as Senior Architect**

Scoring dimensions (1-10):
- Code organization: Score and recommendations
- State management: Score and recommendations
- API design: Score and recommendations
- Security: Score and recommendations
- Scalability: Score and recommendations
- Testing coverage: Score and recommendations

- [ ] **Step 4: Score as Senior Frontend Engineer**

Scoring dimensions (1-10):
- TypeScript strictness: Score and recommendations
- Component reusability: Score and recommendations
- Performance optimization: Score and recommendations
- Bundle size: Score and recommendations
- Code maintainability: Score and recommendations
- Build & CI/CD: Score and recommendations

- [ ] **Step 5: Create prioritized optimization list**

Based on all scores, create a prioritized list of improvements.

---

## Task 8: Frontend Style Polish — Light Mode

**Files:**
- Modify: `frontend/src/styles/tokens.css`
- Modify: `frontend/src/styles/global.css`
- Modify: `frontend/src/styles/base.css`
- Modify: `frontend/src/styles/element-plus-override.css`
- Modify: `frontend/src/styles/page-layout.css`
- Modify: `frontend/src/styles/animations.css`

- [ ] **Step 1: Polish login/register pages**

Improvements:
- Smoother gradient transitions
- Better form field focus states
- Consistent button styles
- Mobile responsive improvements
- Password strength indicator polish

- [ ] **Step 2: Polish sidebar navigation**

Improvements:
- Active state visual feedback
- Hover state animations
- Collapse/expand transitions
- Logo animation on hover
- Nav group label styling

- [ ] **Step 3: Polish topbar and project selector**

Improvements:
- Search button styling
- Project dropdown panel polish
- Environment selector styling
- User avatar and dropdown

- [ ] **Step 4: Polish dashboard**

Improvements:
- Stats card hover effects
- Report list item styling
- Quick actions section
- Chart container styling
- Empty state illustration

- [ ] **Step 5: Polish API list and detail views**

Improvements:
- Table row hover effects
- Method badge consistency
- Filter bar styling
- Tab navigation polish
- Request/Response panel styling

- [ ] **Step 6: Polish scene and report views**

Improvements:
- Scene tree node styling
- Step editor layout
- Execution progress indicator
- Report summary cards
- Report detail sections

- [ ] **Step 7: Polish dialogs and modals**

Improvements:
- Dialog header styling
- Form layout in dialogs
- Button alignment
- Loading states in dialogs

- [ ] **Step 8: Run typecheck and lint**

---

## Task 9: Frontend Style Polish — Dark Mode

**Files:**
- Modify: `frontend/src/styles/tokens.css` (html.dark section)
- Modify: `frontend/src/styles/dark-mode.css`
- Modify: `frontend/src/styles/global.css` (html.dark overrides)

- [ ] **Step 1: Audit dark mode color consistency**

Check all components for proper dark mode styling:
- Background colors (3-level hierarchy: bg, card, elevated)
- Text colors (3-level: primary, secondary, muted)
- Border colors (2-level: default, strong)
- Shadow system (primary glow + dark projection)
- Functional colors (success, warning, error, info)

- [ ] **Step 2: Fix dark mode inconsistencies**

Common issues:
- Input fields not using `--surface-input`
- Cards missing `--surface-card` background
- Text contrast issues (WCAG AA minimum 4.5:1)
- Shadow too dark or too light
- Focus ring visibility in dark mode

- [ ] **Step 3: Polish dark mode specific elements**

- Sidebar dark gradient
- Code block syntax highlighting
- Chart colors in dark mode
- Table striped rows
- Dialog/drawer backgrounds

- [ ] **Step 4: Test theme toggle transition**

Ensure smooth 240ms transition between light and dark modes without flash.

- [ ] **Step 5: Run typecheck and lint**

---

## Task 10: E2E Test — 10 User Simulations

**Files:**
- Modify: `frontend/e2e/user-01-new-user.spec.ts`
- Modify: `frontend/e2e/user-02-developer.spec.ts`
- Modify: `frontend/e2e/user-03-tester.spec.ts`
- Modify: `frontend/e2e/user-04-qa-manager.spec.ts`
- Modify: `frontend/e2e/user-05-project-admin.spec.ts`
- Modify: `frontend/e2e/user-06-doc-maintainer.spec.ts`
- Modify: `frontend/e2e/user-07-mock-user.spec.ts`
- Modify: `frontend/e2e/user-08-power-user.spec.ts`
- Modify: `frontend/e2e/user-09-readonly-guest.spec.ts`
- Modify: `frontend/e2e/user-10-concurrent.spec.ts`
- Modify: `frontend/e2e/utils/` (shared helpers)

- [ ] **Step 1: User 01 — New User (Complete Onboarding)**

Scenario: New user registers → creates first project → explores dashboard → creates first API → runs demo
- Register with new account
- Handle welcome dialog
- Create first project
- Navigate to API list
- Create a GET API
- Add query parameters
- Save as test case
- Execute the case
- View result

- [ ] **Step 2: User 02 — Developer (API-Heavy Workflow)**

Scenario: Developer creates multiple APIs → imports from cURL → tests each → creates cases
- Login as demo user
- Navigate to API list
- Create POST API with JSON body
- Import API from cURL
- Import from OpenAPI spec
- Create test cases for each API
- Execute individual cases
- View test history

- [ ] **Step 3: User 03 — Tester (Scene Testing)**

Scenario: Tester creates scenes → adds steps → configures assertions → runs scenes → views reports
- Login
- Navigate to scenes
- Create new scene
- Add multiple API steps
- Configure assertions
- Run scene
- View execution progress
- Check report details

- [ ] **Step 4: User 04 — QA Manager (Reporting & Analysis)**

Scenario: QA manager reviews reports → exports → shares → analyzes trends
- Login
- Navigate to reports
- Filter by date range
- Filter by status
- View report detail
- Export report
- Share report link
- Check dashboard trends

- [ ] **Step 5: User 05 — Project Admin (Settings & Members)**

Scenario: Admin manages project settings → invites members → configures permissions
- Login as admin
- Navigate to settings
- Edit project info
- Manage members
- Invite new member
- Change member role
- Configure environment
- Import/Export project

- [ ] **Step 6: User 06 — Doc Maintainer (API Documentation)**

Scenario: Maintainer writes docs → previews → shares docs
- Login
- Navigate to API detail
- Edit API documentation
- Preview documentation
- Share documentation link
- Verify shared docs accessible without login

- [ ] **Step 7: User 07 — Mock User (Mock Service)**

Scenario: Developer configures mock rules → tests frontend against mocks
- Login
- Navigate to mock rules
- Create GET mock rule
- Create POST mock rule
- Enable/disable rules
- Test mock responses

- [ ] **Step 8: User 08 — Power User (Keyboard Shortcuts & Advanced)**

Scenario: Power user uses keyboard shortcuts → command palette → batch operations
- Login
- Open command palette (Ctrl+K)
- Search for API
- Use keyboard shortcuts
- Select multiple APIs
- Batch delete
- Batch move to category
- Undo operation

- [ ] **Step 9: User 09 — Read-Only Guest (Unauthenticated)**

Scenario: Guest browses demo project → views APIs → cannot edit
- Access dashboard without login
- View demo project
- Browse API list
- View API details
- Attempt to create API (should redirect to login)
- Verify read-only state

- [ ] **Step 10: User 10 — Concurrent Users (Multi-Tab)**

Scenario: Multiple tabs open simultaneously → verify state consistency
- Open dashboard in tab 1
- Open API list in tab 2
- Create API in tab 1
- Verify API appears in tab 2
- Switch projects in tab 1
- Verify tab 2 updates
- Close tab 1
- Verify tab 2 still works

- [ ] **Step 11: Run all E2E tests**

Run: `pnpm exec playwright test` from `frontend/`
Expected: All tests pass
