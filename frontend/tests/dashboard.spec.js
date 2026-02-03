import { test, expect } from '@playwright/test'

test.beforeEach(async ({ page }) => {
  await page.goto('/')
})

test.describe('Dashboard', () => {
  test('should load dashboard page', async ({ page }) => {
    await expect(page.locator('.header-title')).toContainText('仪表盘')
  })

  test('should show sync button', async ({ page }) => {
    await expect(page.locator('.header-actions button').first()).toBeVisible()
  })

  test('should navigate to different pages from dashboard', async ({ page }) => {
    await page.click('text=订阅源')
    await expect(page).toHaveURL('/sources')
  })
})
