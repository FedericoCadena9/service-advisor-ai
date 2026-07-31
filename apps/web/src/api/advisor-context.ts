/** The vehicle and Advisor Run a request belongs to, so answers and traces stay correlated. */
export type AdvisorContext = {
  vehicleId: string
  currentMileageKm: number
  traceId: string | null
}

export function traceHeaders(context: Pick<AdvisorContext, 'traceId'>): Record<string, string> {
  return context.traceId ? { 'x-trace-id': context.traceId } : {}
}
