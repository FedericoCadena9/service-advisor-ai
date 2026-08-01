import { fireEvent, render, screen } from '@testing-library/react'
import { expect, test, vi } from 'vitest'

import App from './App'
import { CHECKIN_GONE } from './api/failure'
import { fetchHealth } from './api/health'
import { fetchRecommendation } from './api/recommendations'

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

vi.mock('./api/checkins', () => ({
  saveCheckin: vi.fn().mockResolvedValue({ vehicle_id: 'honda-civic-2019-lx' }),
}))

vi.mock('./api/recommendations', () => ({
  fetchRecommendation: vi.fn().mockResolvedValue({
    state: 'due_now',
    service_code: 'HONDA-A1',
    due_reason: 'The Maintenance Minder decides',
  }),
}))

async function confirmCheckin() {
  render(<App />)
  fireEvent.click(await screen.findByRole('button', { name: 'Enter as Advisor' }))
  fireEvent.change(await screen.findByLabelText('Current mileage (km)'), {
    target: { value: '48000' },
  })
  fireEvent.submit(screen.getByRole('form', { name: 'Check-in details' }))
}

test('shows the healthy demo environment state', async () => {
  render(<App />)

  expect(await screen.findByRole('status')).toHaveTextContent('Demo environment healthy')
})

test('shows the unavailable demo environment state', async () => {
  vi.mocked(fetchHealth)
    .mockRejectedValueOnce(new Error('offline'))
    .mockRejectedValueOnce(new Error('offline'))

  render(<App />)

  expect(await screen.findByText('Demo environment unavailable')).toBeVisible()
})

test('reports cold-start progress while the demo wakes from scale to zero', async () => {
  vi.mocked(fetchHealth).mockRejectedValueOnce(new Error('cold start'))

  render(<App />)

  expect(await screen.findByText('Waking the demo environment after scale to zero')).toBeVisible()
  expect(await screen.findByText('Demo environment healthy')).toBeVisible()
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

test('renders labeled check-in controls for an Advisor workspace', async () => {
  render(<App />)
  fireEvent.click(await screen.findByRole('button', { name: 'Enter as Advisor' }))

  expect(await screen.findByLabelText('Current mileage (km)')).toBeVisible()
  expect(screen.getByLabelText('Severe use factors')).toBeVisible()
  expect(screen.getByLabelText('Consent to prepare a message')).toBeVisible()
})

test('shows the grounded recommendation console in an Advisor workspace', async () => {
  render(<App />)
  fireEvent.click(await screen.findByRole('button', { name: 'Enter as Advisor' }))

  expect(await screen.findByText('Grounded maintenance recommendation')).toBeVisible()
})

/** What if the instance restarted between saving the check-in and reading the rule for it? */
test('a recommendation whose check-in is gone asks for the check-in again', async () => {
  vi.mocked(fetchRecommendation).mockRejectedValueOnce(
    Object.assign(new Error('conflict'), { status: 409 }),
  )

  await confirmCheckin()

  expect(await screen.findByText(CHECKIN_GONE)).toBeVisible()
})

/** What if only the recommendation failed — was the check-in in front of it really not saved? */
test('a saved check-in is not reported as unsaved when the recommendation fails', async () => {
  vi.mocked(fetchRecommendation).mockRejectedValueOnce(new Error('offline'))

  await confirmCheckin()

  expect(
    await screen.findByText('The recommendation could not be prepared'),
  ).toBeVisible()
  expect(screen.getByText('Check-in confirmed')).toBeVisible()
})
