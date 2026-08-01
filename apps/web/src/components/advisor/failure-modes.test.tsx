import { fireEvent, render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";

import { CHECKIN_GONE } from "../../api/failure";
import { CIVIC_CITATIONS } from "../../test/fixtures";
import { CustomerTimelinePanel } from "./CustomerTimelinePanel";
import { QuoteDraftPanel } from "./QuoteDraftPanel";
import { ServiceQuestionPanel } from "./ServiceQuestionPanel";

/** The API layer throws a plain Error for a dead network and for a refusal alike. */
const NETWORK_DOWN = new Error("Failed to fetch");
const REFUSED = Object.assign(new Error("rejected"), { status: 422 });
/** A restarted demo instance answers 409 or 404: the signed token outlives the state. */
const CHECKIN_LOST = Object.assign(new Error("conflict"), { status: 409 });

const APPOINTMENT = {
  id: "appointment-1",
  quote_id: "quote-1",
  bay_slot_id: "bay-1-morning",
  starts_at: "2026-08-03T09:00:00",
  approver_role: "advisor",
  simulated: true,
};
const PREVIEW = {
  text: "Hola Demo Customer: ¿Confirma la cita?",
  segments: 1,
  priorities: ["x"],
};

function timeline(overrides: Record<string, unknown> = {}) {
  return {
    onReserve: vi.fn().mockResolvedValue(APPOINTMENT),
    onPreview: vi.fn().mockResolvedValue(PREVIEW),
    onSend: vi.fn().mockResolvedValue({}),
    onAdvance: vi.fn().mockResolvedValue({}),
    ...overrides,
  };
}

test("a dead network while drafting tells the Advisor, instead of failing silently", async () => {
  render(<QuoteDraftPanel onDraft={vi.fn().mockRejectedValue(NETWORK_DOWN)} />);

  fireEvent.click(screen.getByRole("button", { name: "Draft quote" }));

  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Quote draft unavailable",
  );
});

/** What if the instance restarted mid-journey instead of holding the check-in behind the quote? */
test("a draft whose check-in is gone asks for the check-in again", async () => {
  render(
    <QuoteDraftPanel onDraft={vi.fn().mockRejectedValue(CHECKIN_LOST)} />,
  );

  fireEvent.click(screen.getByRole("button", { name: "Draft quote" }));

  expect(await screen.findByRole("alert")).toHaveTextContent(CHECKIN_GONE);
});

test("a dead network while asking a data question is reported", async () => {
  render(
    <ServiceQuestionPanel
      onAskData={vi.fn().mockRejectedValue(NETWORK_DOWN)}
    />,
  );

  fireEvent.click(screen.getByRole("button", { name: "Run read-only query" }));

  expect(
    await screen.findByText(
      "No supported read-only query answers this question",
    ),
  ).toBeVisible();
});

/** What if the session outlived the records the query reads, instead of the query being unsupported? */
test("a data question whose state is gone asks for the check-in again", async () => {
  render(
    <ServiceQuestionPanel
      onAskData={vi.fn().mockRejectedValue(CHECKIN_LOST)}
    />,
  );

  fireEvent.click(screen.getByRole("button", { name: "Run read-only query" }));

  expect(await screen.findByText(CHECKIN_GONE)).toBeVisible();
});

test("a failed reservation is reported rather than leaving the panel blank", async () => {
  render(
    <CustomerTimelinePanel
      quoteId="quote-1"
      {...timeline({ onReserve: vi.fn().mockRejectedValue(NETWORK_DOWN) })}
    />,
  );

  fireEvent.click(screen.getByRole("button", { name: "Reserve appointment" }));

  expect(
    await screen.findByText("The appointment could not be reserved"),
  ).toBeVisible();
});

