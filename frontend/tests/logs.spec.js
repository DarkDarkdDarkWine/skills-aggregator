import { test, expect } from '@playwright/test'

test.beforeEach(async ({ page }) => {
  await page.goto('/logs')
})

test.describe('Logs Page', () => {
  test('should load logs page', async ({ page }) => {
    await expect(page.locator('text=错误日志')).toBeVisible()
  })

  test('should show refresh button', async ({ page }) => {
    await expect(page.locator('button:has-text("刷新")')).toBeVisible()
  })

  test('should show clear logs button', async ({ page }) => {
    await expect(page.locator('button:has-text("清空日志")')).toBeVisible()
  })

  test('should show auto-refresh toggle', async ({ page }) => {
    await expect(page.locator('text=自动刷新')).toBeVisible()
  })

  test('should show log stats', async ({ page }) => {
    await expect(page.locator('.el-tag')).toBeVisible()
  })

  test('should show logs table', async ({ page }) => {
    await expect(page.locator('.el-table')).toBeVisible()
  })

  test('should show empty state when no logs', async ({ page }) => {
    await expect(page.locator('text=暂无错误日志')).toBeVisible()
  })

  test('should toggle auto-refresh', async ({ page }) => {
    await page.locator('.el-switch').click()
    await expect(page.locator('.el-switch').locator('input')).toBeChecked()
  })
})
