import { fireEvent, render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";

import { CIVIC_CITATIONS, CIVIC_VEHICLE_ID } from "../../test/fixtures";
import { RecommendationConsole } from "./RecommendationConsole";

function renderConsole(
  overrides: Partial<Parameters<typeof RecommendationConsole>[0]> = {},
) {
  const props = {
    recommendation: undefined,
    onStartRun: vi.fn().mockResolvedValue({
      id: "run-1",
      events: ["started", "awaiting_human_review"],
    }),
    onApproveRun: vi.fn().mockResolvedValue(undefined),
    onAsk: vi
      .fn()
      .mockResolvedValue(
        `HONDA-A1 is due now, page ${CIVIC_CITATIONS.citation_page}.`,
      ),
    onDraftQuote: vi.fn().mockResolvedValue({
      lines: [
        {
          service_code: "HONDA-A1",
          labor_mxn: "620.00",
          parts_mxn: "973.00",
          iva_mxn: "254.88",
          total_mxn: "1847.88",
          duration_minutes: 50,
          fitment: "confirmed",
          available: true,
          unavailable_reason: null,
        },
        {
          service_code: "HONDA-CABIN-FILTER",
          labor_mxn: "0.00",
          parts_mxn: "0.00",
          iva_mxn: "0.00",
          total_mxn: "0.00",
          duration_minutes: 0,
          fitment: "confirmed",
          available: false,
          unavailable_reason:
            "Part HON-CABIN-80292 is backordered until 2026-08-14",
        },
      ],
      subtotal_mxn: "1593.00",
      iva_mxn: "254.88",
      total_mxn: "1847.88",
      duration_minutes: 50,
      bay_slot_id: "bay-1-morning",
      warnings: [],
    }),
    onOpenReview: vi.fn().mockResolvedValue({
      id: "review-1",
      vehicle_id: CIVIC_VEHICLE_ID,
      approver_role: "advisor",
      approver_session_id: "session-1",
      facts: {
        service_codes: ["HONDA-A1"],
        subtotal_mxn: "1593.00",
        iva_mxn: "254.88",
        total_mxn: "1847.88",
        duration_minutes: 50,
        bay_slot_id: "bay-1-morning",
      },
      citations: { ...CIVIC_CITATIONS },
      status: "in_review",
      invalidation_reason: null,
      escalation_required: false,
      escalation_reasons: [],
      evidence_blocked: false,
      blocking_reason: null,
    }),
    onDecideReview: vi.fn().mockResolvedValue({
      id: "decision-1",
      review_id: "review-1",
      quote_id: "quote-1",
      decision: "approved",
      approver_role: "advisor",
      approver_session_id: "session-1",
      reason: null,
      facts: {
        service_codes: ["HONDA-A1"],
        subtotal_mxn: "1593.00",
        iva_mxn: "254.88",
        total_mxn: "1847.88",
        duration_minutes: 50,
        bay_slot_id: "bay-1-morning",
      },
      citations: { ...CIVIC_CITATIONS },
      escalation_reasons: [],
    }),
    onAskData: vi.fn().mockResolvedValue({
      answer: "Parts availability: HON-OIL-0W20 12 in_stock.",
      sql: "SELECT part_number, on_hand, restock_status FROM v_parts_availability ORDER BY part_number LIMIT 100",
      rows: [["HON-OIL-0W20", "12", "in_stock"]],
      retrieval: {
        views: ["v_parts_availability"],
        columns: ["part_number", "on_hand", "restock_status"],
        row_limit: 100,
        timeout_seconds: 2,
        principal: "semantic_reader",
      },
    }),
    timeline: {
      onReserve: vi.fn().mockResolvedValue({
        id: "appointment-1",
        quote_id: "quote-1",
        bay_slot_id: "bay-1-morning",
        starts_at: "2026-08-03T09:00:00",
        approver_role: "advisor",
        simulated: true,
      }),
      onPreview: vi.fn().mockResolvedValue({
        text: "Hola Demo Customer: su servicio incluye cambio de aceite y filtro. Total $1,847.88 MXN con IVA incluido. Cita 2026-08-03T09:00:00. ¿Confirma la cita?",
        segments: 1,
        priorities: ["cambio de aceite y filtro"],
      }),
      onSend: vi.fn().mockResolvedValue({
        id: "delivery-1",
        quote_id: "quote-1",
        text: "Hola Demo Customer: ¿Confirma la cita?",
        segments: 1,
        state: "queued",
        simulated: true,
        approver_role: "advisor",
        ...CIVIC_CITATIONS,
      }),
      onAdvance: vi.fn().mockResolvedValue({
        id: "delivery-1",
        quote_id: "quote-1",
        text: "Hola Demo Customer: ¿Confirma la cita?",
        segments: 1,
        state: "sent",
        simulated: true,
        approver_role: "advisor",
        ...CIVIC_CITATIONS,
      }),
    },
    ...overrides,
  };
  render(<RecommendationConsole {...props} />);
  return props;
}

test("replays persisted advisor run events after starting a run", async () => {
  renderConsole();
  fireEvent.click(screen.getByRole("tab", { name: "Advisor run" }));

  fireEvent.click(screen.getByRole("button", { name: "Start run" }));

  expect(
    await screen.findByText("Run run-1: started → awaiting_human_review"),
  ).toBeVisible();
});

test("keeps the human decision explicit and idempotent", async () => {
  const props = renderConsole();
  fireEvent.click(screen.getByRole("tab", { name: "Advisor run" }));

  fireEvent.click(screen.getByRole("button", { name: "Approve review" }));

  expect(await screen.findByText("Approved idempotently")).toBeVisible();
  expect(props.onApproveRun).toHaveBeenCalledTimes(1);
});

test("shows priced quote lines with an explicit unavailable reason", async () => {
  renderConsole();
  fireEvent.click(screen.getByRole("tab", { name: "Quote" }));

  fireEvent.click(screen.getByRole("button", { name: "Draft quote" }));

  const lines = await screen.findByRole("table", { name: "Quote draft lines" });
  expect(lines).toHaveTextContent("620.00");
  expect(lines).toHaveTextContent("254.88");
  expect(lines).toHaveTextContent(
    "Part HON-CABIN-80292 is backordered until 2026-08-14",
  );
  expect(
    screen.getByText(
      /Subtotal 1593.00 \+ IVA 254.88 = 1847.88 MXN · 50 min · bay-1-morning/,
    ),
  ).toBeVisible();
});

test("shows the approver, services, facts, and citations before approval", async () => {
  renderConsole();
  fireEvent.click(screen.getByRole("tab", { name: "Approval" }));

  fireEvent.click(screen.getByRole("button", { name: "Open approval" }));

  expect(await screen.findByText("advisor · session session-1")).toBeVisible();
  expect(screen.getByText("HONDA-A1")).toBeVisible();
  expect(
    screen.getByText(
      "1847.88 MXN including IVA 254.88 · 50 min · bay-1-morning",
    ),
  ).toBeVisible();
  expect(
    screen.getByText(
      `${CIVIC_CITATIONS.rule_version} · page ${CIVIC_CITATIONS.citation_page}, ${CIVIC_CITATIONS.citation_section}`,
    ),
  ).toBeVisible();
});

test("reports the saved quote after an approval command", async () => {
  renderConsole();
  fireEvent.click(screen.getByRole("tab", { name: "Approval" }));
  fireEvent.click(screen.getByRole("button", { name: "Open approval" }));

  fireEvent.click(await screen.findByRole("button", { name: "Approve quote" }));

  expect(await screen.findByRole("status")).toHaveTextContent(
    "Quote quote-1 approved by advisor",
  );
});

test("returns an invalidated quote to review", async () => {
  renderConsole({
    onDecideReview: vi.fn().mockRejectedValue(new Error("stale")),
  });
  fireEvent.click(screen.getByRole("tab", { name: "Approval" }));
  fireEvent.click(screen.getByRole("button", { name: "Open approval" }));

  fireEvent.click(await screen.findByRole("button", { name: "Approve quote" }));

  expect(
    await screen.findByText(
      "Quote returned to review: inputs changed or a Manager decision is required",
    ),
  ).toBeVisible();
});

test("routes an escalated quote to a Manager with a recorded reason", async () => {
  const escalated = vi.fn().mockResolvedValue({
    id: "review-2",
    vehicle_id: "honda-civic-2019-lx",
    approver_role: "manager",
    approver_session_id: "session-2",
    facts: {
      service_codes: ["HONDA-A1"],
      subtotal_mxn: "20000.00",
      iva_mxn: "3200.00",
      total_mxn: "23200.00",
      duration_minutes: 50,
      bay_slot_id: "bay-2-afternoon",
    },
    citations: { ...CIVIC_CITATIONS },
    status: "in_review",
    invalidation_reason: null,
    escalation_required: true,
    escalation_reasons: ["Quote total exceeds MXN 15,000.00"],
    evidence_blocked: false,
    blocking_reason: null,
  });
  renderConsole({ onOpenReview: escalated });
  fireEvent.click(screen.getByRole("tab", { name: "Approval" }));

  fireEvent.click(screen.getByRole("button", { name: "Open approval" }));

  expect(
    await screen.findByText(
      "Manager review required: Quote total exceeds MXN 15,000.00",
    ),
  ).toBeVisible();
  expect(screen.getByLabelText("Manager reason")).toBeVisible();
});

test("hides approval when evidence is insufficient for every role", async () => {
  const blocked = vi.fn().mockResolvedValue({
    id: "review-3",
    vehicle_id: "honda-civic-2019-lx",
    approver_role: "manager",
    approver_session_id: "session-3",
    facts: {
      service_codes: ["HONDA-A1"],
      subtotal_mxn: "0.00",
      iva_mxn: "0.00",
      total_mxn: "0.00",
      duration_minutes: 0,
      bay_slot_id: null,
    },
    citations: {
      rule_version: null,
      citation_page: null,
      citation_section: null,
    },
    status: "in_review",
    invalidation_reason: null,
    escalation_required: true,
    escalation_reasons: ["Reviewed evidence is missing or contradictory"],
    evidence_blocked: true,
    blocking_reason: "Reviewed evidence is missing or contradictory",
  });
  renderConsole({ onOpenReview: blocked });
  fireEvent.click(screen.getByRole("tab", { name: "Approval" }));

  fireEvent.click(screen.getByRole("button", { name: "Open approval" }));

  expect(
    await screen.findByText(
      "Not approvable by any role: Reviewed evidence is missing or contradictory",
    ),
  ).toBeVisible();
  expect(screen.queryByRole("button", { name: "Approve quote" })).toBeNull();
});

test("keeps the customer timeline behind an approved quote", async () => {
  renderConsole();
  fireEvent.click(screen.getByRole("tab", { name: "Timeline" }));

  expect(
    screen.getByText(
      "Approve a quote to reserve an appointment and prepare a message.",
    ),
  ).toBeVisible();
});

test("reserves a simulated slot and progresses the simulated delivery", async () => {
  renderConsole();
  fireEvent.click(screen.getByRole("tab", { name: "Approval" }));
  fireEvent.click(screen.getByRole("button", { name: "Open approval" }));
  fireEvent.click(await screen.findByRole("button", { name: "Approve quote" }));
  await screen.findByText("Quote quote-1 approved by advisor");
  fireEvent.click(screen.getByRole("tab", { name: "Timeline" }));

  fireEvent.click(screen.getByRole("button", { name: "Reserve appointment" }));
  expect(
    await screen.findByText(
      "Simulated reservation bay-1-morning at 2026-08-03T09:00:00",
    ),
  ).toBeVisible();

  fireEvent.click(screen.getByRole("button", { name: "Preview message" }));
  expect(await screen.findByText("1 segment(s) · 1 priorities")).toBeVisible();

  fireEvent.click(screen.getByRole("button", { name: "Enqueue message" }));
  expect(await screen.findByText("Simulated delivery: queued")).toBeVisible();
  expect(
    screen.getByText(
      `Approved by advisor · ${CIVIC_CITATIONS.rule_version} page ${CIVIC_CITATIONS.citation_page}`,
    ),
  ).toBeVisible();

  fireEvent.click(screen.getByRole("button", { name: "Advance timeline" }));
  expect(await screen.findByText("Simulated delivery: sent")).toBeVisible();
});

test("shows the accepted SQL and retrieval metadata for an ad hoc question", async () => {
  renderConsole();
  fireEvent.click(screen.getByRole("tab", { name: "Data" }));

  fireEvent.change(screen.getByLabelText("Ad hoc service question"), {
    target: { value: "Which parts are on backorder?" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Run read-only query" }));

  expect(await screen.findByLabelText("Accepted SQL")).toHaveTextContent(
    "LIMIT 100",
  );
  expect(
    screen.getByText(
      "Views v_parts_availability · columns part_number, on_hand, restock_status · limit 100 · timeout 2s · principal semantic_reader",
    ),
  ).toBeVisible();
});

test("reports when no supported read-only query answers the question", async () => {
  renderConsole({
    onAskData: vi.fn().mockRejectedValue(new Error("unsupported")),
  });
  fireEvent.click(screen.getByRole("tab", { name: "Data" }));

  fireEvent.click(screen.getByRole("button", { name: "Run read-only query" }));

  expect(
    await screen.findByText(
      "No supported read-only query answers this question",
    ),
  ).toBeVisible();
});

test("answers a contextual question from grounded evidence", async () => {
  renderConsole();
  fireEvent.click(screen.getByRole("tab", { name: "Explain" }));

  fireEvent.change(screen.getByLabelText("Contextual question"), {
    target: { value: "Why is this due?" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Ask" }));

  expect(
    await screen.findByText(
      `HONDA-A1 is due now, page ${CIVIC_CITATIONS.citation_page}.`,
    ),
  ).toBeVisible();
});
