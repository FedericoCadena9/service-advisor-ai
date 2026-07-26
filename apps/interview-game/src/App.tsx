import { useMemo, useState } from 'react'

import { getMission } from './content/curriculum'
import { MissionBrief } from './components/MissionBrief'
import { RubricPanel } from './components/RubricPanel'
import { SkillMap } from './components/SkillMap'
import { StoryForge } from './components/StoryForge'
import { StudyPlan } from './components/StudyPlan'
import {
  MISSION_SEQUENCE,
  RUBRIC_DIMENSIONS,
  getAdaptiveAllocation,
  getEvaluationScore,
  getMastery,
  isPassingAttempt,
  type EvaluationResult,
  type RubricDimension,
} from './domain/game'
import { useGame } from './hooks/useGame'

const masteryLabels = {
  es: {
    technicalAccuracy: 'Precisión técnica',
    tradeoffs: 'Trade-offs',
    ownership: 'Ownership',
    evidence: 'Evidencia',
    problemSolving: 'Validación',
    bilingualCommunication: 'Inglés técnico',
  },
  en: {
    technicalAccuracy: 'Technical accuracy',
    tradeoffs: 'Trade-offs',
    ownership: 'Ownership',
    evidence: 'Evidence',
    problemSolving: 'Validation',
    bilingualCommunication: 'Technical English',
  },
} as const

