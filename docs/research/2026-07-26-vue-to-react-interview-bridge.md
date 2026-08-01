# Puente Vue 3 → React para entrevista técnica

Fecha: 2026-07-26. Fuentes: documentación oficial de Vue, React, Pinia, Redux y TanStack Query.

## La diferencia mental principal

Vue 3 usa reactividad mutable y granular mediante `ref` y proxies. Con Composition API, `setup` se ejecuta una vez y Vue rastrea automáticamente las dependencias usadas por `computed` y watchers. En React, la función del componente se vuelve a ejecutar durante cada render; cada render recibe un snapshot de props y state, y los Hooks pueden capturar valores de ese render. Las dependencias de Effects y memoización se declaran explícitamente. La propia documentación de Vue explica estas diferencias en su [comparación con React Hooks](https://vuejs.org/guide/extras/composition-api-faq.html#comparison-with-react-hooks); React explica el modelo de snapshot en [State as a Snapshot](https://react.dev/learn/state-as-a-snapshot).

## Mapa de traducción

| Vue 3 | React | Diferencia que debe explicarse |
|---|---|---|
| SFC con `<script setup>` y template | Function component con JSX | La función React se ejecuta en cada render; `setup` normalmente una vez por instancia. |
| `ref()` / `reactive()` | `useState()` / `useReducer()` | Vue permite mutación reactiva mediante refs/proxies; React trata el estado como snapshot y debe reemplazarse mediante setters. |
| `computed()` | Valor derivado durante render; `useMemo()` si es costoso | `computed` rastrea y cachea automáticamente; `useMemo` es una optimización con dependencias explícitas, no una necesidad semántica. |
| `watch()` / `watchEffect()` | `useEffect()` aproximadamente | React Effects sincronizan con sistemas externos después del commit; no deben usarse para estado derivado ni para una acción directa del usuario. |
| `onMounted()` / `onUnmounted()` | Setup y cleanup de `useEffect()` | Es un puente útil, pero React recomienda pensar en sincronización, no imitar lifecycle methods. |
| `defineProps()` | Argumento `props` | Ambos usan flujo de datos de padre a hijo y props readonly conceptualmente. |
| `defineEmits()` | Callback prop: `onSave(value)` | React no tiene un sistema `emit`; el padre entrega una función al hijo. |
| `v-model` | Input controlado: `value` + `onChange` | En ambos, el estado de JavaScript es la fuente de verdad; React hace el contrato explícito. |
| Slots | `children` o render props | Los slots nombrados suelen traducirse a props que contienen elementos o funciones. |
| Composable `useX()` | Custom Hook `useX()` | Hooks React dependen del orden de llamada y no pueden invocarse condicionalmente. |
| `provide` / `inject` | Context | Context transporta un valor por el árbol; no sustituye automáticamente un store. |
| Pinia | Redux Toolkit aproximadamente | Mismo problema general de client state, distinto modelo: Redux enfatiza events/actions, reducers y actualizaciones inmutables. |
| TanStack Vue Query | TanStack React Query | El modelo de server state, query keys, caché, invalidación y mutations se transfiere casi directamente. |
| Template ref | `useRef()` | Para referencias DOM o valores mutables que no deben provocar un render. No confundir con `ref()` reactivo de Vue. |
| `v-if`, `v-for` | Condicionales JS y `array.map()` | React expresa control de flujo dentro de JavaScript/JSX; las keys estables siguen siendo importantes. |

Fuentes específicas: [Vue Reactivity Fundamentals](https://vuejs.org/guide/essentials/reactivity-fundamentals.html), [Vue Computed](https://vuejs.org/guide/essentials/computed.html), [Vue Watchers](https://vuejs.org/guide/essentials/watchers.html), [React Render and Commit](https://react.dev/learn/render-and-commit), [React Effects](https://react.dev/learn/synchronizing-with-effects), [React useMemo](https://react.dev/reference/react/useMemo) y [Custom Hooks](https://react.dev/learn/reusing-logic-with-custom-hooks).

## Trampas importantes

1. `ref()` de Vue no equivale a `useRef()`; para estado visible suele corresponder a `useState()`.
2. `computed()` no debe traducirse automáticamente a `useMemo()`: primero calcular directamente durante el render.
3. `watch()` no debe traducirse automáticamente a `useEffect()`: eventos van en handlers y valores derivados en render.
4. Mutar un objeto de state directamente es contrario al modelo de React.
5. Una función creada dentro del componente tiene una identidad nueva en cada render; normalmente no es un problema. `useCallback` se usa sólo con una razón concreta.
6. Effects y callbacks pueden capturar un snapshot anterior (stale closure) si sus dependencias son incorrectas.
7. Una actualización de state solicita render; render calcula JSX de forma pura; commit aplica al DOM sólo los cambios necesarios.
8. TanStack Query debe encargarse del estado remoto; no copiar sus resultados a Redux sin una necesidad clara.

## Estrategia de entrevista

Para cada concepto, ensayar una respuesta de cuatro pasos:

1. Cómo resolvías el problema en Vue.
2. Cómo se expresa en React.
3. Qué diferencia semántica impide considerarlos idénticos.
4. Un caso real y su trade-off.

Ejemplo: “En Vue usaría `computed` para una lista filtrada. En React normalmente la calculo durante render a partir de props y state. Sólo agregaría `useMemo` si la medición demuestra que el cálculo es costoso o si necesito identidad estable para un hijo memoizado. No usaría un Effect para copiar esa lista a otro state.”

## Ejercicio mínimo sin generación automática

Traducir y explicar seis casos: contador, lista filtrada, formulario controlado, comunicación padre-hijo, fetch cancelable y consulta con TanStack Query. Primero resolverlos sin IA; después usar IA como revisor de semántica, dependencias, casos de error y tests. Esto recupera fluidez real para el live coding sin renunciar al flujo de desarrollo asistido.
