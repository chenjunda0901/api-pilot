import { test, expect } from '@playwright/test'
import { generateUniqueId, generateEmail, TEST_PASSWORDS } from './utils/test-utils'

test.describe('调试注册流程2', () => {
  test('注册后刷新页面', async ({ page }) => {
    const timestamp = generateUniqueId()
    const username = `debugreg2_${timestamp}`
    const nickname = `调试注册2_${timestamp}`
    const email = generateEmail(username)
    const password = TEST_PASSWORDS.strong

    const requests: string[] = []
    
    page.on('request', (request) => {
      if (request.url().includes('/api/')) {
        requests.push(`REQ: ${request.method()} ${request.url()}`)
      }
    })
    
    page.on('response', (response) => {
      if (response.url().includes('/api/')) {
        requests.push(`RES: ${response.status()} ${response.url()}`)
      }
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
    
    console.log('等待 5 秒...')
    await page.waitForTimeout(5000)
    
    const hash1 = await page.evaluate(() => window.location.hash)
    console.log('5秒后 hash:', hash1)
    
    console.log('\n=== API 请求 ===')
    console.log(requests.join('\n'))
    
    console.log('\n刷新页面...')
    await page.reload()
    await page.waitForTimeout(5000)
    
    const hash2 = await page.evaluate(() => window.location.hash)
    console.log('刷新后 hash:', hash2)
    
    const bodyText = await page.locator('body').textContent()
    console.log('刷新后 body 长度:', bodyText?.length)
    
    const inputs = page.locator('input')
    console.log('刷新后输入框数量:', await inputs.count())
    
    await page.screenshot({ path: 'debug-register-after-refresh.png', fullPage: true })
  })
})
