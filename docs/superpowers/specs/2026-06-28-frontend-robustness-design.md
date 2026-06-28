# 前端稳健性 & 丝滑体验架构改进设计

日期: 2026-06-28  
状态: 草案  

## 1. 概述

### 1.1 目标

对 API Pilot 前端进行系统性架构改进，实现：

- **不轻易报错** — 网络韧性提升，自动恢复，优雅降级
- **操作流畅** — SWR 缓存策略 + 乐观更新，消除等待感
- **交互丝滑** — 过渡编排、微动效、统一反馈闭环

### 1.2 范围

4 个独立模块，分批实施，每批独立可交付：

| 批次 | 模块 | 核心能力 |
|:----:|:----|:---------|
| 第一批 | 网络韧性 + 数据缓存 | 请求去重、自动重试、网络检测、SWR、乐观更新 |
| 第二批 | 渲染性能 | Suspense 路由、预加载、Web Worker、KeepAlive |
| 第三批 | 交互丝滑化 | Toast 管理、微动效、过渡编排、反馈闭环 |

### 1.3 设计原则

- **零侵入业务代码** — 基础设施层改动，对业务组件无感
- **渐进可交付** — 每批独立测试，独立上线
- **遵循现有模式** — 沿用 Vue Composition API + Pinia + composables 架构
- **不作架构假设** — 不引入新框架/库，利用 Vue 3 内置能力

## 2. 模块①：网络韧性层

### 2.1 请求去重 (Request Deduplication)

**文件:** `src/composables/useRequestDeduplicator.ts`

**动机:** 多个组件同时挂载时可能并发请求同一接口（如项目列表、环境配置），造成冗余网络开销和服务器压力。

**方案:**

```typescript
// 核心: 基于 cacheKey 的 Promise 复用
// cacheKey = `${method}:${url}:${JSON.stringify(params)}`
// 进行中的请求存入 Map，后续相同请求直接复用 Promise
// 请求完成后自动从 Map 中移除
```

**集成:** 在 `src/api/request.ts` 的请求适配层统一注入，业务代码零感知。

**去重范围:**
- GET/HEAD/OPTIONS 请求全部去重
- POST 请求仅在相同 payload 时去重
- 去重窗口: 请求开始到结束（响应或错误后自动清除）

### 2.2 自动重试 (Automatic Retry)

**文件:** `src/utils/retry.ts`

**动机:** 网络瞬断、服务器重启等场景下临时性失败应自动重试，而非直接展示错误。

**方案:**

```typescript
async function retryWithBackoff<T>(
  fn: () => Promise<T>,
  options: {
    maxRetries: 5,
    baseDelay: 1000,    // 1s
    maxDelay: 30000,    // 30s
    retryOn: (error) => boolean
  }
): Promise<T>
```

**重试策略:**
- **幂等请求 (GET/HEAD/OPTIONS):** 网络错误 + 5xx 全部自动重试
- **非幂等请求 (POST/PUT/DELETE):** 仅网络错误（无响应）重试，4xx/5xx 不重试
- **退避算法:** `Math.min(baseDelay * 2^i + randomJitter(), maxDelay)`
- **jitter:** 随机 0-1000ms，防止惊群效应

**集成:** 在 `request.ts` 的 response 错误拦截器中注入。

### 2.3 网络状态检测 (Network Detector)

**文件:** `src/composables/useNetworkDetector.ts`

**动机:** 用户在网络不稳定时需要明确的"网络已断开"提示，且恢复后自动重发失败请求。

**方案:**

```typescript
// 导出:
//   isOnline: Ref<boolean>
//   connectionQuality: Ref<'fast' | 'normal' | 'slow'>
//   onOnline: (cb) => void    // 网络恢复回调
//   onOffline: (cb) => void   // 网络断开回调

// 检测方式:
//   1. navigator.onLine 事件
//   2. 心跳探测: 每 30s ping /api/v1/ping
//   3. 连接质量: 最近 5 次请求耗时估算
```

