import { test, expect, BrowserContext, Page } from '@playwright/test'
import { TestUtils, generateUniqueId, TEST_PASSWORDS } from './utils/test-utils'

test.describe('用户画像 10：并发压力用户', () => {
  const timestamp = generateUniqueId(8)
  const numUsers = 3
  const users: { username: string; password: string; nickname: string; email: string }[] = []
  let projectId: number

  test.beforeAll(async ({ browser }) => {
    const setupPage = await browser.newPage()
    const setupUtils = new TestUtils(setupPage)

    const adminUsername = `conc_admin_${timestamp}`
    const adminPassword = TEST_PASSWORDS.strong
    console.log('创建管理员用户:', adminUsername)
    await setupUtils.registerUser(adminUsername, adminPassword, '并发管理员', `conc_admin_${timestamp}@test.com`)
    await setupUtils.navigateTo('/dashboard')
    await setupPage.waitForTimeout(2000)

    const url = setupPage.url()
    const match = url.match(/\/projects\/(\d+)/)
    projectId = match ? parseInt(match[1]) : 0
    if (!projectId) {
      projectId = await setupUtils.createProject(`并发项目_${timestamp}`)
    }
    console.log('项目ID:', projectId)

    console.log(`串行创建 ${numUsers} 个测试用户...`)
    for (let i = 0; i < numUsers; i++) {
      const userData = {
        username: `conc_u${i}_${timestamp}`,
        password: TEST_PASSWORDS.strong,
        nickname: `并发用户${i}`,
        email: `conc_u${i}_${timestamp}@test.com`,
      }
      users.push(userData)
      
      const userPage = await browser.newPage()
      const userUtils = new TestUtils(userPage)
      try {
        console.log(`  创建用户 ${i + 1}/${numUsers}: ${userData.username}`)
        await userUtils.registerUser(userData.username, userData.password, userData.nickname, userData.email)
        await userPage.waitForTimeout(500)
      } catch (e) {
        console.log(`  用户 ${userData.username} 创建可能失败: ${e}`)
      } finally {
        await userPage.close()
      }
    }

    await setupPage.close()
    console.log('所有用户创建完成')
  })

  test('10.1 多个用户同时登录', async ({ browser }) => {
    const contexts: BrowserContext[] = []
    const pages: Page[] = []

    await test.step('多个用户同时登录', async () => {
      const loginPromises = users.map(async (user, index) => {
        const context = await browser.newContext()
        const page = await context.newPage()
        const utils = new TestUtils(page)

        console.log(`用户 ${index} 开始登录...`)
        await utils.loginUser(user.username, user.password)
        console.log(`用户 ${index} 登录成功`)

        contexts.push(context)
        pages.push(page)
      })

      await Promise.all(loginPromises)
    })

    await test.step('验证所有用户都成功登录', async () => {
      for (let i = 0; i < pages.length; i++) {
        const currentHash = await pages[i].evaluate(() => window.location.hash)
        const isLoggedIn = currentHash.includes('/dashboard') || currentHash.includes('/projects/')
        expect(isLoggedIn).toBe(true)
      }
    })

    await test.step('清理资源', async () => {
      for (const context of contexts) {
        await context.close()
      }
    })
  })

  test('10.2 多个用户同时访问接口列表', async ({ browser }) => {
    const contexts: BrowserContext[] = []
    const pages: Page[] = []

    await test.step('登录多个用户', async () => {
      const loginPromises = users.map(async (user) => {
        const context = await browser.newContext()
        const page = await context.newPage()
        const utils = new TestUtils(page)
        await utils.loginUser(user.username, user.password)
        contexts.push(context)
        pages.push(page)
      })
      await Promise.all(loginPromises)
    })

    await test.step('同时访问接口列表', async () => {
      const visitPromises = pages.map(async (page) => {
        await page.goto(`/#/projects/${projectId}/apis`)
        await page.waitForLoadState('networkidle')
        await page.waitForTimeout(1000)
      })
      await Promise.all(visitPromises)
    })

    await test.step('验证所有页面都加载成功', async () => {
      for (const page of pages) {
        const currentHash = await page.evaluate(() => window.location.hash)
        expect(currentHash).toContain('/apis')
      }
    })

    await test.step('清理资源', async () => {
      for (const context of contexts) {
        await context.close()
      }
    })
  })

  test('10.3 多个用户同时查看测试报告', async ({ browser }) => {
    const contexts: BrowserContext[] = []
    const pages: Page[] = []

    await test.step('登录多个用户', async () => {
      const loginPromises = users.map(async (user) => {
        const context = await browser.newContext()
        const page = await context.newPage()
        const utils = new TestUtils(page)
        await utils.loginUser(user.username, user.password)
        contexts.push(context)
        pages.push(page)
      })
      await Promise.all(loginPromises)
    })

    await test.step('同时查看测试报告', async () => {
      const visitPromises = pages.map(async (page) => {
        await page.goto(`/#/projects/${projectId}/reports`)
        await page.waitForLoadState('networkidle')
        await page.waitForTimeout(1000)
      })
      await Promise.all(visitPromises)
    })

    await test.step('验证所有页面都加载成功', async () => {
      for (const page of pages) {
        const currentHash = await page.evaluate(() => window.location.hash)
        expect(currentHash).toContain('/reports')
      }
    })

    await test.step('清理资源', async () => {
      for (const context of contexts) {
        await context.close()
      }
    })
  })

  test('10.4 多个用户同时访问工作台', async ({ browser }) => {
    const contexts: BrowserContext[] = []
    const pages: Page[] = []

    await test.step('登录多个用户', async () => {
      const loginPromises = users.map(async (user) => {
        const context = await browser.newContext()
        const page = await context.newPage()
        const utils = new TestUtils(page)
        await utils.loginUser(user.username, user.password)
        contexts.push(context)
        pages.push(page)
      })
      await Promise.all(loginPromises)
    })

    await test.step('同时访问工作台', async () => {
      const visitPromises = pages.map(async (page) => {
        await page.goto('/#/dashboard')
        await page.waitForLoadState('networkidle')
        await page.waitForTimeout(1000)
      })
      await Promise.all(visitPromises)
    })

    await test.step('验证所有页面都加载成功', async () => {
      for (const page of pages) {
        const currentHash = await page.evaluate(() => window.location.hash)
        expect(currentHash).toContain('/dashboard')
      }
    })

    await test.step('清理资源', async () => {
      for (const context of contexts) {
        await context.close()
      }
    })
  })

  test('10.5 验证数据一致性 - 多用户查看同一页面', async ({ browser }) => {
    const contexts: BrowserContext[] = []
    const pages: Page[] = []

    await test.step('登录多个用户', async () => {
      const loginPromises = users.slice(0, 2).map(async (user) => {
        const context = await browser.newContext()
        const page = await context.newPage()
        const utils = new TestUtils(page)
        await utils.loginUser(user.username, user.password)
        contexts.push(context)
        pages.push(page)
      })
      await Promise.all(loginPromises)
    })

    await test.step('同时访问场景测试页面', async () => {
      const visitPromises = pages.map(async (page) => {
        await page.goto(`/#/projects/${projectId}/scenes`)
        await page.waitForLoadState('networkidle')
        await page.waitForTimeout(1000)
      })
      await Promise.all(visitPromises)
    })

    await test.step('验证页面一致性', async () => {
      for (const page of pages) {
        const currentHash = await page.evaluate(() => window.location.hash)
        expect(currentHash).toContain('/scenes')
      }
    })

    await test.step('清理资源', async () => {
      for (const context of contexts) {
        await context.close()
      }
    })
  })
})
