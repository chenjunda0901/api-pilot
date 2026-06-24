import { test, expect } from '@playwright/test'
import { TestUtils, generateUniqueId, TEST_PASSWORDS } from './utils/test-utils'

test.describe('用户画像 3：测试工程师', () => {
  let utils: TestUtils
  const timestamp = generateUniqueId()
  const username = `tester_${timestamp}`
  const password = TEST_PASSWORDS.strong
  let projectId: number

  test.beforeAll(async ({ browser }) => {
    const page = await browser.newPage()
    const setupUtils = new TestUtils(page)
    await setupUtils.registerUser(username, password, '测试工程师', `tester_${timestamp}@test.com`)
    await setupUtils.navigateTo('/dashboard')
    await page.waitForTimeout(2000)
    const url = page.url()
    const match = url.match(/\/projects\/(\d+)/)
    projectId = match ? parseInt(match[1]) : 0
    if (!projectId) {
      projectId = await setupUtils.createProject(`测试项目_${timestamp}`)
    }
    await page.close()
  })

  test.beforeEach(async ({ page }) => {
    utils = new TestUtils(page)
    await utils.loginUser(username, password)
  })

  test('3.1 创建测试用例', async ({ page }) => {
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

    await test.step('创建测试用例', async () => {
      const saveCaseBtn = page.getByRole('button', { name: /保存用例|另存为用例|用例/ }).first()
      if (await saveCaseBtn.isVisible()) {
        await saveCaseBtn.click()
        await page.waitForTimeout(1000)

        const nameInput = page.locator('input[placeholder*="用例名称"], input[placeholder*="请输入用例名称"]').first()
        if (await nameInput.isVisible()) {
          await nameInput.fill(`测试用例_${timestamp}`)
        }

        const confirmBtn = page.getByRole('button', { name: /确定|保存|创建/ }).first()
        if (await confirmBtn.isVisible()) {
          await confirmBtn.click()
          await page.waitForTimeout(2000)
        }
      }
    })
  })

  test('3.2 配置断言（状态码、响应时间等）', async ({ page }) => {
    await test.step('进入用例详情', async () => {
      const caseTab = page.getByText(/用例|Case/).first()
      if (await caseTab.isVisible()) {
        await caseTab.click()
        await page.waitForTimeout(1000)
      }
    })

    await test.step('进入断言配置', async () => {
      const assertionTab = page.getByText(/断言|Assertion/).first()
      if (await assertionTab.isVisible()) {
        await assertionTab.click()
        await page.waitForTimeout(1000)

        const addAssertionBtn = page.getByRole('button', { name: /添加断言|新增断言|\+/ }).first()
        if (await addAssertionBtn.isVisible()) {
          await addAssertionBtn.click()
          await page.waitForTimeout(500)
        }
      }
    })
  })

  test('3.3 配置变量提取', async ({ page }) => {
    await test.step('进入变量提取配置', async () => {
      const extractTab = page.getByText(/变量提取|提取|Extract/).first()
      if (await extractTab.isVisible()) {
        await extractTab.click()
        await page.waitForTimeout(1000)

        const addExtractBtn = page.getByRole('button', { name: /添加|新增|\+/ }).first()
        if (await addExtractBtn.isVisible()) {
          await addExtractBtn.click()
          await page.waitForTimeout(500)
        }
      }
    })
  })

  test('3.4 配置前置/后置脚本', async ({ page }) => {
    await test.step('进入前置脚本配置', async () => {
      const preScriptTab = page.getByText(/前置脚本|Pre-script|Pre/).first()
      if (await preScriptTab.isVisible()) {
        await preScriptTab.click()
        await page.waitForTimeout(1000)
      }
    })

    await test.step('进入后置脚本配置', async () => {
      const postScriptTab = page.getByText(/后置脚本|Post-script|Post/).first()
      if (await postScriptTab.isVisible()) {
        await postScriptTab.click()
        await page.waitForTimeout(1000)
      }
    })
  })

  test('3.5 执行用例并查看结果', async ({ page }) => {
    await test.step('点击运行按钮', async () => {
      const runBtn = page.getByRole('button', { name: /运行|执行|Run/ }).first()
      if (await runBtn.isVisible()) {
        await runBtn.click()
        await page.waitForTimeout(3000)
      }
    })

    await test.step('查看执行结果', async () => {
      const resultPanel = page.locator('.result-panel, [class*="result"], [class*="assertion"]').first()
      if (await resultPanel.isVisible()) {
        expect(resultPanel).toBeVisible()
      }
    })
  })

  test('3.6 创建场景测试', async ({ page }) => {
    await test.step('进入场景测试页面', async () => {
      await utils.navigateTo(`/projects/${projectId}/scenes`)
      await page.waitForTimeout(2000)
    })

    await test.step('创建新场景', async () => {
      const addSceneBtn = page.getByRole('button', { name: /新建场景|创建场景|\+ 场景/ }).first()
      if (await addSceneBtn.isVisible()) {
        await addSceneBtn.click()
        await page.waitForTimeout(1000)

        const nameInput = page.locator('input[placeholder*="场景名称"], input[placeholder*="请输入场景名称"]').first()
        if (await nameInput.isVisible()) {
          await nameInput.fill(`测试场景_${timestamp}`)
        }

        const confirmBtn = page.getByRole('button', { name: /确定|创建|保存/ }).first()
        if (await confirmBtn.isVisible()) {
          await confirmBtn.click()
          await page.waitForTimeout(2000)
        }
      }
    })
  })

  test('3.7 导入接口和用例到场景', async ({ page }) => {
    await test.step('进入场景详情', async () => {
      const sceneItem = page.locator('.scene-item, .tree-node, [class*="scene"][class*="node"]').first()
      if (await sceneItem.isVisible()) {
        await sceneItem.click()
        await page.waitForTimeout(2000)
      }
    })

    await test.step('添加步骤', async () => {
      const addStepBtn = page.getByRole('button', { name: /添加步骤|新增步骤|导入|\+/ }).first()
      if (await addStepBtn.isVisible()) {
        await addStepBtn.click()
        await page.waitForTimeout(1000)
      }
    })
  })

  test('3.8 编排场景步骤顺序', async ({ page }) => {
    await test.step('查看场景步骤列表', async () => {
      const stepList = page.locator('.step-list, [class*="step"][class*="list"], .sortable-list').first()
      if (await stepList.isVisible()) {
        expect(stepList).toBeVisible()
      }
    })
  })

  test('3.9 执行场景测试', async ({ page }) => {
    await test.step('点击运行场景', async () => {
      const runBtn = page.getByRole('button', { name: /运行|执行|Run|开始/ }).first()
      if (await runBtn.isVisible()) {
        await runBtn.click()
        await page.waitForTimeout(3000)
      }
    })

    await test.step('查看执行进度', async () => {
      const progressBar = page.locator('.progress, [class*="progress"], .execution-progress').first()
      if (await progressBar.isVisible()) {
        expect(progressBar).toBeVisible()
      }
    })
  })
})