**网络恢复行为:**
- 自动刷新当前页面的关键数据
- 重发因网络断开而暂存的请求队列
- 移除"网络已断开"横幅，展示"网络已恢复"提示

## 3. 模块②：数据缓存层

### 3.1 SWR 缓存策略

**文件:** `src/composables/useSWR.ts`

**动机:** 当前 TTL 缓存到期后强制刷新导致短暂空白，SWR (stale-while-revalidate) 策略可先展示旧数据再后台刷新，消除"闪烁"。

**方案:**

```typescript
function useSWR<T>(
  key: string,                           // 缓存键
  fetcher: () => Promise<T>,             // 数据获取函数
  options?: {
    ttl?: number                         // 缓存有效期 (默认 60s)
    revalidateOnFocus?: boolean          // 窗口聚焦时刷新 (默认 true)
    revalidateOnReconnect?: boolean      // 网络恢复时刷新 (默认 true)
  }
): {
  data: Ref<T | undefined>
  error: Ref<Error | undefined>
  isValidating: Ref<boolean>             // 是否正在后台刷新
  mutate: (data: T) => void              // 手动更新缓存
  refresh: () => Promise<T>              // 强制刷新
}
```

**缓存 TTL 配置:**

| 数据 | 当前 TTL | 新 TTL | 说明 |
|:----|:--------:|:------:|:-----|
| 项目列表 | 无缓存 | 120s | 低频变化 |
| API 类别树 | 30s | 120s | 树结构稳定 |
| API 详情 | 30s | 60s | 编辑时乐观更新 |
| 环境配置 | 30s | 60s | 全局配置 |
| 场景列表 | 无缓存 | 120s | 低频变化 |

**缓存存储:** 响应式 Map（内存）+ 关键数据 localStorage 持久化（项目列表、环境配置）。

### 3.2 乐观更新 (Optimistic Update)

**文件:** `src/composables/useOptimisticUpdate.ts`

**动机:** 保存/删除操作后用户需等待请求完成才能看到结果，乐观更新可即时反映 UI 变化，大幅提升感知速度。

**方案:**

```typescript
function useOptimisticUpdate<T>(options: {
  key: string
  // 立即更新缓存的函数
  update: (currentData: T) => T
  // 实际的 API 请求
  commit: () => Promise<T>
  // 冲突检测 (可选)
  versionCheck?: (serverData: T, localData: T) => boolean
}): {
  execute: () => Promise<void>   // 触发乐观更新
  isPending: Ref<boolean>        // 同步状态
  error: Ref<Error | null>       // 错误信息
  rollback: () => void           // 手动回滚
}
```

**流程:**

```
用户操作 → ⚡ 立即更新 UI (乐观态)
         → ⟳ 后台发送请求
         → ✓ 成功 → 用服务端响应修正数据
         → ✗ 失败 → 自动回滚 + ElMessage 提示
```

**冲突检测:** 对比 `updated_at` 时间戳。若服务端版本更新，展示 "数据已被他人修改，请刷新后重试"。

**适用范围:**
- API 增/删/改操作
- 环境变量增/删/改
- 场景步骤增/删/改
- 排序/拖拽操作

### 3.3 Store 改造

| Store | 改造内容 |
|:------|:---------|
| `apiStore` | SWR 替换现有 TTL 缓存；增删改操作接入乐观更新 |
| `envStore` | SWR 替换现有 TTL 缓存 |
| `projectStore` | 新增 SWR 缓存 (120s) |
| `editorStore` | 接入乐观更新，与 auto-save 联动 |
| 场景编辑器 | 步骤操作接入乐观更新 + undo 联动 |

## 4. 模块③：渲染性能层

### 4.1 Suspense 路由改造

**动机:** 当前路由懒加载时展示全局 loading bar，但内容组件内部可能还有异步数据依赖。Suspense 可管理整个异步树的加载状态。

