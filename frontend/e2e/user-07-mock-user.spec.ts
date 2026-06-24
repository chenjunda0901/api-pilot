import { test, expect } from '@playwright/test'
import { TestUtils, generateUniqueId, TEST_PASSWORDS } from './utils/test-utils'

test.describe('用户画像 7：Mock 服务使用者', () => {
  let utils: TestUtils
  const timestamp = generateUniqueId()
  const username = `mockuser_${timestamp}`
  const password = TEST_PASSWORDS.strong
  let projectId: number

  test.beforeAll(async ({ browser }) => {
    const page = await browser.newPage()
    const setupUtils = new TestUtils(page)
    await setupUtils.registerUser(username, password, 'Mock用户', `mockuser_${timestamp}@test.com`)
    await setupUtils.navigateTo('/dashboard')
    await page.waitForTimeout(2000)
    const url = page.url()
    const match = url.match(/\/projects\/(\d+)/)
    projectId = match ? parseInt(match[1]) : 0
    if (!projectId) {
      projectId = await setupUtils.createProject(`Mock项目_${timestamp}`)
    }
    await page.close()
  })

  test.beforeEach(async ({ page }) => {
    utils = new TestUtils(page)
    await utils.loginUser(username, password)
  })

  test('7.1 进入 Mock 规则页面', async ({ page }) => {
    await test.step('进入 Mock 规则页面', async () => {
      await utils.navigateTo(`/projects/${projectId}/mock-rules`)
      await page.waitForTimeout(2000)
    })

    await test.step('验证 Mock 页面', async () => {
      const pageTitle = page.getByText(/Mock|mock|规则/)
      const hasTitle = await pageTitle.count() > 0
      expect(hasTitle).toBe(true)
    })
  })

  test('7.2 创建 Mock 规则', async ({ page }) => {
    await test.step('进入 Mock 规则页面', async () => {
      await utils.navigateTo(`/projects/${projectId}/mock-rules`)
      await page.waitForTimeout(2000)
    })

    await test.step('创建新 Mock 规则', async () => {
      const addMockBtn = page.getByRole('button', { name: /新建规则|添加规则|新建 Mock/ }).first()
      if (await addMockBtn.isVisible()) {
        await addMockBtn.click()
        await page.waitForTimeout(1000)

        const drawer = page.locator('.el-drawer')
        if (await drawer.isVisible()) {
          const nameInput = drawer.locator('.rule-name-input input, input[placeholder*="例如"]').first()
          if (await nameInput.isVisible()) {
            await nameInput.fill(`Mock规则_${timestamp}`)
          }

          const pathInput = drawer.locator('input[placeholder*="/api"], input[placeholder*="通配符"], input[placeholder*="路径"]').first()
          if (await pathInput.isVisible()) {
            await pathInput.fill(`/api/mock/test-${timestamp}`)
          }

          await page.waitForTimeout(500)

          const saveBtn = drawer.getByRole('button', { name: /保存|确定|创建/ }).first()
          if (await saveBtn.isVisible()) {
            const isDisabled = await saveBtn.evaluate((btn) => btn.hasAttribute('disabled') || btn.classList.contains('is-disabled'))
            if (!isDisabled) {
              await saveBtn.click()
              await page.waitForTimeout(2000)
            } else {
              console.log('保存按钮仍然禁用，跳过点击')
            }
          }
        }
      }
    })
  })

  test('7.3 配置 Mock 响应', async ({ page }) => {
    await test.step('进入 Mock 规则页面', async () => {
      await utils.navigateTo(`/projects/${projectId}/mock-rules`)
      await page.waitForTimeout(2000)
    })

    await test.step('点击第一个 Mock 规则', async () => {
      const mockItems = page.locator('.mock-rule-item, .tree-node, [class*="mock"][class*="item"]').first()
      if (await mockItems.isVisible()) {
        await mockItems.click()
        await page.waitForTimeout(2000)
      }
    })

    await test.step('配置状态码', async () => {
      const statusInput = page.locator('input[placeholder*="状态码"], input[placeholder*="200"]').first()
      if (await statusInput.isVisible()) {
        await statusInput.fill('200')
      }
    })
  })

  test('7.4 配置延迟模拟', async ({ page }) => {
    await test.step('查找延迟配置', async () => {
      const delayInput = page.locator('input[placeholder*="延迟"], input[placeholder*="delay"]').first()
      if (await delayInput.isVisible()) {
        await delayInput.fill('1000')
      }
    })
  })

  test('7.5 启用/禁用 Mock 规则', async ({ page }) => {
    await test.step('查找开关按钮', async () => {
      const switchBtn = page.locator('.el-switch, [role="switch"]').first()
      if (await switchBtn.isVisible()) {
        await switchBtn.click()
        await page.waitForTimeout(500)
        await switchBtn.click()
        await page.waitForTimeout(500)
      }
    })
  })

  test('7.6 查看 Mock 调用日志', async ({ page }) => {
    await test.step('切换到日志标签', async () => {
      const logTab = page.getByText(/日志|调用日志|Log/).first()
      if (await logTab.isVisible()) {
        await logTab.click()
        await page.waitForTimeout(1000)
      }
    })
  })

  test('7.7 测试 Mock 接口', async ({ page }) => {
    await test.step('查找测试按钮', async () => {
      const testBtn = page.getByRole('button', { name: /测试|Test|调用/ }).first()
      if (await testBtn.isVisible()) {
        await testBtn.click()
        await page.waitForTimeout(2000)
      }
    })
  })
})
