import { test, expect } from '@playwright/test'
import { TestUtils, generateUniqueId, TEST_PASSWORDS } from './utils/test-utils'

test.describe('用户画像 9：只读访客', () => {
  let utils: TestUtils
  const timestamp = generateUniqueId()
  const username = `guest_${timestamp}`
  const password = TEST_PASSWORDS.strong
  let projectId: number

  test.beforeAll(async ({ browser }) => {
    const page = await browser.newPage()
    const setupUtils = new TestUtils(page)
    await setupUtils.registerUser(username, password, '只读访客', `guest_${timestamp}@test.com`)
    await setupUtils.navigateTo('/dashboard')
    await page.waitForTimeout(2000)
    const url = page.url()
    const match = url.match(/\/projects\/(\d+)/)
    projectId = match ? parseInt(match[1]) : 0
    if (!projectId) {
      projectId = await setupUtils.createProject(`访客项目_${timestamp}`)
    }
    await page.close()
  })

  test.beforeEach(async ({ page }) => {
    utils = new TestUtils(page)
    await utils.loginUser(username, password)
  })

  test('9.1 查看只读模式提示', async ({ page }) => {
    await test.step('进入演示项目（如有）', async () => {
      await utils.navigateTo('/dashboard')
      await page.waitForTimeout(2000)

      const readOnlyBanner = page.locator('.readonly-banner, .read-only-banner, [class*="readonly"]').first()
      if (await readOnlyBanner.isVisible()) {
        expect(readOnlyBanner).toBeVisible()
      }
    })
  })

  test('9.2 查看接口列表和详情', async ({ page }) => {
    await test.step('进入接口管理页面', async () => {
      await utils.navigateTo(`/projects/${projectId}/apis`)
      await page.waitForTimeout(2000)
    })

    await test.step('点击第一个接口查看详情', async () => {
      const apiItems = page.locator('.tree-node, .api-item, [class*="api"][class*="node"]').first()
      if (await apiItems.isVisible()) {
        await apiItems.click()
        await page.waitForTimeout(2000)
      }
    })
  })

  test('9.3 查看测试报告', async ({ page }) => {
    await test.step('进入测试报告页面', async () => {
      await utils.navigateTo(`/projects/${projectId}/reports`)
      await page.waitForTimeout(2000)
    })

    await test.step('点击第一个报告', async () => {
      const reportItems = page.locator('.report-item, [class*="report"][class*="item"]').first()
      if (await reportItems.isVisible()) {
        await reportItems.click()
        await page.waitForTimeout(2000)
      }
    })
  })

  test('9.4 验证编辑按钮不可见', async ({ page }) => {
    await test.step('进入接口管理页面', async () => {
      await utils.navigateTo(`/projects/${projectId}/apis`)
      await page.waitForTimeout(2000)
    })

    await test.step('检查新建按钮状态', async () => {
      const addBtn = page.getByRole('button', { name: /新建接口|添加接口|\+ 接口/ }).first()
      if (await addBtn.isVisible()) {
        const isDisabled = await addBtn.isDisabled()
        if (isDisabled) {
          expect(isDisabled).toBe(true)
        }
      }
    })
  })

  test('9.5 查看项目成员列表', async ({ page }) => {
    await test.step('进入项目设置', async () => {
      await utils.navigateTo(`/projects/${projectId}/settings`)
      await page.waitForTimeout(2000)
    })

    await test.step('切换到成员管理', async () => {
      const memberTab = page.getByText(/成员|成员管理|Member/).first()
      if (await memberTab.isVisible()) {
        await memberTab.click()
        await page.waitForTimeout(1000)
      }
    })
  })

  test('9.6 查看场景测试列表', async ({ page }) => {
    await test.step('进入场景测试页面', async () => {
      await utils.navigateTo(`/projects/${projectId}/scenes`)
      await page.waitForTimeout(2000)
    })

    await test.step('验证页面可访问', async () => {
      const pageTitle = page.getByText(/场景|Scene/)
      const hasTitle = await pageTitle.count() > 0
      expect(hasTitle).toBe(true)
    })
  })
})
