import { describe, expect, it, vi } from 'vitest'

vi.mock('./generated/client.gen', () => ({
  client: {
    setConfig: vi.fn(),
  },
}))

const getHealth = vi.fn()

vi.mock('./generated/sdk.gen', () => ({
  getHealthHealthGet: getHealth,
}))

describe('fetchHealth', () => {
  it('returns the typed health response when the generated client succeeds', async () => {
    getHealth.mockResolvedValue({ data: { status: 'healthy' }, error: undefined })

    const { fetchHealth } = await import('./health')

    await expect(fetchHealth()).resolves.toEqual({ status: 'healthy' })
  })

  it('throws when the generated client returns an error', async () => {
    getHealth.mockResolvedValue({ data: undefined, error: { detail: 'boom' } })

    const { fetchHealth } = await import('./health')

    await expect(fetchHealth()).rejects.toThrow('Health request failed')
  })
})
