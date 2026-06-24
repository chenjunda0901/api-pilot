import { test, expect } from '@playwright/test'
import { TestUtils, generateUniqueId, TEST_PASSWORDS } from './utils/test-utils'

test.describe('用户画像 5：项目管理员', () => {
  let utils: TestUtils
  const timestamp = generateUniqueId()
  const username = `admin_${timestamp}`
  const password = TEST_PASSWORDS.strong
  let projectId: number

  test.beforeAll(async ({ browser }) => {
    const page = await browser.newPage()
    const setupUtils = new TestUtils(page)
    await setupUtils.registerUser(username, password, '项目管理员', `admin_${timestamp}@test.com`)
    await setupUtils.navigateTo('/dashboard')
    await page.waitForTimeout(2000)
    const url = page.url()
    const match = url.match(/\/projects\/(\d+)/)
    projectId = match ? parseInt(match[1]) : 0
    if (!projectId) {
      projectId = await setupUtils.createProject(`管理项目_${timestamp}`)
    }
    await page.close()
  })

  test.beforeEach(async ({ page }) => {
    utils = new TestUtils(page)
    await utils.loginUser(username, password)
  })

  test('5.1 进入项目设置', async ({ page }) => {
    await test.step('进入项目设置页面', async () => {
      await utils.navigateTo(`/projects/${projectId}/settings`)
      await page.waitForTimeout(2000)
    })

    await test.step('验证设置页面', async () => {
      const pageTitle = page.getByText(/设置|项目信息|基本信息/)
      const hasTitle = await pageTitle.count() > 0
      expect(hasTitle).toBe(true)
    })
  })

  test('5.2 管理项目成员', async ({ page }) => {
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

    await test.step('添加成员按钮', async () => {
      const addMemberBtn = page.getByRole('button', { name: /添加成员|邀请成员|\+/ }).first()
      if (await addMemberBtn.isVisible()) {
        await addMemberBtn.click()
        await page.waitForTimeout(1000)
        await page.keyboard.press('Escape')
      }
    })
  })

  test('5.3 修改项目基本信息', async ({ page }) => {
    await test.step('进入项目设置', async () => {
      await utils.navigateTo(`/projects/${projectId}/settings`)
      await page.waitForTimeout(2000)
    })

    await test.step('修改项目名称', async () => {
      const nameInput = page.locator('input[placeholder*="项目名称"], input[placeholder*="请输入项目名称"]').first()
      if (await nameInput.isVisible()) {
        await nameInput.fill(`更新的项目_${timestamp}`)
      }

      const saveBtn = page.getByRole('button', { name: /保存|确定|提交/ }).first()
      if (await saveBtn.isVisible()) {
        await saveBtn.click()
        await page.waitForTimeout(1000)
      }
    })
  })

  test('5.4 查看操作日志', async ({ page }) => {
    await test.step('进入项目设置', async () => {
      await utils.navigateTo(`/projects/${projectId}/settings`)
      await page.waitForTimeout(2000)
    })

    await test.step('切换到操作日志', async () => {
      const logTab = page.getByText(/操作日志|日志|Log|History/).first()
      if (await logTab.isVisible()) {
        await logTab.click()
        await page.waitForTimeout(1000)
      }
    })
  })

  test('5.5 导入/导出项目数据', async ({ page }) => {
    await test.step('进入项目设置', async () => {
      await utils.navigateTo(`/projects/${projectId}/settings`)
      await page.waitForTimeout(2000)
    })

    await test.step('查找导入导出功能', async () => {
      const importExportTab = page.getByText(/导入导出|数据导入|数据导出|Import|Export/).first()
      if (await importExportTab.isVisible()) {
        await importExportTab.click()
        await page.waitForTimeout(1000)
      }
    })
  })

  test('5.6 管理回收站', async ({ page }) => {
    await test.step('进入回收站页面', async () => {
      await utils.navigateTo(`/projects/${projectId}/recycle-bin`)
      await page.waitForTimeout(2000)
    })

    await test.step('验证回收站页面', async () => {
      const pageTitle = page.getByText(/回收站|Recycle|Bin/)
      const hasTitle = await pageTitle.count() > 0
      expect(hasTitle).toBe(true)
    })
  })
})
