import { test, expect } from '@playwright/test'

test.beforeEach(async ({ page }) => {
  await page.goto('/sources')
})

test.describe('Sources Page', () => {
  test('should load sources page', async ({ page }) => {
    await expect(page.locator('.header-title:has-text("订阅源管理")')).toBeVisible()
  })

  test('should show add source button', async ({ page }) => {
    await expect(page.locator('.page-header button:has-text("添加订阅源")')).toBeVisible()
  })

  test('should show sources table', async ({ page }) => {
    await expect(page.locator('.el-table')).toBeVisible()
  })

  test('should open add source dialog', async ({ page }) => {
    await page.click('.page-header button:has-text("添加订阅源")')
    await expect(page.locator('.el-dialog__title:has-text("添加订阅源")')).toBeVisible()
  })

  test('should close dialog when cancel', async ({ page }) => {
    await page.click('.page-header button:has-text("添加订阅源")')
    await expect(page.locator('.el-dialog')).toBeVisible()
    await page.click('.el-dialog__header >> .el-dialog__close')
    await expect(page.locator('.el-dialog')).not.toBeVisible()
  })
})
