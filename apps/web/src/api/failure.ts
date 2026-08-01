/**
 * Every API client fails the same way, so a panel can tell a refusal from an outage.
 *
 * A refusal carries an HTTP status the caller can act on -- a 409 means the state a step
 * depended on is gone, which happens whenever the demo instance restarts. A network error
 * carries none.
 */
export function requestFailed(
  message: string,
  response: { response?: { status?: number } },
): Error {
  return Object.assign(new Error(message), { status: response.response?.status })
}

/**
 * The demo keeps every record in memory, so a restart leaves a signed, still-valid session
 * token pointing at state that is gone. Only the Advisor can repair that, by checking the
 * vehicle in again, so every panel says the same sentence rather than inventing its own.
 */
export const CHECKIN_GONE =
  "The check-in behind this step no longer exists; confirm the check-in again"

/**
 * Turn a thrown request into the sentence a Service Advisor can act on.
 *
 * Three outcomes read differently: state that vanished under the session (404, 409) is
 * repaired by redoing the check-in, another refusal is the request's own fault, and
 * anything else -- a 5xx, a cold start, a dead network -- is not the Advisor's to fix.
 */
export function failureMessage(
  failure: unknown,
  unavailable: string,
  refused?: string,
): string {
  const { status } = failure as { status?: number }
  if (status === 404 || status === 409) return CHECKIN_GONE
  if (typeof status === "number" && status >= 400 && status < 500)
    return refused ?? unavailable
  return unavailable
}
