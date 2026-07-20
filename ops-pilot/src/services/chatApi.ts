import { buildApiUrl } from './api'

export type ChatSource = {
  chunk_id: string | null
  filename: string | null
  page: number | null
  chunk_index: number | null
  text: string
  similarity_score: number
}

export type PostChatRequest = {
  question: string
  indexName?: string
  topK?: number
  sessionId?: string
  // Optional overrides (backend has defaults)
  embedModel?: string
  genModel?: string
}

export type PostChatResponse = {
  ok: boolean
  timestamp: string
  question: string
  session_id: string
  index_name: string
  top_k: number
  answer: string
  sources: ChatSource[]
  response_time_ms: number
}

export async function postChat(req: PostChatRequest): Promise<PostChatResponse> {
  const body = {
    question: req.question,
    index_name: req.indexName ?? 'default',
    top_k: req.topK ?? 4,
    session_id: req.sessionId ?? null,
    ...(req.embedModel ? { embed_model: req.embedModel } : {}),
    ...(req.genModel ? { gen_model: req.genModel } : {}),
  }

  const res = await fetch(buildApiUrl('/chat'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`Chat failed: ${res.status} ${text}`)
  }

  const json = (await res.json()) as PostChatResponse
  if (!json.ok) {
    throw new Error('Chat returned ok=false')
  }
  return json
}

