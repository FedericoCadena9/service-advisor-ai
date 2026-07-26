import { useCountdown } from '../hooks/useCountdown'
import type { Language } from '../domain/game'

type CountdownProps = {
  minutes: number
  language: Language
  storageKey?: string
}

export function Countdown({ minutes, language, storageKey }: CountdownProps) {
  const timer = useCountdown(minutes, storageKey)
  const value = `${String(Math.floor(timer.seconds / 60)).padStart(2, '0')}:${String(
    timer.seconds % 60,
  ).padStart(2, '0')}`
  const copy =
    language === 'es'
      ? { start: 'Iniciar reloj', pause: 'Pausar reloj', reset: 'Reiniciar reloj' }
      : { start: 'Start timer', pause: 'Pause timer', reset: 'Reset timer' }

  return (
    <section className={`countdown ${timer.running ? 'is-running' : ''}`} aria-label="Timer">
      <span className="eyebrow">{timer.running ? 'LIVE' : 'T–00'}</span>
      <output aria-live="off">{value}</output>
      <div className="timer-actions">
        <button type="button" onClick={timer.running ? timer.pause : timer.start}>
          {timer.running ? copy.pause : copy.start}
        </button>
        <button type="button" onClick={timer.reset}>
          {copy.reset}
        </button>
      </div>
    </section>
  )
}
