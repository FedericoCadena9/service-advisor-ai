import { expect, test } from '@playwright/test'

test('loads the healthy demo environment', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('status')).toHaveText('Demo environment healthy')
})
