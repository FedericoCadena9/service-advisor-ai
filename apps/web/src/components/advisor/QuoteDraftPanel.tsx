import { useState } from 'react'

import { Button } from '@/components/ui/button'
import type { QuoteDraftResponse } from '../../api/generated/types.gen'

const DRAFT_BUNDLE = ['HONDA-A1', 'HONDA-TIRE-ROTATION', 'HONDA-CABIN-FILTER']

export function QuoteDraftPanel({ onDraft }: { onDraft: (serviceCodes: string[]) => Promise<QuoteDraftResponse> }) {
  const [draft, setDraft] = useState<QuoteDraftResponse>()
  const [error, setError] = useState('')

  async function requestDraft() {
    try {
      setDraft(await onDraft(DRAFT_BUNDLE))
      setError('')
    } catch {
      setError('Quote draft unavailable')
    }
  }

  return (
    <div>
      <Button onClick={() => void requestDraft()}>Draft quote</Button>
      {error && <p role="alert">{error}</p>}
      {draft && (
        <table aria-label="Quote draft lines" className="mt-3 w-full text-sm">
          <thead>
            <tr>
              <th scope="col">Service</th>
              <th scope="col">Labor MXN</th>
              <th scope="col">Parts MXN</th>
              <th scope="col">IVA MXN</th>
              <th scope="col">Total MXN</th>
              <th scope="col">Minutes</th>
              <th scope="col">Fitment</th>
              <th scope="col">Availability</th>
            </tr>
          </thead>
          <tbody>
            {draft.lines.map((line) => (
              <tr key={line.service_code}>
                <td>{line.service_code}</td>
                <td>{line.labor_mxn}</td>
                <td>{line.parts_mxn}</td>
                <td>{line.iva_mxn}</td>
                <td>{line.total_mxn}</td>
                <td>{line.duration_minutes}</td>
                <td>{line.fitment}</td>
                <td>{line.available ? 'Available' : line.unavailable_reason}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {draft && (
        <p className="mt-2">
          {`Subtotal ${draft.subtotal_mxn} + IVA ${draft.iva_mxn} = ${draft.total_mxn} MXN · ${draft.duration_minutes} min · ${draft.bay_slot_id ?? 'no bay slot'}`}
        </p>
      )}
      {draft?.warnings.map((warning) => (
        <p key={warning} role="status">
          {warning}
        </p>
      ))}
    </div>
  )
}
