import { test, expect } from '@playwright/test'

test.beforeEach(async ({ page }) => {
  await page.goto('/')
})

test.describe('Navigation', () => {
  test('should show sidebar navigation', async ({ page }) => {
    await expect(page.locator('.sidebar')).toBeVisible()
    await expect(page.locator('.logo h1:has-text("Skills Aggregator")')).toBeVisible()
  })

  test('should navigate to Sources page', async ({ page }) => {
    await page.click('.el-menu-item:has-text("订阅源")')
    await expect(page).toHaveURL('/sources')
    await expect(page.locator('.header-title:has-text("订阅源管理")')).toBeVisible()
  })

  test('should navigate to Conflicts page', async ({ page }) => {
    await page.click('.el-menu-item:has-text("冲突处理")')
    await expect(page).toHaveURL('/conflicts')
    await expect(page.locator('.header-title:has-text("冲突处理")')).toBeVisible()
  })

  test('should navigate to Skills page', async ({ page }) => {
    await page.click('.el-menu-item:has-text("Skills")')
    await expect(page).toHaveURL('/skills')
    await expect(page.locator('.header-title:has-text("Skills 列表")')).toBeVisible()
  })

  test('should navigate to Logs page', async ({ page }) => {
    await page.goto('/logs')
    await expect(page).toHaveURL('/logs')
    await expect(page.getByRole('heading', { name: '错误日志' })).toBeVisible()
  })
})
