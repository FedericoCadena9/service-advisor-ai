import { useEffect, useState } from 'react'

import type { QualityDashboard as QualityDashboardData } from '../../api/dashboard'

export function QualityDashboard({ onLoad }: { onLoad: () => Promise<QualityDashboardData> }) {
  const [dashboard, setDashboard] = useState<QualityDashboardData>()
  const [error, setError] = useState('')

  useEffect(() => {
    onLoad()
      .then(setDashboard)
      .catch(() => setError('Quality dashboard unavailable'))
  }, [onLoad])

  if (error) return <p>{error}</p>
  if (!dashboard) return <p>Loading quality dashboard</p>

  return (
    <section aria-labelledby="dashboard-heading">
      <h3 id="dashboard-heading">Quality and observability</h3>
      <dl>
        <dt>Citation rate</dt>
        <dd>{`${Math.round(dashboard.citation_rate * 100)}%`}</dd>
        <dt>Latency</dt>
        <dd>{`p50 ${dashboard.p50_latency_ms} ms · p95 ${dashboard.p95_latency_ms} ms`}</dd>
        <dt>Cost</dt>
        <dd>{`${dashboard.total_cost_mxn} MXN across ${dashboard.span_count} spans`}</dd>
        <dt>Evaluation</dt>
        <dd>
          {`${Math.round(dashboard.evaluation_score * 100)}% · thresholds ${
            dashboard.evaluation_thresholds_met ? 'met' : 'not met'
          }`}
        </dd>
        <dt>Escalation outcomes</dt>
        <dd>
          {`approved ${dashboard.escalation_outcomes.approved ?? 0} · rejected ${
            dashboard.escalation_outcomes.rejected ?? 0
          } · escalated ${dashboard.escalation_outcomes.escalated ?? 0}`}
        </dd>
      </dl>
    </section>
  )
}
