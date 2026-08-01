import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { failureMessage } from "../../api/failure";
import type {
  VoiceNoteRequest,
  VoiceNoteResponse,
} from "../../api/generated/types.gen";

export const MAX_DURATION_SECONDS = 90;

export function VoiceCheckinPanel({
  onRecord,
  onConfirm,
  onConfirmed,
}: {
  onRecord: (note: VoiceNoteRequest) => Promise<VoiceNoteResponse>;
  onConfirm: (noteId: string, transcript: string) => Promise<VoiceNoteResponse>;
  onConfirmed: (noteId: string) => void;
}) {
  const [language, setLanguage] = useState<"es" | "en">("es");
  const [duration, setDuration] = useState("42");
  const [note, setNote] = useState<VoiceNoteResponse>();
  const [transcript, setTranscript] = useState("");
  const [error, setError] = useState("");

  async function record() {
    if (Number(duration) > MAX_DURATION_SECONDS) {
      setError(`A voice note may not exceed ${MAX_DURATION_SECONDS} seconds`);
      return;
    }
    try {
      const recorded = await onRecord({
        language,
        duration_seconds: Number(duration),
        consent: true,
        provider_available: true,
      });
      setNote(recorded);
      setTranscript(recorded.transcript);
      setError("");
    } catch (failure) {
      setError(
        failureMessage(
          failure,
          "Transcription is unavailable; enter the concern manually",
        ),
      );
    }
  }

  async function confirm(noteId: string) {
    try {
      const confirmed = await onConfirm(noteId, transcript);
      setNote(confirmed);
      onConfirmed(confirmed.id);
      setError("");
    } catch (failure) {
      setError(
        failureMessage(failure, "The transcript could not be confirmed"),
      );
    }
  }

  return (
    <fieldset className="space-y-3">
      <legend className="text-base font-semibold">Voice check-in</legend>
      <p className="text-sm leading-5 text-muted-foreground">
        Capture a short customer concern in the language they used. Audio is
        deleted after confirmation.
      </p>
      <label className="block text-sm font-medium" htmlFor="voice-language">
        Transcription language
      </label>
      <select
        id="voice-language"
        value={language}
        onChange={(event) => setLanguage(event.target.value as "es" | "en")}
      >
        <option value="es">Spanish</option>
        <option value="en">English</option>
      </select>
      <label className="block text-sm font-medium" htmlFor="voice-duration">
        Recording seconds
      </label>
      <input
        id="voice-duration"
        type="number"
        max={MAX_DURATION_SECONDS}
        value={duration}
        onChange={(event) => setDuration(event.target.value)}
      />
      <Button type="button" onClick={() => void record()}>
        Transcribe voice note
      </Button>
      {note?.state === "failed" && (
        <p className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
          {note.failure_reason}
        </p>
      )}
      {note && note.state !== "failed" && (
        <div className="space-y-3 rounded-lg border border-border bg-muted/40 p-3">
          <ul
            aria-label="Transcript timestamps"
            className="space-y-1 text-xs text-muted-foreground"
          >
            {note.segments.map((segment) => (
              <li
                key={segment.starts_at_seconds}
              >{`${segment.starts_at_seconds}s — ${segment.text}`}</li>
            ))}
          </ul>
          <label
            className="block text-sm font-medium"
            htmlFor="voice-transcript"
          >
            Editable transcript
          </label>
          <Textarea
            id="voice-transcript"
            value={transcript}
            onChange={(event) => setTranscript(event.target.value)}
          />
          <Button
            type="button"
            onClick={() => void confirm(note.id)}
          >
            Confirm transcript
          </Button>
        </div>
      )}
      {note?.state === "confirmed" && (
        <p className="rounded-lg border border-emerald-400/35 bg-emerald-50 p-3 text-sm text-emerald-800">
          Transcript confirmed and audio deleted
        </p>
      )}
      {error && (
        <p className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </p>
      )}
    </fieldset>
  );
}
