import type { ServiceQuestionResponse } from './generated/types.gen'
import { answerServiceQuestionServiceQuestionsPost } from './generated/sdk.gen'

export async function askServiceQuestion(token: string, question: string): Promise<ServiceQuestionResponse> {
  const response = await answerServiceQuestionServiceQuestionsPost({
    body: { question },
    headers: { authorization: `Bearer ${token}` },
  })
  if (!('data' in response) || !response.data) throw new Error('No supported semantic query answers this question')
  return response.data
}
