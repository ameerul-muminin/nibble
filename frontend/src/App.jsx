/**
 * The whole app, for now.
 *
 * Slice 0 does exactly one thing: ask the backend whether it is awake, and say
 * so on screen. That sounds trivial, but it proves the hardest part of any web
 * app is working — two separate programs, talking to each other.
 *
 * Later slices grow this file: uploading notes, listing them, searching, and
 * finally chatting with Nibble.
 */

import { useEffect, useState } from 'react'
import { Show, SignInButton, SignUpButton, UserButton } from '@clerk/react'
import { getHealth } from './api'
import { Mascot } from './components/Mascot'
import './styles/global.css'

// What we say for each state. Errors tell you what to DO, never just "error".
const MESSAGES = {
  checking: 'Looking for the backend…',
  up: 'Backend is up. Nibble is ready to learn.',
  down: 'Can’t reach the backend. Open a second terminal, go to the backend folder, and run: uvicorn app.main:app --reload',
}

export default function App() {
  // useState remembers a value between redraws. Calling setStatus tells React
  // the value changed, and React redraws whatever uses it.
  const [status, setStatus] = useState('checking')

  // useEffect with an empty list at the end runs once, right after the page
  // first appears. Asking the backend for things belongs here.
  useEffect(() => {
    getHealth()
      .then(() => setStatus('up'))
      .catch(() => setStatus('down'))
  }, [])

  return (
    <main style={{ maxWidth: 620, margin: '0 auto', padding: 'var(--gap-xl) var(--gap-lg)' }}>
      <header
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--gap)',
          marginBottom: 'var(--gap-lg)',
        }}
      >
        <Mascot size={80} mood={status === 'checking' ? 'thinking' : 'idle'} />
        <div>
          <h1>Nibble</h1>
          <p style={{ margin: 0, color: 'var(--text-muted)' }}>
            Bite-sized answers from your own notes
          </p>
        </div>

        {/*
          Show picks one branch based on whether somebody is signed in. Clerk
          knows the answer because ClerkProvider wraps the whole app in main.jsx.
          marginLeft: 'auto' pushes this cluster to the right-hand end of the row.
        */}
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 'var(--gap-sm)' }}>
          <Show when="signed-out">
            <SignInButton mode="modal" />
            <SignUpButton mode="modal" />
          </Show>
          <Show when="signed-in">
            <UserButton />
          </Show>
        </div>
      </header>

      <section className="card">
        <h2 style={{ marginBottom: 'var(--gap-sm)' }}>Slice 0 — is everything talking?</h2>

        <p style={{ margin: 0 }}>{MESSAGES[status]}</p>

        <p style={{ marginBottom: 0, color: 'var(--text-muted)' }}>
          {status === 'up'
            ? 'Next up: Slice 1, uploading a PDF.'
            : 'This page asks the backend for /health when it loads.'}
        </p>
      </section>
    </main>
  )
}
