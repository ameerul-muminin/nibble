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
import { deleteDocument, getChunks, getHealth, listDocuments, uploadDocument } from './api'
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
  const [docs, setDocs] = useState([])

  // Three separate small states rather than one big one, because they change
  // at different times and mixing them makes it harder to see what is going on.
  const [docsStatus, setDocsStatus] = useState('loading') // loading | ready | failed
  // True while an upload is in flight. A typed file is instant; a scan or a
  // photo goes to the vision model a page at a time and takes seconds, which
  // is why the button says "Reading…" rather than nothing at all.
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState(null) // a plain sentence, or null

  // A ref is a handle onto a real DOM element. This one lets the visible button
  // below click the invisible file input for us. Built for you — it is the
  // fiddly bit, and it is the same three lines in every React app.
  const fileInput = useRef(null)

  // Bumping this re-runs the load below. It is how the "Try again" button on
  // the failed state works: change the value, the effect runs again.
  const [reloadKey, setReloadKey] = useState(0)

  // Load the notes. This is the one place that REPLACES the whole list rather
  // than adjusting it, which makes it the one place that can throw away a
  // change made while it was still in flight.
  //
  // `ignore` is the guard against that. When this effect is torn down — or run
  // again — the old request is still out there and will still resolve, and
  // without the flag its rows would land on top of whatever happened since.
  // React's StrictMode runs every effect twice in development on purpose, to
  // make exactly this bug show up on a laptop rather than in front of an
  // audience. The cleanup function marks the old run as stale, so only the
  // newest one is allowed to write anything.
  useEffect(() => {
    let ignore = false
    setDocsStatus('loading')

    listDocuments()
      .then((rows) => {
        if (ignore) return
        setDocs(rows)
        setDocsStatus('ready')
      })
      .catch(() => {
        if (ignore) return
        setDocsStatus('failed')
      })

    return () => {
      ignore = true
    }
  }, [reloadKey])

  // -------------------------------------------------------------------------
  // Slice 2 — issue #10. Click a note, see the pieces it was cut into.
  // -------------------------------------------------------------------------

  // Which note is open, by id, or null when none is. Storing the *id* rather
  // than the note object matters: the object in `docs` is replaced every time
  // the list reloads, so a stored object would quietly go stale and stop
  // matching the row it came from. An id stays true.
  const [selectedId, setSelectedId] = useState(null)

  // Derived from state, not stored alongside it. Keeping a second piece of
  // state for "the selected document" would mean two things to keep in step,
  // and they would drift the moment the list reloaded. Work it out on each
  // render instead — it is one array lookup.
  const selectedDoc = docs.find((d) => d.id === selectedId)

  const [chunks, setChunks] = useState([])
  const [chunksStatus, setChunksStatus] = useState('idle') // idle | loading | ready | failed

  // This is the new idea in #10: an effect that re-runs when a *value* changes,
  // rather than once on load. `selectedId` is in the dependency list, so every
  // time it changes React tears down the previous run and starts this again.
  //
  // The `ignore` flag is the same guard as the notes list above, and it earns
  // its keep more here. Click note A then quickly note B, and two requests are
  // in flight; if A's answer arrives second it would land on top of B's pieces
  // and the screen would show B selected with A's contents. The flag makes the
  // stale run drop its result on the floor.
  useEffect(() => {
    if (selectedId === null) {
      setChunks([])
      setChunksStatus('idle')
      return
    }

    let ignore = false
    setChunksStatus('loading')

    getChunks(selectedId)
      .then((rows) => {
        if (ignore) return
        setChunks(rows)
        setChunksStatus('ready')
      })
      .catch(() => {
        if (ignore) return
        setChunksStatus('failed')
      })

    return () => {
      ignore = true
    }
  }, [selectedId])

  /** Open a note, or close it if it is already open. */
  function toggleSelected(id) {
    setSelectedId((current) => (current === id ? null : id))
  }

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
      const created = await uploadDocument(file)

      // The new note goes at the FRONT, because the backend returns newest
      // first and the screen should agree with it.
      //
      // setDocs is given a FUNCTION rather than a value. Written as
      // setDocs([created, ...docs]), `docs` would be the list as it was when
      // this upload started — so a delete that finished while the upload was
      // in flight would be undone, and the deleted note would reappear. The
      // function form is handed the list as it is right now instead.
      //
      // Either way it builds a NEW array rather than calling push(). React
      // only redraws when it sees a different value, and push() changes the
      // old array in place, so the note would be in the list and never show.
      setDocs((current) => [created, ...current])
    } catch (error) {
      // The backend already writes a plain sentence for anything a person
      // caused, and it is more useful than anything guessable here — it says
      // whether the file was the wrong type, unreadable, or too long. Fall
      // back to a generic line only if there was no sentence to show.
      setNotice(
        error.message ||
          'That upload did not work. Check it is a PDF, TXT, MD or a photo, under 20 MB.',
      )
    } finally {
      setBusy(false)
    }
  }

  /** #7 — runs when the X on a row is clicked. */
  async function handleDelete(id) {
    setNotice(null)
    try {
      await deleteDocument(id)

      // Same function form as the upload, and for the same reason: delete two
      // notes quickly and the second one would otherwise filter the list as it
      // was before the first finished, putting the first note back on screen.
      //
      // filter returns a new array and leaves the old one alone, which is what
      // React wants — the same "a new value, not a changed one" idea as above.
      setDocs((current) => current.filter((d) => d.id !== id))

      // If the note that was open is the one just deleted, close the panel.
      // Without this the pieces of a note that no longer exists stay on screen,
      // and the next reload would ask the backend for it and get a 404.
      setSelectedId((current) => (current === id ? null : current))
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
            accept=".pdf,.txt,.md,.png,.jpg,.jpeg,.webp"
            onChange={handleFileChosen}
          />

          <button
            type="button"
            className="btn btn--primary"
            style={{ marginLeft: 'auto' }}
            disabled={busy || docsStatus !== 'ready'}
            onClick={() => fileInput.current.click()}
          >
            {busy ? 'Reading…' : 'Add a note'}
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

        {/*
          A failed load used to be a dead end: the upload button stays disabled
          until the list is known, and nothing here offered a way to try again,
          so one dropped request meant a page refresh. This retries in place.
        */}
        {docsStatus === 'failed' && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--gap)' }}>
            <p style={{ color: 'var(--text-muted)', margin: 0 }}>
              Could not load your notes. Check the backend is running.
            </p>
            <button
              type="button"
              className="btn btn--secondary"
              onClick={() => setReloadKey((n) => n + 1)}
            >
              Try again
            </button>
          </div>
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
              One <li> per document. Every row needs key={doc.id}: React uses
              the key to tell rows apart between redraws, and without it,
              deleting the middle row can leave the wrong one on screen. The
              database id is a perfect key — never the array index, which
              changes the moment something is removed.
            */}
            {docs.map((doc) => (
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
                {/*
                  A <button>, not a <div onClick>. It has to be reachable by Tab
                  and operable with Enter and Space, and a real button is all
                  three for free — see the accessibility floor in docs/design.md.
                  aria-expanded tells a screen reader that this control opens
                  something, and whether it is open right now.
                */}
                <button
                  type="button"
                  onClick={() => toggleSelected(doc.id)}
                  aria-expanded={selectedId === doc.id}
                  style={{
                    flex: 1,
                    textAlign: 'left',
                    background: 'none',
                    border: 'none',
                    font: 'inherit',
                    color: 'inherit',
                    cursor: 'pointer',
                    padding: 0,
                  }}
                >
                  {doc.filename}
                </button>
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
            ))}
          </ul>
        )}
      </section>

      {/*
        Slice 2 — issue #10. The pieces the selected note was cut into.

        Rendered only when something is selected, so the very first thing anyone
        sees is still the notes list and not an empty panel asking to be filled.
        Plain boxes for now: a page number and the text. Slice 5 makes it pretty.
      */}
      {selectedId !== null && (
        <section className="card" style={{ marginTop: 'var(--gap-lg)' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--gap)',
              marginBottom: 'var(--gap)',
            }}
          >
            <h2 style={{ margin: 0 }}>{selectedDoc ? `Inside ${selectedDoc.filename}` : 'Pieces'}</h2>

            <button
              type="button"
              className="btn btn--secondary"
              style={{ marginLeft: 'auto' }}
              onClick={() => setSelectedId(null)}
            >
              Close
            </button>
          </div>

          <p style={{ color: 'var(--text-muted)', marginTop: 0 }}>
            Nibble cuts every note into overlapping pieces, so a search can point at a
            paragraph instead of a whole chapter. Consecutive pieces repeat a little of
            each other on purpose — a sentence cut in half still sits whole in one of them.
          </p>

          {chunksStatus === 'loading' && (
            <p style={{ color: 'var(--text-muted)' }}>Fetching the pieces…</p>
          )}

          {chunksStatus === 'failed' && (
            <p style={{ color: 'var(--danger, #b3261e)' }}>
              Could not load the pieces. Check the backend is running, then click the note
              again.
            </p>
          )}

          {chunksStatus === 'ready' && chunks.length === 0 && (
            <p style={{ color: 'var(--text-muted)', marginBottom: 0 }}>
              This note has no pieces. Anything uploaded before chunking existed is like
              this — delete it and upload it again.
            </p>
          )}

          {chunksStatus === 'ready' && chunks.length > 0 && (
            <>
              <p style={{ color: 'var(--text-muted)' }}>
                {chunks.length} {chunks.length === 1 ? 'piece' : 'pieces'}
              </p>

              <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
                {chunks.map((chunk) => (
                  <li
                    key={chunk.id}
                    style={{
                      border: '2px solid var(--border, #eee)',
                      borderRadius: 'var(--radius, 8px)',
                      padding: 'var(--gap-sm)',
                      marginBottom: 'var(--gap-sm)',
                    }}
                  >
                    <p
                      style={{
                        margin: 0,
                        marginBottom: 'var(--gap-sm)',
                        color: 'var(--text-muted)',
                        fontFamily: 'var(--font-display)',
                      }}
                    >
                      Page {chunk.page}
                    </p>
                    {/*
                      whiteSpace: pre-wrap keeps the line breaks that were in the
                      original page. Without it the browser collapses every run of
                      whitespace and a page of notes arrives as one long paragraph.
                    */}
                    <p style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{chunk.content}</p>
                  </li>
                ))}
              </ul>
            </>
          )}
        </section>
      )}
    </main>
  )
}
