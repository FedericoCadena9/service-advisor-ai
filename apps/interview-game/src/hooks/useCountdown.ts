import { useCallback, useEffect, useState } from 'react'

type StoredTimer = { seconds: number; running: boolean; updatedAt: number }

function timerKey(storageKey: string) {
  return `seniority-quest:timer:${storageKey}`
}

function loadTimer(initialSeconds: number, storageKey: string): StoredTimer {
  try {
    const raw = window.localStorage.getItem(timerKey(storageKey))
    if (!raw) return { seconds: initialSeconds, running: false, updatedAt: Date.now() }
    const stored = JSON.parse(raw) as StoredTimer
    if (!Number.isFinite(stored.seconds) || typeof stored.running !== 'boolean') {
      throw new Error('Invalid timer')
    }
    const elapsed = stored.running
      ? Math.floor(Math.max(0, Date.now() - stored.updatedAt) / 1_000)
      : 0
    const seconds = Math.max(0, stored.seconds - elapsed)
    return { seconds, running: stored.running && seconds > 0, updatedAt: Date.now() }
  } catch {
    return { seconds: initialSeconds, running: false, updatedAt: Date.now() }
  }
}

export function useCountdown(minutes: number, storageKey = 'default') {
  const initialSeconds = minutes * 60
  const initial = loadTimer(initialSeconds, storageKey)
  const [seconds, setSeconds] = useState(initial.seconds)
  const [running, setRunning] = useState(initial.running)

  useEffect(() => {
    const restored = loadTimer(initialSeconds, storageKey)
    setSeconds(restored.seconds)
    setRunning(restored.running)
  }, [initialSeconds, storageKey])

  useEffect(() => {
    window.localStorage.setItem(
      timerKey(storageKey),
      JSON.stringify({ seconds, running, updatedAt: Date.now() }),
    )
  }, [running, seconds, storageKey])

  useEffect(() => {
    if (!running) return
    const timer = window.setInterval(() => {
      setSeconds((current) => {
        if (current <= 1) {
          setRunning(false)
          return 0
        }
        return current - 1
      })
    }, 1_000)
    return () => window.clearInterval(timer)
  }, [running])

  const reset = useCallback(() => {
    setSeconds(initialSeconds)
    setRunning(false)
  }, [initialSeconds])

  return {
    seconds,
    running,
    start: () => {
      if (seconds <= 0) setSeconds(initialSeconds)
      setRunning(true)
    },
    pause: () => setRunning(false),
    reset,
  }
}
