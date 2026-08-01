import type { CreateDemoSessionRequest, WorkspaceResponse } from './generated/types.gen'
import {
  createSessionDemoSessionsPost,
  getWorkspaceWorkspaceGet,
} from './generated/sdk.gen'
import { requestFailed } from './failure'

export async function enterDemoWorkspace(
  role: CreateDemoSessionRequest['role'],
): Promise<{ token: string; workspace: WorkspaceResponse }> {
  const session = await createSessionDemoSessionsPost({ body: { role } })

  if (!('data' in session) || !session.data) {
    throw requestFailed('Demo session could not be created', session)
  }

  const workspace = await getWorkspaceWorkspaceGet({
    headers: { authorization: `Bearer ${session.data.token}` },
  })

  if (!('data' in workspace) || !workspace.data) {
    throw requestFailed('Protected workspace could not be loaded', workspace)
  }

  return { token: session.data.token, workspace: workspace.data }
}
