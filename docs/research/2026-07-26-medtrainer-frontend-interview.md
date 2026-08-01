# MedTrainer: preparación para Technical Knowledge Interview Frontend/React

Fecha de investigación: 2026-07-26.

## Conclusión

La ronda de 20–30 minutos parece diseñada para validar verbalmente que la experiencia del candidato coincide con el nivel esperado antes del live coding. Dado que el reto técnico viene en una etapa separada, la mejor predicción es una combinación de: presentación y recorrido por experiencia, preguntas de amplitud sobre el stack, profundización en una decisión técnica o incidente, y algunos minutos para preguntas del candidato. Esto es una inferencia basada en el proceso comunicado y la duración; MedTrainer no publica un guion oficial de la entrevista.

## Señales verificables de la vacante

La [vacante exacta publicada por MedTrainer en LinkedIn](https://mx.linkedin.com/jobs/view/software-engineer-frontend-react-at-medtrainer-4421975282) pide:

- Más de cinco años en software y al menos tres enfocados en React.
- React, TypeScript y arquitectura SPA.
- TanStack Query para estado de servidor; Redux o Context para estado global de cliente.
- Jest y Cypress.
- Inspección de Figma, componentes reutilizables y Design Systems como fuente única de verdad.
- Git, Jira, Agile/Scrum y prácticas del ciclo de entrega.
- Herramientas de desarrollo asistido por IA y MCP.
- Conocimiento básico de Symfony como ventaja.
- Capacidad para tomar decisiones de arquitectura, dividir proyectos grandes, revisar código, diagnosticar incidentes y colaborar con Product y Design.

La página oficial de [Careers de MedTrainer](https://medtrainer.com/company/careers/) enfatiza resultados, accountability/ownership, mejora continua y colaboración. La página oficial de [seguridad](https://medtrainer.com/security/) afirma que los cambios pasan por revisión de pares, revisiones automáticas, pruebas manuales y automatizadas, y ambientes separados. El [producto](https://medtrainer.com/) integra learning, credentialing y compliance para organizaciones de salud; la confiabilidad, claridad y seguridad tienen peso real en este dominio.

## Evidencia anecdótica

Los reportes anónimos de [Glassdoor](https://www.glassdoor.co.uk/Interview/MedTrainer-Interview-Questions-E2694244.htm) son pocos y pueden estar desactualizados. Un candidato de software en Querétaro reportó entrevista en inglés aunque el idioma no fuera requisito y preguntas básicas sobre `git commit` y `git push`; otro reportó una pregunta sobre Docker. Sirven para justificar un repaso relámpago de herramientas y practicar en inglés, no para predecir preguntas exactas.

## Preguntas de mayor probabilidad

1. Describe una funcionalidad React que hayas llevado de requisito a producción.
2. ¿Qué provoca un render y cómo diagnosticas renders costosos?
3. ¿Cuándo usarías `useEffect` y cuáles son sus errores comunes?
4. ¿Cómo decides entre estado local, Context, Redux y TanStack Query?
5. ¿Cómo manejas caché, invalidación, errores, reintentos y actualizaciones optimistas?
6. ¿Cómo usas TypeScript para modelar estados y prevenir estados imposibles?
7. ¿Cómo estructuras una SPA grande y componentes reutilizables?
8. ¿Qué pruebas pondrías en Jest y cuáles en Cypress?
9. Describe un bug difícil o incidente de producción: diagnóstico, causa y prevención.
10. ¿Cómo optimizas rendimiento sin optimizar prematuramente?
11. ¿Cómo integras APIs y representas loading, empty, error y permisos?
12. ¿Cómo conviertes un diseño de Figma en un componente de Design System?
13. ¿Cómo haces code review y cómo decides si conviene refactorizar?
14. ¿Cómo usas IA/MCP sin comprometer datos, seguridad o calidad?
15. Diferencias básicas entre commit/push, merge/rebase, pruebas unitarias/E2E y contenedor/imagen.

Las respuestas fuertes explican contexto, decisión, alternativas, trade-off, resultado medible y aprendizaje. Si falta experiencia directa, conviene declararlo y razonar desde conocimientos adyacentes en vez de improvisar una experiencia.

## Repaso técnico prioritario

- React: flujo de datos, composición, props/state, render/commit, hooks, closures obsoletos, dependencias y cleanup, keys, formularios, error boundaries y accesibilidad. La documentación de React recomienda mantener el estado mínimo y derivar lo calculable durante el render ([Thinking in React](https://react.dev/learn/thinking-in-react)); los Effects son para sincronizar con sistemas externos, no para estado derivado o eventos ([You Might Not Need an Effect](https://react.dev/learn/you-might-not-need-an-effect)).
- Estado: propiedad, alcance y frecuencia de actualización. TanStack Query existe para obtener, cachear, sincronizar y actualizar estado de servidor, que puede quedar desactualizado fuera del cliente ([documentación oficial](https://tanstack.com/query/latest/docs/framework/react/overview)). Redux/Context no deben duplicar ese caché sin una razón clara.
- TypeScript/JavaScript: unions discriminadas, narrowing, genéricos, `unknown` frente a `any`, inmutabilidad, closures, promesas, `async/await`, event loop y debounce/throttle. TypeScript define narrowing como el refinamiento de tipos mediante guards y análisis de flujo ([Handbook](https://www.typescriptlang.org/docs/handbook/2/narrowing.html)).
- Calidad: unitarias para lógica pura, integración de componentes para comportamiento y Cypress para journeys críticos. Saber qué mockear, cómo evitar tests frágiles y cómo cubrir fallas.
- Web/API: HTTP, códigos de estado, CORS, autenticación/autorización, cancelación y race conditions, loading/empty/error/retry.
- Rendimiento: medir primero; distinguir red, CPU, renders y tamaño de bundle; después aplicar límites de componentes, memoización justificada, virtualización, code splitting o caché y volver a medir.

## Plan de un día

1. 30 min: preparar introducción de 60–90 segundos y cuatro historias técnicas.
2. 50 min: React, efectos, renders y arquitectura de componentes.
3. 35 min: estado local/Context/Redux/TanStack Query.
4. 30 min: TypeScript y fundamentos JavaScript.
5. 35 min: testing, APIs, rendimiento y debugging.
6. 20 min: Git, Docker, Agile/Jira, MCP y Symfony a nivel conceptual.
7. 40 min: simulacro cronometrado en inglés, grabado y con preguntas de seguimiento.
8. 20 min: corregir solamente los tres huecos más visibles y repetir respuestas.

Antes de la entrevista: repaso ligero de 30–40 minutos, sin estudiar temas nuevos; comprobar audio, cámara y conexión; tener abiertas la vacante y cuatro palabras clave por historia.

## Preguntas útiles para el entrevistador

- What frontend decision would you expect this person to own in the first 90 days?
- Where is the biggest frontend complexity today: legacy migration, state management, design systems, testing, or performance?
- How does the team measure frontend quality and product impact?

## Límites

No se encontró un banco oficial de preguntas, nombre del entrevistador ni confirmación pública de que esta ronda incluya código. Las preguntas anteriores son predicciones razonadas desde la vacante, el correo recibido y fuentes técnicas oficiales.
