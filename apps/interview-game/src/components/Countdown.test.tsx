import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { Countdown } from './Countdown'

afterEach(() => vi.useRealTimers())

describe('Countdown', () => {
  it('restarts from the mission duration after reaching zero', () => {
    vi.useFakeTimers()
    render(<Countdown minutes={1} language="es" />)

    fireEvent.click(screen.getByRole('button', { name: 'Iniciar reloj' }))
    act(() => vi.advanceTimersByTime(60_000))
    expect(screen.getByText('00:00')).toBeVisible()

    fireEvent.click(screen.getByRole('button', { name: 'Iniciar reloj' }))

    expect(screen.getByText('01:00')).toBeVisible()
    expect(screen.getByRole('button', { name: 'Pausar reloj' })).toBeVisible()
  })
})
