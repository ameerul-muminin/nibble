/**
 * Slice 7 — the teacher's half of the classroom.
 *
 * Pick a quiz you own, open a room around it, put the code on the board, watch
 * students arrive, press Start, then press End. Contract in docs/api.md under
 * "Slice 7".
 *
 * **A teacher is not a role.** Nothing on this screen is a permission and
 * nothing here is sent to the backend to claim one. You can see a room because
 * you own it, which is one `WHERE owner_id = ?` in the query that fetches it —
 * see docs/adr/0004-teacher-is-an-owner.md. Anybody signed in can open the same
 * screen, and that is the intended behaviour rather than a gap.
 *
 * Its own file rather than more of App.jsx, for the reason written at the top
 * of QuizMe.jsx: App.jsx was already past a thousand lines before slice 6.
 */

import { useEffect, useState } from 'react'
import { createRoom, deleteRoom, getRoom, listQuizzes, listRooms, setRoomState } from '../api'
import { Results } from './Results'
import { Button } from './Button'

/**
 * How often the live screens ask the backend what changed, in milliseconds.
 *
 * Three seconds, and polling rather than a websocket: a websocket is a second
 * protocol, a second failure mode and a second thing to explain, to save a
 * couple of seconds in a room where nobody is racing.
 *
 * Exported so the student screen uses the same number. Thirty students at one
 * request every three seconds is about ten a second against a backend with a
 * tenth of a CPU, and if that ever bites, **the fix is a bigger number here**,
 * not a websocket. One place to change it is the whole point.
 */
export const POLL_MS = 3000

/** What each state means to a person, rather than to the database. */
const STATE_WORDS = {
  waiting: 'Waiting to start',
  open: 'Running now',
  closed: 'Finished',
}

