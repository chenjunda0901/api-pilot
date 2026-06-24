import { Page, expect, Locator } from '@playwright/test'

export class TestUtils {
  constructor(public page: Page) {}

  async waitForPageContent(minElements: number = 1) {
    for (let attempt = 0; attempt < 3; attempt++) {
      try {
        await this.page.waitForFunction((min) => {
          const inputs = document.querySelectorAll('input').length
          const buttons = document.querySelectorAll('button').length
          const links = document.querySelectorAll('a').length
          return inputs + buttons + links >= min
        }, minElements, { timeout: 10000 })
        return true
      } catch {
        if (attempt < 2) {
          console.log(`页面内容加载尝试 ${attempt + 1} 失败，刷新重试...`)
          await this.page.reload()
          await this.page.waitForTimeout(2000)
        }
      }
    }
    return false
  }

  async isLoggedIn(): Promise<boolean> {
    try {
      const userMenu = this.page.locator('.user-avatar, .user-menu-trigger, [class*="user"]').first()
      return await userMenu.isVisible({ timeout: 3000 })
    } catch {
      return false
    }
  }

  async navigateTo(path: string) {
    await this.page.goto(`/#${path}`)
    await this.page.waitForLoadState('networkidle')
    await this.page.waitForTimeout(1000)
    
    const currentHash = await this.page.evaluate(() => window.location.hash)
    if (!currentHash.includes(path)) {
      console.log(`导航到 ${path} 失败（当前 ${currentHash}），刷新重试...`)
      await this.page.reload()
      await this.page.waitForLoadState('networkidle')
      await this.page.waitForTimeout(1000)
    }
    
    await this.waitForPageContent(1)
  }

  async waitForNavigation(targetHash: string, timeout: number = 30000) {
    await this.page.waitForFunction((target) => {
      return window.location.hash.includes(target)
    }, targetHash, { timeout })
  }

  async waitForPageLoadedAfterNavigation() {
    await this.page.waitForLoadState('networkidle')
    await this.page.waitForTimeout(1000)
    
    const hasContent = await this.page.evaluate(() => {
      const inputs = document.querySelectorAll('input').length
      const buttons = document.querySelectorAll('button').length
      const bodyText = document.body.textContent || ''
      return inputs > 0 || buttons > 0 || bodyText.length > 500
    })
    
    if (!hasContent) {
      console.log('页面内容加载失败，刷新重试...')
      await this.page.reload()
      await this.page.waitForLoadState('networkidle')
      await this.page.waitForTimeout(2000)
    }
  }

  async registerUser(username: string, password: string, nickname?: string, email?: string) {
    await this.navigateTo('/register')
    await this.page.waitForSelector('#reg-username', { state: 'visible', timeout: 30000 })
    
    await this.page.fill('#reg-username', username)
    await this.page.fill('#reg-password', password)
    await this.page.fill('#reg-confirm-password', password)
    if (nickname) {
      await this.page.fill('#reg-nickname', nickname)
    }
    if (email) {
      await this.page.fill('#reg-email', email)
    }
    await this.page.click('.register-btn')
    await this.waitForNavigation('dashboard')
    await this.waitForPageLoadedAfterNavigation()
  }

  async loginUser(username: string, password: string) {
    if (await this.isLoggedIn()) {
      console.log('用户已登录，先退出登录...')
      await this.logout()
    }
    
    await this.navigateTo('/login')
    
    try {
      await this.page.waitForSelector('#login-username', { state: 'visible', timeout: 10000 })
    } catch {
      console.log('未找到登录输入框，刷新页面重试...')
      await this.page.reload()
      await this.page.waitForLoadState('networkidle')
      await this.page.waitForTimeout(2000)
      await this.page.waitForSelector('#login-username', { state: 'visible', timeout: 30000 })
    }
    
    await this.page.fill('#login-username', username)
    await this.page.fill('#login-password', password)
    await this.page.click('.login-btn')
    await this.waitForNavigation('dashboard')
    await this.waitForPageLoadedAfterNavigation()
  }

  async logout() {
    const userMenu = this.page.locator('.user-avatar, .user-menu-trigger, [class*="user"]').first()
    if (await userMenu.isVisible()) {
      await userMenu.click()
      await this.page.waitForTimeout(500)
      const logoutBtn = this.page.getByText('退出登录').first()
      if (await logoutBtn.isVisible()) {
        await logoutBtn.click()
        await this.page.waitForTimeout(2000)
        
        const currentHash = await this.page.evaluate(() => window.location.hash)
        if (!currentHash.includes('login')) {
          console.log('退出登录后未跳转到登录页，手动导航...')
          await this.page.goto('/#/login')
          await this.page.waitForLoadState('networkidle')
          await this.page.waitForTimeout(1000)
        }
        
        await this.waitForPageLoadedAfterNavigation()
      }
    }
  }