**方案:**

```html
<!-- App.vue -->
<Suspense @resolve="onRouteResolved">
  <template #default>
    <router-view v-slot="{ Component, route }">
      <Transition :name="route.meta.transition" mode="out-in">
        <component :is="Component" :key="route.path" />
      </Transition>
    </router-view>
  </template>
  <template #fallback>
    <RouteSkeleton :route="currentRoute" />
  </template>
</Suspense>
```

**实现细节:**
- 每个路由组件内部使用 `<Suspense>` 处理异步 setup
- `RouteSkeleton` 组件根据当前路由展示对应 skeleton（API 列表骨架、场景列表骨架等）
- 与 LoadingBar 联动显示整体进度

### 4.2 路由预加载 (Route Prefetching)

**文件:** `src/composables/useRoutePrefetcher.ts`

**动机:** 用户 hover 导航链接时即可开始加载目标路由代码和数据，消除点击后的等待时间。

**三种策略:**
1. **Hover 预加载:** `router-link` 的 `@mouseenter` 触发 `component` 的动态 `import()`
2. **空闲预加载:** `requestIdleCallback` 在空闲时预加载"可能访问"的路由（基于访问历史）
3. **数据预加载:** 结合 SWR，在路由切换前提前获取页面所需数据

### 4.3 Web Worker 池

**文件:** `src/utils/workerPool.ts`

**动机:** 场景执行分析、大批量数据筛选等 CPU 密集型任务阻塞主线程，导致 UI 卡顿。

**方案:**

```typescript
class WorkerPool {
  constructor(maxWorkers: number = 4)
  exec<T>(task: string, data: any): Promise<T>
  terminate(): void
}
```

**适用场景（按优先级）：**
1. 场景执行历史分析（数据处理 + ECharts 数据准备）
2. 大批量断言结果过滤/排序
3. 报告导出（CSV/JSON 预处理）
4. 树形数据扁平化/搜索

### 4.4 KeepAlive 路由缓存

**动机:** 用户频繁在 Dashboard、API 列表、场景列表间切换，每次都重新渲染和请求数据。

**方案:**
- Dashboard → KeepAlive
- API 列表 → KeepAlive
- 场景列表 → KeepAlive
- 编辑器/详情页 → 不缓存（使用 Suspense）
- 最大缓存 5 个实例，LRU 淘汰

## 5. 模块④：交互丝滑层

### 5.1 过渡编排 (Transition Orchestrator)

**文件:** `src/composables/useTransitionOrchestrator.ts`

**动机:** 当前页面切换时 skeleton 突然替换为内容，缺乏平滑过渡。

**方案:**

```typescript
function useTransitionOrchestrator(steps: TransitionStep[]) {
  // 1. 旧内容退出 (fadeOut 150ms)
  // 2. 新 skeleton 进入 (fadeIn 200ms)
  // 3. 数据到达后 skeleton → 内容 (crossfade 300ms)
  // 4. 子元素依次进入 (staggered 50ms/item)
}
// 与 LoadingBar 联动
```

### 5.2 Toast 队列管理器

**文件:** `src/composables/useToastManager.ts`

**动机:** 多条 Toast 同时弹出遮挡操作、同类错误重复提醒造成干扰。

**方案:**

```typescript
const toastManager = {
  show(options: ToastOptions): string       // 显示 toast，返回 id
  dismiss(id: string): void                 // 手动关闭
  clear(): void                             // 清空所有
  // ToastOptions:
  //   type: 'success' | 'error' | 'warning' | 'info'
  //   message: string
  //   action?: { label: string, onClick: () => void }
  //   duration?: number (默认: error=0 不消失, 其余 3000ms)
}

// 特性:
//   同类合并: 3s 内相同 message 的 error 合并为 "3 个请求失败"
//   优先级: error > warning > success > info
//   上限: 同时最多 3 条
//   操作反馈: "保存中..." → "已保存" 自动切换
```

