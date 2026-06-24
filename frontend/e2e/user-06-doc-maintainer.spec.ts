import { test, expect } from '@playwright/test'
import { TestUtils, generateUniqueId, TEST_PASSWORDS } from './utils/test-utils'

test.describe('用户画像 6：接口文档维护者', () => {
  let utils: TestUtils
  const timestamp = generateUniqueId()
  const username = `docwriter_${timestamp}`
  const password = TEST_PASSWORDS.strong
  let projectId: number

  test.beforeAll(async ({ browser }) => {
    const page = await browser.newPage()
    const setupUtils = new TestUtils(page)
    await setupUtils.registerUser(username, password, '文档维护者', `docwriter_${timestamp}@test.com`)
    await setupUtils.navigateTo('/dashboard')
    await page.waitForTimeout(2000)
    const url = page.url()
    const match = url.match(/\/projects\/(\d+)/)
    projectId = match ? parseInt(match[1]) : 0
    if (!projectId) {
      projectId = await setupUtils.createProject(`文档项目_${timestamp}`)
    }
    await page.close()
  })

  test.beforeEach(async ({ page }) => {
    utils = new TestUtils(page)
    await utils.loginUser(username, password)
  })

  test('6.1 编辑接口文档描述', async ({ page }) => {
    await test.step('进入接口管理页面', async () => {
      await utils.navigateTo(`/projects/${projectId}/apis`)
      await page.waitForTimeout(2000)
    })

    await test.step('点击第一个接口', async () => {
      const apiItems = page.locator('.tree-node, .api-item, [class*="api"][class*="node"]').first()
      if (await apiItems.isVisible()) {
        await apiItems.click()
        await page.waitForTimeout(2000)
      }
    })

    await test.step('切换到文档编辑', async () => {
      const docTab = page.getByText(/文档|Doc|描述/).first()
      if (await docTab.isVisible()) {
        await docTab.click()
        await page.waitForTimeout(1000)
      }
    })
  })

  test('6.2 查看接口文档预览', async ({ page }) => {
    await test.step('进入接口管理页面', async () => {
      await utils.navigateTo(`/projects/${projectId}/apis`)
      await page.waitForTimeout(2000)
    })

    await test.step('点击第一个接口', async () => {
      const apiItems = page.locator('.tree-node, .api-item, [class*="api"][class*="node"]').first()
      if (await apiItems.isVisible()) {
        await apiItems.click()
        await page.waitForTimeout(2000)
      }
    })

    await test.step('查看文档预览', async () => {
      const previewBtn = page.getByRole('button', { name: /预览|Preview/ }).first()
      if (await previewBtn.isVisible()) {
        await previewBtn.click()
        await page.waitForTimeout(1000)
        await page.keyboard.press('Escape')
      }
    })
  })

  test('6.3 管理接口分类', async ({ page }) => {
    await test.step('进入接口管理页面', async () => {
      await utils.navigateTo(`/projects/${projectId}/apis`)
      await page.waitForTimeout(2000)
    })

    await test.step('添加新分类', async () => {
      const addCategoryBtn = page.getByRole('button', { name: /新建分类|添加分类|\+ 分类/ }).first()
      if (await addCategoryBtn.isVisible()) {
        await addCategoryBtn.click()
        await page.waitForTimeout(1000)

        const nameInput = page.locator('input[placeholder*="分类名称"], input[placeholder*="请输入分类名称"]').first()
        if (await nameInput.isVisible()) {
          await nameInput.fill(`文档分类_${timestamp}`)
        }

        const confirmBtn = page.getByRole('button', { name: /确定|创建/ }).first()
        if (await confirmBtn.isVisible()) {
          await confirmBtn.click()
          await page.waitForTimeout(1000)
        }
      }
    })
  })

  test('6.4 搜索和筛选接口', async ({ page }) => {
    await test.step('进入接口管理页面', async () => {
      await utils.navigateTo(`/projects/${projectId}/apis`)
      await page.waitForTimeout(2000)
    })

    await test.step('搜索接口', async () => {
      const searchInput = page.locator('input[placeholder*="搜索"], input[placeholder*="Search"]').first()
      if (await searchInput.isVisible()) {
        await searchInput.fill('测试')
        await page.waitForTimeout(1000)
        await searchInput.fill('')
        await page.waitForTimeout(500)
      }
    })
  })

  test('6.5 导出接口文档', async ({ page }) => {
    await test.step('进入接口管理页面', async () => {
      await utils.navigateTo(`/projects/${projectId}/apis`)
      await page.waitForTimeout(2000)
    })

    await test.step('查找导出按钮', async () => {
      const exportBtn = page.getByRole('button', { name: /导出|Export/ }).first()
      if (await exportBtn.isVisible()) {
        await exportBtn.click()
        await page.waitForTimeout(1000)
        await page.keyboard.press('Escape')
      }
    })
  })
})
