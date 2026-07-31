import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/textarea'
import type { RecommendationResponse } from '../../api/generated/types.gen'
import { useState } from 'react'

export function RecommendationConsole({ recommendation, onStartRun, onApproveRun, onAsk }: { recommendation?: RecommendationResponse; onStartRun: () => Promise<{ id: string; events: string[] }>; onApproveRun: () => Promise<void>; onAsk: (question: string) => Promise<string> }) {
  const state = recommendation?.state ?? 'Waiting for a confirmed check-in'
  const [runState, setRunState] = useState('Start a resumable Advisor run')
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState('')
  return <Card className="mt-6 border-slate-700 bg-slate-950 text-slate-100"><CardHeader><div className="flex items-center justify-between"><CardTitle>Grounded maintenance recommendation</CardTitle><Badge>{state}</Badge></div></CardHeader><CardContent className="space-y-4"><Alert><AlertTitle>{recommendation?.service_code ?? 'No actionable service'} </AlertTitle><AlertDescription>{recommendation ? `${recommendation.rule_version} · page ${recommendation.citation_page}, ${recommendation.citation_section}.` : 'Confirm a check-in to load reviewed evidence.'}</AlertDescription></Alert><Tabs defaultValue="evidence"><TabsList><TabsTrigger value="evidence">Evidence</TabsTrigger><TabsTrigger value="run">Advisor run</TabsTrigger><TabsTrigger value="explain">Explain</TabsTrigger></TabsList><TabsContent value="evidence">{recommendation?.due_reason ?? 'No recommendation yet.'}</TabsContent><TabsContent value="run"><Progress value={72} /><p className="mt-2">{runState}</p><Button className="mt-3" onClick={() => void onStartRun().then((run) => setRunState(`Run ${run.id}: ${run.events.join(' → ')}`))}>Start run</Button><Button className="mt-3 ml-2" onClick={() => void onApproveRun().then(() => setRunState('Approved idempotently'))}>Approve review</Button></TabsContent><TabsContent value="explain"><Textarea aria-label="Contextual question" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Ask about this cited recommendation" /><Button className="mt-2" onClick={() => void onAsk(question).then(setAnswer)}>Ask</Button><p className="mt-2 text-sm text-slate-400">{answer || 'Answers remain grounded in the displayed rule and evidence.'}</p></TabsContent></Tabs></CardContent></Card>
}
