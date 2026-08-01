import { useEffect, useState } from "react";

import type { DashboardResponse } from "../../api/generated/types.gen";

export function QualityDashboard({
  onLoad,
}: {
  onLoad: () => Promise<DashboardResponse>;
}) {
  const [dashboard, setDashboard] = useState<DashboardResponse>();
  const [error, setError] = useState("");

  useEffect(() => {
    onLoad()
      .then(setDashboard)
      .catch(() => setError("Quality dashboard unavailable"));
  }, [onLoad]);

  if (error)
    return (
      <p className="mt-6 rounded-xl border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
        {error}
      </p>
    );
  if (!dashboard)
    return (
      <p className="mt-6 rounded-xl border border-border bg-card p-4 text-sm text-muted-foreground">
        Loading quality dashboard
      </p>
    );

  return (
    <section
      aria-labelledby="dashboard-heading"
      className="mt-6 rounded-xl border border-border bg-card p-5 shadow-sm sm:p-6"
    >
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">
        Manager controls
      </p>
      <h3 id="dashboard-heading" className="mt-1 text-xl font-semibold">
        Quality and observability
      </h3>
      <p className="mt-1 text-sm text-muted-foreground">
        Evidence coverage, runtime discipline, and escalation outcomes.
      </p>
      <dl className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <div className="rounded-lg border border-border bg-muted/40 p-4">
          <dt className="text-xs uppercase tracking-wide text-muted-foreground">
            Citation rate
          </dt>
          <dd className="mt-2 text-2xl font-semibold text-primary">{`${Math.round(dashboard.citation_rate * 100)}%`}</dd>
        </div>
        <div className="rounded-lg border border-border bg-muted/40 p-4">
          <dt className="text-xs uppercase tracking-wide text-muted-foreground">
            Latency
          </dt>
          <dd className="mt-2 text-sm font-medium leading-6">{`p50 ${dashboard.p50_latency_ms} ms · p95 ${dashboard.p95_latency_ms} ms`}</dd>
        </div>
        <div className="rounded-lg border border-border bg-muted/40 p-4">
          <dt className="text-xs uppercase tracking-wide text-muted-foreground">
            Cost
          </dt>
          <dd className="mt-2 text-sm font-medium leading-6">{`${dashboard.total_cost_mxn} MXN across ${dashboard.span_count} spans`}</dd>
        </div>
        <div className="rounded-lg border border-border bg-muted/40 p-4">
          <dt className="text-xs uppercase tracking-wide text-muted-foreground">
            Evaluation
          </dt>
          <dd className="mt-2 text-sm font-medium leading-6">
            {`${Math.round(dashboard.evaluation_score * 100)}% · thresholds ${
              dashboard.evaluation_thresholds_met ? "met" : "not met"
            }`}
          </dd>
        </div>
        <div className="rounded-lg border border-border bg-muted/40 p-4">
          <dt className="text-xs uppercase tracking-wide text-muted-foreground">
            Escalation outcomes
          </dt>
          <dd className="mt-2 text-sm font-medium leading-6">
            {`approved ${dashboard.escalation_outcomes.approved ?? 0} · rejected ${
              dashboard.escalation_outcomes.rejected ?? 0
            } · escalated ${dashboard.escalation_outcomes.escalated ?? 0}`}
          </dd>
        </div>
      </dl>
    </section>
  );
}
