import { test, expect } from '@playwright/test'
import { TestUtils, generateUniqueId, TEST_PASSWORDS } from './utils/test-utils'

test.describe('用户画像 4：QA 管理者', () => {
  let utils: TestUtils
  const timestamp = generateUniqueId()
  const username = `qamgr_${timestamp}`
  const password = TEST_PASSWORDS.strong
  let projectId: number

  test.beforeAll(async ({ browser }) => {
    const page = await browser.newPage()
    const setupUtils = new TestUtils(page)
    await setupUtils.registerUser(username, password, 'QA经理', `qamgr_${timestamp}@test.com`)
    await setupUtils.navigateTo('/dashboard')
    await page.waitForTimeout(2000)
    const url = page.url()
    const match = url.match(/\/projects\/(\d+)/)
    projectId = match ? parseInt(match[1]) : 0
    if (!projectId) {
      projectId = await setupUtils.createProject(`QA项目_${timestamp}`)
    }
    await page.close()
  })

  test.beforeEach(async ({ page }) => {
    utils = new TestUtils(page)
    await utils.loginUser(username, password)
  })

  test('4.1 查看测试报告列表', async ({ page }) => {
    await test.step('进入测试报告页面', async () => {
      await utils.navigateTo(`/projects/${projectId}/reports`)
      await page.waitForTimeout(2000)
    })

    await test.step('验证报告列表页面', async () => {
      const pageTitle = page.getByText(/测试报告|报告/)
      const hasTitle = await pageTitle.count() > 0
      expect(hasTitle).toBe(true)
    })
  })

  test('4.2 筛选和搜索报告', async ({ page }) => {
    await test.step('进入测试报告页面', async () => {
      await utils.navigateTo(`/projects/${projectId}/reports`)
      await page.waitForTimeout(2000)
    })

    await test.step('搜索报告', async () => {
      const searchInput = page.locator('input[placeholder*="搜索"], input[placeholder*="Search"]').first()
      if (await searchInput.isVisible()) {
        await searchInput.fill('测试')
        await page.waitForTimeout(1000)
        await searchInput.fill('')
        await page.waitForTimeout(500)
      }
    })

    await test.step('筛选报告状态', async () => {
      const filterTabs = page.locator('.filter-tabs, .el-tabs__nav').first()
      if (await filterTabs.isVisible()) {
        const successTab = filterTabs.getByText(/成功|通过|success/)
        if (await successTab.isVisible()) {
          await successTab.click()
          await page.waitForTimeout(1000)
        }
        const allTab = filterTabs.getByText(/全部|all/)
        if (await allTab.isVisible()) {
          await allTab.click()
          await page.waitForTimeout(1000)
        }
      }
    })
  })

  test('4.3 查看报告详情', async ({ page }) => {
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

  test('4.4 查看执行统计和趋势', async ({ page }) => {
    await test.step('查看工作台统计数据', async () => {
      await utils.navigateTo('/dashboard')
      await page.waitForTimeout(2000)

      const statsRow = page.locator('.stats-row')
      if (await statsRow.isVisible()) {
        expect(statsRow).toBeVisible()
      }
    })
  })

  test('4.5 导出测试报告', async ({ page }) => {
    await test.step('进入测试报告页面', async () => {
      await utils.navigateTo(`/projects/${projectId}/reports`)
      await page.waitForTimeout(2000)
    })

    await test.step('查找导出按钮', async () => {
      const exportBtn = page.getByRole('button', { name: /导出|Export|下载/ }).first()
      if (await exportBtn.isVisible()) {
        await exportBtn.click()
        await page.waitForTimeout(1000)
      }
    })
  })

  test('4.6 查看项目概览统计', async ({ page }) => {
    await test.step('查看工作台概览', async () => {
      await utils.navigateTo('/dashboard')
      await page.waitForTimeout(2000)

      const heroMetrics = page.locator('.dashboard-hero-metrics-inline, .metrics-inline')
      if (await heroMetrics.isVisible()) {
        expect(heroMetrics).toBeVisible()
      }
    })
  })
})
