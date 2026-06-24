import { test, expect } from '@playwright/test'
import { generateUniqueId, generateEmail, TEST_PASSWORDS } from './utils/test-utils'

test.describe('调试注册流程', () => {
  test('注册后查看页面状态', async ({ page }) => {
    const timestamp = generateUniqueId()
    const username = `debugreg_${timestamp}`
    const nickname = `调试注册${timestamp}`
    const email = generateEmail(username)
    const password = TEST_PASSWORDS.strong

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

    console.log('访问注册页面...')
    await page.goto('http://127.0.0.1:8081/#/register')
    await page.waitForTimeout(3000)
    
    console.log('填写注册表单...')
    await page.fill('#reg-username', username)
    await page.fill('#reg-password', password)
    await page.fill('#reg-confirm-password', password)
    await page.fill('#reg-nickname', nickname)
    await page.fill('#reg-email', email)
    
    console.log('点击注册按钮...')
    await page.click('.register-btn')
    
    console.log('等待 10 秒...')
    for (let i = 0; i < 10; i++) {
      await page.waitForTimeout(1000)
      const hash = await page.evaluate(() => window.location.hash)
      const url = page.url()
      console.log(`  ${i + 1}s: hash=${hash}, url=${url}`)
      
      const bodyText = await page.locator('body').textContent()
      console.log(`  body 文本长度: ${bodyText?.length}`)
    }
    
    console.log('\n=== 控制台错误 ===')
    console.log(consoleErrors.length > 0 ? consoleErrors.join('\n') : '无错误')
    
    console.log('\n=== 截图保存 ===')
    await page.screenshot({ path: 'debug-register-result.png', fullPage: true })
    
    const hash = await page.evaluate(() => window.location.hash)
    console.log('\n最终 hash:', hash)
    
    const hasToast = await page.locator('.el-message').count()
    console.log('Toast 数量:', hasToast)
    if (hasToast > 0) {
      const toastText = await page.locator('.el-message').first().textContent()
      console.log('Toast 内容:', toastText)
    }
  })
})
