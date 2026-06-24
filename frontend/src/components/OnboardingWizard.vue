<template>
  <Teleport to="body">
    <Transition name="wizard-overlay">
      <div v-if="visible" class="onboarding-overlay">
        <div class="onboarding-dialog">
          <!-- 步骤指示器 -->
          <div class="wizard-steps">
            <div
              v-for="(step, i) in steps"
              :key="i"
              class="wizard-step"
              :class="{ active: currentStep === i, done: currentStep > i }"
            >
              <div class="step-circle">
                <span v-if="currentStep > i" class="step-check">✓</span>
                <span v-else>{{ i + 1 }}</span>
              </div>
              <div class="step-line" v-if="i < steps.length - 1" :class="{ filled: currentStep > i }"></div>
              <span class="step-label">{{ step.label }}</span>
            </div>
          </div>

          <!-- 步骤内容 -->
          <div class="wizard-body">
            <!-- 步骤 1: 创建项目 -->
            <div v-if="currentStep === 0" class="wizard-content">
              <div class="wizard-illustration">
                <svg viewBox="0 0 120 80" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                  <rect x="10" y="10" width="100" height="60" rx="8" stroke="var(--primary-300)" stroke-width="2.5" fill="var(--primary-50)"/>
                  <path d="M10 30h100" stroke="var(--primary-200)" stroke-width="2"/>
                  <rect x="20" y="38" width="35" height="24" rx="4" fill="var(--primary-200)" stroke="var(--primary-300)" stroke-width="1.5"/>
                  <rect x="62" y="38" width="38" height="10" rx="3" fill="var(--primary-100)" stroke="var(--primary-200)" stroke-width="1"/>
                  <rect x="62" y="52" width="22" height="10" rx="3" fill="var(--primary-100)" stroke="var(--primary-200)" stroke-width="1"/>
                </svg>
              </div>
              <h2 class="wizard-title">创建项目</h2>
              <p class="wizard-desc">项目是您组织和管理 API 接口的工作空间。创建第一个项目，开始您的 API 测试之旅。</p>
              <div class="wizard-tips">
                <p class="wizard-tip-title">快速上手：</p>
                <ul>
                  <li>点击左侧 <strong>"新建项目"</strong> 按钮创建项目</li>
                  <li>为项目设置一个清晰的名称，例如 "电商平台" 或 "SaaS 后端"</li>
                  <li>在项目设置中配置环境变量（如开发/测试/生产环境的 base URL）</li>
                  <li>一个项目可以包含多个接口目录，方便按模块分类管理</li>
                </ul>
              </div>
            </div>

            <!-- 步骤 2: 添加 API -->
            <div v-if="currentStep === 1" class="wizard-content">
              <div class="wizard-illustration">
                <svg viewBox="0 0 120 80" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                  <circle cx="44" cy="40" r="28" stroke="var(--primary-200)" stroke-width="2.5" fill="var(--primary-50)"/>
                  <path d="M64 60l18 18" stroke="var(--primary-300)" stroke-width="2.5" stroke-linecap="round"/>
                  <circle cx="44" cy="40" r="6" fill="var(--primary-200)"/>
                  <line x1="28" y1="62" x2="18" y2="72" stroke="var(--primary-100)" stroke-width="2" stroke-linecap="round"/>
                  <line x1="22" y1="24" x2="16" y2="14" stroke="var(--primary-100)" stroke-width="2" stroke-linecap="round"/>
                </svg>
              </div>
              <h2 class="wizard-title">添加 API 接口</h2>
              <p class="wizard-desc">通过手动创建或 OpenAPI/Swagger 文件导入来添加 API 接口。您可以在项目设置中配置导入方式。</p>
              <div class="wizard-tips">
                <p class="wizard-tip-title">多种添加方式：</p>
                <ul>
                  <li><strong>手动创建：</strong>在左侧目录树右键 → 新建接口，填写请求方法和路径</li>
                  <li><strong>OpenAPI 导入：</strong>支持 Swagger 2.0 / OpenAPI 3.0 格式的 JSON/YAML 文件</li>
                  <li><strong>cURL 导入：</strong>在接口详情页点击 "导入 cURL"，粘贴 curl 命令即可</li>
                  <li>为接口配置请求头、查询参数、请求体、认证方式等完整信息</li>
                </ul>
              </div>
            </div>

            <!-- 步骤 3: 发送测试请求 -->
            <div v-if="currentStep === 2" class="wizard-content">
              <div class="wizard-illustration">
                <svg viewBox="0 0 120 80" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                  <path d="M18 40l18 18L62 24" stroke="var(--success)" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
                  <path d="M40 20l8 4-8 4" stroke="var(--primary-400)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
                  <rect x="54" y="50" width="48" height="22" rx="6" stroke="var(--primary-200)" stroke-width="2.5" fill="var(--primary-50)"/>
                  <rect x="60" y="56" width="36" height="4" rx="2" fill="var(--primary-100)"/>
                  <rect x="60" y="64" width="24" height="4" rx="2" fill="var(--primary-50)"/>
                </svg>
              </div>
              <h2 class="wizard-title">调试与场景测试</h2>
              <p class="wizard-desc">选择接口，配置环境变量，一键发送测试请求并实时查看响应结果。还可以保存测试用例，用于回归测试和场景编排。</p>
              <div class="wizard-tips">
                <p class="wizard-tip-title">核心功能：</p>
                <ul>
                  <li><strong>单接口调试：</strong>在接口详情页填写参数后点击发送，实时查看响应状态码、Headers 和 Body</li>
                  <li><strong>变量替换：</strong>使用 <code>{{变量名}}</code> 语法在 URL、Header、Body 中引用环境变量</li>
                  <li><strong>场景编排：</strong>将多个接口按顺序组成测试场景，支持条件判断、循环、等待等控制流</li>
                  <li><strong>断言验证：</strong>为每个步骤添加状态码、响应体 JSONPath、响应时间等断言规则</li>
                </ul>
              </div>
            </div>

            <!-- 步骤 4: 查看测试报告 -->
            <div v-if="currentStep === 3" class="wizard-content">
              <div class="wizard-illustration">
                <svg viewBox="0 0 120 80" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                  <rect x="16" y="8" width="88" height="64" rx="6" stroke="var(--primary-200)" stroke-width="2.5" fill="var(--primary-50)"/>
                  <rect x="16" y="8" width="88" height="14" rx="6" fill="var(--primary-100)" stroke="var(--primary-200)" stroke-width="2.5"/>
                  <rect x="24" y="30" width="12" height="30" rx="2" fill="var(--success)"/>
                  <rect x="42" y="38" width="12" height="22" rx="2" fill="var(--primary-300)"/>
                  <rect x="60" y="26" width="12" height="34" rx="2" fill="var(--success)"/>
                  <rect x="78" y="44" width="12" height="16" rx="2" fill="var(--primary-200)"/>
                  <circle cx="96" cy="20" r="6" fill="var(--success)" stroke="var(--primary-200)" stroke-width="1.5"/>
                  <path d="M93 20l2 2 4-4" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </div>
              <h2 class="wizard-title">报告与 Mock 服务</h2>
              <p class="wizard-desc">每次执行后自动生成测试报告，包含通过率、响应时间、断言结果等详细数据。支持历史对比和趋势分析，帮助您持续改进 API 质量。</p>
              <div class="wizard-tips">
                <p class="wizard-tip-title">更多功能：</p>
                <ul>
                  <li><strong>测试报告：</strong>查看每次场景执行的详细报告，支持导出 Excel/PDF/CSV/JUnit 格式</li>
                  <li><strong>历史对比：</strong>对比两次执行报告，快速发现通过率变化和性能退化</li>
                  <li><strong>Mock 服务：</strong>为接口生成模拟数据，前端开发无需等待后端接口就绪</li>
                  <li><strong>定时执行：</strong>配置 Cron 表达式，让场景按计划自动运行并发送通知</li>
                </ul>
              </div>
            </div>
          </div>

          <!-- 底部操作 -->
          <div class="wizard-footer">
            <button class="wizard-btn btn-skip" @click="handleSkip">
              {{ currentStep < steps.length - 1 ? '跳过' : '关闭' }}
            </button>
            <div class="wizard-footer-right">
              <button v-if="currentStep > 0" class="wizard-btn btn-prev" @click="currentStep = Math.max(currentStep - 1, 0)">
                上一步
              </button>
              <button
                v-if="currentStep < steps.length - 1"
                class="wizard-btn btn-next"
                @click="currentStep = Math.min(currentStep + 1, steps.length - 1)"
              >
                下一步
              </button>
              <button
                v-else
                class="wizard-btn btn-finish"
                @click="handleFinish"
              >
                开始使用
              </button>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const emit = defineEmits<{
  close: []
  finish: []
}>()

