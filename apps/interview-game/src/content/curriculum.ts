import { MISSION_SEQUENCE, type MissionId, type MissionKind } from '../domain/game'

export type LocalizedText = { es: string; en: string }
export type AnswerFramework = 'technical' | 'experience' | 'hypothetical'

type PromptBase = {
  id: string
  question: LocalizedText
  followUps: LocalizedText[]
}

export type OpenPrompt = PromptBase & { kind: 'open' }
export type RankingPrompt = PromptBase & {
  kind: 'ranking'
  options: LocalizedText[]
}
export type ForensicsPrompt = PromptBase & {
  kind: 'forensics'
  code: string
}
export type ChoicePrompt = PromptBase & {
  kind: 'choice'
  options: [LocalizedText, LocalizedText, LocalizedText, LocalizedText]
}

export type Prompt = OpenPrompt | RankingPrompt | ForensicsPrompt | ChoicePrompt

export type Mission = {
  id: MissionId
  kind: MissionKind
  minutes: number
  title: LocalizedText
  objective: LocalizedText
  vueBridge: LocalizedText
  framework: AnswerFramework
  prompts: Prompt[]
}

const followTradeoff: LocalizedText = {
  es: '¿Qué alternativa razonable descartaste y qué costo aceptaste?',
  en: 'Which reasonable alternative did you reject, and which cost did you accept?',
}

const followEvidence: LocalizedText = {
  es: '¿Cómo comprobarías que tu decisión funcionó en producción?',
  en: 'How would you prove that your decision worked in production?',
}

