import { useState, type FormEvent } from 'react'

import type { Language, Story } from '../domain/game'

type StoryInput = Omit<Story, 'id'>
type StoryForgeProps = {
  language: Language
  stories: Story[]
  onSave: (story: StoryInput) => void
}

const emptyStory: StoryInput = {
  title: '',
  context: '',
  problem: '',
  decision: '',
  rejectedAlternative: '',
  result: '',
  learning: '',
  personalOwnership: '',
  scaleConstraints: '',
  consequence: '',
  evidence: '',
  evidenceConfidence: 'incomplete',
  failureValidation: '',
  vueContext: '',
  reactBridge: '',
  version30: '',
  version90: '',
  deepDive: '',
  englishVersion: '',
  tags: '',
  hostileFollowUps: '',
}

const fieldCopy = {
  es: {
    title: 'Título de la historia',
    context: 'Contexto',
    problem: 'Problema',
    decision: 'Decisión',
    rejectedAlternative: 'Alternativa descartada',
    result: 'Resultado',
    learning: 'Aprendizaje',
    personalOwnership: 'Ownership personal',
    scaleConstraints: 'Escala y restricciones',
    consequence: 'Consecuencia',
    evidence: 'Evidencia verificable',
    evidenceConfidence: 'Confianza de evidencia',
    failureValidation: 'Fallos y validación',
    vueContext: 'Contexto Vue',
    reactBridge: 'Puente React',
    version30: 'Versión 30 segundos',
    version90: 'Versión 90 segundos',
    deepDive: 'Versión deep dive',
    englishVersion: 'Versión en inglés',
    tags: 'Tags',
    hostileFollowUps: 'Follow-ups hostiles',
  },
  en: {
    title: 'Story title',
    context: 'Context',
    problem: 'Problem',
    decision: 'Decision',
    rejectedAlternative: 'Rejected alternative',
    result: 'Result',
    learning: 'Learning',
    personalOwnership: 'Personal ownership',
    scaleConstraints: 'Scale and constraints',
    consequence: 'Consequence',
    evidence: 'Verifiable evidence',
    evidenceConfidence: 'Evidence confidence',
    failureValidation: 'Failures and validation',
    vueContext: 'Vue context',
    reactBridge: 'React Bridge',
    version30: '30-second version',
    version90: '90-second version',
    deepDive: 'Deep-dive version',
    englishVersion: 'English version',
    tags: 'Tags',
    hostileFollowUps: 'Hostile follow-ups',
  },
} as const

export function StoryForge({ language, stories, onSave }: StoryForgeProps) {
  const [draft, setDraft] = useState<StoryInput>(emptyStory)

  function submit(event: FormEvent) {
    event.preventDefault()
    const required = ['title', 'context', 'problem', 'decision', 'rejectedAlternative', 'result', 'learning'] as const
    if (required.some((field) => !draft[field].trim())) return
    onSave(draft)
    setDraft(emptyStory)
  }

  return (
    <section className="forge-workbench" aria-labelledby="forge-title">
      <header>
        <span className="eyebrow">STORY / FORGE</span>
        <h2 id="forge-title">{language === 'es' ? 'Forja evidencia, no ficción' : 'Forge evidence, not fiction'}</h2>
        <p>
          {language === 'es'
            ? 'Construye cuatro historias profundas y dos ejemplos relámpago. Usa solo hechos que puedas defender.'
            : 'Build four deep stories and two lightning examples. Use only facts you can defend.'}
        </p>
      </header>
      <form onSubmit={submit}>
        {(Object.keys(emptyStory) as (keyof StoryInput)[]).map((field) => (
          <label key={field} className={field === 'title' ? 'field-title' : ''}>
            <span>{fieldCopy[language][field]}</span>
            {field === 'title' ? (
              <input
                required
                value={draft[field]}
                onChange={(event) => setDraft({ ...draft, [field]: event.target.value })}
              />
            ) : field === 'evidenceConfidence' ? (
              <select
                value={draft.evidenceConfidence}
                onChange={(event) => setDraft({
                  ...draft,
                  evidenceConfidence: event.target.value as StoryInput['evidenceConfidence'],
                })}
              >
                <option value="verified">{language === 'es' ? 'Verificada' : 'Verified'}</option>
                <option value="remembered_unmeasured">{language === 'es' ? 'Recordada, no medida' : 'Remembered, unmeasured'}</option>
                <option value="incomplete">{language === 'es' ? 'Incompleta' : 'Incomplete'}</option>
              </select>
            ) : (
              <textarea
                rows={3}
                value={draft[field]}
                onChange={(event) => setDraft({ ...draft, [field]: event.target.value })}
              />
            )}
          </label>
        ))}
        <button className="primary-action" type="submit">
          {language === 'es' ? 'Forjar historia' : 'Forge story'}
        </button>
      </form>
      <div className="story-deck" aria-live="polite">
        {stories.length === 0 ? (
          <p className="empty-state">
            {language === 'es' ? 'Aún no hay historias. Empieza por ownership.' : 'No stories yet. Start with ownership.'}
          </p>
        ) : (
          stories.map((story) => (
            <article key={story.id} aria-label={story.title}>
              <span className="story-number">{story.id.replace('story-', '#')}</span>
              <h3>{story.title}</h3>
              {(Object.keys(fieldCopy[language]) as (keyof StoryInput)[])
                .filter((field) => field !== 'title')
                .map((field) => (
                  <section key={field}>
                    <h4>{fieldCopy[language][field]}</h4>
                    <p>{story[field] || (language === 'es' ? 'Pendiente / no inventar' : 'Pending / do not invent')}</p>
                  </section>
                ))}
            </article>
          ))
        )}
      </div>
    </section>
  )
}