withDefaults(defineProps<{
  visible?: boolean
}>(), {
  visible: false,
})

const steps = [
  { label: '创建项目' },
  { label: '添加 API' },
  { label: '发送测试' },
  { label: '查看报告' },
]

const currentStep = ref(0)

function handleSkip() {
  currentStep.value = Math.min(currentStep.value, steps.length - 1)
  localStorage.setItem('api_pilot_onboarding_done', '1')
  emit('close')
}

function handleFinish() {
  currentStep.value = Math.min(currentStep.value, steps.length - 1)
  localStorage.setItem('api_pilot_onboarding_done', '1')
  emit('finish')
}
</script>

<style scoped>
/* ── 遮罩层 ── */
.onboarding-overlay {
  position: fixed;
  inset: 0;
  z-index: var(--z-modal);
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--alpha-overlay);
  backdrop-filter: blur(6px);
}

/* ── 弹窗 ── */
.onboarding-dialog {
  width: min(520px, 90vw);
  background: var(--surface-card);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-pop);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  animation: dialog-in var(--duration-slow) var(--ease-spring);
}

@keyframes dialog-in {
  from {
    opacity: 0;
    transform: translateY(20px) scale(0.96);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

/* ── Transition ── */
.wizard-overlay-enter-active {
  transition: opacity var(--duration-base) var(--ease-out);
}
.wizard-overlay-leave-active {
  transition: opacity var(--duration-fast) var(--ease-in);
}
.wizard-overlay-enter-from,
.wizard-overlay-leave-to {
  opacity: 0;
}

/* ── 步骤指示器 ── */
.wizard-steps {
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: var(--space-8) var(--space-4) var(--space-6);
  gap: 0;
}

.wizard-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
  gap: var(--space-2);
}

.step-circle {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-sm);
  font-weight: var(--weight-bold);
  border: 2px solid var(--border-subtle);
  color: var(--text-muted);
  background: var(--surface-card);
  transition: all var(--duration-base) var(--ease-smooth);
  position: relative;
  z-index: 1;
}

