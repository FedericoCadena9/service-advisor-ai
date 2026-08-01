import { fireEvent, render, screen } from '@testing-library/react'
import { expect, test, vi } from 'vitest'

import { CustomerTimelinePanel } from './CustomerTimelinePanel'
import { QuoteDraftPanel } from './QuoteDraftPanel'
import { ServiceQuestionPanel } from './ServiceQuestionPanel'

/** The API layer throws a plain Error for a dead network and for a refusal alike. */
const NETWORK_DOWN = new Error('Failed to fetch')
const REFUSED = Object.assign(new Error('rejected'), { status: 422 })

const APPOINTMENT = {
  id: 'appointment-1',
  quote_id: 'quote-1',
  bay_slot_id: 'bay-1-morning',
  starts_at: '2026-08-03T09:00:00',
  approver_role: 'advisor',
  simulated: true,
}
const PREVIEW = { text: 'Hola Demo Customer: ¿Confirma la cita?', segments: 1, priorities: ['x'] }

function timeline(overrides: Record<string, unknown> = {}) {
  return {
    onReserve: vi.fn().mockResolvedValue(APPOINTMENT),
    onPreview: vi.fn().mockResolvedValue(PREVIEW),
    onSend: vi.fn().mockResolvedValue({}),
    onAdvance: vi.fn().mockResolvedValue({}),
    ...overrides,
  }
}

test('a dead network while drafting tells the Advisor, instead of failing silently', async () => {
  render(<QuoteDraftPanel onDraft={vi.fn().mockRejectedValue(NETWORK_DOWN)} />)

  fireEvent.click(screen.getByRole('button', { name: 'Draft quote' }))

  expect(await screen.findByRole('alert')).toHaveTextContent('Quote draft unavailable')
})

test('a dead network while asking a data question is reported', async () => {
  render(<ServiceQuestionPanel onAskData={vi.fn().mockRejectedValue(NETWORK_DOWN)} />)

  fireEvent.click(screen.getByRole('button', { name: 'Run read-only query' }))

  expect(
    await screen.findByText('No supported read-only query answers this question'),
  ).toBeVisible()
})

test('a failed reservation is reported rather than leaving the panel blank', async () => {
  render(
    <CustomerTimelinePanel
      quoteId="quote-1"
      {...timeline({ onReserve: vi.fn().mockRejectedValue(NETWORK_DOWN) })}
    />,
  )

  fireEvent.click(screen.getByRole('button', { name: 'Reserve appointment' }))

  expect(await screen.findByText('The appointment could not be reserved')).toBeVisible()
})

test('a network failure and a refused message read differently', async () => {
  const offline = timeline({ onSend: vi.fn().mockRejectedValue(NETWORK_DOWN) })
  const { unmount } = render(<CustomerTimelinePanel quoteId="quote-1" {...offline} />)
  fireEvent.click(screen.getByRole('button', { name: 'Preview message' }))
  fireEvent.click(await screen.findByRole('button', { name: 'Enqueue message' }))
  expect(await screen.findByText('The message could not be sent right now')).toBeVisible()
  unmount()

  const refused = timeline({ onSend: vi.fn().mockRejectedValue(REFUSED) })
  render(<CustomerTimelinePanel quoteId="quote-1" {...refused} />)
  fireEvent.click(screen.getByRole('button', { name: 'Preview message' }))
  fireEvent.click(await screen.findByRole('button', { name: 'Enqueue message' }))

  expect(
    await screen.findByText('The message was rejected because it is not supported by the approved quote'),
  ).toBeVisible()
})

test('a failed preview does not offer a send button built on nothing', async () => {
  render(
    <CustomerTimelinePanel
      quoteId="quote-1"
      {...timeline({ onPreview: vi.fn().mockRejectedValue(NETWORK_DOWN) })}
    />,
  )

  fireEvent.click(screen.getByRole('button', { name: 'Preview message' }))

  expect(await screen.findByText('The message preview is unavailable')).toBeVisible()
  expect(screen.queryByRole('button', { name: 'Enqueue message' })).toBeNull()
})

test('a failed advance keeps the delivery on screen', async () => {
  render(
    <CustomerTimelinePanel
      quoteId="quote-1"
      {...timeline({
        onSend: vi.fn().mockResolvedValue({
          id: 'delivery-1',
          state: 'queued',
          approver_role: 'advisor',
          rule_version: 'v1',
          citation_page: 42,
        }),
        onAdvance: vi.fn().mockRejectedValue(NETWORK_DOWN),
      })}
    />,
  )
  fireEvent.click(screen.getByRole('button', { name: 'Preview message' }))
  fireEvent.click(await screen.findByRole('button', { name: 'Enqueue message' }))
  await screen.findByText('Simulated delivery: queued')

  fireEvent.click(screen.getByRole('button', { name: 'Advance timeline' }))

  expect(await screen.findByText('The timeline could not be advanced')).toBeVisible()
  expect(screen.getByText('Simulated delivery: queued')).toBeVisible()
})