const missionCatalog: Mission[] = [
  {
    id: 'calibration',
    kind: 'level',
    minutes: 15,
    title: { es: 'Puerta de calibración', en: 'Calibration gate' },
    objective: {
      es: 'Medir el punto de partida real en React, transferencia desde Vue, historias disponibles e inglés técnico.',
      en: 'Measure the real baseline in React, Vue transfer, available stories, and technical English.',
    },
    vueBridge: {
      es: 'No busques equivalencias todavía: separa lo que recuerdas, lo que puedes derivar y lo que necesitas verificar.',
      en: 'Do not chase equivalence yet: separate what you recall, what you can derive, and what you must verify.',
    },
    framework: 'technical',
    prompts: [
      {
        id: 'calibration-open-inventory',
        kind: 'open',
        question: {
          es: 'Sin notas, explica qué provoca un render en React y nombra dos historias reales que podrían demostrar seniority.',
          en: 'Without notes, explain what triggers a React render and name two real stories that could demonstrate seniority.',
        },
        followUps: [
          { es: 'Cambia a inglés: ¿qué parte de tu respuesta tiene mayor incertidumbre?', en: 'Switch to English: which part of your answer carries the most uncertainty?' },
          followEvidence,
        ],
      },
      {
        id: 'calibration-forensics-snapshot',
        kind: 'forensics',
        code: `function Counter() {
  const [count, setCount] = useState(0)
  function addThree() {
    setCount(count + 1)
    setCount(count + 1)
    setCount(count + 1)
  }
  return <button onClick={addThree}>{count}</button>
}`,
        question: {
          es: 'Predice el resultado de un click antes de explicar snapshots, batching y la corrección mínima.',
          en: 'Predict one click before explaining snapshots, batching, and the smallest correction.',
        },
        followUps: [followTradeoff],
      },
      {
        id: 'calibration-choice-uncertainty',
        kind: 'choice',
        question: {
          es: 'No recuerdas una API exacta durante la entrevista. ¿Qué respuesta conserva mejor la señal senior?',
          en: 'You do not recall an exact API during the interview. Which response best preserves a senior signal?',
        },
        options: [
          { es: 'Inventar la firma más probable y continuar con seguridad sin validarla', en: 'Invent the most likely signature and continue confidently without validating it' },
          { es: 'Aclarar el principio, marcar la duda y decir cómo verificar', en: 'State the principle, mark uncertainty, and explain verification' },
          { es: 'Cambiar de tema hacia una herramienta que recuerdes mejor', en: 'Change topics toward a tool that you remember much better' },
          { es: 'Responder solo con la solución equivalente que usarías en Vue', en: 'Answer only with the equivalent solution you would use in Vue' },
        ],
        followUps: [followEvidence, followTradeoff],
      },
    ],
  },
  {
    id: 'bridge',
    kind: 'level',
    minutes: 35,
    title: { es: 'Puente de mando', en: 'Command bridge' },
    objective: {
      es: 'Traducir experiencia Vue a un modelo mental React sin fingir memoria sintáctica.',
      en: 'Translate Vue experience into a React mental model without pretending syntax recall.',
    },
    vueBridge: {
      es: 'Composition API y hooks organizan lógica reusable, pero React exige razonar explícitamente sobre renders, closures y dependencias.',
      en: 'Composition API and hooks organize reusable logic, but React requires explicit reasoning about renders, closures, and dependencies.',
    },
    framework: 'technical',
    prompts: [
      {
        id: 'bridge-open-mental-model',
        kind: 'open',
        question: {
          es: 'Explica a un Tech Lead cómo traducirías ref, computed y watch de Vue a React sin afirmar que son equivalentes exactos.',
          en: 'Explain to a Tech Lead how you would translate Vue ref, computed, and watch into React without claiming exact equivalence.',
        },
        followUps: [followTradeoff, followEvidence],
      },
      {
        id: 'bridge-ranking-migration',
        kind: 'ranking',
        question: {
          es: 'Ordena tus primeras acciones al heredar un módulo React creado con mucha asistencia de AI.',
          en: 'Rank your first actions when inheriting a React module created with heavy AI assistance.',
        },
        options: [
          { es: 'Trazar flujo de datos y límites', en: 'Trace data flow and boundaries' },
          { es: 'Confirmar pruebas y comportamiento', en: 'Confirm tests and behavior' },
          { es: 'Revisar efectos y closures', en: 'Review effects and closures' },
          { es: 'Optimizar renders visibles', en: 'Optimize visible renders' },
        ],
        followUps: [followTradeoff],
      },
      {
        id: 'bridge-choice-derived-state',
        kind: 'choice',
        question: {
          es: 'Un total depende solo de items y taxRate. ¿Qué decisión demuestra mejor criterio en React?',
          en: 'A total depends only on items and taxRate. Which decision shows the best React judgment?',
        },
        options: [
          { es: 'Guardarlo en state y sincronizarlo con un effect', en: 'Store it in state and synchronize it through an effect' },
          { es: 'Mover el cálculo completo a un store global compartido', en: 'Move the full calculation into a shared global store' },
          { es: 'Derivarlo al render y medir antes de memorizarlo', en: 'Derive it during render and measure before memoizing it' },
          { es: 'Calcularlo dentro de un callback con referencia estable', en: 'Calculate it inside a callback with a stable reference' },
        ],
        followUps: [followTradeoff, followEvidence],
      },
    ],
  },
  {
    id: 'rendering',
    kind: 'level',
    minutes: 30,
    title: { es: 'Cámara de renders', en: 'Render chamber' },
    objective: {
      es: 'Defender decisiones sobre estado, efectos, identidad y concurrencia bajo preguntas de seguimiento.',
      en: 'Defend decisions about state, effects, identity, and concurrency under follow-up questions.',
    },
    vueBridge: {
      es: 'Vue rastrea dependencias reactivas; React vuelve a ejecutar componentes y cada render captura su propio snapshot.',
      en: 'Vue tracks reactive dependencies; React re-executes components and each render captures its own snapshot.',
    },
    framework: 'technical',
    prompts: [
      {
        id: 'render-forensics-stale',
        kind: 'forensics',
        code: `function Search({ query }) {
  const [results, setResults] = useState([])
  useEffect(() => {
    fetch('/api/search?q=' + query).then(r => r.json()).then(setResults)
  }, [])
  return <Results items={results} />
}`,
        question: {
          es: 'Encuentra el fallo más peligroso, explica por qué ocurre y diseña una corrección que también maneje carreras.',
          en: 'Find the most dangerous failure, explain why it happens, and design a fix that also handles races.',
        },
        followUps: [followTradeoff, followEvidence],
      },
      {
        id: 'render-open-effects',
        kind: 'open',
        question: {
          es: '¿Cuándo un useEffect es señal de estado mal modelado y cuándo sí representa sincronización legítima?',
          en: 'When is useEffect a sign of poorly modeled state, and when is it legitimate synchronization?',
        },
        followUps: [
          { es: '¿Cómo cambia tu respuesta con SSR?', en: 'How does SSR change your answer?' },
          followEvidence,
        ],
      },
      {
        id: 'render-choice-key',
        kind: 'choice',
        question: {
          es: 'Inputs editables se reordenan y conservan valores de la fila incorrecta. ¿Cuál es el diagnóstico inicial más sólido?',
          en: 'Editable inputs reorder and retain values from the wrong row. What is the strongest initial diagnosis?',
        },
        options: [
          { es: 'Las keys usan posición y rompen identidad entre renders', en: 'Position-based keys break identity across renders' },
          { es: 'Los setters de state necesitan ejecutarse de forma síncrona', en: 'State setters need to execute in a synchronous way' },
          { es: 'El listado debería envolverse con memo en todos los casos', en: 'The list should always be wrapped with memo first' },
          { es: 'Los eventos del input requieren referencias siempre estables', en: 'Input events require references that are always stable' },
        ],
        followUps: [followEvidence, followTradeoff],
      },
    ],
  },
  {
    id: 'architecture',
    kind: 'level',
    minutes: 30,
    title: { es: 'Sala de decisiones', en: 'Decision room' },
    objective: {
      es: 'Hacer visible la seniority mediante límites, rendimiento, pruebas y evolución segura.',
      en: 'Make seniority visible through boundaries, performance, testing, and safe evolution.',
    },
    vueBridge: {
      es: 'Pinia y composables se traducen mejor como responsabilidades y ownership que como librerías React uno-a-uno.',
      en: 'Pinia and composables translate better as responsibilities and ownership than as one-to-one React libraries.',
    },
    framework: 'hypothetical',
    prompts: [
      {
        id: 'architecture-open-form',
        kind: 'open',
        question: {
          es: 'Diseña un formulario clínico largo con autosave, permisos y recuperación offline. Aclara antes de proponer.',
          en: 'Design a long clinical form with autosave, permissions, and offline recovery. Clarify before proposing.',
        },
        followUps: [
          { es: '¿Cuál sería tu primera versión deliberadamente simple?', en: 'What would your deliberately simple first version be?' },
          followEvidence,
        ],
      },
      {
        id: 'architecture-ranking-performance',
        kind: 'ranking',
        question: {
          es: 'Una tabla de 3,000 filas se siente lenta. Ordena el diagnóstico antes de recomendar memoización.',
          en: 'A 3,000-row table feels slow. Rank the diagnosis before recommending memoization.',
        },
        options: [
          { es: 'Reproducir y perfilar la interacción', en: 'Reproduce and profile the interaction' },
          { es: 'Separar red, cálculo y render', en: 'Separate network, compute, and render' },
          { es: 'Reducir trabajo con virtualización', en: 'Reduce work through virtualization' },
          { es: 'Estabilizar props donde se pruebe', en: 'Stabilize props where evidence supports it' },
        ],
        followUps: [followTradeoff],
      },
      {
        id: 'architecture-choice-testing',
        kind: 'choice',
        question: {
          es: 'Un hook coordina caché, formulario y navegación. ¿Qué prueba aporta la señal más valiosa primero?',
          en: 'A hook coordinates cache, form, and navigation. Which test provides the strongest first signal?',
        },
        options: [
          { es: 'Un snapshot amplio de todo el árbol de componentes', en: 'A broad snapshot of the entire component tree' },
          { es: 'Una prueba aislada de cada variable interna del hook', en: 'An isolated test for every internal hook variable' },
          { es: 'Un E2E para cada variante de datos y cada error posible', en: 'One E2E for every data variant and possible error' },
          { es: 'Una prueba de integración del comportamiento observable', en: 'An integration test of the observable behavior' },
        ],
        followUps: [followTradeoff, followEvidence],
      },
    ],
  },
  {
    id: 'knowledge_boss',
    kind: 'boss',
    minutes: 30,
    title: { es: 'Boss: presión técnica', en: 'Boss: technical pressure' },
    objective: {
      es: 'Responder con precisión, trade-offs y evidencia sin esconderse detrás del framework.',
      en: 'Answer with precision, trade-offs, and evidence without hiding behind the framework.',
    },
    vueBridge: {
      es: 'La experiencia Vue es evidencia válida si distingues principios transferibles de mecanismos específicos de React.',
      en: 'Vue experience is valid evidence when you separate transferable principles from React-specific mechanisms.',
    },
    framework: 'technical',
    prompts: [
      {
        id: 'boss-open-state',
        kind: 'open',
        question: {
          es: 'Compara estado local, contexto y store externo para una aplicación de cumplimiento regulatorio.',
          en: 'Compare local state, context, and an external store for a regulatory compliance application.',
        },
        followUps: [followTradeoff, followEvidence],
      },
      {
        id: 'boss-forensics-memo',
        kind: 'forensics',
        code: `const visible = useMemo(() => filter(rows, query), [rows])
const onSelect = useCallback(() => save(selectedId), [])
return <Grid rows={visible} onSelect={onSelect} />`,
        question: {
          es: 'Prioriza los riesgos: corrección, rendimiento e identidad. No propongas cambios hasta justificar el orden.',
          en: 'Prioritize the risks: correctness, performance, and identity. Do not propose changes before justifying the order.',
        },
        followUps: [followEvidence],
      },
      {
        id: 'boss-choice-transition',
        kind: 'choice',
        question: {
          es: 'Una búsqueda filtra lentamente mientras el input debe seguir fluido. ¿Cuál es el uso más defendible de una transición?',
          en: 'A search filters slowly while the input must remain fluid. What is the most defensible use of a transition?',
        },
        options: [
          { es: 'Marcar la actualización del propio input como no urgente', en: 'Mark the input value update itself as non-urgent work' },
          { es: 'Mantener el input urgente y diferir el resultado costoso', en: 'Keep input updates urgent and defer the costly results' },
          { es: 'Sustituir la optimización del cálculo por una transición', en: 'Replace computation optimization with a transition' },
          { es: 'Ejecutar la petición de red dentro de una transición larga', en: 'Run the network request inside one long transition' },
        ],
        followUps: [followTradeoff, followEvidence],
      },
    ],
  },
  {
    id: 'story_forge',
    kind: 'level',
    minutes: 45,
    title: { es: 'Forja de evidencia', en: 'Evidence forge' },
    objective: {
      es: 'Convertir experiencia real en cuatro historias profundas y dos ejemplos relámpago defendibles.',
      en: 'Turn real experience into four deep stories and two defensible lightning examples.',
    },
    vueBridge: {
      es: 'Cuenta la decisión y el impacto; menciona Vue solo donde el mecanismo técnico ayude a entender el criterio.',
      en: 'Tell the decision and impact; mention Vue only where the technical mechanism clarifies your judgment.',
    },
    framework: 'experience',
    prompts: [
      {
        id: 'story-open-ownership',
        kind: 'open',
        question: {
          es: 'Cuenta una ocasión donde heredaste código riesgoso, redujiste incertidumbre y asumiste ownership del resultado.',
          en: 'Tell me about a time you inherited risky code, reduced uncertainty, and owned the outcome.',
        },
        followUps: [followTradeoff, followEvidence],
      },
      {
        id: 'story-ranking',
        kind: 'ranking',
        question: {
          es: 'Ordena la narrativa para que una historia técnica muestre juicio y no sea una cronología larga.',
          en: 'Order the narrative so a technical story demonstrates judgment instead of becoming a long chronology.',
        },
        options: [
          { es: 'Contexto y riesgo concreto', en: 'Context and concrete risk' },
          { es: 'Decisión y alternativa descartada', en: 'Decision and rejected alternative' },
          { es: 'Resultado con evidencia', en: 'Result supported by evidence' },
          { es: 'Aprendizaje transferible', en: 'Transferable learning' },
        ],
        followUps: [
          { es: '¿Qué detalle eliminarías para responder en 90 segundos?', en: 'Which detail would you remove to answer in 90 seconds?' },
        ],
      },
      {
        id: 'story-choice-ai',
        kind: 'choice',
        question: {
          es: 'Te preguntan por uso de AI al programar. ¿Qué enfoque protege mejor una señal senior?',
          en: 'You are asked about AI-assisted coding. Which approach best preserves a senior signal?',
        },
        options: [
          { es: 'Evitar el tema y enfocar toda respuesta en trabajo manual', en: 'Avoid the topic and frame every answer as manual work' },
          { es: 'Afirmar que una revisión visual consistente sustituye comprender el código', en: 'Claim that consistent visual review replaces understanding the generated code' },
          { es: 'Explicar límites, verificación y ownership del resultado', en: 'Explain limits, verification, and ownership of outcomes' },
          { es: 'Presentar velocidad de generación como métrica suficiente', en: 'Present generation speed as a sufficient quality metric' },
        ],
        followUps: [followEvidence, followTradeoff],
      },
    ],
  },
  {
    id: 'challenge',
    kind: 'level',
    minutes: 25,
    title: { es: 'Prólogo de live coding', en: 'Live-coding prologue' },
    objective: {
      es: 'Practicar clarificación, solución incremental, casos borde y comunicación mientras codificas.',
      en: 'Practice clarification, incremental solutions, edge cases, and communication while coding.',
    },
    vueBridge: {
      es: 'Tu ventaja no es recordar APIs: es modelar datos, mantener estados explícitos y verificar comportamiento.',
      en: 'Your advantage is not API recall: it is modeling data, keeping states explicit, and verifying behavior.',
    },
    framework: 'hypothetical',
    prompts: [
      {
        id: 'challenge-open-autocomplete',
        kind: 'open',
        question: {
          es: 'Implementa mentalmente un autocomplete remoto. Expón preguntas, estados, carreras, errores y estrategia de prueba.',
          en: 'Mentally implement a remote autocomplete. State questions, states, races, errors, and test strategy.',
        },
        followUps: [
          { es: '¿Qué dejarías fuera en una prueba de 45 minutos?', en: 'What would you leave out in a 45-minute exercise?' },
          followEvidence,
        ],
      },
      {
        id: 'challenge-forensics-reducer',
        kind: 'forensics',
        code: `function reducer(state, action) {
  if (action.type === 'saved') {
    state.items.push(action.item)
    return state
  }
  return state
}`,
        question: {
          es: 'Explica el síntoma observable, la causa por identidad y la corrección mínima antes de refactorizar.',
          en: 'Explain the observable symptom, the identity cause, and the smallest fix before refactoring.',
        },
        followUps: [followTradeoff],
      },
      {
        id: 'challenge-choice-loading',
        kind: 'choice',
        question: {
          es: 'Dos guardados simultáneos comparten un boolean loading. ¿Qué modelo resiste mejor concurrencia y errores parciales?',
          en: 'Two simultaneous saves share one loading boolean. Which model best handles concurrency and partial errors?',
        },
        options: [
          { es: 'Registrar operaciones por id con su estado y su error', en: 'Track operations by id with their own status and error' },
          { es: 'Conservar un boolean y bloquear cualquier segunda acción', en: 'Keep one boolean and block every second action' },
          { es: 'Agregar un timeout fijo antes de limpiar el indicador', en: 'Add a fixed timeout before clearing the indicator' },
          { es: 'Mover el boolean a un contexto compartido sin cambiar su semántica', en: 'Move the boolean into shared context without changing its underlying semantics' },
        ],
        followUps: [followTradeoff, followEvidence],
      },
    ],
  },
  {
    id: 'final_boss',
    kind: 'boss',
    minutes: 30,
    title: { es: 'Boss final: entrevista', en: 'Final boss: interview' },
    objective: {
      es: 'Simular 20–30 minutos bilingües con follow-ups adversariales y respuestas sin ayuda.',
      en: 'Simulate 20–30 bilingual minutes with adversarial follow-ups and unaided answers.',
    },
    vueBridge: {
      es: 'Habla desde principios y evidencia: reconoce la oxidación de React, demuestra transferencia y nunca inventes experiencia.',
      en: 'Speak from principles and evidence: acknowledge React rust, prove transfer, and never invent experience.',
    },
    framework: 'hypothetical',
    prompts: [
      {
        id: 'final-open-intro',
        kind: 'open',
        question: {
          es: 'Preséntate en 90 segundos para este rol y conecta Vue reciente, React previo y tu trabajo actual con AI.',
          en: 'Introduce yourself in 90 seconds for this role, connecting recent Vue, prior React, and current AI-assisted work.',
        },
        followUps: [
          { es: '¿Por qué deberíamos confiar en tu React hoy?', en: 'Why should we trust your React skills today?' },
          followEvidence,
        ],
      },
      {
        id: 'final-forensics-system',
        kind: 'forensics',
        code: `useEffect(() => {
  socket.on('update', updateRows)
  return () => socket.off('update', updateRows)
}, [socket, updateRows])`,
        question: {
          es: 'No asumas que está mal. Enumera condiciones de corrección, riesgos de identidad y cómo obtendrías evidencia.',
          en: 'Do not assume it is wrong. List correctness conditions, identity risks, and how you would gather evidence.',
        },
        followUps: [followTradeoff],
      },
      {
        id: 'final-choice-production',
        kind: 'choice',
        question: {
          es: 'Tras un release sube la latencia percibida sin error claro. ¿Cuál es la primera respuesta más senior?',
          en: 'After a release, perceived latency rises without a clear error. What is the most senior first response?',
        },
        options: [
          { es: 'Reescribir el componente lento usando un patrón distinto', en: 'Rewrite the slow component using a different pattern' },
          { es: 'Agregar memoización a cada componente del recorrido', en: 'Add memoization to every component in the journey' },
          { es: 'Revertir siempre antes de revisar alcance e impacto', en: 'Always revert before checking scope and impact' },
          { es: 'Definir impacto, comparar señales y contener el riesgo', en: 'Define impact, compare signals, and contain the risk' },
        ],
        followUps: [followEvidence, followTradeoff],
      },
    ],
  },
]

export const curriculum: Mission[] = MISSION_SEQUENCE.map((missionId) => {
  const mission = missionCatalog.find((candidate) => candidate.id === missionId)
  if (!mission) throw new Error(`Missing curriculum mission: ${missionId}`)
  return mission
})

export function getMission(missionId: MissionId): Mission {
  const mission = curriculum.find((candidate) => candidate.id === missionId)
  if (!mission) throw new Error(`Unknown mission: ${missionId}`)
  return mission
}
