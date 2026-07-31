import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import type { ServiceQuestionResponse } from '../../api/generated/types.gen'

export function ServiceQuestionPanel({ onAskData }: { onAskData: (question: string) => Promise<ServiceQuestionResponse> }) {
  const [question, setQuestion] = useState('')
  const [result, setResult] = useState<ServiceQuestionResponse>()
  const [error, setError] = useState('')

  async function ask() {
    try {
      setResult(await onAskData(question))
      setError('')
    } catch {
      setResult(undefined)
      setError('No supported read-only query answers this question')
    }
  }

  return (
    <div>
      <label htmlFor="service-question">Ad hoc service question</label>
      <Textarea
        id="service-question"
        value={question}
        onChange={(event) => setQuestion(event.target.value)}
      />
      <Button className="mt-2" onClick={() => void ask()}>
        Run read-only query
      </Button>
      {result && (
        <div className="mt-3">
          <p>{result.answer}</p>
          <pre aria-label="Accepted SQL">{result.sql}</pre>
          <p>{`Views ${result.retrieval.views.join(', ')} · columns ${result.retrieval.columns.join(', ')} · limit ${result.retrieval.row_limit} · timeout ${result.retrieval.timeout_seconds}s · principal ${result.retrieval.principal}`}</p>
        </div>
      )}
      {error && <p>{error}</p>}
    </div>
  )
}
