import { BookOpenCheck, CircleAlert, ShieldCheck } from 'lucide-react'
import { useState } from 'react'

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/textarea'
import type { QuoteDecisionResponse, QuoteDraftResponse, QuoteReviewResponse, RecommendationResponse, ServiceQuestionResponse } from '../../api/generated/types.gen'
import { CustomerTimelinePanel, type TimelineActions } from './CustomerTimelinePanel'
import { QuoteApprovalPanel } from './QuoteApprovalPanel'
import { QuoteDraftPanel } from './QuoteDraftPanel'
import { ServiceQuestionPanel } from './ServiceQuestionPanel'

type Props = { recommendation?: RecommendationResponse; onStartRun: () => Promise<{ id: string; events: string[] }>; onApproveRun: () => Promise<void>; onAsk: (question: string) => Promise<string>; onDraftQuote: (serviceCodes: string[]) => Promise<QuoteDraftResponse>; onOpenReview: (serviceCodes: string[]) => Promise<QuoteReviewResponse>; onDecideReview: (reviewId: string, decision: 'approve' | 'reject', reason?: string) => Promise<QuoteDecisionResponse>; onAskData: (question: string) => Promise<ServiceQuestionResponse>; timeline: TimelineActions }

export function RecommendationConsole({ recommendation, onStartRun, onApproveRun, onAsk, onDraftQuote, onOpenReview, onDecideReview, onAskData, timeline }: Props) {
  const state = recommendation?.state ?? 'Waiting for a confirmed check-in'
  const [runState, setRunState] = useState('Start a resumable Advisor run')
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState('')
  const [quoteId, setQuoteId] = useState<string | null>(null)
  return <Card className="mt-6 border border-white/10 bg-[#20201c]/95 py-0 shadow-2xl shadow-black/20">
    <CardHeader className="border-b border-white/10 px-5 py-5 sm:px-6"><div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between"><div><p className="mb-1 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-primary"><BookOpenCheck className="size-3.5" /> 02 · Evidence review</p><CardTitle className="text-xl">Grounded maintenance recommendation</CardTitle><p className="mt-1 text-sm text-muted-foreground">A recommendation cannot outpace its reviewed source.</p></div><Badge className="h-auto max-w-64 whitespace-normal bg-primary/15 px-3 py-1.5 text-center text-primary" variant="outline">{state}</Badge></div></CardHeader>
    <CardContent className="space-y-5 px-5 py-5 sm:px-6"><Alert className="border-primary/25 bg-primary/7"><ShieldCheck className="size-4 text-primary" /><AlertTitle>{recommendation?.service_code ?? 'No actionable service'}</AlertTitle><AlertDescription>{recommendation ? `${recommendation.rule_version} · page ${recommendation.citation_page}, ${recommendation.citation_section}.` : 'Confirm a check-in to load reviewed evidence.'}</AlertDescription></Alert>
      <Tabs defaultValue="evidence" className="space-y-4"><TabsList className="h-auto w-full justify-start gap-1 overflow-x-auto rounded-lg border border-white/10 bg-black/15 p-1"><TabsTrigger value="evidence">Evidence</TabsTrigger><TabsTrigger value="run">Advisor run</TabsTrigger><TabsTrigger value="explain">Explain</TabsTrigger><TabsTrigger value="quote">Quote</TabsTrigger><TabsTrigger value="approval">Approval</TabsTrigger><TabsTrigger value="timeline">Timeline</TabsTrigger><TabsTrigger value="data">Data</TabsTrigger></TabsList>
        <TabsContent value="evidence" className="rounded-xl border border-white/10 bg-black/15 p-5 text-sm leading-6 text-muted-foreground"><div className="mb-3 flex items-center gap-2 font-medium text-foreground"><BookOpenCheck className="size-4 text-primary" /> Reviewed manual evidence</div>{recommendation?.due_reason ?? 'No recommendation yet.'}</TabsContent>
        <TabsContent value="run" className="rounded-xl border border-white/10 bg-black/15 p-5"><Progress value={72} className="h-2" /><p className="mt-3 text-sm text-muted-foreground">{runState}</p><div className="mt-4 flex flex-wrap gap-2"><Button onClick={() => void onStartRun().then((run) => setRunState(`Run ${run.id}: ${run.events.join(' → ')}`))}>Start run</Button><Button variant="outline" onClick={() => void onApproveRun().then(() => setRunState('Approved idempotently'))}>Approve review</Button></div></TabsContent>
        <TabsContent value="explain" className="rounded-xl border border-white/10 bg-black/15 p-5"><label className="mb-1.5 block text-sm font-medium" htmlFor="contextual-question">Ask about this citation</label><Textarea id="contextual-question" aria-label="Contextual question" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Ask about this cited recommendation" /><Button className="mt-3" onClick={() => void onAsk(question).then(setAnswer)}>Ask</Button><p className="mt-3 text-sm text-muted-foreground">{answer || 'Answers remain grounded in the displayed rule and evidence.'}</p></TabsContent>
        <TabsContent value="quote" className="rounded-xl border border-white/10 bg-black/15 p-5"><QuoteDraftPanel onDraft={onDraftQuote} /></TabsContent>
        <TabsContent value="approval" className="rounded-xl border border-white/10 bg-black/15 p-5"><QuoteApprovalPanel onOpenReview={onOpenReview} onDecide={onDecideReview} onApproved={setQuoteId} /></TabsContent>
        <TabsContent value="timeline" className="rounded-xl border border-white/10 bg-black/15 p-5"><CustomerTimelinePanel quoteId={quoteId} {...timeline} /></TabsContent>
        <TabsContent value="data" className="rounded-xl border border-white/10 bg-black/15 p-5"><ServiceQuestionPanel onAskData={onAskData} /></TabsContent>
      </Tabs>
      {!recommendation && <p className="flex gap-2 rounded-lg border border-amber-300/20 bg-amber-300/5 p-3 text-sm text-amber-100"><CircleAlert className="mt-0.5 size-4 shrink-0" />Evidence is intentionally absent until check-in is confirmed.</p>}
    </CardContent>
  </Card>
}
