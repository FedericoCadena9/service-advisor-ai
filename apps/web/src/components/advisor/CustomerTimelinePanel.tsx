import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import type {
  AppointmentResponse,
  SmsDeliveryResponse,
  SmsPreviewResponse,
} from "../../api/generated/types.gen";

export type TimelineActions = {
  onReserve: (quoteId: string) => Promise<AppointmentResponse>;
  onPreview: (quoteId: string) => Promise<SmsPreviewResponse>;
  onSend: (quoteId: string, text: string) => Promise<SmsDeliveryResponse>;
  onAdvance: (deliveryId: string) => Promise<SmsDeliveryResponse>;
};

export function CustomerTimelinePanel({
  quoteId,
  onReserve,
  onPreview,
  onSend,
  onAdvance,
}: TimelineActions & { quoteId: string | null }) {
  const [appointment, setAppointment] = useState<AppointmentResponse>();
  const [preview, setPreview] = useState<SmsPreviewResponse>();
  const [text, setText] = useState("");
  const [delivery, setDelivery] = useState<SmsDeliveryResponse>();
  const [error, setError] = useState("");

  if (!quoteId)
    return (
      <p>Approve a quote to reserve an appointment and prepare a message.</p>
    );

  /** A refusal and an outage need different words: one is the Advisor's to fix, the other is not. */
  async function run(
    action: () => Promise<void>,
    unavailable: string,
    refused?: string,
  ) {
    try {
      await action();
      setError("");
    } catch (failure) {
      const status = (failure as { status?: number }).status;
      const isRefusal =
        typeof status === "number" && status >= 400 && status < 500;
      setError(isRefusal && refused ? refused : unavailable);
    }
  }

  return (
    <div className="space-y-3">
      <p className="text-sm text-muted-foreground">
        Messages stay simulated and refuse copy that invents a price or exceeds
        the approved quote.
      </p>
      <Button
        onClick={() =>
          void run(
            async () => {
              setAppointment(await onReserve(quoteId));
            },
            "The appointment could not be reserved",
            "The appointment is no longer available",
          )
        }
      >
        Reserve appointment
      </Button>
      {appointment && (
        <p className="rounded-lg border border-emerald-400/35 bg-emerald-50 p-3 text-sm text-emerald-800">{`Simulated reservation ${appointment.bay_slot_id} at ${appointment.starts_at}`}</p>
      )}
      <Button
        className="mt-2"
        onClick={() =>
          void run(async () => {
            const next = await onPreview(quoteId);
            setPreview(next);
            setText(next.text);
          }, "The message preview is unavailable")
        }
      >
        Preview message
      </Button>
      {preview && (
        <div className="space-y-3 rounded-lg border border-border bg-muted/40 p-4">
          <label className="block text-sm font-medium" htmlFor="sms-text">
            Message to the customer
          </label>
          <Textarea
            id="sms-text"
            value={text}
            onChange={(event) => setText(event.target.value)}
          />
          <p className="text-xs text-muted-foreground">{`${preview.segments} segment(s) · ${preview.priorities.length} priorities`}</p>
          <Button
            onClick={() =>
              void run(
                async () => {
                  setDelivery(await onSend(quoteId, text));
                },
                "The message could not be sent right now",
                "The message was rejected because it is not supported by the approved quote",
              )
            }
          >
            Enqueue message
          </Button>
        </div>
      )}
      {delivery && (
        <div className="space-y-2 rounded-lg border border-primary/20 bg-primary/7 p-4">
          <p
            role="status"
            className="font-medium text-primary"
          >{`Simulated delivery: ${delivery.state}`}</p>
          <p className="text-sm text-muted-foreground">{`Approved by ${delivery.approver_role} · ${delivery.rule_version} page ${delivery.citation_page}`}</p>
          <Button
            onClick={() =>
              void run(async () => {
                setDelivery(await onAdvance(delivery.id));
              }, "The timeline could not be advanced")
            }
          >
            Advance timeline
          </Button>
        </div>
      )}
      {error && (
        <p className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </p>
      )}
    </div>
  );
}
