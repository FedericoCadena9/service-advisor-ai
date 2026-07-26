import { useEffect, useMemo, useState } from 'react'

import type { LocalizedText, Mission, Prompt } from '../content/curriculum'
import type { GameMode, Language, MissionStatus } from '../domain/game'
import { Countdown } from './Countdown'

type MissionBriefProps = {
  mission: Mission
  language: Language
  mode: GameMode
  status: MissionStatus
  onPrepare: () => void
  onEvaluate: () => void
}

type MissionDraft = {
  missionId: string
  promptIndex: number
  notes: string
  selectedChoice: number | null
  rankingOrder: number[]
  prepared: boolean
  handoffId: string
  handoffCopied: boolean
}

const frameworks = {
  technical: {
    es: 'Definición → cuándo lo usarías → trade-off → ejemplo real.',
    en: 'Definition → when you would use it → trade-off → real example.',
  },
  experience: {
    es: 'Contexto → problema → decisión → alternativa descartada → resultado → aprendizaje.',
    en: 'Context → problem → decision → rejected alternative → result → learning.',
  },
  hypothetical: {
    es: 'Aclarar requisitos → identificar riesgos → solución sencilla → errores → probar y medir.',
    en: 'Clarify requirements → identify risks → simple solution → failures → test and measure.',
  },
} as const

const draftKey = (missionId: string) => `seniority-quest:draft:${missionId}`

function emptyDraft(mission: Mission): MissionDraft {
  return {
    missionId: mission.id,
    promptIndex: 0,
    notes: '',
    selectedChoice: null,
    rankingOrder: mission.prompts[0].kind === 'ranking'
      ? mission.prompts[0].options.map((_, index) => index)
      : [],
    prepared: false,
    handoffId: '',
    handoffCopied: false,
  }
}

function loadDraft(mission: Mission): MissionDraft {
  try {
    const stored = window.localStorage.getItem(draftKey(mission.id))
    if (!stored) return emptyDraft(mission)
    const candidate = JSON.parse(stored) as Partial<MissionDraft>
    if (candidate.missionId !== mission.id || typeof candidate.promptIndex !== 'number') {
      return emptyDraft(mission)
    }
    return { ...emptyDraft(mission), ...candidate }
  } catch {
    return emptyDraft(mission)
  }
}

function move(order: number[], from: number, to: number): number[] {
  if (to < 0 || to >= order.length) return order
  const next = [...order]
  const [item] = next.splice(from, 1)
  next.splice(to, 0, item)
  return next
}

function PromptBody({
  prompt,
  language,
  selectedChoice,
  rankingOrder,
  onChoice,
  onRank,
}: {
  prompt: Prompt
  language: Language
  selectedChoice: number | null
  rankingOrder: number[]
  onChoice: (index: number) => void
  onRank: (order: number[]) => void
}) {
  if (prompt.kind === 'forensics') return <pre><code>{prompt.code}</code></pre>
  if (prompt.kind === 'choice') {
    return (
      <fieldset className="choice-grid">
        <legend>{language === 'es' ? 'Explicaciones que compiten' : 'Competing explanations'}</legend>
        {prompt.options.map((option, index) => (
          <label key={option.en}>
            <input
              type="radio"
              name={prompt.id}
              value={index}
              checked={selectedChoice === index}
              onChange={() => onChoice(index)}
            />
            <span>{option[language]}</span>
          </label>
        ))}
      </fieldset>
    )
  }
  if (prompt.kind === 'ranking') {
    const order = rankingOrder.length === prompt.options.length
      ? rankingOrder
      : prompt.options.map((_, index) => index)
    return (
      <ol className="ranking-list interactive-ranking">
        {order.map((optionIndex, position) => {
          const option = prompt.options[optionIndex]
          return (
            <li key={option.en}>
              <span>{option[language]}</span>
              <span className="rank-actions">
                <button
                  type="button"
                  disabled={position === 0}
                  aria-label={`${language === 'es' ? 'Subir' : 'Move up'}: ${option[language]}`}
                  onClick={() => onRank(move(order, position, position - 1))}
                >↑</button>
                <button
                  type="button"
                  disabled={position === order.length - 1}
                  aria-label={`${language === 'es' ? 'Bajar' : 'Move down'}: ${option[language]}`}
                  onClick={() => onRank(move(order, position, position + 1))}
                >↓</button>
              </span>
            </li>
          )
        })}
      </ol>
    )
  }
  return null
}

