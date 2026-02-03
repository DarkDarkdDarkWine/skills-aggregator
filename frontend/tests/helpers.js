export const API_BASE = process.env.API_BASE || 'http://localhost:8080/api'

export const waitForBackend = async (page, timeout = 30000) => {
  const startTime = Date.now()
  while (Date.now() - startTime < timeout) {
    try {
      const response = await page.request.get(`${API_BASE}/health`)
      if (response.ok()) {
        return true
      }
    } catch {
      await page.waitForTimeout(1000)
    }
  }
  throw new Error('Backend not available')
}
