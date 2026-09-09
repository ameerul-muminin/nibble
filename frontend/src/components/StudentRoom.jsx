/**
 * Slice 7 — the student's half of the classroom. Issue #23.
 *
 * Type the code off the board, wait, answer, hand it in. Contract in
 * docs/api.md under "Slice 7".
 *
 * **Everything on this screen comes out of one value: `state`.** That is the
 * whole reason a room is a three-state machine rather than four booleans that
 * can disagree with each other — "what should be on screen right now" has one
 * answer, and it is a lookup rather than a puzzle.
 *
 *   waiting  → the lobby. You are in; your teacher has not started yet.
 *   open     → the questions, or "Submitted" if you already handed in.
 *   closed   → the class has ended, and you are signed out.
 *
 * **You never receive the answer key.** The questions arrive without `correct`
 * in them at all — this is somebody else's quiz, made from notes that are not
 * yours, and seeing answers follows ownership everywhere in Nibble.
 *
 * **And you are not shown a score.** The mark is worked out and stored the
 * moment you hand in, but your teacher can change it in slice 8, and a number
 * that later moves is worse than no number. Practising alone is the opposite
 * case and shows the score straight away, because there nobody is going to
 * overrule it.
 */

import { useEffect, useRef, useState } from 'react'
import { useClerk, useUser } from '@clerk/react'
import { getStudentRoom, joinRoom, submitAnswers } from '../api'
import { POLL_MS } from './Classroom'

/** A letter per option, so a question reads like a real exam paper. */
const LETTERS = ['A', 'B', 'C', 'D']

/**
 * How long the "that is the end" card stays up before the student is signed out.
 *
 * Signing out immediately is what was asked for and it is what happens — but
 * signing out unmounts this whole screen and drops the person on the landing
 * page, so doing it the instant the poll reports `closed` means the sentence
 * explaining what just happened never gets read. Four seconds is long enough to
 * read one line, and the button below it is there for anybody who does not want
 * to wait.
 */
const SIGN_OUT_MS = 4000

