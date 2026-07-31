import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import type { VoiceNoteRequest, VoiceNoteResponse } from '../../api/generated/types.gen'

export const MAX_DURATION_SECONDS = 90

export function VoiceCheckinPanel({
  onRecord,
  onConfirm,
  onConfirmed,
}: {
  onRecord: (note: VoiceNoteRequest) => Promise<VoiceNoteResponse>
  onConfirm: (noteId: string, transcript: string) => Promise<VoiceNoteResponse>
  onConfirmed: (noteId: string) => void
}) {
  const [language, setLanguage] = useState<'es' | 'en'>('es')
  const [duration, setDuration] = useState('42')
  const [note, setNote] = useState<VoiceNoteResponse>()
  const [transcript, setTranscript] = useState('')
  const [error, setError] = useState('')

  async function record() {
    if (Number(duration) > MAX_DURATION_SECONDS) {
      setError(`A voice note may not exceed ${MAX_DURATION_SECONDS} seconds`)
      return
    }
    try {
      const recorded = await onRecord({
        language,
        duration_seconds: Number(duration),
        consent: true,
        provider_available: true,
      })
      setNote(recorded)
      setTranscript(recorded.transcript)
      setError('')
    } catch {
      setError('Transcription is unavailable; enter the concern manually')
    }
  }

  return (
    <fieldset>
      <legend>Voice check-in</legend>
      <label htmlFor="voice-language">Transcription language</label>
      <select
        id="voice-language"
        value={language}
        onChange={(event) => setLanguage(event.target.value as 'es' | 'en')}
      >
        <option value="es">Spanish</option>
        <option value="en">English</option>
      </select>
      <label htmlFor="voice-duration">Recording seconds</label>
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
      {note?.state === 'failed' && <p>{note.failure_reason}</p>}
      {note && note.state !== 'failed' && (
        <div>
          <ul aria-label="Transcript timestamps">
            {note.segments.map((segment) => (
              <li key={segment.starts_at_seconds}>{`${segment.starts_at_seconds}s — ${segment.text}`}</li>
            ))}
          </ul>
          <label htmlFor="voice-transcript">Editable transcript</label>
          <Textarea
            id="voice-transcript"
            value={transcript}
            onChange={(event) => setTranscript(event.target.value)}
          />
          <Button
            type="button"
            onClick={() =>
              void onConfirm(note.id, transcript).then((confirmed) => {
                setNote(confirmed)
                onConfirmed(confirmed.id)
              })
            }
          >
            Confirm transcript
          </Button>
        </div>
      )}
      {note?.state === 'confirmed' && <p>Transcript confirmed and audio deleted</p>}
      {error && <p>{error}</p>}
    </fieldset>
  )
}
