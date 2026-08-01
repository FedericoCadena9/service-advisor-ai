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
