import { test, expect } from '@playwright/test'

test.describe('调试重试', () => {
  test('多次尝试访问登录页面', async ({ page }) => {
    const maxAttempts = 5
    
    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      console.log(`\n=== 第 ${attempt} 次尝试 ===`)
      
      await page.goto('http://127.0.0.1:8081/')
      await page.waitForTimeout(3000)
      
      const inputs = page.locator('input')
      const inputCount = await inputs.count()
      console.log(`输入框数量: ${inputCount}`)
      
      const buttons = page.getByRole('button')
      const buttonCount = await buttons.count()
      console.log(`按钮数量: ${buttonCount}`)
      
      const bodyText = await page.locator('body').textContent()
      console.log(`body 文本长度: ${bodyText?.length}`)
      
      if (inputCount > 0 && buttonCount > 0) {
        console.log('页面加载成功！')
        
        const loginInput = page.locator('#login-username')
        if (await loginInput.isVisible()) {
          console.log('找到登录输入框')
        }
        
        await page.screenshot({ path: `debug-success-attempt-${attempt}.png`, fullPage: true })
        break
      } else {
        console.log('页面加载失败，刷新重试...')
        await page.screenshot({ path: `debug-fail-attempt-${attempt}.png`, fullPage: true })
        await page.reload()
        await page.waitForTimeout(3000)
      }
    }
  })

  test('从首页导航到登录页面', async ({ page }) => {
    console.log('访问首页...')
    await page.goto('http://127.0.0.1:8081/')
    await page.waitForTimeout(5000)
    
    const url = page.url()
    console.log('首页 URL:', url)
    
    const hash = await page.evaluate(() => window.location.hash)
    console.log('首页 hash:', hash)
    
    const inputs = page.locator('input')
    const inputCount = await inputs.count()
    console.log('输入框数量:', inputCount)
    
    await page.screenshot({ path: 'debug-homepage.png', fullPage: true })
    
    if (inputCount === 0) {
      console.log('首页没有输入框，尝试导航到登录页...')
      await page.evaluate(() => {
        window.location.hash = '/login'
      })
      await page.waitForTimeout(5000)
      
      const inputsAfter = page.locator('input')
      console.log('导航后输入框数量:', await inputsAfter.count())
      
      await page.screenshot({ path: 'debug-after-hash-nav.png', fullPage: true })
    }
  })
})
