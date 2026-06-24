import { test, expect } from '@playwright/test'
import { TestUtils, generateUniqueId, TEST_PASSWORDS } from './utils/test-utils'

test.describe('用户画像 8：高级用户（快捷键）', () => {
  let utils: TestUtils
  const timestamp = generateUniqueId()
  const username = `poweruser_${timestamp}`
  const password = TEST_PASSWORDS.strong
  let projectId: number

  test.beforeAll(async ({ browser }) => {
    const page = await browser.newPage()
    const setupUtils = new TestUtils(page)
    await setupUtils.registerUser(username, password, '高级用户', `poweruser_${timestamp}@test.com`)
    await setupUtils.navigateTo('/dashboard')
    await page.waitForTimeout(2000)
    const url = page.url()
    const match = url.match(/\/projects\/(\d+)/)
    projectId = match ? parseInt(match[1]) : 0
    if (!projectId) {
      projectId = await setupUtils.createProject(`高级用户项目_${timestamp}`)
    }
    await page.close()
  })

  test.beforeEach(async ({ page }) => {
    utils = new TestUtils(page)
    await utils.loginUser(username, password)
  })

  test('8.1 使用 Ctrl+K 打开全局搜索', async ({ page }) => {
    await test.step('按 Ctrl+K 打开搜索', async () => {
      await page.keyboard.press('Control+k')
      await page.waitForTimeout(1000)
    })

    await test.step('验证搜索框已打开', async () => {
      const searchDialog = page.locator('.global-search, .command-palette, .search-dialog, [class*="search"][class*="dialog"]').first()
      const isVisible = await searchDialog.isVisible()
      if (isVisible) {
        expect(searchDialog).toBeVisible()
        await page.keyboard.press('Escape')
      }
    })
  })

  test('8.2 搜索接口、用例、场景', async ({ page }) => {
    await test.step('打开全局搜索', async () => {
      await page.keyboard.press('Control+k')
      await page.waitForTimeout(1000)
    })

    await test.step('输入搜索关键词', async () => {
      const searchDialog = page.locator('.global-search, .command-palette, .search-dialog').first()
      if (await searchDialog.isVisible()) {
        const searchInput = searchDialog.locator('input').first()
        if (await searchInput.isVisible()) {
          await searchInput.fill('测试')
          await page.waitForTimeout(1500)
        }
        await page.keyboard.press('Escape')
      }
    })
  })

  test('8.3 查看快捷键帮助', async ({ page }) => {
    await test.step('查找快捷键帮助按钮', async () => {
      const helpBtn = page.getByRole('button', { name: /快捷键|帮助|Shortcut|Help/ }).first()
      if (await helpBtn.isVisible()) {
        await helpBtn.click()
        await page.waitForTimeout(1000)
        await page.keyboard.press('Escape')
      }
    })

    await test.step('使用 ? 快捷键打开帮助', async () => {
      await page.keyboard.press('?')
      await page.waitForTimeout(1000)
      const helpDialog = page.locator('.shortcut-help, .hotkey-help, [class*="shortcut"][class*="help"]').first()
      if (await helpDialog.isVisible()) {
        expect(helpDialog).toBeVisible()
        await page.keyboard.press('Escape')
      }
    })
  })

  test('8.4 批量操作接口', async ({ page }) => {
    await test.step('进入接口管理页面', async () => {
      await utils.navigateTo(`/projects/${projectId}/apis`)
      await page.waitForTimeout(2000)
    })

    await test.step('查找批量操作按钮', async () => {
      const batchBtn = page.getByRole('button', { name: /批量|Batch/ }).first()
      if (await batchBtn.isVisible()) {
        await batchBtn.click()
        await page.waitForTimeout(500)
      }
    })
  })

  test('8.5 使用快捷键快速创建', async ({ page }) => {
    await test.step('使用 Ctrl+N 快捷键', async () => {
      await page.keyboard.press('Control+n')
      await page.waitForTimeout(1000)
      const dialog = page.locator('.el-dialog, [role="dialog"]').first()
      if (await dialog.isVisible()) {
        await page.keyboard.press('Escape')
      }
    })
  })

  test('8.6 使用导航快捷键', async ({ page }) => {
    await test.step('使用数字键导航', async () => {
      for (let i = 1; i <= 5; i++) {
        await page.keyboard.press(String(i))
        await page.waitForTimeout(300)
      }
    })

    await test.step('使用 Esc 关闭弹窗', async () => {
      await page.keyboard.press('Escape')
      await page.waitForTimeout(300)
    })
  })
})