function localizedOptions(prompt: Prompt): LocalizedText[] {
  return prompt.kind === 'choice' || prompt.kind === 'ranking' ? prompt.options : []
}

export function MissionBrief({
  mission,
  language,
  mode,
  status,
  onPrepare,
  onEvaluate,
}: MissionBriefProps) {
  const [draft, setDraft] = useState<MissionDraft>(() => loadDraft(mission))
  const [copyState, setCopyState] = useState<'idle' | 'copied' | 'failed'>('idle')

  useEffect(() => setDraft(loadDraft(mission)), [mission])
  useEffect(() => {
    if (draft.missionId === mission.id) {
      window.localStorage.setItem(draftKey(mission.id), JSON.stringify(draft))
    }
  }, [draft, mission.id])

  const prompt = mission.prompts[draft.promptIndex] ?? mission.prompts[0]
  const promptLanguage: Language =
    draft.promptIndex === 2 || (mission.kind === 'boss' && draft.promptIndex === 1)
      ? 'en'
      : language
  const options = localizedOptions(prompt)

  const handoff = useMemo(() => {
    const lines = [
      `EVENT: ${draft.handoffId || 'pending'}`,
      `MODE: ${mode}`,
      `MISSION: ${mission.title[language]}`,
      `QUESTION (${promptLanguage.toUpperCase()}): ${prompt.question[promptLanguage]}`,
    ]
    if (prompt.kind === 'forensics') lines.push(`CODE:\n${prompt.code}`)
    if (prompt.kind === 'choice') {
      lines.push('OPTIONS:')
      options.forEach((option, index) => {
        lines.push(`${index + 1}. ${option[promptLanguage]}${draft.selectedChoice === index ? ' [SELECTED]' : ''}`)
      })
    }
    if (prompt.kind === 'ranking') {
      lines.push('RANKING SUBMITTED:')
      draft.rankingOrder.forEach((optionIndex, index) => {
        lines.push(`${index + 1}. ${prompt.options[optionIndex]?.[promptLanguage] ?? '?'}`)
      })
    }
    if (draft.notes.trim()) lines.push(`LOCAL NOTES:\n${draft.notes.trim()}`)
    if (mode === 'coach') lines.push(`ANSWER FRAMEWORK: ${frameworks[mission.framework][language]}`)
    lines.push(
      'INSTRUCTIONS FOR CODEX:',
      '- Do not reveal a canned answer or answer key before the attempt closes.',
      '- Ask exactly two meaningful follow-ups; the second must transfer the concept to a changed constraint, React/Vue surface, or English.',
      `- ${mode === 'coach' ? 'Offer at most one bounded hint if explicitly requested and record hintUsed=true.' : 'Give no hints and withhold all feedback until the attempt closes.'}`,
      '- After the answer and two follow-ups, return ONLY valid JSON with: scores { technicalAccuracy, tradeoffs, ownership, evidence, problemSolving, bilingualCommunication }, followUpCount, hintUsed, unassistedTransfer, evidenceSummary, attemptClosed:true.',
    )
    return lines.join('\n\n')
  }, [draft, language, mission, mode, options, prompt, promptLanguage])

  function prepare() {
    onPrepare()
    setDraft((current) => ({
      ...current,
      prepared: true,
      handoffId: current.handoffId || `handoff-${mission.id}-${Date.now()}`,
      handoffCopied: false,
    }))
    setCopyState('idle')
  }

  async function copyHandoff() {
    try {
      if (!navigator.clipboard?.writeText) throw new Error('Clipboard unavailable')
      await navigator.clipboard.writeText(handoff)
      setDraft((current) => ({ ...current, handoffCopied: true }))
      setCopyState('copied')
    } catch {
      setCopyState('failed')
    }
  }

  function nextPrompt() {
    const nextIndex = (draft.promptIndex + 1) % mission.prompts.length
    const nextPromptValue = mission.prompts[nextIndex]
    setDraft({
      ...emptyDraft(mission),
      promptIndex: nextIndex,
      rankingOrder: nextPromptValue.kind === 'ranking'
        ? nextPromptValue.options.map((_, index) => index)
        : [],
    })
    setCopyState('idle')
  }

  return (
    <article className="mission-brief panel">
      <header className="brief-header">
        <div>
          <span className="eyebrow">{mission.kind === 'boss' ? 'BOSS / GATE' : 'ACTIVE / MISSION'}</span>
          <h2>{mission.title[language]}</h2>
          <p>{mission.objective[language]}</p>
        </div>
        <Countdown minutes={mission.minutes} language={language} storageKey={mission.id} />
      </header>

      {mode === 'coach' && (
        <aside className="vue-bridge">
          <span>VUE ⇄ REACT</span>
          <p>{mission.vueBridge[language]}</p>
        </aside>
      )}

      <section className="prompt-stage" aria-labelledby="prompt-title">
        <div className="prompt-meta">
          <span>{prompt.kind.toUpperCase().replace('_', ' ')}</span>
          <span className={promptLanguage !== language ? 'language-switch' : ''}>
            {promptLanguage !== language ? 'EN SWITCH · ' : ''}
            {String(draft.promptIndex + 1).padStart(2, '0')} / {String(mission.prompts.length).padStart(2, '0')}
          </span>
        </div>
        <h3 id="prompt-title">{prompt.question[promptLanguage]}</h3>
        <PromptBody
          prompt={prompt}
          language={promptLanguage}
          selectedChoice={draft.selectedChoice}
          rankingOrder={draft.rankingOrder}
          onChoice={(selectedChoice) => setDraft((current) => ({ ...current, selectedChoice }))}
          onRank={(rankingOrder) => setDraft((current) => ({ ...current, rankingOrder }))}
        />
        <label className="notes-field">
          <span>{language === 'es' ? 'Borrador / evidencia' : 'Draft / evidence'}</span>
          <textarea
            rows={5}
            value={draft.notes}
            onChange={(event) => setDraft((current) => ({ ...current, notes: event.target.value }))}
            placeholder={language === 'es' ? 'Ideas, trade-offs, métricas verificables…' : 'Ideas, trade-offs, verifiable metrics…'}
          />
        </label>
        <div className="brief-actions">
          <button className="primary-action" type="button" onClick={prepare}>
            {language === 'es' ? 'Preparar respuesta' : 'Prepare answer'}
          </button>
          <button type="button" disabled={!draft.handoffCopied} onClick={onEvaluate}>
            {language === 'es' ? 'Importar veredicto' : 'Import verdict'}
          </button>
          <button type="button" onClick={nextPrompt}>
            {language === 'es' ? 'Siguiente reto' : 'Next challenge'}
          </button>
        </div>
      </section>

      {draft.prepared && (
        <section className="chat-dispatch" role="region" aria-label={language === 'es' ? 'Despacho al chat' : 'Chat dispatch'}>
          <div>
            <span className="eyebrow">CODEX / HANDOFF</span>
            <h3>{language === 'es' ? 'Copia y responde en este chat' : 'Copy and answer in this chat'}</h3>
          </div>
          <p>
            {mode === 'coach'
              ? frameworks[mission.framework][language]
              : language === 'es'
                ? 'Sin estructura visible. El feedback llegará al cerrar el intento.'
                : 'No visible structure. Feedback arrives after the attempt closes.'}
          </p>
          <button type="button" onClick={copyHandoff}>
            {copyState === 'copied'
              ? language === 'es' ? 'Handoff copiado' : 'Handoff copied'
              : language === 'es' ? 'Copiar handoff completo' : 'Copy complete handoff'}
          </button>
          {copyState === 'failed' && (
            <div className="manual-handoff">
              <label>
                <span>
                  {language === 'es'
                    ? 'Handoff completo para copia manual'
                    : 'Complete handoff for manual copy'}
                </span>
                <textarea
                  readOnly
                  rows={8}
                  value={handoff}
                  onFocus={(event) => event.currentTarget.select()}
                />
              </label>
              <button
                type="button"
                onClick={() => {
                  setDraft((current) => ({ ...current, handoffCopied: true }))
                  setCopyState('copied')
                }}
              >
                {language === 'es' ? 'Ya lo copié manualmente' : 'I copied it manually'}
              </button>
            </div>
          )}
        </section>
      )}

      <p className="pressure-note">
        {mode === 'coach'
          ? language === 'es'
            ? 'Coach activo: una pista máxima; después debes transferir sin ayuda.'
            : 'Coach active: one hint maximum; then transfer without help.'
          : language === 'es'
            ? 'Sin pistas ni feedback hasta cerrar respuesta y dos follow-ups.'
            : 'No cues or feedback until the answer and two follow-ups close.'}
        <span>{status.toUpperCase()}</span>
      </p>
    </article>
  )
}
