import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";

import App from "./App";
import { CHECKIN_GONE } from "./api/failure";
import { openQuoteReview } from "./api/quote-reviews";
import { saveCheckin } from "./api/checkins";

/**
 * Every panel is covered on its own, and the seam between them is what broke: a step read
 * state an earlier step wrote, and a restart in between was reported as nothing at all.
 * This walks the journey the Service Advisor actually walks, against a mocked API.
 *
 * The modules are mocked by naming each export. A `Proxy` factory does not intercept named
 * ESM imports, and letting the real clients through puts the suite on the network. The
 * fixtures come through `vi.hoisted` for the same reason: `vi.mock` runs above the imports.
 */
const {
  CIVIC_CITATIONS,
  CIVIC_VEHICLE_ID,
  VEHICLE,
  RECOMMENDATION,
  FACTS,
  REVIEW,
} = await vi.hoisted(async () => {
  const { CIVIC_CITATIONS, CIVIC_VEHICLE_ID } = await import("./test/fixtures");
  const VEHICLE = {
    id: CIVIC_VEHICLE_ID,
    vehicle_label: "2019 Honda Civic LX",
    customer_label: "Demo Customer",
    plate: "ABC-123",
  };
  const RECOMMENDATION = {
    state: "Due now by Maintenance Minder",
    service_code: "HONDA-A1",
    due_reason: "The Maintenance Minder decides when this service is due.",
    ...CIVIC_CITATIONS,
  };
  const FACTS = {
    service_codes: ["HONDA-A1"],
    subtotal_mxn: "1593.00",
    iva_mxn: "254.88",
    total_mxn: "1847.88",
    duration_minutes: 50,
    bay_slot_id: "bay-1-morning",
  };
  const REVIEW = {
    id: "review-1",
    vehicle_id: CIVIC_VEHICLE_ID,
    approver_role: "advisor",
    approver_session_id: "demo-session",
    facts: FACTS,
    citations: { ...CIVIC_CITATIONS },
    status: "in_review",
    invalidation_reason: null,
    escalation_required: false,
    escalation_reasons: [],
    evidence_blocked: false,
    blocking_reason: null,
  };
  return {
    CIVIC_CITATIONS,
    CIVIC_VEHICLE_ID,
    VEHICLE,
    RECOMMENDATION,
    FACTS,
    REVIEW,
  };
});

vi.mock("./api/health", () => ({
  fetchHealth: vi.fn().mockResolvedValue({ status: "healthy" }),
}));
vi.mock("./api/demo-session", () => ({
  enterDemoWorkspace: vi.fn().mockResolvedValue({
    token: "signed-demo-token",
    workspace: {
      shop_id: "demo-shop",
      demo_session_id: "demo-session",
      role: "advisor",
      generation: 0,
    },
  }),
}));
vi.mock("./api/vehicles", () => ({
  searchDemoVehicles: vi.fn().mockResolvedValue([VEHICLE]),
}));
vi.mock("./api/checkins", () => ({
  saveCheckin: vi.fn().mockResolvedValue({ vehicle_id: CIVIC_VEHICLE_ID }),
}));
vi.mock("./api/recommendations", () => ({
  fetchRecommendation: vi.fn().mockResolvedValue(RECOMMENDATION),
}));
vi.mock("./api/quotes", () => ({
  draftQuote: vi.fn().mockResolvedValue({
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
    ],
    ...FACTS,
    warnings: [],
  }),
}));
vi.mock("./api/quote-reviews", () => ({
  openQuoteReview: vi.fn().mockResolvedValue(REVIEW),
  decideQuoteReview: vi.fn().mockResolvedValue({
    id: "decision-1",
    review_id: "review-1",
    quote_id: "quote-1",
    decision: "approved",
    approver_role: "advisor",
    approver_session_id: "demo-session",
    reason: null,
    facts: FACTS,
    citations: { ...CIVIC_CITATIONS },
    escalation_reasons: [],
  }),
}));
vi.mock("./api/messaging", () => ({
  reserveAppointment: vi.fn().mockResolvedValue({
    id: "appointment-1",
    quote_id: "quote-1",
    bay_slot_id: "bay-1-morning",
    starts_at: "2026-08-03T09:00:00",
    approver_role: "advisor",
    simulated: true,
  }),
  previewSms: vi.fn().mockResolvedValue({
    text: "Hola Demo Customer: ¿Confirma la cita?",
    segments: 1,
    priorities: ["cambio de aceite y filtro"],
  }),
  sendSms: vi.fn().mockResolvedValue({
    id: "delivery-1",
    quote_id: "quote-1",
    text: "Hola Demo Customer: ¿Confirma la cita?",
    segments: 1,
    state: "queued",
    simulated: true,
    approver_role: "advisor",
    ...CIVIC_CITATIONS,
  }),
  advanceMessage: vi.fn().mockResolvedValue({
    id: "delivery-1",
    quote_id: "quote-1",
    text: "Hola Demo Customer: ¿Confirma la cita?",
    segments: 1,
    state: "sent",
    simulated: true,
    approver_role: "advisor",
    ...CIVIC_CITATIONS,
  }),
}));
vi.mock("./api/chat", () => ({
  askContextualChat: vi.fn().mockResolvedValue({ text: "Grounded answer" }),
}));
vi.mock("./api/service-questions", () => ({
  askServiceQuestion: vi.fn().mockResolvedValue({
    answer: "Parts availability",
    sql: "SELECT part_number FROM v_parts_availability LIMIT 100",
    rows: [],
    retrieval: {
      views: ["v_parts_availability"],
      columns: ["part_number"],
      row_limit: 100,
      timeout_seconds: 2,
      principal: "semantic_reader",
    },
  }),
}));
vi.mock("./api/advisor-run", () => ({
  startAdvisorRun: vi
    .fn()
    .mockResolvedValue({ id: "run-1", trace_id: "trace-1" }),
  fetchAdvisorRunEvents: vi.fn().mockResolvedValue(["started"]),
  decideAdvisorRun: vi.fn().mockResolvedValue(undefined),
}));
vi.mock("./api/dashboard", () => ({
  fetchQualityDashboard: vi.fn(),
}));
vi.mock("./api/voice", () => ({
  recordVoiceNote: vi.fn(),
  confirmTranscript: vi.fn(),
}));

