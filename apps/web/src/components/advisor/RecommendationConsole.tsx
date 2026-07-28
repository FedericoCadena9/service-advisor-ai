import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/textarea'

export function RecommendationConsole() {
  return <Card className="mt-6 border-slate-700 bg-slate-950 text-slate-100"><CardHeader><div className="flex items-center justify-between"><CardTitle>Grounded maintenance recommendation</CardTitle><Badge>Due now</Badge></div></CardHeader><CardContent className="space-y-4"><Alert><AlertTitle>HONDA-A1 · 48,000 km service</AlertTitle><AlertDescription>Reviewed rule honda-civic-2019-lx-v1 · page 42, Maintenance Minder.</AlertDescription></Alert><Tabs defaultValue="evidence"><TabsList><TabsTrigger value="evidence">Evidence</TabsTrigger><TabsTrigger value="run">Advisor run</TabsTrigger><TabsTrigger value="explain">Explain</TabsTrigger></TabsList><TabsContent value="evidence">Actionable because the interval has been reached. Completed and declined history remains auditable.</TabsContent><TabsContent value="run"><Progress value={72} /><p className="mt-2">Awaiting human review — no command has run.</p><Button className="mt-3">Approve review</Button></TabsContent><TabsContent value="explain"><Textarea aria-label="Contextual question" placeholder="Ask about this cited recommendation" /><p className="mt-2 text-sm text-slate-400">Answers remain grounded in the displayed rule and evidence.</p></TabsContent></Tabs></CardContent></Card>
}
