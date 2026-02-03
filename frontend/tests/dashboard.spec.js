import { test, expect } from '@playwright/test'

test.beforeEach(async ({ page }) => {
  await page.goto('/')
})

test.describe('Dashboard', () => {
  test('should load dashboard page', async ({ page }) => {
    await expect(page.locator('text=仪表盘')).toBeVisible()
  })

  test('should show sync button', async ({ page }) => {
    await expect(page.locator('button:has-text("同步")')).toBeVisible()
  })

  test('should show stats cards', async ({ page }) => {
    await expect(page.locator('.el-card')).toHaveCount(4)
  })

  test('should navigate to different pages from dashboard', async ({ page }) => {
    await page.click('text=订阅源')
    await expect(page).toHaveURL('/sources')
  })
})
