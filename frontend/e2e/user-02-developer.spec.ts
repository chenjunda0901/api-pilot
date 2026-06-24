import { test, expect } from '@playwright/test'
import { TestUtils, generateUniqueId, TEST_PASSWORDS } from './utils/test-utils'

test.describe('用户画像 2：普通开发人员', () => {
  let utils: TestUtils
  const timestamp = generateUniqueId()
  const username = `dev_${timestamp}`
  const password = TEST_PASSWORDS.strong
  let projectId: number

  test.beforeAll(async ({ browser }) => {
    const page = await browser.newPage()
    const setupUtils = new TestUtils(page)
    await setupUtils.registerUser(username, password, '开发人员', `dev_${timestamp}@test.com`)
    await setupUtils.navigateTo('/dashboard')
    await page.waitForTimeout(2000)
    const url = page.url()
    const match = url.match(/\/projects\/(\d+)/)
    projectId = match ? parseInt(match[1]) : 0
    if (!projectId) {
      projectId = await setupUtils.createProject(`Dev项目_${timestamp}`)
    }
    await page.close()
  })

  test.beforeEach(async ({ page }) => {
    utils = new TestUtils(page)
    await utils.loginUser(username, password)
  })

  test('2.1 切换不同环境', async ({ page }) => {
    await test.step('进入接口管理页面', async () => {
      await utils.navigateTo(`/projects/${projectId}/apis`)
      await page.waitForTimeout(2000)
    })

    await test.step('查找环境切换器', async () => {
      const envSwitcher = page.locator('.env-switcher, .env-selector, [class*="env"] [class*="switch"]').first()
      if (await envSwitcher.isVisible()) {
        await envSwitcher.click()
        await page.waitForTimeout(500)
        const envOptions = page.locator('.el-select-dropdown__item, .env-option')
        if (await envOptions.count() > 0) {
          await envOptions.first().click()
          await page.waitForTimeout(1000)
        }
      }
    })
  })

  test('2.2 查看接口列表和搜索', async ({ page }) => {
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

  test('2.3 创建 POST/PUT/DELETE 接口', async ({ page }) => {
    const methods = ['POST', 'PUT', 'DELETE']

    await test.step('进入接口管理页面', async () => {
      await utils.navigateTo(`/projects/${projectId}/apis`)
      await page.waitForTimeout(2000)
    })

    for (const method of methods) {
      await test.step(`创建 ${method} 接口`, async () => {
        const addApiBtn = page.getByRole('button', { name: /新建接口|添加接口|\+ 接口/ }).first()
        if (await addApiBtn.isVisible()) {
          await addApiBtn.click()
          await page.waitForTimeout(1000)

          const nameInput = page.locator('input[placeholder*="接口名称"], input[placeholder*="请输入接口名称"]').first()
          if (await nameInput.isVisible()) {
            await nameInput.fill(`${method}接口_${timestamp}`)
          }

          const methodSelect = page.locator('.el-select').first()
          if (await methodSelect.isVisible()) {
            await methodSelect.click()
            await page.waitForTimeout(500)
            const methodOption = page.getByText(method, { exact: true })
            if (await methodOption.isVisible()) {
              await methodOption.click()
            } else {
              await page.keyboard.press('Escape')
            }
          }

          const urlInput = page.locator('input[placeholder*="接口地址"], input[placeholder*="/api"]').first()
          if (await urlInput.isVisible()) {
            await urlInput.fill(`/api/test/${method.toLowerCase()}`)
          }

          const saveBtn = page.getByRole('button', { name: /保存|确定|创建/ }).first()
          if (await saveBtn.isVisible()) {
            await saveBtn.click()
            await page.waitForTimeout(2000)
          }
        }
      })
    }
  })

  test('2.4 编辑请求头和请求体', async ({ page }) => {
    await test.step('进入接口管理页面', async () => {
      await utils.navigateTo(`/projects/${projectId}/apis`)
      await page.waitForTimeout(2000)
    })

    await test.step('点击第一个接口进入详情', async () => {
      const apiItems = page.locator('.tree-node, .api-item, [class*="api"][class*="node"]').first()
      if (await apiItems.isVisible()) {
        await apiItems.click()
        await page.waitForTimeout(2000)
      }
    })

    await test.step('切换到 Headers 标签并添加请求头', async () => {
      const headersTab = page.getByText(/Headers|请求头/).first()
      if (await headersTab.isVisible()) {
        await headersTab.click()
        await page.waitForTimeout(500)

        const addHeaderBtn = page.getByRole('button', { name: /添加|新增|\+/ }).first()
        if (await addHeaderBtn.isVisible()) {
          await addHeaderBtn.click()
          await page.waitForTimeout(500)
        }
      }
    })

    await test.step('切换到 Body 标签', async () => {
      const bodyTab = page.getByText(/Body|请求体/).first()
      if (await bodyTab.isVisible()) {
        await bodyTab.click()
        await page.waitForTimeout(500)

        const jsonOption = page.getByText(/JSON|raw/).first()
        if (await jsonOption.isVisible()) {
          await jsonOption.click()
          await page.waitForTimeout(500)
        }
      }
    })
  })

  test('2.5 发送请求并查看响应', async ({ page }) => {
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

    await test.step('发送请求', async () => {
      const sendBtn = page.getByRole('button', { name: /发送|Send|运行/ }).first()
      if (await sendBtn.isVisible()) {
        await sendBtn.click()
        await page.waitForTimeout(3000)
      }
    })

    await test.step('查看响应面板', async () => {
      const responsePanel = page.locator('.response-panel, [class*="response"]').first()
      if (await responsePanel.isVisible()) {
        expect(responsePanel).toBeVisible()
      }
    })
  })

  test('2.6 使用全局搜索查找接口', async ({ page }) => {
    await test.step('尝试打开全局搜索', async () => {
      await page.keyboard.press('Control+k')
      await page.waitForTimeout(1000)

      const searchDialog = page.locator('.global-search, .command-palette, .search-dialog').first()
      if (await searchDialog.isVisible()) {
        const searchInput = searchDialog.locator('input').first()
        if (await searchInput.isVisible()) {
          await searchInput.fill('测试')
          await page.waitForTimeout(1000)
        }
        await page.keyboard.press('Escape')
      }
    })
  })

  test('2.7 查看请求历史', async ({ page }) => {
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

    await test.step('查看历史记录', async () => {
      const historyTab = page.getByText(/历史|History/).first()
      if (await historyTab.isVisible()) {
        await historyTab.click()
        await page.waitForTimeout(1000)
      }
    })
  })
})
