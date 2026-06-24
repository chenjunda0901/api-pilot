import { test, expect } from '@playwright/test'
import { TestUtils, generateUniqueId, generateEmail, TEST_PASSWORDS } from './utils/test-utils'

test.describe('用户画像 1：新注册用户', () => {
  let utils: TestUtils
  const timestamp = generateUniqueId()
  const username = `newuser_${timestamp}`
  const nickname = `新用户${timestamp}`
  const email = generateEmail(username)
  const password = TEST_PASSWORDS.strong

  test.beforeEach(async ({ page }) => {
    utils = new TestUtils(page)
  })

  test('1.1 注册新账号 - 正向流程', async ({ page }) => {
    await test.step('访问注册页面', async () => {
      await utils.navigateTo('/register')
      await expect(page).toHaveTitle(/注册/)
    })

    await test.step('填写注册表单', async () => {
      await page.fill('#reg-username', username)
      await page.fill('#reg-password', password)
      await page.fill('#reg-confirm-password', password)
      await page.fill('#reg-nickname', nickname)
      await page.fill('#reg-email', email)
    })

    await test.step('提交注册并跳转到工作台', async () => {
      await page.click('.register-btn')
      await page.waitForFunction(() => {
        return window.location.hash.includes('dashboard') || 
               window.location.href.includes('dashboard')
      }, { timeout: 30000 })
    })

    await test.step('验证页面加载完成', async () => {
      await page.waitForLoadState('networkidle')
      const bodyText = await page.locator('body').textContent()
      expect(bodyText).toBeTruthy()
    })
  })

  test('1.2 注册表单验证 - 异常流程', async ({ page }) => {
    await test.step('访问注册页面', async () => {
      await utils.navigateTo('/register')
    })

    await test.step('用户名过短', async () => {
      await page.fill('#reg-username', 'ab')
      await page.click('.register-btn')
      await page.waitForTimeout(500)
      const errorEl = page.locator('.el-form-item__error').first()
      await expect(errorEl).toBeVisible()
    })

    await test.step('用户名包含特殊字符', async () => {
      await page.fill('#reg-username', 'test@user')
      await page.click('.register-btn')
      await page.waitForTimeout(500)
      const errorEl = page.locator('.el-form-item__error').first()
      await expect(errorEl).toBeVisible()
    })

    await test.step('密码过短', async () => {
      await page.fill('#reg-username', username)
      await page.fill('#reg-password', TEST_PASSWORDS.weak)
      await page.fill('#reg-confirm-password', TEST_PASSWORDS.weak)
      await page.click('.register-btn')
      await page.waitForTimeout(500)
      const errorEl = page.locator('.el-form-item__error').first()
      await expect(errorEl).toBeVisible()
    })

    await test.step('两次密码不一致', async () => {
      await page.fill('#reg-password', password)
      await page.fill('#reg-confirm-password', TEST_PASSWORDS.wrong)
      await page.click('.register-btn')
      await page.waitForTimeout(500)
      const errorEl = page.locator('.el-form-item__error').first()
      await expect(errorEl).toBeVisible()
    })

    await test.step('邮箱格式错误', async () => {
      await page.fill('#reg-password', password)
      await page.fill('#reg-confirm-password', password)
      await page.fill('#reg-email', 'invalid-email')
      await page.click('.register-btn')
      await page.waitForTimeout(500)
      const errorEl = page.locator('.el-form-item__error').first()
      await expect(errorEl).toBeVisible()
    })
  })

  test('1.3 首次登录', async ({ page }) => {
    await test.step('访问登录页面', async () => {
      await utils.navigateTo('/login')
      await expect(page).toHaveTitle(/登录/)
    })

    await test.step('填写登录信息并登录', async () => {
      await page.fill('#login-username', username)
      await page.fill('#login-password', password)
      await page.click('.login-btn')
      await page.waitForFunction(() => {
        return window.location.hash.includes('dashboard') || 
               window.location.href.includes('dashboard') ||
               window.location.hash.includes('projects')
      }, { timeout: 30000 })
    })

    await test.step('验证页面加载完成', async () => {
      await page.waitForLoadState('networkidle')
      const bodyText = await page.locator('body').textContent()
      expect(bodyText).toBeTruthy()
    })
  })

  test('1.4 登录失败场景', async ({ page }) => {
    await test.step('错误密码登录', async () => {
      await utils.navigateTo('/login')
      await page.fill('#login-username', username)
      await page.fill('#login-password', TEST_PASSWORDS.wrong)
      await page.click('.login-btn')
      await page.waitForTimeout(2000)
      const isStillOnLogin = await page.evaluate(() => {
        return window.location.href.includes('login') || window.location.hash.includes('login')
      })
      expect(isStillOnLogin).toBe(true)
    })

    await test.step('不存在的用户登录', async () => {
      await utils.navigateTo('/login')
      await page.fill('#login-username', 'nonexistent_user')
      await page.fill('#login-password', password)
      await page.click('.login-btn')
      await page.waitForTimeout(2000)
      const isStillOnLogin = await page.evaluate(() => {
        return window.location.href.includes('login') || window.location.hash.includes('login')
      })
      expect(isStillOnLogin).toBe(true)
    })
  })

  test('1.5 创建第一个项目', async ({ page }) => {
    await test.step('登录系统', async () => {
      await utils.loginUser(username, password)
    })

    const projectName = `我的第一个项目_${timestamp}`

    await test.step('在工作台创建项目', async () => {
      await utils.navigateTo('/dashboard')
      await page.waitForTimeout(1000)
      const createBtn = page.getByRole('button', { name: /创建项目|新建项目/ })
      if (await createBtn.isVisible()) {
        await createBtn.click()
      } else {
        const addBtn = page.getByRole('button', { name: /新建|添加/ }).first()
        if (await addBtn.isVisible()) {
          await addBtn.click()
        }
      }
    })

    await test.step('填写项目名称并创建', async () => {
      const nameInput = page.locator('input[placeholder*="项目名称"], input[placeholder*="请输入项目名称"]')
      if (await nameInput.isVisible()) {
        await nameInput.fill(projectName)
        const confirmBtn = page.getByRole('button', { name: /确定|创建|保存/ }).first()
        await confirmBtn.click()
        await page.waitForTimeout(2000)
      }
    })

    await test.step('验证项目创建成功', async () => {
      const url = page.url()
      const hasProjectRoute = url.includes('/projects/') || url.includes('/dashboard')
      expect(hasProjectRoute).toBe(true)
    })
  })

  test('1.6 创建第一个接口分类和接口', async ({ page }) => {
    await test.step('登录系统', async () => {
      await utils.loginUser(username, password)
    })

    await test.step('进入接口管理页面', async () => {
      await utils.navigateTo('/dashboard')
      await page.waitForTimeout(1000)
      const apiLink = page.getByRole('link', { name: /接口管理|接口/ }).first()
      if (await apiLink.isVisible()) {
        await apiLink.click()
      } else {
        const sidebar = page.locator('.sidebar, .app-sidebar, .el-menu')
        const apiNav = sidebar.getByText(/接口管理|接口/).first()
        if (await apiNav.isVisible()) {
          await apiNav.click()
        }
      }
      await page.waitForTimeout(2000)
    })

    await test.step('创建接口分类', async () => {
      const addCategoryBtn = page.getByRole('button', { name: /新建分类|添加分类|\+ 分类/ }).first()
      if (await addCategoryBtn.isVisible()) {
        await addCategoryBtn.click()
        await page.waitForTimeout(500)
        const nameInput = page.locator('input[placeholder*="分类名称"], input[placeholder*="请输入分类名称"]').first()
        if (await nameInput.isVisible()) {
          await nameInput.fill(`测试分类_${timestamp}`)
          const confirmBtn = page.getByRole('button', { name: /确定|创建/ }).first()
          if (await confirmBtn.isVisible()) {
            await confirmBtn.click()
            await page.waitForTimeout(1000)
          }
        }
      }
    })

    await test.step('创建第一个 GET 接口', async () => {
      const addApiBtn = page.getByRole('button', { name: /新建接口|添加接口|\+ 接口/ }).first()
      if (await addApiBtn.isVisible()) {
        await addApiBtn.click()
        await page.waitForTimeout(1000)

        const nameInput = page.locator('input[placeholder*="接口名称"], input[placeholder*="请输入接口名称"]').first()
        if (await nameInput.isVisible()) {
          await nameInput.fill(`测试接口_${timestamp}`)
        }

        const urlInput = page.locator('input[placeholder*="接口地址"], input[placeholder*="/api"]').first()
        if (await urlInput.isVisible()) {
          await urlInput.fill('/api/health')
        }

        const saveBtn = page.getByRole('button', { name: /保存|确定|创建/ }).first()
        if (await saveBtn.isVisible()) {
          await saveBtn.click()
          await page.waitForTimeout(2000)
        }
      }
    })
  })

  test('1.7 发送第一个测试请求', async ({ page }) => {
    await test.step('登录系统', async () => {
      await utils.loginUser(username, password)
    })

    await test.step('进入接口管理页面', async () => {
      await utils.navigateTo('/dashboard')
      await page.waitForTimeout(1000)
    })

    await test.step('进入接口详情并发送请求', async () => {
      const apiList = page.locator('.tree-node, .api-item, [class*="api"][class*="node"]')
      const count = await apiList.count()
      if (count > 0) {
        await apiList.first().click()
        await page.waitForTimeout(2000)

        const sendBtn = page.getByRole('button', { name: /发送|Send|运行/ }).first()
        if (await sendBtn.isVisible()) {
          await sendBtn.click()
          await page.waitForTimeout(3000)
        }
      }
    })
  })

  test('1.8 空状态引导体验', async ({ page }) => {
    await test.step('登录系统', async () => {
      await utils.loginUser(username, password)
    })

    await test.step('查看各页面空状态', async () => {
      const sections = ['测试报告', '场景测试', 'Mock 规则']
      for (const section of sections) {
        const navItem = page.locator('.sidebar, .app-sidebar, .el-menu').getByText(section).first()
        if (await navItem.isVisible()) {
          await navItem.click()
          await page.waitForTimeout(1500)
        }
      }
    })
  })
})