.wizard-step.active .step-circle {
  border-color: var(--primary-500);
  color: var(--primary-500);
  background: var(--color-primary-alpha-08);
  box-shadow: 0 0 0 4px var(--color-primary-alpha-12);
}

.wizard-step.done .step-circle {
  border-color: var(--success);
  color: var(--success);
  background: var(--success-bg);
}

.step-check {
  font-size: var(--text-sm);
  line-height: 1;
}

.step-line {
  position: absolute;
  top: 18px;
  left: calc(50% + 22px);
  width: 80px;
  height: 2px;
  background: var(--border-subtle);
  transition: background var(--duration-base) var(--ease-smooth);
}

.step-line.filled {
  background: var(--success);
}

.step-label {
  font-size: var(--text-xs);
  color: var(--text-muted);
  white-space: nowrap;
  transition: color var(--duration-base) var(--ease-smooth);
}

.wizard-step.active .step-label {
  color: var(--text-primary);
  font-weight: var(--weight-semibold);
}

.wizard-step.done .step-label {
  color: var(--text-secondary);
}

/* ── 内容区 ── */
.wizard-body {
  padding: 0 var(--space-8) var(--space-6);
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.wizard-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: var(--space-4);
}

.wizard-illustration {
  width: 100px;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: var(--space-2);
}

