import { fireEvent, render, screen } from '@testing-library/react'
import { expect, test, vi } from 'vitest'

import App from './App'
import { fetchHealth } from './api/health'

vi.mock('./api/health', () => ({
  fetchHealth: vi.fn().mockResolvedValue({ status: 'healthy' }),
}))

vi.mock('./api/demo-session', () => ({
  enterDemoWorkspace: vi.fn().mockResolvedValue({
    token: 'signed-demo-token',
    workspace: {
      shop_id: 'demo-shop',
      demo_session_id: 'demo-session',
      role: 'advisor',
      generation: 0,
    },
  }),
}))

test('shows the healthy demo environment state', async () => {
  render(<App />)

  expect(await screen.findByRole('status')).toHaveTextContent('Demo environment healthy')
})

test('shows the unavailable demo environment state', async () => {
  vi.mocked(fetchHealth).mockRejectedValueOnce(new Error('offline'))

  render(<App />)

  expect(await screen.findByRole('status')).toHaveTextContent('Demo environment unavailable')
})

test('lets a visitor choose the Advisor role before entering the workspace', async () => {
  render(<App />)

  expect(await screen.findByRole('button', { name: 'Enter as Advisor' })).toBeVisible()
})

test('offers an accessible vehicle search after the demo workspace opens', async () => {
  render(<App />)
  fireEvent.click(await screen.findByRole('button', { name: 'Enter as Advisor' }))

  expect(await screen.findByRole('searchbox', { name: 'Search demo vehicle' })).toBeVisible()
})
