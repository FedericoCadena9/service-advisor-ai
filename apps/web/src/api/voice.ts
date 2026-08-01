import type { VoiceNoteRequest, VoiceNoteResponse } from './generated/types.gen'
import {
  confirmVoiceNoteVoiceNotesNoteIdConfirmationPost,
  createVoiceNoteVoiceNotesPost,
} from './generated/sdk.gen'
import { requestFailed } from './failure'

export async function recordVoiceNote(token: string, note: VoiceNoteRequest): Promise<VoiceNoteResponse> {
  const response = await createVoiceNoteVoiceNotesPost({
    body: note,
    headers: { authorization: `Bearer ${token}` },
  })
  if (!('data' in response) || !response.data) throw requestFailed('Voice note could not be transcribed', response)
  return response.data
}

export async function confirmTranscript(token: string, noteId: string, transcript: string): Promise<VoiceNoteResponse> {
  const response = await confirmVoiceNoteVoiceNotesNoteIdConfirmationPost({
    body: { transcript },
    headers: { authorization: `Bearer ${token}` },
    path: { note_id: noteId },
  })
  if (!('data' in response) || !response.data) throw requestFailed('Transcript could not be confirmed', response)
  return response.data
}
