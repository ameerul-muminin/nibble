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
import { useAuth, UserButton } from '@clerk/react'
import { ask, deleteDocument, getChunks, getHealth, listDocuments, search, setTokenGetter, uploadDocument } from './api'
import { Button } from './components/Button'
import { Mascot } from './components/Mascot'
import { Classroom } from './components/Classroom'
import { Landing } from './components/Landing'
import { QuizMe } from './components/QuizMe'
import { StudentRoom } from './components/StudentRoom'
import './styles/global.css'
import './styles/app.css'

// What we say for each state. Errors tell you what to DO, never just "error".
const MESSAGES = {
  checking: 'Looking for the backend…',
  up: 'Backend is up. Nibble is ready to learn.',
  down: 'Can’t reach the backend. Open a second terminal, go to the backend folder, and run: uvicorn app.main:app --reload',
}

/**
 * Everything below belongs to whoever is signed in right now, and nothing of it
 * survives them signing out.
 *
 * This wrapper is four lines and it exists for a bug that is easy to write and
 * hard to spot. `Nibble` returns <Landing /> when nobody is signed in — but a
 * `return` is not the component going away. React keeps it mounted in the same
 * place in the tree, so every useState inside it keeps its value. Sign out, sign
 * in as somebody else in the same tab, and the previous person's conversation is
 * still on screen: their questions, the answers, and the text they searched for.
 *
 * `key` is how you say "this is a different one now". React uses it to decide
 * whether the thing at this position is the same thing it drew last time, and
 * when it changes React throws the old one away and builds a new one — with
 * every piece of state fresh. It is the same idea as key={doc.id} on the rows of
 * the notes list, used deliberately rather than incidentally.
 *
 * Doing it here rather than clearing each piece of state by hand is the same
 * reasoning as ON DELETE CASCADE in db.py: a list of things to reset is a list
 * somebody has to remember to add to, and the day it gets forgotten it fails
 * silently. This cannot be forgotten. Every state added from here on is covered
 * by it for free, including an answer still in flight when the user changes —
 * that arrives to a component that no longer exists, and React drops it.
 */
export default function App() {
  const { userId, getToken } = useAuth()

  // Slice 7: which door somebody came in by. 'notes', 'teach' or 'join'.
  //
  // **It lives up here rather than in Nibble, and that is the whole reason it
  // works.** The doors are on the landing page, which Nibble renders — and the
  // moment you sign in, `key` below changes and React throws that Nibble away
  // along with every piece of state in it, on purpose. A choice made before
  // signing in would go with it. App is never thrown away, so this survives.
  //
  // It is navigation and nothing else. It is never sent to the backend, and the
  // backend would ignore it if it were: being a teacher is owning a room, not
  // claiming to be one. See docs/adr/0004-teacher-is-an-owner.md.
  const [door, setDoor] = useState('notes')

  // Slice 4.5: teach api.js how to get a sign-in token, so every request it
  // makes carries one. See setTokenGetter in api.js for why it takes the
  // function rather than a token.
  //
  // Done here in the body rather than in a useEffect, and that ordering is the
  // whole reason. React renders a parent before its children, and runs every
  // effect only after all of them have rendered — so an effect here would run
  // AFTER Nibble's effect that loads the notes list, and that first request
  // would go out with no token and come back 401. Setting it during render
  // means it is in place before any child exists to ask for it.
  //
  // Assigning something outside React during render is normally a thing to
  // avoid. It is safe here because it is the same value every time and nothing
  // reads it while rendering.
  setTokenGetter(getToken)

  // ?? 'signed-out' because userId is null when nobody is signed in and
  // undefined while Clerk is still looking. A key of null or undefined is the
  // same as no key at all, which would leave the state exactly where it was.
  return <Nibble key={userId ?? 'signed-out'} door={door} onDoor={setDoor} />
}

