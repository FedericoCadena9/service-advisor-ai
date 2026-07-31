import { fireEvent, render, screen } from '@testing-library/react'
import { expect, test, vi } from 'vitest'

import { RecommendationConsole } from './RecommendationConsole'

function renderConsole(overrides: Partial<Parameters<typeof RecommendationConsole>[0]> = {}) {
  const props = {
    recommendation: undefined,
    onStartRun: vi.fn().mockResolvedValue({ id: 'run-1', events: ['started', 'awaiting_human_review'] }),
    onApproveRun: vi.fn().mockResolvedValue(undefined),
    onAsk: vi.fn().mockResolvedValue('HONDA-A1 is due now, page 42.'),
    onDraftQuote: vi.fn().mockResolvedValue({
      lines: [
        {
          service_code: 'HONDA-A1',
          labor_mxn: '620.00',
          parts_mxn: '973.00',
          iva_mxn: '254.88',
          total_mxn: '1847.88',
          duration_minutes: 50,
          fitment: 'confirmed',
          available: true,
          unavailable_reason: null,
        },
        {
          service_code: 'HONDA-CABIN-FILTER',
          labor_mxn: '0.00',
          parts_mxn: '0.00',
          iva_mxn: '0.00',
          total_mxn: '0.00',
          duration_minutes: 0,
          fitment: 'confirmed',
          available: false,
          unavailable_reason: 'Part HON-CABIN-80292 is backordered until 2026-08-14',
        },
      ],
      subtotal_mxn: '1593.00',
      iva_mxn: '254.88',
      total_mxn: '1847.88',
      duration_minutes: 50,
      bay_slot_id: 'bay-1-morning',
      warnings: [],
    }),
    onOpenReview: vi.fn().mockResolvedValue({
      id: 'review-1',
      vehicle_id: 'honda-civic-2019-lx',
      approver_role: 'advisor',
      approver_session_id: 'session-1',
      facts: {
        service_codes: ['HONDA-A1'],
        subtotal_mxn: '1593.00',
        iva_mxn: '254.88',
        total_mxn: '1847.88',
        duration_minutes: 50,
        bay_slot_id: 'bay-1-morning',
      },
      citations: {
        rule_version: 'honda-civic-2019-lx-v1',
        citation_page: 42,
        citation_section: 'Maintenance Minder',
      },
      status: 'in_review',
      invalidation_reason: null,
    }),
    onDecideReview: vi.fn().mockResolvedValue({
      id: 'decision-1',
      review_id: 'review-1',
      quote_id: 'quote-1',
      decision: 'approved',
      approver_role: 'advisor',
      approver_session_id: 'session-1',
      reason: null,
      facts: {
        service_codes: ['HONDA-A1'],
        subtotal_mxn: '1593.00',
        iva_mxn: '254.88',
        total_mxn: '1847.88',
        duration_minutes: 50,
        bay_slot_id: 'bay-1-morning',
      },
      citations: {
        rule_version: 'honda-civic-2019-lx-v1',
        citation_page: 42,
        citation_section: 'Maintenance Minder',
      },
    }),
    ...overrides,
  }
  render(<RecommendationConsole {...props} />)
  return props
}

test('replays persisted advisor run events after starting a run', async () => {
  renderConsole()
  fireEvent.click(screen.getByRole('tab', { name: 'Advisor run' }))

  fireEvent.click(screen.getByRole('button', { name: 'Start run' }))

  expect(await screen.findByText('Run run-1: started → awaiting_human_review')).toBeVisible()
})

test('keeps the human decision explicit and idempotent', async () => {
  const props = renderConsole()
  fireEvent.click(screen.getByRole('tab', { name: 'Advisor run' }))

  fireEvent.click(screen.getByRole('button', { name: 'Approve review' }))

  expect(await screen.findByText('Approved idempotently')).toBeVisible()
  expect(props.onApproveRun).toHaveBeenCalledTimes(1)
})

test('shows priced quote lines with an explicit unavailable reason', async () => {
  renderConsole()
  fireEvent.click(screen.getByRole('tab', { name: 'Quote' }))

  fireEvent.click(screen.getByRole('button', { name: 'Draft quote' }))

  const lines = await screen.findByRole('table', { name: 'Quote draft lines' })
  expect(lines).toHaveTextContent('620.00')
  expect(lines).toHaveTextContent('254.88')
  expect(lines).toHaveTextContent('Part HON-CABIN-80292 is backordered until 2026-08-14')
  expect(screen.getByText(/Subtotal 1593.00 \+ IVA 254.88 = 1847.88 MXN · 50 min · bay-1-morning/)).toBeVisible()
})

test('shows the approver, services, facts, and citations before approval', async () => {
  renderConsole()
  fireEvent.click(screen.getByRole('tab', { name: 'Approval' }))

  fireEvent.click(screen.getByRole('button', { name: 'Open approval' }))

  expect(await screen.findByText('advisor · session session-1')).toBeVisible()
  expect(screen.getByText('HONDA-A1')).toBeVisible()
  expect(screen.getByText('1847.88 MXN including IVA 254.88 · 50 min · bay-1-morning')).toBeVisible()
  expect(screen.getByText('honda-civic-2019-lx-v1 · page 42, Maintenance Minder')).toBeVisible()
})

test('reports the saved quote after an approval command', async () => {
  renderConsole()
  fireEvent.click(screen.getByRole('tab', { name: 'Approval' }))
  fireEvent.click(screen.getByRole('button', { name: 'Open approval' }))

  fireEvent.click(await screen.findByRole('button', { name: 'Approve quote' }))

  expect(await screen.findByRole('status')).toHaveTextContent('Quote quote-1 approved by advisor')
})

test('returns an invalidated quote to review', async () => {
  renderConsole({ onDecideReview: vi.fn().mockRejectedValue(new Error('stale')) })
  fireEvent.click(screen.getByRole('tab', { name: 'Approval' }))
  fireEvent.click(screen.getByRole('button', { name: 'Open approval' }))

  fireEvent.click(await screen.findByRole('button', { name: 'Approve quote' }))

  expect(
    await screen.findByText('Price, inventory, or slot inputs changed; the quote returned to review'),
  ).toBeVisible()
})

test('answers a contextual question from grounded evidence', async () => {
  renderConsole()
  fireEvent.click(screen.getByRole('tab', { name: 'Explain' }))

  fireEvent.change(screen.getByLabelText('Contextual question'), { target: { value: 'Why is this due?' } })
  fireEvent.click(screen.getByRole('button', { name: 'Ask' }))

  expect(await screen.findByText('HONDA-A1 is due now, page 42.')).toBeVisible()
})