.wizard-illustration svg {
  width: 100%;
  height: 100%;
}

.wizard-title {
  font-size: var(--text-xl);
  font-weight: var(--weight-bold);
  color: var(--text-primary);
  margin: 0;
  line-height: var(--leading-tight);
}

.wizard-desc {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  line-height: var(--leading-relaxed);
  margin: 0;
  max-width: 380px;
}

/* 快速上手提示 */
.wizard-tips {
  margin-top: var(--space-2);
  padding: var(--space-3) var(--space-4);
  background: var(--surface-nested);
  border-radius: var(--radius-md);
  text-align: left;
  width: 100%;
  max-width: 380px;
}
.wizard-tip-title {
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  color: var(--primary-600);
  margin: 0 0 var(--space-2);
}
.wizard-tips ul {
  margin: 0;
  padding-left: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}
.wizard-tips li {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  line-height: var(--leading-relaxed);
}
.wizard-tips li strong {
  color: var(--text-primary);
  font-weight: var(--weight-semibold);
}
.wizard-tips li code {
  font-family: var(--font-mono, monospace);
  font-size: var(--text-xs);
  background: var(--color-primary-alpha-08);
  color: var(--primary-600);
  padding: 1px 4px;
  border-radius: var(--radius-xs);
}

/* ── 底部操作栏 ── */
.wizard-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4) var(--space-6);
  border-top: 1px solid var(--border-subtle);
  background: var(--surface-nested);
}

.wizard-footer-right {
  display: flex;
  gap: var(--space-3);
}

.wizard-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-2) var(--space-5);
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  font-family: inherit;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-smooth);
  border: 1px solid transparent;
  min-height: 36px;
  line-height: 1.5;
}

.wizard-btn:active {
  transform: scale(var(--press-scale));
}

.btn-skip {
  background: transparent;
  color: var(--text-muted);
  border-color: transparent;
}

.btn-skip:hover {
  color: var(--text-secondary);
}

.btn-prev {
  background: var(--surface-card);
  color: var(--text-secondary);
  border-color: var(--border-default);
}

.btn-prev:hover {
  background: var(--surface-hover);
  color: var(--text-primary);
}

.btn-next {
  background: var(--primary-500);
  color: var(--text-inverse);
  border: none;
  box-shadow: 0 2px 8px var(--color-primary-alpha-18);
}

.btn-next:hover {
  background: var(--primary-400);
  box-shadow: 0 4px 16px var(--color-primary-alpha-30);
}

.btn-finish {
  background: var(--grad-primary);
  color: var(--text-inverse);
  border: none;
  box-shadow: 0 2px 8px var(--color-primary-alpha-18);
}

.btn-finish:hover {
  box-shadow: 0 4px 16px var(--color-primary-alpha-30), 0 2px 6px var(--color-primary-alpha-15);
}

/* ── 暗色模式 ── */
html.dark .onboarding-dialog {
  background: var(--surface-card);
  box-shadow: var(--shadow-pop);
}

html.dark .wizard-footer {
  background: var(--surface-nested);
}

html.dark .step-circle {
  background: var(--surface-card);
  border-color: var(--border-subtle);
}

html.dark .wizard-step.active .step-circle {
  border-color: var(--primary-400);
  color: var(--primary-400);
  background: var(--color-primary-alpha-12);
}

html.dark .wizard-tips {
  background: var(--surface-nested);
}
html.dark .wizard-tip-title {
  color: var(--primary-400);
}
html.dark .wizard-tips li code {
  background: var(--color-primary-alpha-12);
  color: var(--primary-400);
}
</style>