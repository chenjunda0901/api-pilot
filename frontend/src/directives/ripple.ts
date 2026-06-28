import type { Directive } from 'vue'

/**
 * v-ripple 点击波纹指令
 *
 * 为按钮/卡片添加 Material Design 风格的水波纹点击反馈。
 *
 * 用法:
 *   <el-button v-ripple>点击</el-button>
 *   <div v-ripple class="card">可点击卡片</div>
 */

export const vRipple: Directive = {
  mounted(el: HTMLElement) {
    el.style.position = 'relative'
    el.style.overflow = 'hidden'
    el.style.cursor = el.style.cursor || 'pointer'

    el.addEventListener('click', createRipple)
  },

  unmounted(el: HTMLElement) {
    el.removeEventListener('click', createRipple)
  },
}

function createRipple(this: HTMLElement, event: MouseEvent) {
  const el = this
  const rect = el.getBoundingClientRect()

  const ripple = document.createElement('span')
  ripple.className = 'v-ripple-element'

  const size = Math.max(rect.width, rect.height)
  const x = event.clientX - rect.left - size / 2
  const y = event.clientY - rect.top - size / 2

  ripple.style.cssText = `
    position: absolute;
    width: ${size}px;
    height: ${size}px;
    left: ${x}px;
    top: ${y}px;
    border-radius: 50%;
    background: currentColor;
    opacity: 0.15;
    transform: scale(0);
    animation: ripple-animation 0.5s ease-out forwards;
    pointer-events: none;
  `

  el.appendChild(ripple)

  // 动画结束后移除
  setTimeout(() => {
    ripple.remove()
  }, 600)
}