import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import App from './App'

const passingEvaluation = JSON.stringify({
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
})

describe('Seniority Quest', () => {
  it('renders the interview mission and Vue-to-React bridge', () => {
    render(<App />)

    expect(screen.getByRole('heading', { name: /seniority quest/i })).toBeVisible()
    expect(screen.getByText(/technical knowledge/i)).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Puerta de calibración' })).toBeVisible()
    expect(screen.getByText(/No busques equivalencias todavía/)).toBeVisible()
    expect(screen.getByRole('button', { name: 'Modo Coach' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
  })

  it('switches language and pressure mode through visible controls', () => {
    render(<App />)

    fireEvent.click(screen.getByRole('button', { name: 'English' }))
    fireEvent.click(screen.getByRole('button', { name: 'Interview mode' }))

    expect(screen.getByRole('heading', { name: 'Calibration gate' })).toBeVisible()
    expect(screen.getByText(/No cues or feedback until/)).toBeVisible()
    expect(screen.queryByText(/Do not chase equivalence yet/)).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Interview mode' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
  })

  it('prepares a chat prompt without revealing a model answer', () => {
    render(<App />)

    fireEvent.click(screen.getByRole('button', { name: 'Preparar respuesta' }))

    const dispatch = screen.getByRole('region', { name: 'Despacho al chat' })
    expect(within(dispatch).getByText(/Definición → cuándo/)).toBeVisible()
    expect(within(dispatch).getByText(/Copia y responde en este chat/)).toBeVisible()
    expect(within(dispatch).queryByText(/respuesta correcta/i)).not.toBeInTheDocument()
  })

  it('offers a manual handoff when clipboard access is denied', async () => {
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText: vi.fn().mockRejectedValue(new Error('denied')) },
    })
    render(<App />)

    fireEvent.click(screen.getByRole('button', { name: 'Preparar respuesta' }))
    fireEvent.click(screen.getByRole('button', { name: 'Copiar handoff completo' }))

    expect(await screen.findByLabelText('Handoff completo para copia manual')).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Ya lo copié manualmente' }))
    expect(screen.getByRole('button', { name: 'Importar veredicto' })).toBeEnabled()
  })

  it('records a passing rubric, updates mastery, and unlocks the next mission', async () => {
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText: vi.fn().mockResolvedValue(undefined) },
    })
    render(<App />)

    fireEvent.click(screen.getByRole('button', { name: 'Preparar respuesta' }))
    fireEvent.click(screen.getByRole('button', { name: 'Copiar handoff completo' }))
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Importar veredicto' })).toBeEnabled()
    })
    fireEvent.click(screen.getByRole('button', { name: 'Importar veredicto' }))
    fireEvent.change(screen.getByLabelText('Resultado JSON de Codex'), {
      target: { value: passingEvaluation },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Registrar evaluación' }))

    expect(screen.getByText(/Misión superada/, { selector: '[role="status"]' })).toBeVisible()
    expect(screen.getByRole('button', { name: /Puente de mando/ })).toBeEnabled()
    expect(screen.getByText('82%', { selector: '[data-mastery]' })).toBeVisible()
  })

  it('creates a reusable Story Forge card', () => {
    render(<App />)

    fireEvent.click(screen.getByRole('button', { name: 'Story Forge' }))
    const values: Record<string, string> = {
      'Título de la historia': 'Migración sin regresiones',
      Contexto: 'Equipo pequeño y release cercano.',
      Problema: 'Estado duplicado generaba inconsistencias.',
      Decisión: 'Definí una sola fuente de verdad.',
      'Alternativa descartada': 'Reescribir todo el módulo.',
      Resultado: 'Cero regresiones durante el rollout.',
      Aprendizaje: 'Migrar por comportamiento redujo el riesgo.',
      'Puente React': 'El mismo ownership se expresa con estado derivado y reducer.',
    }
    for (const [label, value] of Object.entries(values)) {
      fireEvent.change(screen.getByLabelText(label), { target: { value } })
    }
    fireEvent.click(screen.getByRole('button', { name: 'Forjar historia' }))

    expect(screen.getByRole('article', { name: 'Migración sin regresiones' })).toBeVisible()
    expect(screen.getByText('Cero regresiones durante el rollout.')).toBeVisible()
  })

  it('requires explicit confirmation before resetting progress', () => {
    render(<App />)

    fireEvent.click(screen.getByRole('button', { name: 'Reiniciar progreso' }))
    expect(screen.getByRole('button', { name: 'Confirmar reinicio' })).toBeVisible()
    expect(screen.getByRole('button', { name: 'Cancelar' })).toBeVisible()
  })

  it('shows the approved eight-hour study schedule and burnout guardrails', () => {
    render(<App />)

    fireEvent.click(screen.getByRole('button', { name: 'Plan 8h' }))

    expect(screen.getByRole('heading', { name: 'Hoy · 240 minutos' })).toBeVisible()
    expect(screen.getByText('08:45–09:15')).toBeVisible()
    expect(screen.getByRole('note', { name: /11:10.*stop obligatorio/i })).toBeVisible()
    expect(screen.getByText(/hasta 15 minutos/i)).toBeVisible()
  })
})
