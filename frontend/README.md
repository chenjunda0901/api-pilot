# API Pilot 前端

基于 Vue 3 + TypeScript + Vite 的 API 测试管理平台前端项目。

## 技术栈

- **框架**: Vue 3.5 + TypeScript 5.7
- **构建**: Vite 6
- **UI组件**: Element Plus 2.9
- **状态管理**: Pinia
- **HTTP客户端**: Axios
- **图表**: ECharts

## 快速开始

```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build
```

## 项目结构

```
src/
├── api/           # API 请求
├── assets/        # 静态资源
├── components/    # 组件
│   ├── common/    # 通用组件
│   └── tree/      # 树形组件
├── layout/        # 布局组件
├── router/        # 路由配置
├── stores/        # Pinia 状态
├── styles/        # 样式文件
├── utils/         # 工具函数
└── views/         # 页面视图
```

## UI 工具类

项目提供了一套完整的 CSS 工具类，用于快速构建界面。

### 排版工具类

```html
<!-- 字号层级 -->
<span class="text-2xs">10px</span>
<span class="text-xs">12px</span>
<span class="text-sm">14px</span>
<span class="text-base">16px</span>
<span class="text-lg">18px</span>
<span class="text-xl">20px</span>
<span class="text-2xl">24px</span>
<span class="text-3xl">30px</span>

<!-- 行高 -->
<p class="leading-tight">标题行高 1.25</p>
<p class="leading-normal">正文行高 1.5</p>
<p class="leading-relaxed">长文行高 1.75</p>

<!-- 字重 -->
<span class="font-normal">400</span>
<span class="font-medium">500</span>
<span class="font-semibold">600</span>
<span class="font-bold">700</span>
<span class="font-extrabold">800</span>
```

### 布局工具类

```html
<!-- Flex 布局 -->
<div class="flex">flex 容器</div>
<div class="flex-col">垂直排列</div>
<div class="flex items-center justify-between">两端对齐</div>

<!-- 间距 -->
<div class="p-4">内边距 16px</div>
<div class="m-4">外边距 16px</div>
<div class="flex gap-4">间距 16px</div>
```

### 组件工具类

```html
<!-- 按钮 -->
<button class="btn btn-primary">主要按钮</button>
<button class="btn btn-secondary">次要按钮</button>
<button class="btn btn-ghost">文字按钮</button>
<button class="btn btn-danger">危险按钮</button>

<!-- 表单 -->
<div class="form-group">
  <label class="form-label">用户名</label>
  <input class="input" placeholder="请输入" />
  <span class="form-hint">3-20 个字符</span>
</div>

<!-- 标签和徽章 -->
<span class="tag tag-success">成功</span>
<span class="badge badge-primary">1</span>

<!-- 列表项 -->
<div class="list-item">
  <div class="list-item-icon">📄</div>
  <div class="list-item-content">
    <div class="list-item-title">标题</div>
    <div class="list-item-desc">描述</div>
  </div>
</div>

<!-- 空状态 -->
<div class="empty-state">
  <div class="empty-state-icon">📋</div>
  <div class="empty-state-title">暂无数据</div>
  <div class="empty-state-desc">描述文字</div>
</div>
```

### 暗色模式

所有工具类自动支持暗色模式，无需额外适配。

### 示例组件

查看 `src/components/UIShowcase.vue` 了解所有工具类的实际效果。

## 开发指南

### 添加新组件

1. 在 `src/components/` 目录创建 `.vue` 文件
2. 使用 `<script setup lang="ts">` 语法
3. 优先使用工具类，减少 scoped 样式
4. 使用 CSS 变量确保暗色模式兼容

### 样式规范

1. **优先使用工具类**: 通用样式使用工具类
2. **使用 CSS 变量**: 避免硬编码颜色和尺寸
3. **暗色模式**: 自定义样式需适配暗色模式
4. **响应式**: 使用媒体查询支持移动端

### 常用 CSS 变量

```css
/* 颜色 */
--color-primary-500    /* 主色 */
--color-success        /* 成功色 */
--color-warning        /* 警告色 */
--color-error          /* 错误色 */
--color-info           /* 信息色 */

/* 文字 */
--text-primary         /* 主文字 */
--text-secondary       /* 次文字 */
--text-tertiary        /* 辅助文字 */
--text-muted           /* 弱化文字 */

/* 背景 */
--surface-page         /* 页面背景 */
--surface-card         /* 卡片背景 */
--surface-hover        /* 悬停背景 */

/* 边框 */
--border-default       /* 默认边框 */
--border-hairline      /* 细边框 */

/* 间距 */
--space-1 到 --space-12  /* 4px - 48px */

/* 圆角 */
--radius-sm            /* 小圆角 */
--radius-md            /* 中圆角 */
--radius-lg            /* 大圆角 */
```

## 浏览器支持

- Chrome >= 87
- Firefox >= 78
- Edge >= 88
- Safari >= 14

## 相关文档

- [UI 工具类使用指南](./docs/ui-utilities-guide.md)
- [组件库文档](./docs/components.md)
- [设计规范](./docs/design-system.md)
