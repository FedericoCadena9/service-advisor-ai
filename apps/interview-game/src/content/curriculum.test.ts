import { describe, expect, it } from 'vitest'

import { MISSION_SEQUENCE } from '../domain/game'
import { curriculum } from './curriculum'

describe('interview curriculum', () => {
  it('covers the complete eight-stage journey in order', () => {
    expect(curriculum.map((mission) => mission.id)).toEqual(MISSION_SEQUENCE)
    expect(curriculum.filter((mission) => mission.kind === 'boss')).toHaveLength(2)
    expect(curriculum.every((mission) => mission.prompts.length >= 3)).toBe(true)
  })

  it('localizes every user-facing question and mission description', () => {
    for (const mission of curriculum) {
      expect(mission.title.es).not.toHaveLength(0)
      expect(mission.title.en).not.toHaveLength(0)
      expect(mission.objective.es).not.toHaveLength(0)
      expect(mission.objective.en).not.toHaveLength(0)
      expect(mission.vueBridge.es).not.toHaveLength(0)
      expect(mission.vueBridge.en).not.toHaveLength(0)

      for (const prompt of mission.prompts) {
        expect(prompt.question.es).not.toHaveLength(0)
        expect(prompt.question.en).not.toHaveLength(0)
        for (const followUp of prompt.followUps) {
          expect(followUp.es).not.toHaveLength(0)
          expect(followUp.en).not.toHaveLength(0)
        }
      }
    }
  })

  it('mixes open, ranking, code-forensics, and competing-explanation prompts', () => {
    const kinds = new Set(
      curriculum.flatMap((mission) => mission.prompts.map((prompt) => prompt.kind)),
    )

    expect(kinds).toEqual(new Set(['open', 'ranking', 'forensics', 'choice']))
  })

  it('does not ship answer keys and keeps option detail comparable', () => {
    const choices = curriculum
      .flatMap((mission) => mission.prompts)
      .filter((prompt) => prompt.kind === 'choice')
    for (const language of ['es', 'en'] as const) {
      for (const prompt of choices) {
        expect('correctIndex' in prompt).toBe(false)
        const lengths = prompt.options.map((option) => option[language].length)
        expect(Math.max(...lengths) / Math.min(...lengths)).toBeLessThan(1.75)
      }
    }

    for (const prompt of curriculum.flatMap((mission) => mission.prompts)) {
      expect('idealOrder' in prompt).toBe(false)
    }
  })
})