function Nibble({ door, onDoor }) {
  // Who is looking at this? isLoaded is false for the first moment, while Clerk
  // checks the browser for an existing session. Both flags matter: <Show> was
  // used here before and it renders NOTHING while loading, which is invisible
  // when it wraps one button and a blank white page when it wraps the whole app.
  const { isLoaded, isSignedIn } = useAuth()

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

  // What the backend said when the list failed to load, or null if it said
  // nothing useful. Kept separately from docsStatus because "it failed" and
  // "here is why" are two different facts, and the second one is the one that
  // saves somebody an hour.
  const [docsError, setDocsError] = useState(null)
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

        // If the open note is not in the list any more, close the panel.
        // handleDelete covers the note YOU deleted; this covers the note
        // somebody else deleted, which is reachable because every document is
        // shared by everyone — two tabs, or two laptops on demo day. Without
        // it the panel keeps showing a deleted note's pieces, under a heading
        // that has quietly fallen back to the generic "Pieces" because the
        // document it named is gone.
        //
        // The function form, not `rows.some((r) => r.id === selectedId)`.
        // selectedId is not in this effect's dependency list, so the value
        // captured here would be whatever it was when the load started — and
        // clicking a note while the list is in flight would then close the
        // panel that had just been opened. The updater is handed the current
        // value instead.
        setSelectedId((current) => (rows.some((row) => row.id === current) ? current : null))
      })
      .catch((error) => {
        if (ignore) return

        // Keep the backend's own sentence. This used to throw the error away
        // and show a fixed line guessing the backend was down — and the day the
        // database file turned out to be from before notes had owners, the
        // backend said exactly that, in words naming the fix, and the guess
        // replaced it. Somebody then spent a while checking a backend that was
        // running perfectly. Show what the server said whenever it said
        // anything; the guess is only for when it truly said nothing.
        setDocsError(error?.message || null)
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

  // -------------------------------------------------------------------------
  // Slice 3 — issue #14. Type a question, see the pieces that match it.
  // -------------------------------------------------------------------------

  // What is in the box right now. A "controlled input": React holds the value
  // and the input just displays it, which is why onChange has to write it back
  // — leave that out and typing appears to do nothing.
  const [query, setQuery] = useState('')

  // The query that produced the results currently on screen. Kept separately
  // from `query` on purpose: the heading should keep saying what was actually
  // searched for while somebody types their next question over the top of it.
  const [searched, setSearched] = useState('')

  const [results, setResults] = useState([])
  const [searchStatus, setSearchStatus] = useState('idle') // idle | searching | ready | failed
  const [searchError, setSearchError] = useState(null)

  // Which notes cannot be searched at all, by id, straight from the backend.
  // These are notes stored before slice 3 existed, which have no embedding —
  // they sit in the list looking perfectly normal and match nothing, so they get
  // said out loud rather than left to be discovered during a demo.
  //
  // Ids rather than the count, because a count cannot survive a deletion: delete
  // one of these notes and a number cannot tell you whether it was one of the
  // ones being counted, so the page would keep telling you to delete a note that
  // is already gone. A list can be filtered, exactly like the results are, and
  // the number shown is counted from what is left.
  const [unsearchableIds, setUnsearchableIds] = useState([])
  const unsearchable = unsearchableIds.length

  // Which search is the newest one. Every search takes the next number, and an
  // answer is only allowed to write to the screen if its number is still the
  // current one.
  //
  // This is the same idea as the `ignore` flag on the two effects above, in the
  // shape an event handler needs: an effect gets a cleanup function to mark the
  // old run stale, and a click handler does not, so the marker has to live
  // somewhere that survives between calls. A ref does; a normal variable would
  // be created fresh on every render.
  //
  // Not reachable through the UI today, because the Search button is disabled
  // while a search is in flight and that stops the Enter key submitting too.
  // Written anyway: it is one line of bookkeeping, and "the answer to the
  // question you asked two questions ago silently replaces the one on screen"
  // is a horrible bug to meet for the first time in front of an audience.
  const searchRun = useRef(0)

  // Notes deleted while a search was in the air. See handleSearch below.
  const deletedIds = useRef(new Set())

  /**
   * #14 — runs when the search form is submitted.
   *
   * A <form> with onSubmit rather than a button with onClick, because that is
   * what makes the Enter key work, and typing a question and pressing Enter is
   * how everybody expects a search box to behave.
   */
  async function handleSearch(event) {
    // Without this the browser reloads the whole page on submit — its default
    // behaviour since forms predate JavaScript.
    event.preventDefault()

    const trimmed = query.trim()
    if (!trimmed) return

    const run = searchRun.current + 1
    searchRun.current = run

    setSearchStatus('searching')
    setSearchError(null)

    try {
      const body = await search(trimmed)

      // A newer search started while this one was still out. Its answer is the
      // one that belongs on screen, so drop this one on the floor.
      if (searchRun.current !== run) return

      // Results are a snapshot of the moment the request was sent, and a note
      // can be deleted while it is in the air — the delete button stays live
      // during a search. Without this filter, the arriving results would put a
      // deleted note's pieces back on screen, under a filename that no longer
      // exists, and nothing would clear them until the next search.
      //
      // Unlike the stale-response guard above, this one is reachable right now:
      // start a search, click × on a note, and the results land after it.
      // Both lists go through the same filter, for the same reason. A note
      // deleted while this request was in the air is gone, whether it was one
      // of the matches or one of the notes that could never be matched.
      const notDeleted = (id) => !deletedIds.current.has(id)

      setResults(body.results.filter((result) => notDeleted(result.document_id)))

      // ?? [] because a backend older than this page does not send this field,
      // and reaching for .filter on nothing is a TypeError — which would land in
      // the catch below and put a raw JavaScript error on screen. That is the
      // stale-backend problem again, and the same rule applies: the two halves
      // of the app disagreeing must never look like a crash. Search still works
      // here; only the notice about unsearchable notes goes quiet.
      setUnsearchableIds((body.unsearchable_note_ids ?? []).filter(notDeleted))
      setSearched(trimmed)
      setSearchStatus('ready')
    } catch (error) {
      if (searchRun.current !== run) return

      // The backend writes a plain sentence for anything a person caused. Show
      // that, and keep a generic line only for when there was nothing to show.
      setSearchError(error.message || 'Nibble could not search just now. Try again in a moment.')
      setSearchStatus('failed')
    }
  }

  /** 0.82 -> "82%". A percentage is far easier to read at a glance than 0.82. */
  function asPercentage(score) {
    return `${Math.round(score * 100)}%`
  }

  // -------------------------------------------------------------------------
  // Slice 4 — issue #17. Ask a question, get an answer with the pages it read.
  // -------------------------------------------------------------------------

  // The whole conversation, oldest first. Each turn is
  // { role: 'user' | 'nibble', content: string, sources: [] }.
  //
  // One array rather than a question state and an answer state, because a chat
  // is a list that grows and never shrinks. Two separate states could only ever
  // hold the latest pair, and the second question would erase the first answer.
  const [turns, setTurns] = useState([])

  const [question, setQuestion] = useState('')
  const [askStatus, setAskStatus] = useState('idle') // idle | asking | failed
  const [askError, setAskError] = useState(null)

  /**
   * #17 — runs when the question form is submitted.
   *
   * Two appends, at two different moments, and that is the whole shape of a
   * chat: the question goes up the instant it is asked, and the answer joins it
   * whenever it arrives. Waiting for the answer before showing either would
   * leave the box empty for several seconds after somebody pressed Enter, which
   * reads as the app having ignored them.
   */
  async function handleAsk(event) {
    event.preventDefault()

    const trimmed = question.trim()
    if (!trimmed) return

    // setTurns is given a FUNCTION rather than a value, the same as setDocs on
    // the upload above and for the same reason: `turns` inside this handler is
    // the list as it was when the handler started, so building a new array from
    // it would undo anything that landed in between. The function form is
    // handed the list as it is right now.
    setTurns((current) => [...current, { role: 'user', content: trimmed, sources: [] }])

    // Clear the box straight away. The question is on screen in a bubble now,
    // so leaving it in the input as well says it has not been sent yet.
    setQuestion('')
    setAskStatus('asking')
    setAskError(null)

    try {
      // `turns` here is the conversation as it was when this handler started —
      // everything already said, and not the question just typed. That is
      // exactly the history the backend wants, and it is the one place where
      // the stale-closure behaviour the comments above warn about is the
      // correct behaviour rather than a bug: the new question travels in its
      // own field, so including it here would send it twice.
      const body = await ask(trimmed, turns)

      // A refusal arrives here, not in the catch. "That isn't in your notes
      // yet." is Nibble working correctly, and it goes in a bubble like any
      // other answer — rendering it as an error would be exactly backwards.
      setTurns((current) => [
        ...current,
        { role: 'nibble', content: body.answer, sources: body.sources ?? [] },
      ])
      setAskStatus('idle')
    } catch (error) {
      // The failed question stays on screen rather than being taken back. It is
      // still what was asked, and removing it would leave somebody staring at
      // an error with no idea which question caused it.
      setAskError(
        error.message || 'Nibble could not answer just now. Try again in a moment.',
      )
      setAskStatus('failed')
    }

    // No stale-answer guard here, unlike handleSearch. The Ask button and the
    // box are both disabled while an answer is in flight, so a second question
    // cannot be sent until the first has landed — and in a transcript an answer
    // has to go in one particular place, which makes silently dropping one
    // worse than never having two.
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

      // Same reasoning for the search results, which are a second place a
      // deleted note can keep being shown. Search results are a snapshot of the
      // moment they were fetched, not live data, so nothing else would ever
      // clear them — the pieces of a deleted note would sit there under a
      // filename that no longer exists until somebody searched again.
      setResults((current) => current.filter((result) => result.document_id !== id))

      // And the same for the notes-that-cannot-be-searched notice, which is the
      // other thing on screen naming a document. Without this, deleting exactly
      // the note that notice is about leaves it saying "1 note was added before
      // search existed — delete it and upload again" about a note that is no
      // longer there. That one needs no race at all to see.
      setUnsearchableIds((current) => current.filter((noteId) => noteId !== id))

      // Clearing what is on screen is not enough on its own: a search that was
      // already in the air will arrive afterwards carrying this note, in either
      // list, and put it straight back. Remembering the id is what lets
      // handleSearch filter it out when that answer lands.
      deletedIds.current.add(id)
    } catch {
      setNotice('Could not delete that note. Try again in a moment.')
    }
  }

  // Clerk has not answered yet. Say so, rather than drawing a blank page that
  // looks broken. It is normally too fast to read.
  if (!isLoaded) {
    return (
      <main className="shell">
        <p style={{ color: 'var(--text-muted)' }}>Waking Nibble up…</p>
      </main>
    )
  }

  // Signed-out visitors get the landing page and nothing else. onDoor is how
  // its two doors say which screen to land on once Clerk is done.
  if (!isSignedIn) {
    return <Landing onDoor={onDoor} />
  }

  return (
    <>
      {/*
        The black band, straight off the deck's cover slide: near-black, the
        word in lime, one thin line of what this is.

        It sits outside <main> rather than inside it because it runs the full
        width of the window while everything else is held to a 1200px column.
        `.on-dark` is what makes the buttons inside it press against a light
        edge instead of an invisible ink one — see global.css.
      */}
      <header className="topbar on-dark">
        <div className="topbar__inner">
          {/*
            Nibble in the header, which is the one place it is always visible.
            Decorative: the word "Nibble" is right beside it, so a screen reader
            announcing a cat here would say the same thing twice.
          */}
          <Mascot size={52} />

          <div>
            <h1 className="topbar__word">Nibble</h1>
            <p className="topbar__tagline">Bite-sized answers from your own notes</p>
          </div>

          {/* Already inside signed-in, so just the user menu. */}
          <div className="topbar__user">
            <UserButton />
          </div>
        </div>

      {/*
        Slice 7 — the switch between the three screens.

        `door` is the whole of it: one value, three screens, and nothing else to
        keep in step. Nobody is stuck behind the door they came in by — a student
        can go back to their own notes, and a teacher can quiz himself — which is
        the point made in adr/0004: the doors are navigation, never permission.

        Real buttons, so Tab and Enter work for free, and aria-pressed says which
        one you are on rather than leaving the lime background to say it alone.
      */}
        <nav aria-label="Screens" className="topbar__nav">
          {[
            ['notes', 'Your notes'],
            ['teach', 'Teach a class'],
            ['join', 'Join a class'],
          ].map(([name, label]) => (
            <Button
              key={name}
              variant={door === name ? 'primary' : 'secondary'}
              aria-pressed={door === name}
              onClick={() => onDoor(name)}
            >
              {label}
            </Button>
          ))}
        </nav>
      </header>

      <main className="shell">
      {door === 'teach' && <Classroom />}
      {door === 'join' && <StudentRoom />}

      {door === 'notes' && (
        <div className="notes-grid">
        {/*
          Step one, across the full width of the grid, because nothing else on
          this page does anything until a note exists. It was three cards down
          before, which meant the first thing a new person saw was a question
          box for notes they had not uploaded yet.
        */}
        <div className="notes-top">

      {/*
        Slice 1 — your notes. Issues #5 (list and upload) and #7 (delete).
        The layout, classes and file-input plumbing are built; the behaviour
        is marked TODO in the handlers above.
      */}
      <section className="card">
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

          <Button
            variant="primary"
            style={{ marginLeft: 'auto' }}
            disabled={busy || docsStatus !== 'ready'}
            onClick={() => fileInput.current.click()}
          >
            {busy ? 'Reading…' : 'Add a note'}
          </Button>
        </div>

        {/*
          What is happening while an upload is in flight.

          This is here because "Reading…" on a button is not enough feedback for
          how long this actually takes. Nibble turns every piece of a chapter
          into numbers before it stores it, on the free host's very small share
          of a CPU, and a chapter can take a minute or more. With nothing on
          screen, people conclude it has hung and reload — which loses the
          upload that was very nearly finished.

          Two sentences: what it is doing, and roughly how long. Saying "this
          takes a moment" without a number is the thing that reads as a hang.
        */}
        {busy && (
          <p role="status" style={{ color: 'var(--text-muted)' }}>
            Reading your note and getting it ready to search. A long chapter can take
            a minute or two — you can leave this open.
          </p>
        )}

        {/* One plain sentence when something went wrong. Never a raw error. */}
        {notice && (
          <p role="status" className="notice-bad">
            <span className="notice-bad__mark" aria-hidden="true">
              !
            </span>
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
              {docsError || 'Could not load your notes. Check the backend is running.'}
            </p>
            <Button
              variant="secondary"
              onClick={() => setReloadKey((n) => n + 1)}
            >
              Try again
            </Button>
          </div>
        )}

        {/*
          The empty state. Worth having from the start: the very first thing
          anybody sees when they open Nibble is this, not a list.
        */}
        {docsStatus === 'ready' && docs.length === 0 && (
          <div className="nibble-say">
            <Mascot size={72} mood="curious" />
            <p style={{ color: 'var(--text-muted)', margin: 0 }}>
              Nothing here yet. Add a chapter and Nibble will read it.
            </p>
          </div>
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
                  borderBottom: 'var(--border)',
                }}
              >
                {/*
                  A <button>, not a <div onClick>. It has to be reachable by Tab
                  and operable with Enter and Space, and a real button is all
                  three for free — see the accessibility floor in docs/design.md.
                  aria-expanded tells a screen reader that this control opens
                  something, and whether it is open right now.
                */}
                <Button
                  variant="plain"
                  onClick={() => toggleSelected(doc.id)}
                  aria-expanded={selectedId === doc.id}
                  style={{ flex: 1 }}
                >
                  {doc.filename}
                </Button>
                <span style={{ color: 'var(--text-muted)' }}>
                  {doc.page_count} {doc.page_count === 1 ? 'page' : 'pages'}
                </span>
                <Button
                  variant="secondary"
                  aria-label={`Delete ${doc.filename}`}
                  onClick={() => handleDelete(doc.id)}
                >
                  ×
                </Button>
              </li>
            ))}
          </ul>
        )}
      </section>
        </div>

        {/*
          Below the upload card, two columns on a laptop and one on anything
          smaller. The split is the order you actually do things in: get a note
          in, ask it things, then test yourself on it and look inside it.
        */}
        <div className="notes-col">

      {/*
        Slice 4 — issue #17. The actual product.

        First on the page, above search, because this is what Nibble is for.
        Search stays below it rather than being folded in: being able to see the
        retrieval on its own, with no model near it, is what makes the answer up
        here believable rather than magic.
      */}
      <section className="card">
        <h2 style={{ marginBottom: 'var(--gap-sm)' }}>Ask Nibble</h2>

        <p style={{ marginTop: 0, color: 'var(--text-muted)' }}>
          Nibble answers from your notes and nothing else, and shows you the pages it
          read. Ask it something they don’t cover and it will say so.
        </p>

        {/*
          The transcript. An empty state rather than a blank space, because this
          is the first thing anybody sees when they open Nibble.
        */}
        {turns.length === 0 && askStatus === 'idle' && (
          <div className="nibble-say">
            <Mascot size={72} mood="curious" />
            <p style={{ color: 'var(--text-muted)', margin: 0 }}>
              Nothing asked yet. Try “explain this chapter in three sentences”.
            </p>
          </div>
        )}

        {turns.length > 0 && (
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: 'var(--gap)',
              marginBottom: 'var(--gap)',
            }}
          >
            {turns.map((turn, index) => {
              const fromNibble = turn.role !== 'user'

              /*
                Nibble sits beside the newest answer and no other. design.md is
                blunt about why: a mascot that turns up next to every message
                stops being charming within a day. It also steps aside while a
                new question is in flight, because the thinking cat below the
                transcript is the one that should be moving then.
              */
              const cheer = fromNibble && index === turns.length - 1 && askStatus === 'idle'

              const bubble = (
              <div
                /*
                  The index as the key, which is normally the wrong answer —
                  and is the right one here for a reason worth knowing. An
                  index breaks when a list is reordered or has things removed
                  from the middle, because React then matches up the wrong
                  rows. A transcript does neither: turns are only ever appended
                  to the end, so turn 3 is turn 3 forever. Nothing else here is
                  unique — the same question asked twice is genuinely the same
                  string.
                */
                key={index}
                className={`bubble ${fromNibble ? 'bubble--cat' : 'bubble--user'}`}
              >
                {turn.content}

                {/*
                  The pages Nibble was allowed to read. This is the part that
                  makes an answer checkable rather than something to take on
                  faith — and checking is the point, because the honest claim
                  is "it only had these pages", not "it quoted this one".

                  These are left alone when a note is deleted, unlike the search
                  results. A transcript is a record of what was said at the
                  time, and quietly editing the sources out of an answer already
                  given would make it look like Nibble had read something else.
                */}
                {turn.sources.length > 0 && (
                  <div className="sources">
                    {turn.sources.map((source) => (
                      <span
                        key={`${source.document_id}-${source.page}-${source.excerpt.slice(0, 24)}`}
                        className="source-chip"
                        title={source.excerpt}
                      >
                        {source.filename} · p. {source.page}
                      </span>
                    ))}
                  </div>
                )}
              </div>
              )

              return cheer ? (
                <div key={index} className="nibble-row">
                  <Mascot size={48} mood="happy" />
                  {bubble}
                </div>
              ) : (
                bubble
              )
            })}
          </div>
        )}

        <form onSubmit={handleAsk} className="form-row">
          {/* A real label, hidden from sight but not from a screen reader. */}
          <label htmlFor="ask-box" className="visually-hidden">
            What do you want to ask Nibble?
          </label>

          <input
            id="ask-box"
            className="input"
            type="text"
            placeholder="Explain osmosis simply"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            disabled={askStatus === 'asking'}
          />

          <Button
            type="submit"
            variant="primary"
            disabled={askStatus === 'asking' || !question.trim()}
          >
            {askStatus === 'asking' ? 'Thinking…' : 'Ask'}
          </Button>
        </form>

        {/* Announced to a screen reader when it changes, without stealing focus. */}
        <div role="status">
          {askStatus === 'asking' && (
            <div className="nibble-say">
              <Mascot size={56} mood="thinking" />
              <p style={{ color: 'var(--text-muted)', margin: 0 }}>Reading your notes…</p>
            </div>
          )}

          {askStatus === 'failed' && (
            <p className="notice-bad" style={{ marginBottom: 0 }}>
              <span className="notice-bad__mark" aria-hidden="true">
                !
              </span>
              {askError}
            </p>
          )}
        </div>
      </section>

      {/*
        Slice 3 — issue #14. Search, with no AI anywhere in it.

        Sits between the chat and the notes list. Everything on screen here comes
        from cosine similarity and nothing else: no model wrote a word of it,
        which is exactly what makes this slice worth demoing on its own — and
        what shows where the answer above actually came from.
      */}
      <section className="card">
        <h2 style={{ marginBottom: 'var(--gap-sm)' }}>Search your notes</h2>

        <p style={{ marginTop: 0, color: 'var(--text-muted)' }}>
          Ask in your own words. Nibble matches meaning, not spelling, so “how does water
          cross a membrane” finds the page about osmosis.
        </p>

        <form onSubmit={handleSearch} className="form-row">
          {/*
            A real <label>, hidden from sight but not from a screen reader. A
            placeholder is not a label: it disappears the moment you type, and
            some screen readers never announce it at all.
          */}
          <label htmlFor="search-box" className="visually-hidden">
            What do you want to find?
          </label>

          <input
            id="search-box"
            className="input"
            type="search"
            placeholder="How does osmosis work?"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />

          <Button
            type="submit"
            variant="primary"
            disabled={searchStatus === 'searching' || !query.trim()}
          >
            {searchStatus === 'searching' ? 'Looking…' : 'Search'}
          </Button>
        </form>

        {/*
          role="status" tells a screen reader to announce this when it changes,
          without stealing focus — which is how somebody who cannot see the page
          finds out the search finished.
        */}
        <div role="status">
          {searchStatus === 'searching' && (
            <p style={{ color: 'var(--text-muted)' }}>Reading through your notes…</p>
          )}

          {searchStatus === 'failed' && (
            <p className="notice-bad">
              <span className="notice-bad__mark" aria-hidden="true">
                !
              </span>
              {searchError}
            </p>
          )}

          {searchStatus === 'ready' && results.length === 0 && (
            <p style={{ color: 'var(--text-muted)', marginBottom: 0 }}>
              Nothing in your notes came close to “{searched}”. Try different words, or add
              the chapter it should be in.
            </p>
          )}
        </div>

        {/*
          The count of notes that cannot be searched. Shown whenever it is not
          zero, and only underneath a search, so it explains a disappointing
          result at the moment somebody is looking at one.
        */}
        {searchStatus === 'ready' && unsearchable > 0 && (
          <p style={{ color: 'var(--text-muted)' }}>
            {unsearchable} {unsearchable === 1 ? 'note was' : 'notes were'} added before search
            existed, so {unsearchable === 1 ? 'it cannot' : 'they cannot'} be found here. Delete{' '}
            {unsearchable === 1 ? 'it' : 'them'} and upload again to fix that.
          </p>
        )}

        {searchStatus === 'ready' && results.length > 0 && (
          <>
            <p style={{ color: 'var(--text-muted)' }}>
              {results.length} {results.length === 1 ? 'piece' : 'pieces'} for “{searched}”, closest
              first.
            </p>

            <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
              {results.map((result) => (
                <li
                  // Two pieces of the same note can both come back, so the id
                  // of the document is not unique enough to be a key on its
                  // own. Document plus page plus the first few characters is.
                  key={`${result.document_id}-${result.page}-${result.content.slice(0, 24)}`}
                  style={{
                    border: 'var(--border)',
                    borderRadius: 'var(--radius)',
                    padding: 'var(--gap-sm)',
                    marginBottom: 'var(--gap-sm)',
                  }}
                >
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 'var(--gap-sm)',
                      marginBottom: 'var(--gap-sm)',
                      flexWrap: 'wrap',
                    }}
                  >
                    <span className="source-chip">
                      {result.filename} · p. {result.page}
                    </span>

                    {/*
                      The score as a percentage. This is the most convincing
                      thing on the screen at a demo: it shows the system is
                      ranking rather than guessing. Worth knowing that the floor
                      is not zero — total nonsense still scores about 46%,
                      because two pieces of ordinary English are never truly
                      unrelated. A good match is far higher.
                    */}
                    <span style={{ marginLeft: 'auto', fontFamily: 'var(--font-display)' }}>
                      {asPercentage(result.score)} match
                    </span>
                  </div>

                  <p style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{result.content}</p>
                </li>
              ))}
            </ul>
          </>
        )}
      </section>

        </div>

        <div className="notes-col">

      {/*
        Slice 6 — quiz yourself.

        Beside the pieces rather than under the question box, because this side
        of the grid is what you make from a note and what is inside it, while
        the left is the conversation with it. It is made FROM a note, so you
        have to have one before it does anything, and the empty state says so
        rather than offering a form that cannot work.

        `docs` is passed down rather than fetched again, so the note dropdown
        and the notes list can never disagree about what exists. onNoteGone lets
        the quiz card tell App that a note turned out to be too old to quiz —
        the one failure whose fix is deleting and re-uploading it — and it
        reuses the same reloadKey the "Try again" button uses rather than adding
        a second way to refresh the same list.
      */}
      <QuizMe docs={docs} onNoteGone={() => setReloadKey((n) => n + 1)} />

      {/*
        Slice 2 — issue #10. The pieces the selected note was cut into.

        Rendered only when something is selected, so the very first thing anyone
      {/*
        sees is still the notes list and not an empty panel asking to be filled.
        Plain boxes for now: a page number and the text. Slice 5 makes it pretty.
      */}
      {selectedId !== null && (
        <section className="card">
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--gap)',
              marginBottom: 'var(--gap)',
            }}
          >
            <h2 style={{ margin: 0 }}>{selectedDoc ? `Inside ${selectedDoc.filename}` : 'Pieces'}</h2>

            <Button
              variant="secondary"
              style={{ marginLeft: 'auto' }}
              onClick={() => setSelectedId(null)}
            >
              Close
            </Button>
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
            <p className="notice-bad">
              <span className="notice-bad__mark" aria-hidden="true">
                !
              </span>
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
                      border: 'var(--border)',
                      borderRadius: 'var(--radius)',
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

      {/*
        The health check, moved out of first position.

        It used to be the first card on the page — a developer's panel sitting
        above the thing the product is for, telling somebody looking at eight
        finished slices that slice 1 is next. The check itself is worth keeping;
        being the first thing anybody reads was not. #21 still owes it a rewrite.
      */}
      <section className="card">
        <h2 style={{ marginBottom: 'var(--gap-sm)' }}>Slice 0 — is everything talking?</h2>

        <p style={{ margin: 0 }}>{MESSAGES[status]}</p>

        <p style={{ marginBottom: 0, color: 'var(--text-muted)' }}>
          {status === 'up'
            ? 'Next up: Slice 1, uploading a PDF.'
            : 'This page asks the backend for /health when it loads.'}
        </p>
      </section>
        </div>
        </div>
      )}
    </main>
    </>
  )
}
