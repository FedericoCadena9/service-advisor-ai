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

test('answers a contextual question from grounded evidence', async () => {
  renderConsole()
  fireEvent.click(screen.getByRole('tab', { name: 'Explain' }))

  fireEvent.change(screen.getByLabelText('Contextual question'), { target: { value: 'Why is this due?' } })
  fireEvent.click(screen.getByRole('button', { name: 'Ask' }))

  expect(await screen.findByText('HONDA-A1 is due now, page 42.')).toBeVisible()
})
