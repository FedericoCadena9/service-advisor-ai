import type { VoiceNoteRequest, VoiceNoteResponse } from './generated/types.gen'
import {
  confirmVoiceNoteVoiceNotesNoteIdConfirmationPost,
  createVoiceNoteVoiceNotesPost,
} from './generated/sdk.gen'

export async function recordVoiceNote(token: string, note: VoiceNoteRequest): Promise<VoiceNoteResponse> {
  const response = await createVoiceNoteVoiceNotesPost({
    body: note,
    headers: { authorization: `Bearer ${token}` },
  })
  if (!('data' in response) || !response.data) throw new Error('Voice note could not be transcribed')
  return response.data
}

export async function confirmTranscript(token: string, noteId: string, transcript: string): Promise<VoiceNoteResponse> {
  const response = await confirmVoiceNoteVoiceNotesNoteIdConfirmationPost({
    body: { transcript },
    headers: { authorization: `Bearer ${token}` },
    path: { note_id: noteId },
  })
  if (!('data' in response) || !response.data) throw new Error('Transcript could not be confirmed')
  return response.data
}
