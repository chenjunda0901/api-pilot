import { test, expect } from '@playwright/test'

test.describe('调试完整页面', () => {
  test('检查登录页面完整HTML和控制台错误', async ({ page }) => {
    const consoleErrors: string[] = []
    const consoleLogs: string[] = []
    
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text())
      }
      consoleLogs.push(`[${msg.type()}] ${msg.text()}`)
    })
    
    page.on('pageerror', (error) => {
      consoleErrors.push(`Page error: ${error.message}`)
    })
    
    console.log('访问登录页面...')
    await page.goto('http://127.0.0.1:8081/#/login', { waitUntil: 'networkidle' })
    
    await page.waitForTimeout(10000)
    
    const url = page.url()
    console.log('当前 URL:', url)
    
    const title = await page.title()
    console.log('页面标题:', title)
    
    const fullHTML = await page.content()
    console.log('完整 HTML 长度:', fullHTML.length)
    console.log('\n=== 完整 HTML (前 2000 字符) ===')
    console.log(fullHTML.substring(0, 2000))
    
    console.log('\n=== 控制台错误 ===')
    console.log(consoleErrors.length > 0 ? consoleErrors.join('\n') : '无错误')
    
    console.log('\n=== 所有控制台日志 (前 20 条) ===')
    console.log(consoleLogs.slice(0, 20).join('\n'))
    
    const bodyText = await page.locator('body').textContent()
    console.log('\n=== body 文本 ===')
    console.log(bodyText)
    
    await page.screenshot({ path: 'debug-full-page.png', fullPage: true })
  })
})
