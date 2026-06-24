import { test, expect } from '@playwright/test'
import { TestUtils, generateUniqueId, generateEmail, TEST_PASSWORDS } from './utils/test-utils'

test.describe('调试登录', () => {
  let utils: TestUtils
  const timestamp = generateUniqueId()
  const username = `debug_${timestamp}`
  const nickname = `调试用户${timestamp}`
  const email = generateEmail(username)
  const password = TEST_PASSWORDS.strong

  test.beforeEach(async ({ page }) => {
    utils = new TestUtils(page)
  })

  test('调试注册和登录', async ({ page }) => {
    await test.step('1. 注册用户', async () => {
      console.log('开始注册用户:', username)
      await utils.navigateTo('/register')
      await page.fill('#reg-username', username)
      await page.fill('#reg-password', password)
      await page.fill('#reg-confirm-password', password)
      await page.fill('#reg-nickname', nickname)
      await page.fill('#reg-email', email)
      
      console.log('点击注册按钮...')
      await page.click('.register-btn')
      
      await page.waitForTimeout(5000)
      
      const url = page.url()
      console.log('注册后的 URL:', url)
      
      const hash = await page.evaluate(() => window.location.hash)
      console.log('注册后的 hash:', hash)
      
      const bodyText = await page.locator('body').textContent()
      console.log('页面内容长度:', bodyText?.length)
      
      await page.screenshot({ path: 'debug-after-register.png', fullPage: true })
    })

    await test.step('2. 退出登录（如果已登录）', async () => {
      const hash = await page.evaluate(() => window.location.hash)
      if (hash.includes('dashboard') || hash.includes('projects')) {
        console.log('尝试退出登录...')
        try {
          const userMenu = page.locator('.user-avatar, .user-menu-trigger, [class*="user"]').first()
          if (await userMenu.isVisible()) {
            await userMenu.click()
            await page.waitForTimeout(1000)
            const logoutBtn = page.getByText('退出登录').first()
            if (await logoutBtn.isVisible()) {
              await logoutBtn.click()
              await page.waitForTimeout(2000)
            }
          }
        } catch (e) {
          console.log('退出登录失败:', e)
        }
      }
    })

    await test.step('3. 尝试登录', async () => {
      console.log('开始登录用户:', username)
      await utils.navigateTo('/login')
      
      const urlBefore = page.url()
      console.log('登录前 URL:', urlBefore)
      
      await page.fill('#login-username', username)
      await page.fill('#login-password', password)
      
      console.log('点击登录按钮...')
      await page.click('.login-btn')
      
      await page.waitForTimeout(5000)
      
      const urlAfter = page.url()
      console.log('登录后 URL:', urlAfter)
      
      const hash = await page.evaluate(() => window.location.hash)
      console.log('登录后 hash:', hash)
      
      const bodyText = await page.locator('body').textContent()
      console.log('页面内容长度:', bodyText?.length)
      
      const pageTitle = await page.title()
      console.log('页面标题:', pageTitle)
      
      await page.screenshot({ path: 'debug-after-login.png', fullPage: true })
      
      const hasError = await page.locator('.el-message, .error-message, [class*="error"]').count()
      console.log('错误消息数量:', hasError)
      
      if (hasError > 0) {
        const errorText = await page.locator('.el-message, .error-message').first().textContent()
        console.log('错误消息内容:', errorText)
      }
    })
  })
})
