import { useState } from "react";

import { Button } from "@/components/ui/button";
import { failureMessage } from "../../api/failure";
import type { QuoteDraftResponse } from "../../api/generated/types.gen";

const DRAFT_BUNDLE = ["HONDA-A1", "HONDA-TIRE-ROTATION", "HONDA-CABIN-FILTER"];

export function QuoteDraftPanel({
  onDraft,
}: {
  onDraft: (serviceCodes: string[]) => Promise<QuoteDraftResponse>;
}) {
  const [draft, setDraft] = useState<QuoteDraftResponse>();
  const [error, setError] = useState("");

  async function requestDraft() {
    try {
      setDraft(await onDraft(DRAFT_BUNDLE));
      setError("");
    } catch (failure) {
      setDraft(undefined);
      setError(failureMessage(failure, "Quote draft unavailable"));
    }
  }

  return (
    <div className="space-y-3">
      <p className="text-sm text-muted-foreground">
        Prices use the shop inventory and available bay capacity. A draft
        remains a draft until approval.
      </p>
      <Button onClick={() => void requestDraft()}>Draft quote</Button>
      {error && <p role="alert">{error}</p>}
      {draft && (
        <div className="overflow-x-auto rounded-lg border border-border bg-card">
          <table
            aria-label="Quote draft lines"
            className="w-full min-w-180 text-left text-sm"
          >
            <thead className="bg-muted text-xs uppercase tracking-wide text-muted-foreground">
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
            <tbody className="divide-y divide-white/8">
              {draft.lines.map((line) => (
                <tr key={line.service_code}>
                  <td>{line.service_code}</td>
                  <td>{line.labor_mxn}</td>
                  <td>{line.parts_mxn}</td>
                  <td>{line.iva_mxn}</td>
                  <td>{line.total_mxn}</td>
                  <td>{line.duration_minutes}</td>
                  <td>{line.fitment}</td>
                  <td>
                    {line.available ? "Available" : line.unavailable_reason}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {draft && (
        <p className="rounded-lg border border-primary/20 bg-primary/7 p-3 text-sm text-primary">
          {`Subtotal ${draft.subtotal_mxn} + IVA ${draft.iva_mxn} = ${draft.total_mxn} MXN · ${draft.duration_minutes} min · ${draft.bay_slot_id ?? "no bay slot"}`}
        </p>
      )}
      {draft?.warnings.map((warning) => (
        <p
          key={warning}
          role="status"
          className="rounded-lg border border-amber-300/20 bg-amber-300/5 p-3 text-sm text-amber-100"
        >
          {warning}
        </p>
      ))}
    </div>
  );
}
