import { render, screen } from '@testing-library/react'
import { expect, test, vi } from 'vitest'

import { QualityDashboard } from './QualityDashboard'

const DASHBOARD = {
  trace_count: 3,
  span_count: 12,
  spans_by_kind: { http: 3, workflow: 3, tool: 1, retrieval: 2, provider: 2, command: 1 },
  citation_rate: 0.5,
  p50_latency_ms: 12,
  p95_latency_ms: 42,
  total_cost_mxn: '0.0250',
  escalation_outcomes: { approved: 2, rejected: 1, escalated: 1 },
  evaluation_thresholds_met: true,
  evaluation_score: 1,
}

test('shows quality metrics, evaluation status, and escalation outcomes', async () => {
  render(<QualityDashboard onLoad={vi.fn().mockResolvedValue(DASHBOARD)} />)

  expect(await screen.findByText('50%')).toBeVisible()
  expect(screen.getByText('p50 12 ms · p95 42 ms')).toBeVisible()
  expect(screen.getByText('0.0250 MXN across 12 spans')).toBeVisible()
  expect(screen.getByText('100% · thresholds met')).toBeVisible()
  expect(screen.getByText('approved 2 · rejected 1 · escalated 1')).toBeVisible()
})

test('reports when the dashboard cannot be read', async () => {
  render(<QualityDashboard onLoad={vi.fn().mockRejectedValue(new Error('forbidden'))} />)

  expect(await screen.findByText('Quality dashboard unavailable')).toBeVisible()
})
