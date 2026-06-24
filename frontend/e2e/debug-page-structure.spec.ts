import { test, expect } from '@playwright/test'

test.describe('调试页面结构', () => {
  test('检查登录页面结构', async ({ page }) => {
    console.log('访问登录页面...')
    await page.goto('http://127.0.0.1:8081/#/login')
    await page.waitForTimeout(5000)
    
    const url = page.url()
    console.log('当前 URL:', url)
    
    const title = await page.title()
    console.log('页面标题:', title)
    
    const bodyHTML = await page.locator('body').innerHTML()
    console.log('body HTML 长度:', bodyHTML.length)
    
    console.log('\n=== 查找所有输入框 ===')
    const inputs = page.locator('input')
    const inputCount = await inputs.count()
    console.log('输入框数量:', inputCount)
    for (let i = 0; i < inputCount; i++) {
      const input = inputs.nth(i)
      const id = await input.getAttribute('id')
      const placeholder = await input.getAttribute('placeholder')
      const type = await input.getAttribute('type')
      console.log(`  输入框 ${i}: id=${id}, type=${type}, placeholder=${placeholder}`)
    }
    
    console.log('\n=== 查找所有按钮 ===')
    const buttons = page.getByRole('button')
    const buttonCount = await buttons.count()
    console.log('按钮数量:', buttonCount)
    for (let i = 0; i < Math.min(buttonCount, 20); i++) {
      const btn = buttons.nth(i)
      const text = await btn.textContent()
      console.log(`  按钮 ${i}: text=${text?.trim()}`)
    }
    
    console.log('\n=== 查找所有表单元素 ===')
    const formItems = page.locator('[class*="form"]')
    console.log('包含 form 的元素数量:', await formItems.count())
    
    await page.screenshot({ path: 'debug-login-page.png', fullPage: true })
  })

  test('检查注册页面结构', async ({ page }) => {
    console.log('访问注册页面...')
    await page.goto('http://127.0.0.1:8081/#/register')
    await page.waitForTimeout(5000)
    
    const url = page.url()
    console.log('当前 URL:', url)
    
    const title = await page.title()
    console.log('页面标题:', title)
    
    console.log('\n=== 查找所有输入框 ===')
    const inputs = page.locator('input')
    const inputCount = await inputs.count()
    console.log('输入框数量:', inputCount)
    for (let i = 0; i < inputCount; i++) {
      const input = inputs.nth(i)
      const id = await input.getAttribute('id')
      const placeholder = await input.getAttribute('placeholder')
      const type = await input.getAttribute('type')
      console.log(`  输入框 ${i}: id=${id}, type=${type}, placeholder=${placeholder}`)
    }
    
    console.log('\n=== 查找所有按钮 ===')
    const buttons = page.getByRole('button')
    const buttonCount = await buttons.count()
    console.log('按钮数量:', buttonCount)
    for (let i = 0; i < Math.min(buttonCount, 20); i++) {
      const btn = buttons.nth(i)
      const text = await btn.textContent()
      console.log(`  按钮 ${i}: text=${text?.trim()}`)
    }
    
    await page.screenshot({ path: 'debug-register-page.png', fullPage: true })
  })
})
