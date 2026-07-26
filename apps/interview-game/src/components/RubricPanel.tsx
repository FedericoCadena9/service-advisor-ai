import { useState } from 'react'

import {
  RUBRIC_DIMENSIONS,
  type EvaluationResult,
  type Language,
} from '../domain/game'

type RubricPanelProps = {
  language: Language
  onSubmit: (evaluation: EvaluationResult) => void
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function parseEvaluation(value: string): EvaluationResult | null {
  try {
    const parsed: unknown = JSON.parse(value)
    if (!isRecord(parsed) || !isRecord(parsed.scores)) return null
    const scores = parsed.scores
    const validScores = RUBRIC_DIMENSIONS.every((dimension) => {
      const score = scores[dimension]
      return typeof score === 'number' && Number.isFinite(score) && score >= 0 && score <= 100
    })
    if (!validScores) return null
    if (!Number.isInteger(parsed.followUpCount) || Number(parsed.followUpCount) < 0) return null
    if (typeof parsed.hintUsed !== 'boolean') return null
    if (typeof parsed.unassistedTransfer !== 'boolean') return null
    if (typeof parsed.evidenceSummary !== 'string' || !parsed.evidenceSummary.trim()) return null
    if (parsed.attemptClosed !== true) return null
    return parsed as EvaluationResult
  } catch {
    return null
  }
}

export function RubricPanel({ language, onSubmit }: RubricPanelProps) {
  const [payload, setPayload] = useState('')
  const [error, setError] = useState('')

  function submit() {
    const evaluation = parseEvaluation(payload)
    if (!evaluation) {
      setError(
        language === 'es'
          ? 'El resultado no tiene el formato de evaluación esperado. Pide a Codex que lo regenere.'
          : 'The result does not match the evaluation format. Ask Codex to regenerate it.',
      )
      return
    }
    setError('')
    onSubmit(evaluation)
  }

  return (
    <section className="rubric" aria-labelledby="rubric-title">
      <div className="rubric-heading">
        <div>
          <span className="eyebrow">CODEX / VERDICT</span>
          <h3 id="rubric-title">
            {language === 'es' ? 'Importa la evaluación cerrada' : 'Import the closed evaluation'}
          </h3>
        </div>
      </div>
      <p className="rubric-rule">
        {language === 'es'
          ? 'Primero responde en el chat y sobrevive dos follow-ups. Después pega aquí únicamente el JSON que Codex te entregue.'
          : 'Answer in chat and survive two follow-ups first. Then paste only the JSON that Codex returns.'}
      </p>
      <label className="evaluation-import">
        <span>{language === 'es' ? 'Resultado JSON de Codex' : 'Codex evaluation JSON'}</span>
        <textarea
          rows={9}
          value={payload}
          onChange={(event) => setPayload(event.target.value)}
          placeholder='{ "scores": { … }, "followUpCount": 2, … }'
        />
      </label>
      {error && <p className="import-error" role="alert">{error}</p>}
      <button className="primary-action" type="button" onClick={submit}>
        {language === 'es' ? 'Registrar evaluación' : 'Record evaluation'}
      </button>
    </section>
  )
}