export default function App() {
  const [state, dispatch] = useGame()
  const [view, setView] = useState<'missions' | 'stories' | 'plan'>('missions')
  const [showRubric, setShowRubric] = useState(false)
  const [feedback, setFeedback] = useState('')
  const [confirmReset, setConfirmReset] = useState(false)
  const mission = getMission(state.activeMissionId)
  const mastery = getMastery(state)
  const adaptive = getAdaptiveAllocation(state)
  const passedCount = MISSION_SEQUENCE.filter(
    (missionId) => state.missions[missionId].status === 'passed',
  ).length
  const xp = passedCount * 100 + state.attempts.length * 10 + state.stories.length * 25
  const overallMastery = useMemo(() => {
    if (state.attempts.length === 0) return 0
    return Math.round(
      RUBRIC_DIMENSIONS.reduce((sum, dimension) => sum + mastery[dimension], 0) /
        RUBRIC_DIMENSIONS.length,
    )
  }, [mastery, state.attempts.length])

  function scoreAttempt(evaluation: EvaluationResult) {
    const passed = isPassingAttempt(mission.id, evaluation)
    const score = getEvaluationScore(evaluation)
    dispatch({ type: 'attempt_scored', missionId: mission.id, evaluation })
    setFeedback(
      state.language === 'es'
        ? passed
          ? `Misión superada · ${score}/100`
          : `Reintento requerido · ${score}/100`
        : passed
          ? `Mission passed · ${score}/100`
          : `Retry required · ${score}/100`,
    )
    setShowRubric(false)
  }

  function resetGame() {
    dispatch({ type: 'game_reset' })
    setFeedback('')
    setConfirmReset(false)
    setView('missions')
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-lockup">
          <span className="brand-mark" aria-hidden="true">SQ</span>
          <div>
            <span className="eyebrow">MEDTRAINER / FRONTEND REACT</span>
            <h1>Seniority Quest</h1>
          </div>
        </div>
        <div className="interview-chip">
          <span>{state.language === 'es' ? 'OBJETIVO' : 'TARGET'}</span>
          <strong>Technical Knowledge · 20–30 min</strong>
        </div>
        <div className="top-controls">
          <div className="segmented" aria-label={state.language === 'es' ? 'Idioma' : 'Language'}>
            <button type="button" aria-pressed={state.language === 'es'} onClick={() => dispatch({ type: 'language_set', language: 'es' })}>Español</button>
            <button type="button" aria-pressed={state.language === 'en'} onClick={() => dispatch({ type: 'language_set', language: 'en' })}>English</button>
          </div>
        </div>
      </header>

      <section className="control-strip">
        <nav className="view-tabs" aria-label={state.language === 'es' ? 'Área de trabajo' : 'Workspace'}>
          <button type="button" aria-pressed={view === 'missions'} onClick={() => setView('missions')}>
            {state.language === 'es' ? 'Misiones' : 'Missions'}
          </button>
          <button type="button" aria-pressed={view === 'stories'} onClick={() => setView('stories')}>Story Forge</button>
          <button type="button" aria-pressed={view === 'plan'} onClick={() => setView('plan')}>Plan 8h</button>
        </nav>
        <div className="mode-switch">
          <button type="button" aria-pressed={state.mode === 'coach'} onClick={() => dispatch({ type: 'mode_set', mode: 'coach' })}>
            {state.language === 'es' ? 'Modo Coach' : 'Coach mode'}
          </button>
          <button type="button" aria-pressed={state.mode === 'interview'} onClick={() => dispatch({ type: 'mode_set', mode: 'interview' })}>
            {state.language === 'es' ? 'Modo entrevista' : 'Interview mode'}
          </button>
        </div>
        <p className="progress-summary">
          <span>{xp} XP</span>
          <strong>{passedCount}/8</strong>{' '}
          {state.language === 'es' ? 'misiones superadas' : 'missions passed'}
        </p>
      </section>

      {view === 'missions' ? (
        <main className="mission-layout">
          <SkillMap
            state={state}
            language={state.language}
            onSelect={(missionId) => {
              dispatch({ type: 'mission_selected', missionId })
              setShowRubric(false)
              setFeedback('')
            }}
          />
          <section className="mission-column">
            {feedback && <p role="status" className={`feedback ${feedback.includes('superada') || feedback.includes('passed') ? 'is-success' : 'is-retry'}`}>{feedback}</p>}
            <MissionBrief
              mission={mission}
              language={state.language}
              mode={state.mode}
              status={state.missions[mission.id].status}
              onPrepare={() => {
                dispatch({ type: 'mission_started', missionId: mission.id })
              }}
              onEvaluate={() => setShowRubric(true)}
            />
            {showRubric && (
              <RubricPanel
                language={state.language}
                onSubmit={scoreAttempt}
              />
            )}
          </section>
          <aside className="evidence-panel panel">
            <div className="mastery-orbit">
              <span className="eyebrow">MASTERY</span>
              <strong data-mastery>{overallMastery}%</strong>
              <small>{state.language === 'es' ? 'señal actual' : 'current signal'}</small>
            </div>
            <div className="mastery-list">
              {RUBRIC_DIMENSIONS.map((dimension: RubricDimension) => (
                <div key={dimension}>
                  <span>{masteryLabels[state.language][dimension]}</span>
                  <div className="meter"><i style={{ width: `${mastery[dimension]}%` }} /></div>
                  <b>{mastery[dimension]}</b>
                </div>
              ))}
            </div>
            <section className="adaptive-card">
              <span className="eyebrow">GAP LOG / +15</span>
              <h3>{state.language === 'es' ? 'Brecha prioritaria' : 'Priority gap'}</h3>
              <p>
                {adaptive
                  ? state.language === 'es'
                    ? `Asigna 15 min a ${masteryLabels.es[adaptive.dimension].toLowerCase()} (${adaptive.average}).`
                    : `Assign 15 min to ${masteryLabels.en[adaptive.dimension].toLowerCase()} (${adaptive.average}).`
                  : state.language === 'es'
                    ? 'Completa un intento para detectar la brecha más débil.'
                    : 'Complete one attempt to detect your weakest gap.'}
              </p>
            </section>
            <div className="reset-zone">
              {!confirmReset ? (
                <button type="button" onClick={() => setConfirmReset(true)}>{state.language === 'es' ? 'Reiniciar progreso' : 'Reset progress'}</button>
              ) : (
                <div role="group" aria-label={state.language === 'es' ? 'Confirmar reinicio' : 'Confirm reset'}>
                  <button type="button" className="danger" onClick={resetGame}>{state.language === 'es' ? 'Confirmar reinicio' : 'Confirm reset'}</button>
                  <button type="button" onClick={() => setConfirmReset(false)}>{state.language === 'es' ? 'Cancelar' : 'Cancel'}</button>
                </div>
              )}
            </div>
          </aside>
        </main>
      ) : view === 'stories' ? (
        <main className="forge-layout">
          <StoryForge
            language={state.language}
            stories={state.stories}
            onSave={(story) => dispatch({ type: 'story_saved', story })}
          />
        </main>
      ) : (
        <StudyPlan language={state.language} />
      )}

      <footer>
        <span>LOCAL-FIRST · NO EXTERNAL AI KEY</span>
        <span>{state.language === 'es' ? 'Hard stop mañana 11:10' : 'Hard stop tomorrow 11:10'}</span>
      </footer>
    </div>
  )
}
