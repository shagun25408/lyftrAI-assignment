export interface Metadata {
  resolution_source: 'LIVE_INFERENCE' | 'LLM_CACHE'
  model: string
  latency_ms: number
  input_tokens: number
  output_tokens: number
  key_id: string | null
  fallback_attempts: number
}
export interface ChatMessage { role: 'user' | 'assistant'; content: string; metadata?: Metadata }
export interface Health { status: string; keys_configured: number; cache_enabled: boolean }
const base = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, '') || 'http://localhost:8000'

async function parse<T>(response: Response): Promise<T> {
  const data = await response.json().catch(() => null)
  if (!response.ok) {
    if (response.status === 503 && data?.detail === 'all providers unavailable') {
      throw new Error('Lyftr AI is temporarily unavailable. Please try again.')
    }
    throw new Error(typeof data?.detail === 'string' ? data.detail : `Request failed (${response.status})`)
  }
  if (!data) throw new Error('The server returned an invalid response.')
  return data as T
}
export const api = {
  health: () => fetch(`${base}/health`).then(parse<Health>),
  send: (session_id: string, message: string, system_prompt?: string) => fetch(`${base}/chat`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ session_id, message, ...(system_prompt ? { system_prompt } : {}) }) }).then(parse<{ session_id: string; reply: string; metadata: Metadata }>),
  history: (session: string) => fetch(`${base}/sessions/${encodeURIComponent(session)}/messages`).then(parse<{ session_id: string; messages: ChatMessage[] }>),
}