/** What if the quote behind the appointment vanished, instead of the slot being taken? */
test("a reservation whose quote is gone asks for the check-in again", async () => {
  render(
    <CustomerTimelinePanel
      quoteId="quote-1"
      {...timeline({ onReserve: vi.fn().mockRejectedValue(CHECKIN_LOST) })}
    />,
  );

  fireEvent.click(screen.getByRole("button", { name: "Reserve appointment" }));

  expect(await screen.findByText(CHECKIN_GONE)).toBeVisible();
});

test("a network failure and a refused message read differently", async () => {
  const offline = timeline({ onSend: vi.fn().mockRejectedValue(NETWORK_DOWN) });
  const { unmount } = render(
    <CustomerTimelinePanel quoteId="quote-1" {...offline} />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Preview message" }));
  fireEvent.click(
    await screen.findByRole("button", { name: "Enqueue message" }),
  );
  expect(
    await screen.findByText("The message could not be sent right now"),
  ).toBeVisible();
  unmount();

  const refused = timeline({ onSend: vi.fn().mockRejectedValue(REFUSED) });
  render(<CustomerTimelinePanel quoteId="quote-1" {...refused} />);
  fireEvent.click(screen.getByRole("button", { name: "Preview message" }));
  fireEvent.click(
    await screen.findByRole("button", { name: "Enqueue message" }),
  );

  expect(
    await screen.findByText(
      "The message was rejected because it is not supported by the approved quote",
    ),
  ).toBeVisible();
});

test("a failed preview does not offer a send button built on nothing", async () => {
  render(
    <CustomerTimelinePanel
      quoteId="quote-1"
      {...timeline({ onPreview: vi.fn().mockRejectedValue(NETWORK_DOWN) })}
    />,
  );

  fireEvent.click(screen.getByRole("button", { name: "Preview message" }));

  expect(
    await screen.findByText("The message preview is unavailable"),
  ).toBeVisible();
  expect(screen.queryByRole("button", { name: "Enqueue message" })).toBeNull();
});

test("a failed advance keeps the delivery on screen", async () => {
  render(
    <CustomerTimelinePanel
      quoteId="quote-1"
      {...timeline({
        onSend: vi.fn().mockResolvedValue({
          id: "delivery-1",
          state: "queued",
          approver_role: "advisor",
          ...CIVIC_CITATIONS,
        }),
        onAdvance: vi.fn().mockRejectedValue(NETWORK_DOWN),
      })}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Preview message" }));
  fireEvent.click(
    await screen.findByRole("button", { name: "Enqueue message" }),
  );
  await screen.findByText("Simulated delivery: queued");

  fireEvent.click(screen.getByRole("button", { name: "Advance timeline" }));

  expect(
    await screen.findByText("The timeline could not be advanced"),
  ).toBeVisible();
  expect(screen.getByText("Simulated delivery: queued")).toBeVisible();
});

/** What if the check-in behind the review was dropped by a restart, instead of the review being refused? */
test("an approval whose check-in is gone asks for the check-in again", async () => {
  const { QuoteApprovalPanel } = await import("./QuoteApprovalPanel");
  render(
    <QuoteApprovalPanel
      onOpenReview={vi.fn().mockRejectedValue(CHECKIN_LOST)}
      onDecide={vi.fn()}
      onApproved={vi.fn()}
    />,
  );

  fireEvent.click(screen.getByRole("button", { name: "Open approval" }));

  expect(await screen.findByText(CHECKIN_GONE)).toBeVisible();
});

/** What if the API is merely unreachable — is the Advisor still told to redo the check-in? */
test("an unreachable approval does not send the Advisor back to the check-in", async () => {
  const { QuoteApprovalPanel } = await import("./QuoteApprovalPanel");
  render(
    <QuoteApprovalPanel
      onOpenReview={vi.fn().mockRejectedValue(NETWORK_DOWN)}
      onDecide={vi.fn()}
      onApproved={vi.fn()}
    />,
  );

  fireEvent.click(screen.getByRole("button", { name: "Open approval" }));

  expect(
    await screen.findByText("The quote could not be opened for approval"),
  ).toBeVisible();
});
