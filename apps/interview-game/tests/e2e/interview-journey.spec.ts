import { expect, test } from '@playwright/test'

test.beforeEach(async ({ context, page }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write'], {
    origin: 'http://127.0.0.1:4174',
  })
  await page.goto('/')
  await page.evaluate(() => window.localStorage.clear())
  await page.reload()
})

test('complete calibration and preserve progress @critical', async ({ page }) => {
  await page.getByRole('button', { name: 'Modo Coach' }).click()
  await page.getByRole('button', { name: 'Preparar respuesta' }).click()
  await expect(page.getByRole('region', { name: 'Despacho al chat' })).toBeVisible()

  await page.getByRole('button', { name: 'Copiar handoff completo' }).click()
  await page.getByRole('button', { name: 'Importar veredicto' }).click()
  await page.getByLabel('Resultado JSON de Codex').fill(JSON.stringify({
    scores: {
      technicalAccuracy: 82,
      tradeoffs: 82,
      ownership: 82,
      evidence: 82,
      problemSolving: 82,
      bilingualCommunication: 82,
    },
    followUpCount: 2,
    hintUsed: false,
    unassistedTransfer: true,
    evidenceSummary: 'Defendió decisión, alternativa y validación.',
    attemptClosed: true,
  }))
  await page.getByRole('button', { name: 'Registrar evaluación' }).click()

  await expect(page.getByText(/Misión superada · 82\/100/)).toBeVisible()
  await expect(page.getByRole('button', { name: /Puente de mando.*disponible/ })).toBeEnabled()
  await expect(page.getByText(/1\/8.*misiones superadas/)).toBeVisible()

  await page.reload()

  await expect(page.getByRole('button', { name: /Puerta de calibración.*superada.*82/ })).toBeEnabled()
  await expect(page.getByText(/1\/8.*misiones superadas/)).toBeVisible()
})

test('forge and persist a defensible story', async ({ page }) => {
  await page.getByRole('button', { name: 'Story Forge' }).click()
  const fields = {
    'Título de la historia': 'Migración sin regresiones',
    Contexto: 'Release cercano con un equipo pequeño.',
    Problema: 'Estado duplicado causaba inconsistencias.',
    Decisión: 'Definí una sola fuente de verdad.',
    'Alternativa descartada': 'Reescribir el módulo completo.',
    Resultado: 'El rollout no produjo regresiones.',
    Aprendizaje: 'Migrar por comportamiento redujo el riesgo.',
  }
  for (const [label, value] of Object.entries(fields)) {
    await page.getByLabel(label, { exact: true }).fill(value)
  }
  await page.getByRole('button', { name: 'Forjar historia' }).click()
  await expect(page.getByRole('article', { name: 'Migración sin regresiones' })).toBeVisible()

  await page.reload()
  await page.getByRole('button', { name: 'Story Forge' }).click()
  await expect(page.getByRole('article', { name: 'Migración sin regresiones' })).toBeVisible()
})

test('exposes the recovery-first schedule', async ({ page }) => {
  await page.getByRole('button', { name: 'Plan 8h' }).click()

  await expect(page.getByRole('heading', { name: 'Hoy · 240 minutos' })).toBeVisible()
  await expect(page.getByRole('note', { name: '11:10 · Stop obligatorio' })).toBeVisible()
  await expect(page.getByText('12:30', { exact: true })).toBeVisible()
})
