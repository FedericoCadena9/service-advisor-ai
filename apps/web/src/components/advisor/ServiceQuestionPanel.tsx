import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import type { ServiceQuestionResponse } from "../../api/generated/types.gen";

export function ServiceQuestionPanel({
  onAskData,
}: {
  onAskData: (question: string) => Promise<ServiceQuestionResponse>;
}) {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<ServiceQuestionResponse>();
  const [error, setError] = useState("");

  async function ask() {
    try {
      setResult(await onAskData(question));
      setError("");
    } catch {
      setResult(undefined);
      setError("No supported read-only query answers this question");
    }
  }

  return (
    <div className="space-y-3">
      <p className="text-sm text-muted-foreground">
        This surface accepts only approved, read-only service data questions.
      </p>
      <label className="block text-sm font-medium" htmlFor="service-question">
        Ad hoc service question
      </label>
      <Textarea
        id="service-question"
        value={question}
        onChange={(event) => setQuestion(event.target.value)}
      />
      <Button className="mt-2" onClick={() => void ask()}>
        Run read-only query
      </Button>
      {result && (
        <div className="space-y-3 rounded-lg border border-border bg-muted/40 p-4">
          <p>{result.answer}</p>
          <pre
            aria-label="Accepted SQL"
            className="overflow-x-auto rounded-md border border-border bg-card p-3 text-xs text-primary"
          >
            {result.sql}
          </pre>
          <p className="text-xs leading-5 text-muted-foreground">{`Views ${result.retrieval.views.join(", ")} · columns ${result.retrieval.columns.join(", ")} · limit ${result.retrieval.row_limit} · timeout ${result.retrieval.timeout_seconds}s · principal ${result.retrieval.principal}`}</p>
        </div>
      )}
      {error && (
        <p className="rounded-lg border border-amber-300/20 bg-amber-300/5 p-3 text-sm text-amber-100">
          {error}
        </p>
      )}
    </div>
  );
}
