import { fireEvent, render, screen } from '@testing-library/react'
import { expect, test, vi } from 'vitest'

import { RecommendationConsole } from './RecommendationConsole'

function renderConsole(overrides: Partial<Parameters<typeof RecommendationConsole>[0]> = {}) {
  const props = {
    recommendation: undefined,
    onStartRun: vi.fn().mockResolvedValue({ id: 'run-1', events: ['started', 'awaiting_human_review'] }),
    onApproveRun: vi.fn().mockResolvedValue(undefined),
    onAsk: vi.fn().mockResolvedValue('HONDA-A1 is due now, page 42.'),
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

test('answers a contextual question from grounded evidence', async () => {
  renderConsole()
  fireEvent.click(screen.getByRole('tab', { name: 'Explain' }))

  fireEvent.change(screen.getByLabelText('Contextual question'), { target: { value: 'Why is this due?' } })
  fireEvent.click(screen.getByRole('button', { name: 'Ask' }))

  expect(await screen.findByText('HONDA-A1 is due now, page 42.')).toBeVisible()
})
