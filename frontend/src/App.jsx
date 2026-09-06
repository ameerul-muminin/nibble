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

import { useEffect, useRef, useState } from 'react'
import { Show, SignInButton, SignUpButton, UserButton } from '@clerk/react'
// The three Slice 1 functions are imported ready for the TODOs below. Each
// eslint-disable in this file marks something the scaffold set up but has not
// used yet — when a TODO is finished, delete the matching disable with it. If
// `npm run lint` passes with none of them left, the wiring is complete.
// eslint-disable-next-line no-unused-vars -- delete once the TODOs below use these
import { deleteDocument, getHealth, listDocuments, uploadDocument } from './api'
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

  // -------------------------------------------------------------------------
  // Slice 1 — issues #5 and #7
  //
  // Everything below this line is scaffolding: the layout, the classes and the
  // hidden-file-input plumbing are done, and each piece of behaviour is a TODO.
  // Work down them in order; each one is small on its own.
  // -------------------------------------------------------------------------

  // The list of notes. It starts as an empty array rather than null, so the
  // rendering code below can always call .map on it without checking first.
  // eslint-disable-next-line no-unused-vars -- delete once setDocs is called
  const [docs, setDocs] = useState([])

  // Three separate small states rather than one big one, because they change
  // at different times and mixing them makes it harder to see what is going on.
  // eslint-disable-next-line no-unused-vars -- delete once setDocsStatus is called
  const [docsStatus, setDocsStatus] = useState('loading') // loading | ready | failed
  const [busy, setBusy] = useState(false) // true while an upload is in flight
  const [notice, setNotice] = useState(null) // a plain sentence, or null

  // A ref is a handle onto a real DOM element. This one lets the visible button
  // below click the invisible file input for us. Built for you — it is the
  // fiddly bit, and it is the same three lines in every React app.
  const fileInput = useRef(null)

  // TODO(Alif): #5 — load the notes once, when the page appears.
  //   Another useEffect with an empty dependency list, same shape as the
  //   health one above:
  //     listDocuments()
  //       .then((rows) => { setDocs(rows); setDocsStatus('ready') })
  //       .catch(() => setDocsStatus('failed'))

  /** #5 — runs when a file has been chosen in the hidden input. */
  async function handleFileChosen(event) {
    const file = event.target.files[0]
    if (!file) return

    // Clearing the input's value means picking the SAME file twice in a row
    // still fires this. Without it, the second pick does nothing and looks
    // broken. Built for you because it is pure trivia, not a React idea.
    event.target.value = ''

    setBusy(true)
    setNotice(null)
    try {
      // TODO(Alif): #5 — await uploadDocument(file), then put the new
      //   document at the FRONT of the list, because the backend returns
      //   newest first and the screen should agree with it:
      //     const created = await uploadDocument(file)
      //     setDocs([created, ...docs])
      //
      //   Note it builds a NEW array rather than calling docs.push(). React
      //   only redraws when it sees a different value, and push() changes the
      //   old array in place, so the screen would not update.
      throw new Error('TODO(Alif): the upload is not wired up yet')
    } catch {
      // Never show the raw error. A plain sentence, and a way to try again.
      setNotice('That upload did not work. Check it is a PDF, TXT or MD under 20 MB, then try again.')
    } finally {
      setBusy(false)
    }
  }

  /** #7 — runs when the X on a row is clicked. */
  // eslint-disable-next-line no-unused-vars -- delete once the row below calls this
  async function handleDelete(id) {
    setNotice(null)
    try {
      // TODO(Alif): #7 — await deleteDocument(id), then take it out of state:
      //     setDocs(docs.filter((d) => d.id !== id))
      //
      //   filter returns a new array and leaves the old one alone, which is
      //   exactly what React wants. This is the same "new value, not a changed
      //   one" idea as the upload above — worth noticing that it came up twice.
      throw new Error('TODO(Alif): the delete is not wired up yet')
    } catch {
      setNotice('Could not delete that note. Try again in a moment.')
    }
  }

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

      {/*
        Slice 1 — your notes. Issues #5 (list and upload) and #7 (delete).
        The layout, classes and file-input plumbing are built; the behaviour
        is marked TODO in the handlers above.
      */}
      <section className="card" style={{ marginTop: 'var(--gap-lg)' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--gap)',
            marginBottom: 'var(--gap)',
          }}
        >
          <h2 style={{ margin: 0 }}>Your notes</h2>

          {/*
            The real file input is hidden, because a raw one cannot be styled
            and looks nothing like the rest of the page. The button below is
            what people see, and clicking it clicks this through the ref.
          */}
          <input
            type="file"
            ref={fileInput}
            hidden
            accept=".pdf,.txt,.md"
            onChange={handleFileChosen}
          />

          <button
            type="button"
            className="btn btn--primary"
            style={{ marginLeft: 'auto' }}
            disabled={busy}
            onClick={() => fileInput.current.click()}
          >
            {busy ? 'Adding…' : 'Add a note'}
          </button>
        </div>

        {/* One plain sentence when something went wrong. Never a raw error. */}
        {notice && (
          <p role="status" style={{ color: 'var(--danger, #b3261e)' }}>
            {notice}
          </p>
        )}

        {docsStatus === 'loading' && (
          <p style={{ color: 'var(--text-muted)' }}>Fetching your notes…</p>
        )}

        {docsStatus === 'failed' && (
          <p style={{ color: 'var(--text-muted)' }}>
            Could not load your notes. Check the backend is running, then refresh.
          </p>
        )}

        {/*
          The empty state. Worth having from the start: the very first thing
          anybody sees when they open Nibble is this, not a list.
        */}
        {docsStatus === 'ready' && docs.length === 0 && (
          <p style={{ color: 'var(--text-muted)', marginBottom: 0 }}>
            Nothing here yet. Add a chapter and Nibble will read it.
          </p>
        )}

        {docsStatus === 'ready' && docs.length > 0 && (
          <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
            {/*
              TODO(Alif): #5 — render one <li> per document.
                docs.map((doc) => ( ...one row... )) goes here.

                Every row needs key={doc.id}. React uses the key to tell rows
                apart between redraws; without it, deleting the middle row can
                leave the wrong one on screen. The id from the database is a
                perfect key — do not use the array index, which changes when
                something is removed.

                One row looks like this. Copy it inside the map:

                <li
                  key={doc.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 'var(--gap-sm)',
                    padding: 'var(--gap-sm) 0',
                    borderBottom: '2px solid var(--border, #eee)',
                  }}
                >
                  <span style={{ flex: 1 }}>{doc.filename}</span>
                  <span style={{ color: 'var(--text-muted)' }}>
                    {doc.page_count} {doc.page_count === 1 ? 'page' : 'pages'}
                  </span>
                  <button
                    type="button"
                    className="btn btn--secondary"
                    aria-label={`Delete ${doc.filename}`}
                    onClick={() => handleDelete(doc.id)}
                  >
                    ×
                  </button>
                </li>

                The aria-label matters: on its own, "×" is read out as
                "multiplication sign" by a screen reader, which tells somebody
                nothing about which note it deletes. docs/design.md has the
                accessibility floor this is part of.
            */}
          </ul>
        )}
      </section>
    </main>
  )
}