export function StudentRoom() {
  const { signOut } = useClerk()

  // Slice 8: what the teacher's marking screen will call this person.
  //
  // Read from Clerk rather than asked for, because a box saying "your name"
  // is one more thing to fill in while thirty people are typing a code off a
  // projector, and Clerk already knows.
  //
  // Every one of these can be missing — Clerk allows an account with an email
  // and nothing else — so this falls through to '' and the backend calls them
  // "Student 1" by join order. An empty name is normal here, not an error.
  //
  // **`isLoaded` matters as much as `user` does**, and leaving it out was a bug
  // review caught. Being signed in does not mean the profile has arrived: for
  // the first moments after this screen mounts, `user` is undefined and the
  // name falls through to '' — which is indistinguishable, here, from somebody
  // who genuinely has no name. Join in that window and the backend stores the
  // empty one, and `INSERT OR IGNORE` means the first join wins *forever*: the
  // student is "Student 3" on the marking screen for the rest of the lesson,
  // even though Clerk knew their name a heartbeat later.
  //
  // So joining waits for this. It is a fraction of a second, against typing a
  // six-character code, and it is the difference between a name and a number.
  const { user, isLoaded } = useUser()
  const myName = user?.fullName || user?.firstName || user?.username || ''

  // What the student typed, before it is a room.
  const [code, setCode] = useState('')
  const [joining, setJoining] = useState(false)
  const [notice, setNotice] = useState(null)

  // The code of the room actually joined. null means the join form is showing.
  //
  // This is deliberately not remembered anywhere: refresh the page and you type
  // the code again. Storing it would be a fourth place the truth about "which
  // class am I in" lives, and the code is on the board in front of you.
  const [joined, setJoined] = useState(null)

  // The last thing the poll said. Everything below is drawn from this.
  const [room, setRoom] = useState(null)

  // Question id → the index of the option picked. Lives here and nowhere else
  // until Hand it in, which is why nothing is stored for an unfinished paper.
  const [picked, setPicked] = useState({})
  const [sending, setSending] = useState(false)

  // ---------------------------------------------------------------------------
  // The poll
  // ---------------------------------------------------------------------------
  //
  // Once every three seconds, the same shape as the teacher's, and for the same
  // three reasons: clearInterval in the cleanup so the timer cannot outlive the
  // screen, `inFlight` so a slow reply on a sleeping backend cannot stack, and
  // `ignore` so a reply that lands after this screen has gone is dropped.
  //
  // It runs once immediately as well as on the interval. Without that, joining a
  // class shows an empty lobby for three seconds before anything appears, which
  // reads as broken.
  useEffect(() => {
    if (!joined) return

    let ignore = false
    let inFlight = false

    const tick = () => {
      if (inFlight) return
      inFlight = true

      getStudentRoom(joined)
        .then((next) => {
          if (!ignore) setRoom(next)
        })
        .catch((error) => {
          // A dropped poll is silent — the next one is three seconds away. A
          // 404 is not: it means the class was deleted while you were in it, and
          // sitting in a lobby forever is worse than being told.
          if (ignore) return
          if (error?.status === 404) {
            setJoined(null)
            setRoom(null)
            setNotice('That class is no longer there. Ask your teacher for a new code.')
          }
        })
        .finally(() => {
          inFlight = false
        })
    }

    tick()
    const timer = setInterval(tick, POLL_MS)

    return () => {
      ignore = true
      clearInterval(timer)
    }
  }, [joined])

  // ---------------------------------------------------------------------------
  // Being signed out when the class ends
  // ---------------------------------------------------------------------------
  //
  // Stated as a cost rather than discovered as one: this is a real sign-out, so
  // a student who wants to go back to their own notes has to sign in again.
  //
  // The ref stops a second timer being started if the poll reports `closed`
  // again — which it will, every three seconds, until the sign-out lands.
  const signingOut = useRef(false)

  useEffect(() => {
    if (room?.state !== 'closed' || signingOut.current) return

    signingOut.current = true
    const timer = setTimeout(() => signOut(), SIGN_OUT_MS)

    return () => clearTimeout(timer)
  }, [room?.state, signOut])

  // ---------------------------------------------------------------------------
  // Doing things
  // ---------------------------------------------------------------------------

  async function handleJoin(event) {
    event.preventDefault()
    // `isLoaded` as well as the code, because the button is not the only way
    // into this function — Enter in the text box submits the form too, and a
    // disabled button would not have stopped it. See the note over useUser: a
    // join sent before Clerk has the profile stores an empty name permanently.
    if (!code.trim() || !isLoaded) return

    setJoining(true)
    setNotice(null)
    try {
      const entry = await joinRoom(code, myName)
      setJoined(entry.code)
      setPicked({})
    } catch (error) {
      setNotice(error?.message || 'Nibble could not find that class.')
    } finally {
      setJoining(false)
    }
  }

  async function handleHandIn() {
    const answers = Object.entries(picked).map(([questionId, chosen]) => ({
      question_id: Number(questionId),
      chosen,
    }))

    if (answers.length === 0) return

    setSending(true)
    setNotice(null)
    try {
      await submitAnswers(room.room_id, answers)
      // Set here rather than waiting for the next poll to say so, which would
      // leave the paper on screen for up to three seconds after handing it in
      // and invite a second press.
      setRoom((current) => (current ? { ...current, submitted: true } : current))
    } catch (error) {
      setNotice(error?.message || 'Nibble could not hand that in.')
    } finally {
      setSending(false)
    }
  }

  // ---------------------------------------------------------------------------
  // What is on screen
  // ---------------------------------------------------------------------------

  const problem = notice && (
    /* The word, not just the colour — design.md forbids meaning by colour alone.
       The sentence stays ink because coral text is about 3.2:1 on white, under
       the 4.5:1 floor; the coral lives in the mark instead. */
    <p className="notice-bad">
      <span className="notice-bad__mark" aria-hidden="true">
        !
      </span>
      <span>
        <strong>Problem:</strong> {notice}
      </span>
    </p>
  )

  if (!joined) {
    return (
      <section className="card" style={{ marginTop: 'var(--gap-lg)' }}>
        <h2 style={{ marginBottom: 'var(--gap-sm)' }}>Join a class</h2>
        <p style={{ marginTop: 0, color: 'var(--text-muted)' }}>
          Type the code your teacher put on the board.
        </p>

        {problem}

        <form onSubmit={handleJoin} className="form-row">
          <label className="visually-hidden" htmlFor="class-code">
            Class code
          </label>
          <input
            id="class-code"
            className="input"
            value={code}
            onChange={(event) => setCode(event.target.value)}
            placeholder="K7M2QP"
            autoComplete="off"
            maxLength={12}
            style={{
              flex: 1,
              minWidth: 160,
              fontFamily: 'var(--font-display)',
              letterSpacing: '0.12em',
              textTransform: 'uppercase',
            }}
          />
          <button
            type="submit"
            className="btn btn--primary"
            disabled={joining || !code.trim() || !isLoaded}
          >
            {joining ? 'Joining…' : 'Join'}
          </button>
        </form>
      </section>
    )
  }

  if (!room) {
    return (
      <section className="card" style={{ marginTop: 'var(--gap-lg)' }}>
        <p style={{ color: 'var(--text-muted)', margin: 0 }}>Finding the class…</p>
      </section>
    )
  }

  if (room.state === 'closed') {
    return (
      <section className="card" style={{ marginTop: 'var(--gap-lg)' }} role="status">
        <h2 style={{ marginBottom: 'var(--gap-sm)' }}>That’s the end of the class</h2>
        <p style={{ color: 'var(--text-muted)' }}>
          Thanks for taking part. Your teacher has everything you handed in. Nibble is
          signing you out.
        </p>
        <button type="button" className="btn btn--primary" onClick={() => signOut()}>
          Sign out now
        </button>
      </section>
    )
  }

  if (room.state === 'waiting') {
    return (
      <section className="card" style={{ marginTop: 'var(--gap-lg)' }}>
        <h2 style={{ marginBottom: 'var(--gap-sm)' }}>{room.title}</h2>
        <p role="status" style={{ color: 'var(--text-muted)' }}>
          You’re in. Waiting for your teacher to start…
        </p>
        {problem}
      </section>
    )
  }

  if (room.submitted) {
    return (
      <section className="card" style={{ marginTop: 'var(--gap-lg)' }} role="status">
        <h2 style={{ marginBottom: 'var(--gap-sm)' }}>Submitted</h2>
        <p style={{ color: 'var(--text-muted)', marginBottom: 0 }}>
          That’s handed in. Your teacher will go through the answers — hang on until they
          end the class.
        </p>
      </section>
    )
  }

  const answered = Object.keys(picked).length

  return (
    <section className="card" style={{ marginTop: 'var(--gap-lg)' }}>
      <h2 style={{ marginBottom: 'var(--gap-sm)' }}>{room.title}</h2>
      <p style={{ marginTop: 0, color: 'var(--text-muted)' }}>
        {answered} of {room.questions.length} answered. You can hand in early.
      </p>

      {problem}

      <ol style={{ listStyle: 'none', margin: 0, padding: 0 }}>
        {room.questions.map((question, index) => (
          <li
            key={question.id}
            style={{
              border: 'var(--border)',
              borderRadius: 'var(--radius)',
              padding: 'var(--gap)',
              marginBottom: 'var(--gap)',
            }}
          >
            <p style={{ marginTop: 0, fontFamily: 'var(--font-display)' }}>
              {index + 1}. {question.prompt}
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--gap-xs)' }}>
              {question.options.map((option, optionIndex) => {
                const chosen = picked[question.id] === optionIndex

                return (
                  <button
                    key={optionIndex}
                    type="button"
                    // aria-pressed is what tells a screen reader this button is a
                    // choice that is currently made, rather than an action. The
                    // lime background says the same thing to everyone else, and
                    // neither is doing the job on its own.
                    aria-pressed={chosen}
                    onClick={() =>
                      setPicked((current) => ({ ...current, [question.id]: optionIndex }))
                    }
                    style={{
                      textAlign: 'left',
                      background: chosen ? 'var(--lime)' : 'var(--paper)',
                      border: 'var(--border)',
                      borderRadius: 'var(--radius-sm)',
                      padding: 'var(--gap-sm)',
                      font: 'inherit',
                      cursor: 'pointer',
                    }}
                  >
                    <strong style={{ fontFamily: 'var(--font-display)' }}>
                      {LETTERS[optionIndex]}
                    </strong>{' '}
                    {option}
                  </button>
                )
              })}
            </div>
          </li>
        ))}
      </ol>

      <button
        type="button"
        className="btn btn--primary"
        disabled={sending || answered === 0}
        onClick={handleHandIn}
      >
        {sending ? 'Handing in…' : 'Hand it in'}
      </button>

      <p style={{ color: 'var(--text-muted)', marginBottom: 0 }}>
        You can only hand in once, so check your answers first.
      </p>
    </section>
  )
}
