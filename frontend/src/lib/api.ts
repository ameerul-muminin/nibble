/**
 * The ONLY place in the frontend that talks to the backend.
 *
 * Every function here mirrors an endpoint in docs/api.md. Keeping them
 * together means when the backend changes a response shape, exactly one file
 * needs fixing — not fifteen components.
 */

const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export type Doc = {
  id: string
  filename: string
  status: 'processing' | 'ready' | 'failed'
  page_count: number
  created_at: string
}

export type Source = {
  document_id: string
  filename: string
  page: number
  excerpt: string
}

export type AskResponse = {
  session_id: string
  answer: string
  sources: Source[]
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, init)
  if (!response.ok) {
    const detail = await response.text()
    throw new Error(detail || `Request failed with ${response.status}`)
  }
  return response.status === 204 ? (undefined as T) : ((await response.json()) as T)
}

export const api = {
  listDocuments: () => request<Doc[]>('/documents'),

  uploadDocument: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return request<Doc>('/documents', { method: 'POST', body: form })
  },

  deleteDocument: (id: string) => request<void>(`/documents/${id}`, { method: 'DELETE' }),

  ask: (question: string, sessionId: string | null) =>
    request<AskResponse>('/chat/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, session_id: sessionId }),
    }),
}
