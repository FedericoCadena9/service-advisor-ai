import { fireEvent, render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";

import { CHECKIN_GONE } from "../../api/failure";
import { VoiceCheckinPanel } from "./VoiceCheckinPanel";

const TRANSCRIBED = {
  id: "note-1",
  language: "es",
  duration_seconds: 42,
  state: "transcribed",
  segments: [
    { starts_at_seconds: 0, text: "El cliente reporta un ruido al frenar" },
    {
      starts_at_seconds: 6.5,
      text: "Pide revision antes del viaje del viernes",
    },
  ],
  transcript: "El cliente reporta un ruido al frenar",
  audio_retained: true,
  audio_retention_expires_at: null,
  failure_reason: null,
  manual_entry_available: true,
};

function renderPanel(overrides: Record<string, unknown> = {}) {
  const props = {
    onRecord: vi.fn().mockResolvedValue(TRANSCRIBED),
    onConfirm: vi.fn().mockResolvedValue({
      ...TRANSCRIBED,
      state: "confirmed",
      transcript: "Rechinido al frenar",
      audio_retained: false,
    }),
    onConfirmed: vi.fn(),
    ...overrides,
  };
  render(
    <VoiceCheckinPanel
      {...(props as unknown as Parameters<typeof VoiceCheckinPanel>[0])}
    />,
  );
  return props;
}

test("presents language, timestamps, and an editable transcript", async () => {
  renderPanel();

  fireEvent.click(
    screen.getByRole("button", { name: "Transcribe voice note" }),
  );

  expect(await screen.findByLabelText("Editable transcript")).toBeVisible();
  expect(screen.getByLabelText("Transcript timestamps")).toHaveTextContent(
    "6.5s — Pide revision antes del viaje del viernes",
  );
  expect(screen.getByLabelText("Transcription language")).toHaveValue("es");
});

test("refuses a recording longer than ninety seconds", async () => {
  const props = renderPanel();
  fireEvent.change(screen.getByLabelText("Recording seconds"), {
    target: { value: "120" },
  });

  fireEvent.click(
    screen.getByRole("button", { name: "Transcribe voice note" }),
  );

  expect(
    await screen.findByText("A voice note may not exceed 90 seconds"),
  ).toBeVisible();
  expect(props.onRecord).not.toHaveBeenCalled();
});

test("reports the confirmed transcript and deleted audio", async () => {
  const props = renderPanel();
  fireEvent.click(
    screen.getByRole("button", { name: "Transcribe voice note" }),
  );
  fireEvent.change(await screen.findByLabelText("Editable transcript"), {
    target: { value: "Rechinido al frenar" },
  });

  fireEvent.click(screen.getByRole("button", { name: "Confirm transcript" }));

  expect(
    await screen.findByText("Transcript confirmed and audio deleted"),
  ).toBeVisible();
  expect(props.onConfirm).toHaveBeenCalledWith("note-1", "Rechinido al frenar");
  expect(props.onConfirmed).toHaveBeenCalledWith("note-1");
});

/** What if the note was dropped between recording and confirming, instead of surviving? */
test("a confirmation whose voice note is gone asks for the check-in again", async () => {
  const props = renderPanel({
    onConfirm: vi
      .fn()
      .mockRejectedValue(Object.assign(new Error("gone"), { status: 404 })),
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Transcribe voice note" }),
  );
  await screen.findByLabelText("Editable transcript");

  fireEvent.click(screen.getByRole("button", { name: "Confirm transcript" }));

  expect(await screen.findByText(CHECKIN_GONE)).toBeVisible();
  expect(props.onConfirmed).not.toHaveBeenCalled();
});

test("keeps manual entry available after a provider failure", async () => {
  renderPanel({
    onRecord: vi.fn().mockResolvedValue({
      ...TRANSCRIBED,
      state: "failed",
      segments: [],
      transcript: "",
      failure_reason:
        "Transcription provider is unavailable; enter the concern manually",
    }),
  });

  fireEvent.click(
    screen.getByRole("button", { name: "Transcribe voice note" }),
  );

  expect(
    await screen.findByText(
      "Transcription provider is unavailable; enter the concern manually",
    ),
  ).toBeVisible();
  expect(screen.queryByLabelText("Editable transcript")).toBeNull();
});