/** Recorded calls carry over between tests; the resolved values are left in place. */
beforeEach(() => {
  vi.clearAllMocks();
});

async function enterWorkspace() {
  render(<App />);
  fireEvent.click(
    await screen.findByRole("button", { name: "Enter as Advisor" }),
  );
}

async function findVehicle() {
  fireEvent.change(
    await screen.findByRole("searchbox", { name: "Search demo vehicle" }),
    { target: { value: "ABC-123" } },
  );
  fireEvent.submit(screen.getByRole("search"));
  fireEvent.click(
    await screen.findByRole("button", { name: /2019 Honda Civic LX/ }),
  );
}

function confirmCheckin() {
  fireEvent.change(screen.getByLabelText("Current mileage (km)"), {
    target: { value: "48000" },
  });
  fireEvent.submit(screen.getByRole("form", { name: "Check-in details" }));
}

function openTab(name: string) {
  fireEvent.click(screen.getByRole("tab", { name }));
}

test("an Advisor walks a vehicle from search to a simulated customer message", async () => {
  await enterWorkspace();
  await findVehicle();

  confirmCheckin();
  expect(await screen.findByText("Check-in confirmed")).toBeVisible();
  expect(
    await screen.findByText(
      `${CIVIC_CITATIONS.rule_version} · page ${CIVIC_CITATIONS.citation_page}, ${CIVIC_CITATIONS.citation_section}.`,
    ),
  ).toBeVisible();

  openTab("Quote");
  fireEvent.click(screen.getByRole("button", { name: "Draft quote" }));
  expect(
    await screen.findByRole("table", { name: "Quote draft lines" }),
  ).toHaveTextContent("1847.88");

  openTab("Approval");
  fireEvent.click(screen.getByRole("button", { name: "Open approval" }));
  fireEvent.click(await screen.findByRole("button", { name: "Approve quote" }));
  expect(
    await screen.findByText("Quote quote-1 approved by advisor"),
  ).toBeVisible();

  openTab("Timeline");
  fireEvent.click(screen.getByRole("button", { name: "Reserve appointment" }));
  expect(
    await screen.findByText(
      "Simulated reservation bay-1-morning at 2026-08-03T09:00:00",
    ),
  ).toBeVisible();

  fireEvent.click(screen.getByRole("button", { name: "Preview message" }));
  fireEvent.click(
    await screen.findByRole("button", { name: "Enqueue message" }),
  );
  expect(await screen.findByText("Simulated delivery: queued")).toBeVisible();
});

/**
 * What if the instance restarted between the check-in and the approval, instead of holding
 * the state the whole way through? This is the failure the browser E2E hit: the token stays
 * valid because it is signed, so the journey keeps going until a step reads what is gone.
 */
test("an approval refused mid-journey is recoverable by confirming the check-in again", async () => {
  vi.mocked(openQuoteReview).mockRejectedValueOnce(
    Object.assign(new Error("conflict"), { status: 409 }),
  );
  await enterWorkspace();
  await findVehicle();
  confirmCheckin();
  await screen.findByText("Check-in confirmed");

  openTab("Approval");
  fireEvent.click(screen.getByRole("button", { name: "Open approval" }));

  expect(await screen.findByText(CHECKIN_GONE)).toBeVisible();
  expect(screen.queryByRole("button", { name: "Approve quote" })).toBeNull();

  confirmCheckin();
  fireEvent.click(screen.getByRole("button", { name: "Open approval" }));

  fireEvent.click(await screen.findByRole("button", { name: "Approve quote" }));
  expect(
    await screen.findByText("Quote quote-1 approved by advisor"),
  ).toBeVisible();
  expect(vi.mocked(saveCheckin)).toHaveBeenCalledTimes(2);
});
