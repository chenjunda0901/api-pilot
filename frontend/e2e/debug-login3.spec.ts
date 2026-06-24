import { test, expect } from '@playwright/test'
import { TestUtils, generateUniqueId, generateEmail, TEST_PASSWORDS } from './utils/test-utils'

test.describe('调试 utils.loginUser', () => {
  const timestamp = generateUniqueId()
  const username = `testlogin_${timestamp}`
  const nickname = `测试登录${timestamp}`
  const email = generateEmail(username)
  const password = TEST_PASSWORDS.strong

  console.log('用户名:', username)
  console.log('用户名长度:', username.length)

  test('先注册再用 utils.loginUser 登录', async ({ page }) => {
    const utils = new TestUtils(page)

    console.log('=== 第一步：注册 ===')
    await utils.registerUser(username, password, nickname, email)
    
    const hash1 = await page.evaluate(() => window.location.hash)
    console.log('注册后 hash:', hash1)

    console.log('=== 第二步：导航到登录页 ===')
    await utils.navigateTo('/login')
    
    const hash2 = await page.evaluate(() => window.location.hash)
    console.log('导航后 hash:', hash2)

    console.log('=== 第三步：用 utils.loginUser 登录 ===')
    try {
      await utils.loginUser(username, password)
      console.log('登录成功！')
    } catch (e) {
      console.log('登录失败:', e)
      
      const currentHash = await page.evaluate(() => window.location.hash)
      console.log('当前 hash:', currentHash)
      
      const hasToast = await page.locator('.el-message').count()
      if (hasToast > 0) {
        const toastText = await page.locator('.el-message').first().textContent()
        console.log('Toast 内容:', toastText)
      }
      
      await page.screenshot({ path: 'debug-login3-failed.png', fullPage: true })
    }
  })
})
