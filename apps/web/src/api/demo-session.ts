import type { CreateDemoSessionRequest, WorkspaceResponse } from './generated/types.gen'
import {
  createSessionDemoSessionsPost,
  getWorkspaceWorkspaceGet,
} from './generated/sdk.gen'

export async function enterDemoWorkspace(
  role: CreateDemoSessionRequest['role'],
): Promise<{ token: string; workspace: WorkspaceResponse }> {
  const session = await createSessionDemoSessionsPost({ body: { role } })

  if (!('data' in session) || !session.data) {
    throw new Error('Demo session could not be created')
  }

  const workspace = await getWorkspaceWorkspaceGet({
    headers: { authorization: `Bearer ${session.data.token}` },
  })

  if (!('data' in workspace) || !workspace.data) {
    throw new Error('Protected workspace could not be loaded')
  }

  return { token: session.data.token, workspace: workspace.data }
}
