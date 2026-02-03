import { test, expect } from '@playwright/test'

test.beforeEach(async ({ page }) => {
  await page.goto('/logs')
})

test.describe('Logs Page', () => {
  test('should load logs page', async ({ page }) => {
    await expect(page.getByRole('heading', { name: '错误日志' })).toBeVisible()
  })

  test('should show refresh button', async ({ page }) => {
    await expect(page.getByRole('button', { name: '刷新' })).toBeVisible()
  })

  test('should show clear logs button', async ({ page }) => {
    await expect(page.getByRole('button', { name: '清空日志' })).toBeVisible()
  })

  test('should show auto-refresh toggle', async ({ page }) => {
    await expect(page.getByText('自动刷新')).toBeVisible()
  })

  test('should show log stats', async ({ page }) => {
    await expect(page.locator('.el-tag').first()).toBeVisible()
  })

  test('should show empty state when no logs', async ({ page }) => {
    await expect(page.getByText('暂无错误日志')).toBeVisible()
  })
})
