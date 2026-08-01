import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

import { expect, test } from 'vitest'

const read = (relative: string) =>
  readFileSync(fileURLToPath(new URL(relative, import.meta.url)), 'utf8')

/**
 * The CSS pipeline fails silently: without the plugin the build still succeeds and still
 * emits a stylesheet, but it carries theme variables and fonts only — every utility class
 * the components use is missing, and the app ships unstyled.
 */
test('vite registers the Tailwind plugin so utility classes are generated', () => {
  const config = read('../../vite.config.ts')

  expect(config).toContain('@tailwindcss/vite')
  expect(config).toMatch(/plugins:\s*\[[^\]]*tailwindcss\(\)/s)
})

test('the stylesheet still imports Tailwind', () => {
  expect(read('../index.css')).toContain('@import "tailwindcss"')
})
