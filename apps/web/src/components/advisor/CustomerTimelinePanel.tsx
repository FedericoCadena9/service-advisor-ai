import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import type {
  AppointmentResponse,
  SmsDeliveryResponse,
  SmsPreviewResponse,
} from '../../api/generated/types.gen'

export type TimelineActions = {
  onReserve: (quoteId: string) => Promise<AppointmentResponse>
  onPreview: (quoteId: string) => Promise<SmsPreviewResponse>
  onSend: (quoteId: string, text: string) => Promise<SmsDeliveryResponse>
  onAdvance: (deliveryId: string) => Promise<SmsDeliveryResponse>
}

export function CustomerTimelinePanel({
  quoteId,
  onReserve,
  onPreview,
  onSend,
  onAdvance,
}: TimelineActions & { quoteId: string | null }) {
  const [appointment, setAppointment] = useState<AppointmentResponse>()
  const [preview, setPreview] = useState<SmsPreviewResponse>()
  const [text, setText] = useState('')
  const [delivery, setDelivery] = useState<SmsDeliveryResponse>()
  const [error, setError] = useState('')

  if (!quoteId) return <p>Approve a quote to reserve an appointment and prepare a message.</p>

  async function run(action: () => Promise<void>) {
    try {
      await action()
      setError('')
    } catch {
      setError('The message was rejected because it is not supported by the approved quote')
    }
  }

  return (
    <div>
      <Button
        onClick={() =>
          void run(async () => {
            setAppointment(await onReserve(quoteId))
          })
        }
      >
        Reserve appointment
      </Button>
      {appointment && (
        <p>{`Simulated reservation ${appointment.bay_slot_id} at ${appointment.starts_at}`}</p>
      )}
      <Button
        className="mt-2"
        onClick={() =>
          void run(async () => {
            const next = await onPreview(quoteId)
            setPreview(next)
            setText(next.text)
          })
        }
      >
        Preview message
      </Button>
      {preview && (
        <div className="mt-2">
          <label htmlFor="sms-text">Message to the customer</label>
          <Textarea id="sms-text" value={text} onChange={(event) => setText(event.target.value)} />
          <p>{`${preview.segments} segment(s) · ${preview.priorities.length} priorities`}</p>
          <Button
            onClick={() =>
              void run(async () => {
                setDelivery(await onSend(quoteId, text))
              })
            }
          >
            Enqueue message
          </Button>
        </div>
      )}
      {delivery && (
        <div className="mt-2">
          <p role="status">{`Simulated delivery: ${delivery.state}`}</p>
          <p>{`Approved by ${delivery.approver_role} · ${delivery.rule_version} page ${delivery.citation_page}`}</p>
          <Button
            onClick={() =>
              void run(async () => {
                setDelivery(await onAdvance(delivery.id))
              })
            }
          >
            Advance timeline
          </Button>
        </div>
      )}
      {error && <p>{error}</p>}
    </div>
  )
}
