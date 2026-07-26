import type { Language } from '../domain/game'

const today = [
  ['Calibration Gate', 15],
  ['Framework Translator', 35],
  ['State Strategist', 30],
  ['Break', 10],
  ['Architecture Guardian', 30],
  ['Story Forge', 45],
  ['Break', 10],
  ['Boss 1', 30],
  ['Technical Challenge Prologue', 25],
  ['Gap Log + save point', 10],
] as const

const tomorrow = [
  ['08:00–08:45', 'Breakfast, shower, movement'],
  ['08:45–09:15', 'Active Vue-to-React recall'],
  ['09:15–09:25', 'Break'],
  ['09:25–10:05', 'Random Story Card recall'],
  ['10:05–10:20', 'Break'],
  ['10:20–10:50', 'Boss 2'],
  ['10:50–11:10', 'Correct only the top gaps'],
  ['11:10–12:30', 'Food, walk, equipment, recovery'],
  ['12:30', 'Interview'],
] as const

const tomorrowEs: Record<string, string> = {
  'Breakfast, shower, movement': 'Desayuno, ducha y movimiento',
  'Active Vue-to-React recall': 'Recuerdo activo Vue→React',
  Break: 'Descanso',
  'Random Story Card recall': 'Recuerdo aleatorio de Story Cards',
  'Boss 2': 'Boss 2',
  'Correct only the top gaps': 'Corregir solo las brechas principales',
  'Food, walk, equipment, recovery': 'Comida ligera, caminata, equipo y recuperación',
  Interview: 'Entrevista',
}

export function StudyPlan({ language }: { language: Language }) {
  return (
    <main className="schedule-layout">
      <header className="schedule-hero">
        <span className="eyebrow">RECOVERY IS PART OF PERFORMANCE</span>
        <h2>{language === 'es' ? 'Ocho horas. Cero maratón.' : 'Eight hours. No marathon.'}</h2>
        <p>
          {language === 'es'
            ? 'Hoy construyes señal. Mañana solo recuperas, simulas y cierras. El descanso no es tiempo perdido.'
            : 'Today you build signal. Tomorrow you only recall, simulate, and close. Recovery is not wasted time.'}
        </p>
      </header>
      <section className="schedule-card">
        <div className="schedule-heading">
          <span>DAY / 01</span>
          <h3>{language === 'es' ? 'Hoy · 240 minutos' : 'Today · 240 minutes'}</h3>
        </div>
        <ol>
          {today.map(([label, minutes], index) => (
            <li key={label + index} className={label === 'Break' ? 'is-break' : ''}>
              <span>{String(index + 1).padStart(2, '0')}</span>
              <strong>{language === 'es' && label === 'Break' ? 'Descanso' : label}</strong>
              <time>{minutes} min</time>
            </li>
          ))}
        </ol>
        <aside>
          {language === 'es'
            ? 'El diagnóstico puede mover hasta 15 minutos del prólogo o de una historia ya dominada hacia la brecha de mayor riesgo.'
            : 'The diagnostic may move up to 15 minutes from the prologue or a mastered story toward the highest-risk gap.'}
        </aside>
      </section>
      <section className="schedule-card tomorrow-card">
        <div className="schedule-heading">
          <span>DAY / 02</span>
          <h3>{language === 'es' ? 'Mañana · recall y recuperación' : 'Tomorrow · recall and recovery'}</h3>
        </div>
        <ol>
          {tomorrow.map(([time, label]) => (
            <li key={time} className={time === '12:30' ? 'is-interview' : ''}>
              <time>{time}</time>
              <strong>{language === 'es' ? tomorrowEs[label] : label}</strong>
            </li>
          ))}
        </ol>
        <div
          className="hard-stop"
          role="note"
          aria-label={language === 'es' ? '11:10 · Stop obligatorio' : '11:10 · Mandatory stop'}
        >
          <span>11:10</span>
          <strong>{language === 'es' ? 'Stop obligatorio' : 'Mandatory stop'}</strong>
          <p>{language === 'es' ? 'Nada de “una última lectura”. Cambia a recuperación.' : 'No “one last read.” Switch to recovery.'}</p>
        </div>
      </section>
    </main>
  )
}