### 5.3 微交互动效

| 动效 | 实现方式 | 说明 |
|:----|:---------|:-----|
| 按钮波纹 | `v-ripple` 指令 | 点击产生水波纹扩散 |
| 列表进入/离开 | TransitionGroup + 现有 animations.css | 新增滑入 (300ms)、缩小消失 (200ms) |
| 数据变化高亮 | 背景色闪烁 1s | 类似 git diff，仅数据变化时触发 |
| 已保存提示 | 底部常驻指示器 | 2s 后淡出，不遮挡操作区 |

### 5.4 操作反馈闭环

| 场景 | 反馈流程 |
|:----|:---------|
| 保存 API | ⚡ 乐观更新 → "保存中..." → ✓ "已保存" |
| 删除步骤 | ⚡ 立即消失 + 撤销按钮 → 后台同步 → 超时自动确认 |
| 网络断开 | 🌐 顶部 "网络已断开" 横幅 → 操作可继续 → 恢复后同步 |
| 路由切换 | 旧页淡出 → 目标 skeleton → 内容渐入 |

## 6. 实施计划

### 第一批：网络韧性 + 缓存层

**新增文件（4 个 composable + 1 个 util）：**
- `src/composables/useRequestDeduplicator.ts`
- `src/composables/useNetworkDetector.ts`
- `src/composables/useSWR.ts`
- `src/composables/useOptimisticUpdate.ts`
- `src/utils/retry.ts`

**修改文件：**
- `src/api/request.ts` — 注入去重、重试、网络状态集成
- `src/stores/apiStore.ts` — SWR + 乐观更新
- `src/stores/envStore.ts` — SWR
- `src/stores/projectStore.ts` — SWR

**验证标准：**
- 并发请求去重: 同一接口并发 5 次实际只发 1 次
- 自动重试: 模拟网络波动，GET 请求失败后自动重试成功
- SWR 缓存: 列表数据刷新无闪烁
- 乐观更新: 保存操作即时反映，失败自动回滚

### 第二批：渲染性能

**新增文件：**
- `src/composables/useRoutePrefetcher.ts`
- `src/utils/workerPool.ts`
- `src/composables/useTransitionOrchestrator.ts`

**修改文件：**
- `src/App.vue` — Suspense + KeepAlive
- `src/router/index.ts` — 路由过渡优化
- `src/components/common/SkeletonLoader.vue` — 路由骨架屏变体

**验证标准：**
- 路由切换: 无白屏，skeleton → 内容平滑过渡
- hover 预加载: 鼠标悬停导航后即刻触发 import
- Web Worker: 大量数据处理不阻塞主线程

### 第三批：交互丝滑化

**新增文件：**
- `src/composables/useToastManager.ts`
- `src/directives/ripple.ts`

**修改文件：**
- `src/components/LoadingBar.vue` — 与过渡编排联动
- `src/styles/animations.css` — 新增动效
- 各操作组件 — 接入反馈闭环

**验证标准：**
- 同类错误合并: 3 个相同错误只显示 1 条
- 操作反馈: 每次操作都有明确的进行中/成功/失败指示
- 微动效: 有动画不卡顿，`prefers-reduced-motion` 正常工作

## 7. 风险管理

| 风险 | 影响 | 缓解措施 |
|:----|:----|:---------|
| SWR 缓存返回旧数据 | 用户看到过时信息 | TTL 合理配置 + revalidateOnFocus |
| 乐观更新回滚失败 | 数据不一致 | 版本号冲突检测 + 手动刷新入口 |
| Web Worker 通信开销 > 计算收益 | 性能反而下降 | 仅迁移 >100ms 的任务，保守评估 |
| Element Plus 升级兼容 | 组件行为变化 | 锁定版本，改造前充分测试 |
| 动画过多导致性能下降 | 低端设备卡顿 | `prefers-reduced-motion` 媒体查询 + will-change 优化 |