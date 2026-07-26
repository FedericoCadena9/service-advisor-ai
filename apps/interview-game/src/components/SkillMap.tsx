import { curriculum } from '../content/curriculum'
import type { GameState, Language, MissionId } from '../domain/game'

type SkillMapProps = {
  state: GameState
  language: Language
  onSelect: (missionId: MissionId) => void
}

const statusCopy = {
  es: { locked: 'bloqueada', available: 'disponible', active: 'activa', retry: 'reintento', passed: 'superada' },
  en: { locked: 'locked', available: 'available', active: 'active', retry: 'retry', passed: 'passed' },
} as const

export function SkillMap({ state, language, onSelect }: SkillMapProps) {
  return (
    <nav className="skill-map panel" aria-label={language === 'es' ? 'Mapa de misiones' : 'Mission map'}>
      <div className="panel-heading">
        <span className="eyebrow">01 / JOURNEY</span>
        <h2>{language === 'es' ? 'Ruta de seniority' : 'Seniority route'}</h2>
      </div>
      <ol>
        {curriculum.map((mission, index) => {
          const progress = state.missions[mission.id]
          const active = state.activeMissionId === mission.id
          return (
            <li key={mission.id} className={`mission-node is-${progress.status}`}>
              <button
                type="button"
                disabled={progress.status === 'locked'}
                aria-current={active ? 'step' : undefined}
                onClick={() => onSelect(mission.id)}
              >
                <span className="node-index">{mission.kind === 'boss' ? 'B' : String(index + 1).padStart(2, '0')}</span>
                <span className="node-copy">
                  <strong>{mission.title[language]}</strong>
                  <small>
                    {statusCopy[language][progress.status]}
                    {progress.bestScore !== null ? ` · ${progress.bestScore}` : ''}
                  </small>
                </span>
                <span className="node-signal" aria-hidden="true" />
              </button>
            </li>
          )
        })}
      </ol>
    </nav>
  )
}