  async createProject(projectName: string): Promise<number> {
    await this.navigateTo('/dashboard')
    await this.page.waitForTimeout(1000)
    
    const createBtn = this.page.getByRole('button', { name: /创建项目|新建项目/ })
    if (await createBtn.isVisible()) {
      await createBtn.click()
    } else {
      const addBtn = this.page.getByRole('button', { name: /新建|添加/ }).first()
      if (await addBtn.isVisible()) {
        await addBtn.click()
      }
    }
    
    await this.page.waitForTimeout(1000)
    
    const nameInput = this.page.locator('input[placeholder*="项目名称"]')
    if (await nameInput.isVisible()) {
      await nameInput.fill(projectName)
      const confirmBtn = this.page.getByRole('button', { name: /确定|创建|保存/ }).first()
      await confirmBtn.click()
      await this.page.waitForTimeout(3000)
    }
    
    const url = this.page.url()
    const match = url.match(/\/projects\/(\d+)/)
    return match ? parseInt(match[1]) : 0
  }

  async createCategory(categoryName: string) {
    const addBtn = this.page.getByRole('button', { name: /新建分类|添加分类|\+ 分类/ }).first()
    if (await addBtn.isVisible()) {
      await addBtn.click()
      await this.page.waitForTimeout(500)
      const nameInput = this.page.locator('input[placeholder*="分类名称"]').first()
      if (await nameInput.isVisible()) {
        await nameInput.fill(categoryName)
        const confirmBtn = this.page.getByRole('button', { name: /确定|创建/ }).first()
        await confirmBtn.click()
        await this.page.waitForTimeout(1000)
      }
    }
  }

  async createApi(apiName: string, method: string = 'GET', path: string = '/api/test') {
    const addBtn = this.page.getByRole('button', { name: /新建接口|添加接口|\+ 接口/ }).first()
    if (await addBtn.isVisible()) {
      await addBtn.click()
      await this.page.waitForTimeout(1000)
      
      const nameInput = this.page.locator('input[placeholder*="接口名称"]').first()
      if (await nameInput.isVisible()) {
        await nameInput.fill(apiName)
      }
      
      const methodSelect = this.page.locator('.el-select').first()
      if (await methodSelect.isVisible()) {
        await methodSelect.click()
        await this.page.getByText(method.toUpperCase()).click()
      }
      
      const urlInput = this.page.locator('input[placeholder*="接口地址"]').first()
      if (await urlInput.isVisible()) {
        await urlInput.fill(path)
      }
      
      const saveBtn = this.page.getByRole('button', { name: /确定|保存|创建/ }).first()
      if (await saveBtn.isVisible()) {
        await saveBtn.click()
        await this.page.waitForTimeout(2000)
      }
    }
  }

  async sendRequest() {
    const sendBtn = this.page.getByRole('button', { name: /发送|Send|运行/ }).first()
    if (await sendBtn.isVisible()) {
      await sendBtn.click()
      await this.page.waitForTimeout(3000)
    }
  }

  async getToastMessage(): Promise<string> {
    const toast = this.page.locator('.el-message').first()
    try {
      await toast.waitFor({ state: 'visible', timeout: 5000 })
      return await toast.textContent() || ''
    } catch {
      return ''
    }
  }

  async waitForToastContains(text: string) {
    await expect(this.page.locator('.el-message').first()).toContainText(text)
  }

  async selectEnvironment(envName: string) {
    const envSwitcher = this.page.locator('.env-switcher, .env-selector')
    if (await envSwitcher.isVisible()) {
      await envSwitcher.click()
      await this.page.getByText(envName).first().click()
    }
  }

  async goToSection(section: string) {
    const sidebar = this.page.locator('.sidebar, .app-sidebar, .el-menu')
    const link = sidebar.getByText(section).first()
    if (await link.isVisible()) {
      await link.click()
      await this.page.waitForTimeout(1500)
    }
  }

  async clickButtonByText(text: string) {
    await this.page.getByRole('button', { name: text }).first().click()
  }

  async fillInputByPlaceholder(placeholder: string, value: string) {
    await this.page.fill(`input[placeholder*="${placeholder}"]`, value)
  }

  async isElementVisible(selector: string): Promise<boolean> {
    try {
      await this.page.waitForSelector(selector, { state: 'visible', timeout: 5000 })
      return true
    } catch {
      return false
    }
  }

  async takeScreenshot(name: string) {
    await this.page.screenshot({ path: `screenshots/${name}.png`, fullPage: true })
  }

  async waitForLoading() {
    try {
      await this.page.waitForSelector('.el-loading-mask', { state: 'hidden', timeout: 15000 })
    } catch {
    }
  }

  async getTextContent(locator: Locator): Promise<string> {
    return (await locator.textContent()) || ''
  }

  async delay(ms: number) {
    await this.page.waitForTimeout(ms)
  }
}

export function generateUniqueId(maxLength: number = 10): string {
  const id = Date.now().toString(36) + Math.random().toString(36).substr(2, 5)
  return id.substr(0, maxLength)
}

export function generateEmail(username: string): string {
  return `${username}@test.com`
}

export const TEST_PASSWORDS = {
  strong: 'Test@123456',
  weak: '123',
  wrong: 'Wrong@123456',
}
