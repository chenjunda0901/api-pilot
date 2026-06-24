import { test, expect } from '@playwright/test'
import { generateUniqueId, generateEmail, TEST_PASSWORDS } from './utils/test-utils'

test.describe('调试登录流程', () => {
  test('注册后立即登录', async ({ page }) => {
    const timestamp = generateUniqueId()
    const username = `debuglogin_${timestamp}`
    const nickname = `调试登录${timestamp}`
    const email = generateEmail(username)
    const password = TEST_PASSWORDS.strong

    const requests: { url: string; method: string; status: number; responseBody?: string }[] = []
    
    page.on('response', async (response) => {
      if (response.url().includes('/api/')) {
        const req = {
          url: response.url(),
          method: response.request().method(),
          status: response.status(),
        }
        try {
          const body = await response.text()
          if (body.length < 500) {
            (req as any).responseBody = body
          }
        } catch {}
        requests.push(req)
      }
    })

    console.log('=== 第一步：注册用户 ===')
    console.log('用户名:', username)
    console.log('密码:', password)
    
    await page.goto('http://127.0.0.1:8081/#/register')
    await page.waitForTimeout(3000)
    
    await page.fill('#reg-username', username)
    await page.fill('#reg-password', password)
    await page.fill('#reg-confirm-password', password)
    await page.fill('#reg-nickname', nickname)
    await page.fill('#reg-email', email)
    
    console.log('点击注册按钮...')
    await page.click('.register-btn')
    
    await page.waitForTimeout(5000)
    
    const hash1 = await page.evaluate(() => window.location.hash)
    console.log('注册后 hash:', hash1)
    
    console.log('\n=== 第二步：退出登录 ===')
    
    let userMenuFound = false
    const userMenuSelectors = [
      '.user-avatar',
      '.user-menu-trigger',
      '[class*="user"]',
      '.top-bar .el-avatar',
    ]
    
    for (const selector of userMenuSelectors) {
      const el = page.locator(selector).first()
      if (await el.isVisible()) {
        console.log(`找到用户菜单: ${selector}`)
        await el.click()
        await page.waitForTimeout(1000)
        userMenuFound = true
        break
      }
    }
    
    if (!userMenuFound) {
      console.log('未找到用户菜单，尝试刷新页面...')
      await page.reload()
      await page.waitForTimeout(3000)
      
      for (const selector of userMenuSelectors) {
        const el = page.locator(selector).first()
        if (await el.isVisible()) {
          console.log(`刷新后找到用户菜单: ${selector}`)
          await el.click()
          await page.waitForTimeout(1000)
          userMenuFound = true
          break
        }
      }
    }
    
    if (userMenuFound) {
      const logoutBtn = page.getByText('退出登录').first()
      if (await logoutBtn.isVisible()) {
        console.log('点击退出登录...')
        await logoutBtn.click()
        await page.waitForTimeout(3000)
      }
    }
    
    const hash2 = await page.evaluate(() => window.location.hash)
    console.log('退出后 hash:', hash2)
    
    console.log('\n=== 第三步：重新登录 ===')
    
    if (!hash2.includes('login')) {
      console.log('手动导航到登录页...')
      await page.goto('http://127.0.0.1:8081/#/login')
      await page.waitForTimeout(3000)
    }
    
    const loginInput = page.locator('#login-username')
    if (await loginInput.isVisible()) {
      console.log('找到登录输入框')
    } else {
      console.log('未找到登录输入框，刷新页面...')
      await page.reload()
      await page.waitForTimeout(3000)
    }
    
    console.log('填写登录信息...')
    await page.fill('#login-username', username)
    await page.fill('#login-password', password)
    
    console.log('点击登录按钮...')
    await page.click('.login-btn')
    
    console.log('等待 10 秒...')
    for (let i = 0; i < 10; i++) {
      await page.waitForTimeout(1000)
      const hash = await page.evaluate(() => window.location.hash)
      console.log(`  ${i + 1}s: hash=${hash}`)
    }
    
    console.log('\n=== API 请求记录 ===')
    requests.forEach((req, i) => {
      console.log(`${i + 1}. ${req.method} ${req.status} ${req.url}`)
      if (req.responseBody) {
        console.log(`   响应: ${req.responseBody}`)
      }
    })
    
    const finalHash = await page.evaluate(() => window.location.hash)
    console.log('\n最终 hash:', finalHash)
    
    const hasToast = await page.locator('.el-message').count()
    if (hasToast > 0) {
      const toastText = await page.locator('.el-message').first().textContent()
      console.log('Toast 内容:', toastText)
    }
    
    await page.screenshot({ path: 'debug-login-final.png', fullPage: true })
  })
})