export function Classroom() {
  // The quizzes you could run. Fetched here rather than handed down from App:
  // this screen and "Quiz me" are never on screen at the same time, so there is
  // no chance of the two disagreeing, and passing it through App would have
  // meant App loading something it does not itself use.
  const [quizzes, setQuizzes] = useState([])
  const [quizId, setQuizId] = useState('')

  const [rooms, setRooms] = useState([])
  const [listStatus, setListStatus] = useState('loading') // loading | ready | failed
  const [listError, setListError] = useState(null)

  // The room on screen right now, with its live count. null means the list is
  // showing.
  const [open, setOpen] = useState(null)

  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState(null)

  useEffect(() => {
    let ignore = false

    Promise.all([listRooms(), listQuizzes()])
      .then(([myRooms, myQuizzes]) => {
        if (ignore) return
        setRooms(myRooms)
        setQuizzes(myQuizzes)
        setListStatus('ready')
      })
      .catch((error) => {
        if (ignore) return
        // The backend's own sentence, for the reason written into App's notes
        // list: a fixed line here once sent somebody to check a backend that
        // was running perfectly well.
        setListError(error?.message || null)
        setListStatus('failed')
      })

    return () => {
      ignore = true
    }
  }, [])

  // ---------------------------------------------------------------------------
  // The poll
  // ---------------------------------------------------------------------------
  //
  // While a room is on screen and has not finished, ask every three seconds how
  // many students have joined. This is the only thing on this screen that
  // changes without the teacher doing anything.
  //
  // Three details, and all three are the difference between a poll and a leak:
  //
  //   * `clearInterval` in the cleanup. Without it the timer outlives the
  //     screen — go back to the list and it keeps asking about a room nobody is
  //     looking at, forever, and again for every room opened after it.
  //   * `inFlight`, so a slow reply cannot stack. The free backend sleeps after
  //     fifteen minutes and its first reply can take half a minute; without
  //     this, ten more requests are sent while that one is still in the air.
  //   * `ignore`, so a reply that lands after the screen changed is dropped
  //     rather than drawn. The same guard as `openRun` in QuizMe.jsx.
  //
  // A failed poll is deliberately silent. One dropped request on a flaky
  // classroom wifi is not worth a red sentence over the code on the projector,
  // and the next tick is three seconds away.
  const openId = open?.id ?? null
  const openState = open?.state ?? null

  useEffect(() => {
    if (openId === null || openState === 'closed') return

    let ignore = false
    let inFlight = false

    const timer = setInterval(() => {
      if (inFlight) return
      inFlight = true

      getRoom(openId)
        .then((room) => {
          if (ignore) return
          // Compared by id inside the updater, which is handed the state as it
          // is NOW rather than as it was when the request went out.
          setOpen((current) => (current && current.id === room.id ? room : current))
        })
        .catch(() => {})
        .finally(() => {
          inFlight = false
        })
    }, POLL_MS)

    return () => {
      ignore = true
      clearInterval(timer)
    }
  }, [openId, openState])

  // ---------------------------------------------------------------------------
  // Doing things
  // ---------------------------------------------------------------------------

  async function handleOpenClass(event) {
    event.preventDefault()
    if (!quizId) return

    setBusy(true)
    setNotice(null)
    try {
      const room = await createRoom(Number(quizId))
      setRooms((current) => [room, ...current])
      setOpen(room)
    } catch (error) {
      setNotice(error?.message || 'Nibble could not open a class just then.')
    } finally {
      setBusy(false)
    }
  }

  async function handleState(nextState) {
    const roomId = open.id
    setBusy(true)
    setNotice(null)
    try {
      const room = await setRoomState(roomId, nextState)
      setOpen((current) => (current && current.id === roomId ? room : current))
      setRooms((current) => current.map((r) => (r.id === roomId ? room : r)))
    } catch (error) {
      setNotice(error?.message || 'Nibble could not change the class just then.')
    } finally {
      setBusy(false)
    }
  }

  async function handleShow(id) {
    setNotice(null)
    try {
      setOpen(await getRoom(id))
    } catch (error) {
      setNotice(error?.message || 'Nibble could not open that class.')
    }
  }

  async function handleDelete(id) {
    setNotice(null)
    try {
      await deleteRoom(id)
      setRooms((current) => current.filter((room) => room.id !== id))
      setOpen((current) => (current && current.id === id ? null : current))
    } catch (error) {
      setNotice(error?.message || 'Nibble could not delete that class.')
    }
  }

  // ---------------------------------------------------------------------------
  // What is on screen
  // ---------------------------------------------------------------------------

  if (open) {
    const joined = open.member_count

    return (
      <section className="card" style={{ marginTop: 'var(--gap-lg)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--gap)' }}>
          <h2 style={{ margin: 0 }}>{open.title}</h2>
          <Button
            variant="secondary"
            style={{ marginLeft: 'auto' }}
            onClick={() => setOpen(null)}
          >
            ← All classes
          </Button>
        </div>

        <p style={{ color: 'var(--text-muted)' }}>
          {STATE_WORDS[open.state]} · {open.question_count}{' '}
          {open.question_count === 1 ? 'question' : 'questions'}
        </p>

        {notice && (
          /* The word matters: coral alone carries the meaning by colour, which
             design.md forbids. The mark is the same point made twice over, and
             it is what lets the sentence itself stay ink — coral text is about
             3.2:1 on white, under the floor. See .notice-bad in global.css. */
          <p className="notice-bad">
            <span className="notice-bad__mark" aria-hidden="true">
              !
            </span>
            <span>
              <strong>Problem:</strong> {notice}
            </span>
          </p>
        )}

        {open.state !== 'closed' && (
          <>
            <p style={{ marginBottom: 'var(--gap-xs)', color: 'var(--text-muted)' }}>
              Put this on the board:
            </p>
            {/*
              The code, as big as the card allows, because it is being read off a
              projector from the back of a room. letterSpacing so a 6 and a G do
              not run together at that size.
            */}
            <p
              style={{
                fontFamily: 'var(--font-display)',
                fontSize: '3rem',
                letterSpacing: '0.12em',
                margin: 0,
                marginBottom: 'var(--gap)',
              }}
            >
              {open.code}
            </p>
          </>
        )}

        {/*
          role="status" so a screen reader announces the count changing without
          the teacher having to go looking for it. Same reason the answer and the
          search results have one.
        */}
        <p role="status" style={{ fontFamily: 'var(--font-display)' }}>
          {joined === 0 ? 'Nobody has joined yet.' : `${joined} ${joined === 1 ? 'student' : 'students'} joined`}
        </p>

        <div style={{ display: 'flex', gap: 'var(--gap-sm)', flexWrap: 'wrap' }}>
          {open.state === 'waiting' && (
            <Button
              variant="primary"
              disabled={busy}
              onClick={() => handleState('open')}
            >
              Start the quiz
            </Button>
          )}

          {open.state === 'open' && (
            <Button
              variant="accent"
              disabled={busy}
              onClick={() => handleState('closed')}
            >
              End the class
            </Button>
          )}

          {open.state === 'closed' && (
            <p style={{ color: 'var(--text-muted)', margin: 0 }}>
              This class has finished. What came back is below.
            </p>
          )}
        </div>

        {open.state === 'open' && (
          <p style={{ color: 'var(--text-muted)', marginBottom: 0 }}>
            Students are answering now. Ending the class stops anyone else handing in,
            and signs them out.
          </p>
        )}

        {/*
          Slice 8. Not while `waiting`, because nobody can have handed anything
          in yet and an empty marking table is noise on the screen with the code
          on it. From `open` onwards it shows the papers that are already in —
          the backend puts no state rule on this at all, and a fourth rule about
          state would buy nothing.

          Keyed by room id so moving between two classes rebuilds it rather than
          showing one room's marks under another's title while it fetches.
        */}
        {open.state !== 'waiting' && <Results key={open.id} roomId={open.id} />}
      </section>
    )
  }

  return (
    <section className="card" style={{ marginTop: 'var(--gap-lg)' }}>
      <h2 style={{ marginBottom: 'var(--gap-sm)' }}>Teach a class</h2>

      <p style={{ marginTop: 0, color: 'var(--text-muted)' }}>
        Run one of your quizzes as a class. Everybody joins with a code, answers at the
        same time, and you end it when you are done.
      </p>

      {notice && (
        <p className="notice-bad">
          <span className="notice-bad__mark" aria-hidden="true">
            !
          </span>
          <span>
            <strong>Problem:</strong> {notice}
          </span>
        </p>
      )}

      {listStatus === 'loading' && <p style={{ color: 'var(--text-muted)' }}>Loading…</p>}

      {listStatus === 'failed' && (
        <p className="notice-bad">
          <span className="notice-bad__mark" aria-hidden="true">
            !
          </span>
          <span>
            <strong>Problem:</strong>{' '}
            {listError || 'Nibble couldn’t fetch your classes just now. Try again in a moment.'}
          </span>
        </p>
      )}

      {listStatus === 'ready' && quizzes.length === 0 && (
        <p style={{ color: 'var(--text-muted)' }}>
          You need a quiz first. Make one under “Quiz me” in Your notes, then come back.
        </p>
      )}

      {listStatus === 'ready' && quizzes.length > 0 && (
        <form
          onSubmit={handleOpenClass}
          style={{ display: 'flex', gap: 'var(--gap-sm)', flexWrap: 'wrap', alignItems: 'center' }}
        >
          <label className="visually-hidden" htmlFor="room-quiz">
            Which quiz to run
          </label>
          <select
            id="room-quiz"
            className="input"
            value={quizId}
            onChange={(event) => setQuizId(event.target.value)}
            style={{ flex: 1, minWidth: 200 }}
          >
            <option value="">Pick a quiz…</option>
            {quizzes.map((quiz) => (
              <option key={quiz.id} value={quiz.id}>
                {quiz.title} ({quiz.question_count})
              </option>
            ))}
          </select>

          <Button type="submit" variant="primary" disabled={busy || !quizId}>
            {busy ? 'Opening…' : 'Open a class'}
          </Button>
        </form>
      )}

      {listStatus === 'ready' && rooms.length > 0 && (
        <ul style={{ listStyle: 'none', margin: 0, marginTop: 'var(--gap)', padding: 0 }}>
          {rooms.map((room) => (
            <li
              key={room.id}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--gap-sm)',
                padding: 'var(--gap-sm) 0',
                borderBottom: 'var(--border)',
              }}
            >
              <Button
                variant="plain"
                onClick={() => handleShow(room.id)}
                style={{
                  flex: 1,
                  padding: 0,
                }}
              >
                {room.title}
              </Button>

              <span className="source-chip">{room.code}</span>
              <span style={{ color: 'var(--text-muted)' }}>{STATE_WORDS[room.state]}</span>

              <Button
                variant="secondary"
                aria-label={`Delete the class ${room.title}`}
                onClick={() => handleDelete(room.id)}
              >
                ×
              </Button>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
