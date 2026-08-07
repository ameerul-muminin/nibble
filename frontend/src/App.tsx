import { useEffect, useRef, useState } from 'react'
import { Button } from './components/Button'
import { ChatBubble } from './components/ChatBubble'
import { Mascot } from './components/Mascot'
import { api, type Doc, type Source } from './lib/api'
import './styles/global.css'

type Turn = { role: 'user' | 'assistant'; content: string; sources?: Source[] }

const GREETING: Turn = {
  role: 'assistant',
  content: 'Upload a chapter and ask me anything about it. I only answer from your own notes.',
}

export default function App() {
  const [docs, setDocs] = useState<Doc[]>([])
  const [turns, setTurns] = useState<Turn[]>([GREETING])
  const [question, setQuestion] = useState('')
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const fileInput = useRef<HTMLInputElement>(null)

  useEffect(() => {
    api.listDocuments().then(setDocs).catch(() => setError('Could not reach the server.'))
  }, [])

  async function handleUpload(file: File) {
    setError(null)
    setBusy(true)
    try {
      const doc = await api.uploadDocument(file)
      setDocs((current) => [doc, ...current])
    } catch {
      setError('That upload did not work. Try a PDF under 20 MB.')
    } finally {
      setBusy(false)
    }
  }

  async function handleAsk() {
    const text = question.trim()
    if (!text || busy) return

    setTurns((current) => [...current, { role: 'user', content: text }])
    setQuestion('')
    setError(null)
    setBusy(true)
    try {
      const result = await api.ask(text, sessionId)
      setSessionId(result.session_id)
      setTurns((current) => [
        ...current,
        { role: 'assistant', content: result.answer, sources: result.sources },
      ])
    } catch {
      setError('Nibble could not answer that one. Check the backend is running.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <main style={{ maxWidth: 780, margin: '0 auto', padding: 'var(--gap-lg)' }}>
      <header
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--gap)',
          marginBottom: 'var(--gap-lg)',
        }}
      >
        <Mascot size={72} mood={busy ? 'thinking' : 'idle'} />
        <div>
          <h1>Nibble</h1>
          <p style={{ margin: 0, color: 'var(--text-muted)' }}>
            Bite-sized answers from your own notes
          </p>
        </div>
        <span className="streak" style={{ marginLeft: 'auto' }}>
          {docs.length} {docs.length === 1 ? 'note' : 'notes'}
        </span>
      </header>

      <section className="card" style={{ marginBottom: 'var(--gap-lg)' }}>
        <h2 style={{ marginBottom: 'var(--gap-sm)' }}>Your notes</h2>
        {docs.length === 0 ? (
          <p style={{ color: 'var(--text-muted)', marginTop: 0 }}>
            Nothing here yet. Add a PDF and Nibble will read it.
          </p>
        ) : (
          <ul style={{ paddingLeft: 18, margin: '0 0 var(--gap) 0' }}>
            {docs.map((doc) => (
              <li key={doc.id}>
                {doc.filename} <span style={{ color: 'var(--text-faint)' }}>· {doc.status}</span>
              </li>
            ))}
          </ul>
        )}
        <input
          ref={fileInput}
          type="file"
          accept=".pdf,.txt,.md"
          hidden
          onChange={(event) => {
            const file = event.target.files?.[0]
            if (file) handleUpload(file)
            event.target.value = ''
          }}
        />
        <Button onClick={() => fileInput.current?.click()} disabled={busy}>
          Add notes
        </Button>
      </section>

      <section className="card">
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--gap-sm)',
            minHeight: 220,
            marginBottom: 'var(--gap)',
          }}
        >
          {turns.map((turn, index) => (
            <ChatBubble key={index} {...turn} />
          ))}
          {busy && <div className="bubble bubble--cat">Reading your notes…</div>}
        </div>

        {error && (
          <p style={{ color: 'var(--coral)', fontWeight: 700, marginTop: 0 }}>{error}</p>
        )}

        <div style={{ display: 'flex', gap: 'var(--gap-sm)' }}>
          <input
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={(event) => event.key === 'Enter' && handleAsk()}
            placeholder="Ask anything about your notes…"
            style={{
              flex: 1,
              font: 'inherit',
              padding: '12px 16px',
              border: 'var(--border)',
              borderRadius: 'var(--radius)',
            }}
          />
          <Button variant="accent" onClick={handleAsk} disabled={busy || !question.trim()}>
            Ask
          </Button>
        </div>
      </section>
    </main>
  )
}
