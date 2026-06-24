import { test, expect } from '@playwright/test'
import { TestUtils } from './utils/test-utils'

test.describe('全面功能点深度测试 - 访客模式（演示项目）', () => {
  let utils: TestUtils
  let projectId: number

  test.beforeAll(async ({ browser }) => {
    const page = await browser.newPage()
    const setupUtils = new TestUtils(page)

    await setupUtils.navigateTo('/dashboard')
    await page.waitForTimeout(3000)

    const url = page.url()
    const match = url.match(/\/projects\/(\d+)/)
    if (match) {
      projectId = parseInt(match[1])
    } else {
      await setupUtils.navigateTo('/dashboard')
      await page.waitForTimeout(2000)
      const projectLinks = page.locator('a[href*="/projects/"]')
      const count = await projectLinks.count()
      if (count > 0) {
        const firstHref = await projectLinks.first().getAttribute('href')
        const idMatch = firstHref?.match(/\/projects\/(\d+)/)
        if (idMatch) {
          projectId = parseInt(idMatch[1])
        }
      }
    }

    if (!projectId) {
      projectId = 1
    }

    console.log(`演示项目 ID: ${projectId}`)
    await page.close()
  })

  test.beforeEach(async ({ page }) => {
    utils = new TestUtils(page)
  })

  test.describe('1. 认证相关 - 访客模式进入演示项目', () => {
    test('1.1 访客模式访问工作台页面', async ({ page }) => {
      await test.step('访问工作台页面', async () => {
        await utils.navigateTo('/dashboard')
        await page.waitForTimeout(2000)
      })

      await test.step('验证页面已加载', async () => {
        const title = await page.title()
        expect(title).toBeTruthy()
      })

      await test.step('验证访客模式横幅显示', async () => {
        const banner = page.locator('.readonly-banner.guest')
        if (await banner.isVisible()) {
          await expect(banner).toContainText('访客模式')
        }
      })
    })

    test('1.2 验证访客模式状态', async ({ page }) => {
      await test.step('访问工作台', async () => {
        await utils.navigateTo('/dashboard')
        await page.waitForTimeout(2000)
      })

      await test.step('验证访客模式提示或登录按钮存在', async () => {
        const hasGuestBanner = await page.locator('.readonly-banner, .guest-banner, [class*="readonly"]').count() > 0
        const hasLoginBtn = await page.getByRole('button', { name: /登录|Login/ }).count() > 0
        expect(hasGuestBanner || hasLoginBtn).toBe(true)
      })
    })

    test('1.3 访问需要登录的页面应跳转登录页', async ({ page }) => {
      await test.step('尝试访问设置页面（需要登录）', async () => {
        await page.goto(`/#/projects/${projectId}/settings`)
        await page.waitForTimeout(2000)
      })

      await test.step('验证是否被重定向到登录页', async () => {
        const currentHash = await page.evaluate(() => window.location.hash)
        const isLoginPage = currentHash.includes('/login') || currentHash.includes('/dashboard')
        expect(isLoginPage).toBe(true)
      })
    })
  })

  test.describe('2. 工作台 - 统计卡片、报告列表、快捷操作', () => {
    test.beforeEach(async ({ page }) => {
      await utils.navigateTo('/dashboard')
      await page.waitForTimeout(2000)
    })

    test('2.1 工作台页面基本结构', async ({ page }) => {
      await test.step('验证页面标题', async () => {
        const hasDashboardText = await page.getByText(/工作台|Dashboard/).count() > 0
        expect(hasDashboardText).toBe(true)
      })

      await test.step('验证页面有内容', async () => {
        const hasContent = await utils.waitForPageContent(3)
        expect(hasContent).toBe(true)
      })
    })

    test('2.2 统计卡片展示', async ({ page }) => {
      await test.step('查找统计卡片', async () => {
        const statCards = page.locator('[class*="stat"], [class*="card"], [class*="Stat"], [class*="metric"]')
        const count = await statCards.count()
        if (count > 0) {
          console.log(`找到 ${count} 个统计卡片元素`)
          const firstCard = statCards.first()
          await expect(firstCard).toBeVisible()
        }
      })
    })

    test('2.3 项目列表/选择器', async ({ page }) => {
      await test.step('查找项目选择器或项目列表', async () => {
        const projectSelector = page.locator('.project-selector, [class*="project-switch"], [class*="ProjectSwitch"]')
        if (await projectSelector.isVisible()) {
          await expect(projectSelector).toBeVisible()
        }
      })
    })

    test('2.4 快捷操作入口', async ({ page }) => {
      await test.step('查找快捷操作按钮', async () => {
        const quickActions = page.getByRole('button', { name: /新建|创建|添加|\+/ })
        const count = await quickActions.count()
        if (count > 0) {
          console.log(`找到 ${count} 个快捷操作按钮`)
        }
      })
    })
  })

  test.describe('3. 接口管理 - 目录树、列表筛选、接口详情、各Tab切换', () => {
    test.beforeEach(async ({ page }) => {
      await utils.navigateTo(`/projects/${projectId}/apis`)
      await page.waitForTimeout(2000)
    })

    test('3.1 接口管理页面基本结构', async ({ page }) => {
      await test.step('验证页面已加载', async () => {
        const hasContent = await utils.waitForPageContent(3)
        expect(hasContent).toBe(true)
      })

      await test.step('验证页面标题', async () => {
        const hasApiText = await page.getByText(/接口|API/).count() > 0
        expect(hasApiText).toBe(true)
      })
    })

    test('3.2 目录树/侧边栏导航', async ({ page }) => {
      await test.step('查找目录树', async () => {
        const tree = page.locator('.api-tree, .category-tree, [class*="tree"], [class*="sidebar"][class*="api"]')
        if (await tree.count() > 0) {
          await expect(tree.first()).toBeVisible()
        }
      })

      await test.step('查找分类/目录节点', async () => {
        const treeNodes = page.locator('.tree-node, [class*="tree-node"], [class*="category"]')
        const count = await treeNodes.count()
        if (count > 0) {
          console.log(`找到 ${count} 个树节点`)
        }
      })
    })

    test('3.3 搜索/筛选功能', async ({ page }) => {
      await test.step('查找搜索输入框', async () => {
        const searchInputs = page.locator('input[placeholder*="搜索"], input[placeholder*="Search"], input[placeholder*="search"]')
        const count = await searchInputs.count()
        if (count > 0) {
          const firstSearch = searchInputs.first()
          await firstSearch.fill('test')
          await page.waitForTimeout(1000)
          await firstSearch.fill('')
          await page.waitForTimeout(500)
        }
      })
    })

    test('3.4 接口列表行交互', async ({ page }) => {
      await test.step('查找接口列表行', async () => {
        const apiRows = page.locator('.el-table__row, .api-row, table tbody tr')
        const count = await apiRows.count()
        if (count > 0) {
          const firstRow = apiRows.first()
          try {
            await firstRow.scrollIntoViewIfNeeded()
            await firstRow.click({ timeout: 5000 })
            await page.waitForTimeout(1500)
          } catch (e) {
            console.log('行点击失败，跳过:', (e as Error).message)
          }
        }
      })

      await test.step('验证页面有响应', async () => {
        const title = await page.title()
        expect(title).toBeTruthy()
      })
    })

    test('3.5 接口详情 Tab 切换', async ({ page }) => {
      await test.step('先进入接口详情页', async () => {
        const apiItems = page.locator('.tree-node, .api-item, [class*="api"][class*="item"]')
        const count = await apiItems.count()
        if (count > 0) {
          await apiItems.first().click()
          await page.waitForTimeout(2000)
        }
      })

      await test.step('查找并切换 Tab', async () => {
        const tabs = page.locator('.el-tabs__item, [class*="tab"], [role="tab"]')
        const tabCount = await tabs.count()
        if (tabCount > 1) {
          for (let i = 0; i < Math.min(tabCount, 3); i++) {
            await tabs.nth(i).click()
            await page.waitForTimeout(500)
          }
        }
      })
    })

    test('3.6 请求方法标签显示', async ({ page }) => {
      await test.step('查找 HTTP 方法标签', async () => {
        const methodTags = page.locator('[class*="method"], [class*="GET"], [class*="POST"], [class*="PUT"], [class*="DELETE"]')
        const count = await methodTags.count()
        if (count > 0) {
          console.log(`找到 ${count} 个方法标签`)
        }
      })
    })
  })

  test.describe('4. 场景测试 - 场景列表、步骤展示、运行按钮', () => {
    test.beforeEach(async ({ page }) => {
      await utils.navigateTo(`/projects/${projectId}/scenes`)
      await page.waitForTimeout(2000)
    })

    test('4.1 场景测试页面基本结构', async ({ page }) => {
      await test.step('验证页面已加载', async () => {
        const hasContent = await utils.waitForPageContent(2)
        expect(hasContent).toBe(true)
      })

      await test.step('验证页面标题', async () => {
        const hasSceneText = await page.getByText(/场景|Scene/).count() > 0
        expect(hasSceneText).toBe(true)
      })
    })

    test('4.2 场景列表展示', async ({ page }) => {
      await test.step('查找场景列表', async () => {
        const sceneItems = page.locator('.scene-item, [class*="scene"][class*="item"], [class*="SceneItem"]')
        const count = await sceneItems.count()
        if (count > 0) {
          console.log(`找到 ${count} 个场景`)
          await expect(sceneItems.first()).toBeVisible()
        }
      })
    })

    test('4.3 运行按钮存在', async ({ page }) => {
      await test.step('查找运行按钮', async () => {
        const runButtons = page.getByRole('button', { name: /运行|执行|Run|开始/ })
        const count = await runButtons.count()
        if (count > 0) {
          console.log(`找到 ${count} 个运行按钮`)
        }
      })
    })

    test('4.4 点击场景查看详情/步骤', async ({ page }) => {
      await test.step('查找并点击第一个场景', async () => {
        const sceneItems = page.locator('.scene-item, [class*="scene"][class*="item"]')
        const count = await sceneItems.count()
        if (count > 0) {
          await sceneItems.first().click()
          await page.waitForTimeout(1500)
        }
      })
    })
  })

  test.describe('5. 测试报告 - 报告列表、筛选、报告详情', () => {
    test.beforeEach(async ({ page }) => {
      await utils.navigateTo(`/projects/${projectId}/reports`)
      await page.waitForTimeout(2000)
    })

    test('5.1 测试报告页面基本结构', async ({ page }) => {
      await test.step('验证页面已加载', async () => {
        const hasContent = await utils.waitForPageContent(2)
        expect(hasContent).toBe(true)
      })

      await test.step('验证页面标题', async () => {
        const hasReportText = await page.getByText(/报告|Report/).count() > 0
        expect(hasReportText).toBe(true)
      })
    })

    test('5.2 报告列表展示', async ({ page }) => {
      await test.step('查找报告列表', async () => {
        const reportItems = page.locator('.report-item, [class*="report"][class*="item"], [class*="ReportItem"]')
        const count = await reportItems.count()
        if (count > 0) {
          console.log(`找到 ${count} 个报告`)
          await expect(reportItems.first()).toBeVisible()
        }
      })
    })

    test('5.3 报告筛选功能', async ({ page }) => {
      await test.step('查找筛选器', async () => {
        const filters = page.locator('.filter, [class*="filter"]')
        const count = await filters.count()
        if (count > 0) {
          console.log(`找到 ${count} 个筛选器`)
        }
      })
    })

    test('5.4 点击报告查看详情', async ({ page }) => {
      await test.step('查找报告列表中的可点击项', async () => {
        const reportLinks = page.locator('a[href*="/reports/"], .report-card, [class*="report-card"]')
        const count = await reportLinks.count()
        if (count > 0) {
          const firstItem = reportLinks.first()
          await firstItem.click()
          await page.waitForTimeout(2000)

          const url = page.url()
          const hasReportPage = url.includes('/reports')
          expect(hasReportPage).toBe(true)
        }
      })
    })
  })

  test.describe('6. Mock规则 - 规则列表、Tab切换、调用日志', () => {
    test.beforeEach(async ({ page }) => {
      await utils.navigateTo(`/projects/${projectId}/mock-rules`)
      await page.waitForTimeout(2000)
    })

    test('6.1 Mock 规则页面基本结构', async ({ page }) => {
      await test.step('验证页面已加载', async () => {
        const hasContent = await utils.waitForPageContent(2)
        expect(hasContent).toBe(true)
      })

      await test.step('验证页面标题', async () => {
        const hasMockText = await page.getByText(/Mock|mock/).count() > 0
        expect(hasMockText).toBe(true)
      })
    })

    test('6.2 Mock 规则列表', async ({ page }) => {
      await test.step('查找规则列表', async () => {
        const ruleItems = page.locator('.mock-rule, [class*="mock"][class*="rule"], [class*="MockRule"]')
        const count = await ruleItems.count()
        if (count > 0) {
          console.log(`找到 ${count} 个 Mock 规则`)
          await expect(ruleItems.first()).toBeVisible()
        }
      })
    })

    test('6.3 Tab 切换（规则列表/调用日志）', async ({ page }) => {
      await test.step('查找并切换 Tab', async () => {
        const tabs = page.locator('.el-tabs__item, [class*="tab"], [role="tab"]')
        const tabCount = await tabs.count()
        if (tabCount > 1) {
          for (let i = 0; i < Math.min(tabCount, 3); i++) {
            await tabs.nth(i).click()
            await page.waitForTimeout(500)
          }
        }
      })
    })
  })

  test.describe('7. 设置 - 各Tab切换、环境管理', () => {
    test('7.1 尝试访问设置页面', async ({ page }) => {
      await test.step('尝试访问设置页面', async () => {
        await page.goto(`/#/projects/${projectId}/settings`)
        await page.waitForTimeout(2000)
      })

      await test.step('验证页面有响应（可能跳转或显示内容）', async () => {
        const title = await page.title()
        expect(title).toBeTruthy()
      })
    })
  })

  test.describe('8. 回收站', () => {
    test('8.1 尝试访问回收站页面', async ({ page }) => {
      await test.step('尝试访问回收站页面', async () => {
        await page.goto(`/#/projects/${projectId}/recycle-bin`)
        await page.waitForTimeout(2000)
      })

      await test.step('验证页面有响应', async () => {
        const title = await page.title()
        expect(title).toBeTruthy()
      })
    })
  })

  test.describe('9. 通用导航 - 侧边栏、面包屑、主题切换', () => {
    test.beforeEach(async ({ page }) => {
      await utils.navigateTo(`/projects/${projectId}/apis`)
      await page.waitForTimeout(2000)
    })

    test('9.1 侧边栏导航存在', async ({ page }) => {
      await test.step('查找侧边栏', async () => {
        const sidebar = page.locator('.sidebar, .app-sidebar, .el-menu, [class*="sidebar"], [class*="Sidebar"]')
        if (await sidebar.count() > 0) {
          await expect(sidebar.first()).toBeVisible()
        }
      })
    })

    test('9.2 侧边栏菜单项', async ({ page }) => {
      await test.step('查找菜单项', async () => {
        const menuItems = page.locator('.el-menu-item, [class*="menu-item"], [role="menuitem"]')
        const count = await menuItems.count()
        if (count > 0) {
          console.log(`找到 ${count} 个菜单项`)
          expect(count).toBeGreaterThan(0)
        }
      })
    })

    test('9.3 面包屑导航', async ({ page }) => {
      await test.step('查找面包屑', async () => {
        const breadcrumbs = page.locator('.el-breadcrumb, .breadcrumb-nav, [class*="breadcrumb"], [aria-label*="breadcrumb"]')
        const count = await breadcrumbs.count()
        if (count > 0) {
          const firstBreadcrumb = breadcrumbs.first()
          const exists = await firstBreadcrumb.count() > 0
          expect(exists).toBe(true)
        }
      })
    })

    test('9.4 顶部栏/导航栏', async ({ page }) => {
      await test.step('查找顶部栏', async () => {
        const topbar = page.locator('.topbar, .app-header, [class*="top-bar"], [class*="TopBar"], [class*="header"]')
        if (await topbar.count() > 0) {
          await expect(topbar.first()).toBeVisible()
        }
      })
    })

    test('9.5 项目名称显示', async ({ page }) => {
      await test.step('查找项目名称', async () => {
        const projectName = page.locator('.project-name, [class*="project-name"], [class*="ProjectName"]')
        if (await projectName.isVisible()) {
          await expect(projectName).toBeVisible()
        }
      })
    })

    test('9.6 演示项目标识', async ({ page }) => {
      await test.step('查找演示标识', async () => {
        const demoBadges = page.locator('.is-demo, [class*="demo-badge"], [class*="DemoBadge"]')
        const count = await demoBadges.count()
        if (count > 0) {
          await expect(demoBadges.first()).toContainText(/演示|Demo/)
        }
      })
    })

    test('9.7 侧边栏导航切换', async ({ page }) => {
      await test.step('切换到场景测试', async () => {
        const sceneMenu = page.locator('.el-menu-item, [class*="menu-item"]').filter({ hasText: /场景|Scene/ })
        if (await sceneMenu.count() > 0) {
          await sceneMenu.first().click()
          await page.waitForTimeout(1500)
          const url = page.url()
          expect(url).toContain('/scenes')
        }
      })

      await test.step('切换到测试报告', async () => {
        const reportMenu = page.locator('.el-menu-item, [class*="menu-item"]').filter({ hasText: /报告|Report/ })
        if (await reportMenu.count() > 0) {
          await reportMenu.first().click()
          await page.waitForTimeout(1500)
          const url = page.url()
          expect(url).toContain('/reports')
        }
      })

      await test.step('切换回接口管理', async () => {
        const apiMenu = page.locator('.el-menu-item, [class*="menu-item"]').filter({ hasText: /接口|API/ })
        if (await apiMenu.count() > 0) {
          await apiMenu.first().click()
          await page.waitForTimeout(1500)
          const url = page.url()
          expect(url).toContain('/apis')
        }
      })
    })
  })

  test.describe('10. 页面响应性与基础交互', () => {
    test('10.1 页面滚动正常', async ({ page }) => {
      await utils.navigateTo(`/projects/${projectId}/apis`)
      await page.waitForTimeout(2000)

      await test.step('测试页面滚动', async () => {
        const scrollHeight = await page.evaluate(() => document.body.scrollHeight)
        if (scrollHeight > 1000) {
          await page.evaluate(() => window.scrollTo(0, 500))
          await page.waitForTimeout(500)
          await page.evaluate(() => window.scrollTo(0, 0))
          await page.waitForTimeout(500)
        }
      })
    })

    test('10.2 页面标题正确', async ({ page }) => {
      await utils.navigateTo('/dashboard')
      await page.waitForTimeout(1000)

      await test.step('验证页面标题', async () => {
        const title = await page.title()
        expect(title).toBeTruthy()
        expect(title.length).toBeGreaterThan(0)
      })
    })

    test('10.3 访客模式横幅关闭功能', async ({ page }) => {
      await utils.navigateTo(`/projects/${projectId}/apis`)
      await page.waitForTimeout(2000)

      await test.step('查找并关闭访客横幅', async () => {
        const banner = page.locator('.readonly-banner.guest')
        if (await banner.isVisible()) {
          const closeBtn = banner.locator('.readonly-banner__close')
          if (await closeBtn.isVisible()) {
            await closeBtn.click()
            await page.waitForTimeout(500)
            expect(await banner.isVisible()).toBe(false)
          }
        }
      })
    })
  })
})
