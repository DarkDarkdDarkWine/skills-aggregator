import { test, expect } from '@playwright/test'

test.beforeEach(async ({ page }) => {
  await page.goto('/sources')
})

test.describe('Sources Page', () => {
  test('should load sources page', async ({ page }) => {
    await expect(page.locator('.header-title')).toContainText('订阅源管理')
  })

  test('should show add source button', async ({ page }) => {
    await expect(page.getByRole('button', { name: '添加订阅源' })).toBeVisible()
  })

  test('should show sources table', async ({ page }) => {
    await expect(page.locator('.el-table')).toBeVisible()
  })

  test('should open add source dialog', async ({ page }) => {
    await page.click('button:has-text("添加订阅源")')
    await expect(page.getByRole('heading', { name: '添加订阅源' })).toBeVisible()
  })

  test('should close dialog when cancel', async ({ page }) => {
    await page.click('button:has-text("添加订阅源")')
    await expect(page.locator('.el-dialog')).toBeVisible()
    await page.click('.el-dialog__header >> .el-dialog__close')
    await expect(page.locator('.el-dialog')).not.toBeVisible()
  })
})


test.describe('Conflicts Page', () => {
  test('should load conflicts page', async ({ page }) => {
    await page.goto('/conflicts')
    await expect(page.locator('.header-title')).toContainText('冲突处理')
  })

  test('should show conflicts table', async ({ page }) => {
    await page.goto('/conflicts')
    await expect(page.locator('.el-table')).toBeVisible()
  })
})


test.describe('Skills Page', () => {
  test('should load skills page', async ({ page }) => {
    await page.goto('/skills')
    await expect(page.locator('.header-title')).toContainText('Skills 列表')
  })

  test('should show skills table', async ({ page }) => {
    await page.goto('/skills')
    await expect(page.locator('.el-table')).toBeVisible()
  })
})
