/**
 * Slice 8 — marking. What the class handed in, and the teacher's last word.
 *
 * Two tables out of one response: what each question did across the room, and
 * what each student put. Contract in docs/api.md under "Slice 8".
 *
 * **The marks are already decided when this screen opens.** They were worked out
 * and stored at submit time, in slice 7, before anything read them — which is
 * what makes changing one an ordinary edit rather than a second rule competing
 * with the first. Everything here either shows a stored mark or changes it.
 *
 * **This is the one screen in Nibble that holds the answer key**, because it is
 * the only one whose reader owns the quiz. The student's poll strips `correct`
 * field by field. Do not copy shapes from here into anything a student opens.
 *
 * Its own file rather than more of App.jsx, for the third slice running — see
 * the top of QuizMe.jsx and Classroom.jsx. The slice 8 checklist in scope.md
 * originally said App.jsx and was corrected rather than followed.
 */

import { useCallback, useEffect, useState } from 'react'
import { getResults, setMark } from '../api'
import { Button } from './Button'

/**
 * A student's answers, drawn against every question rather than only the ones
 * they answered.
 *
 * That is the point of walking the questions instead of the answers: a student
 * who ran out of time simply has no row for question 4, and a table built from
 * their answers alone would silently not have a line for it. A partial paper
 * should look partial.
 */
function StudentAnswers({ questions, answers, busyId, onMark }) {
  return (
    <ol style={{ margin: 'var(--gap-sm) 0 0', paddingLeft: '1.4em' }}>
      {questions.map((question) => {
        const answer = answers.find((a) => a.question_id === question.id)

        if (!answer) {
          return (
            <li key={question.id} style={{ marginBottom: 'var(--gap-sm)' }}>
              <span style={{ color: 'var(--text-muted)' }}>{question.prompt}</span>
              <br />
              {/*
                Not wrong — unanswered. And there is no mark to change, because
                there is no answer row to change it on. See the note in
                docs/api.md: giving credit for a blank needs a nullable `chosen`
                and a decision about what such a row means, which is a slice of
                its own.
              */}
              <em style={{ color: 'var(--text-faint)' }}>Not answered</em>
            </li>
          )
        }

        const right = answer.mark === 1

        return (
          <li key={question.id} style={{ marginBottom: 'var(--gap-sm)' }}>
            <span style={{ color: 'var(--text-muted)' }}>{question.prompt}</span>
            <br />

            <span>
              Put: <strong>{question.options[answer.chosen]}</strong>
            </span>

            {answer.chosen !== question.correct && (
              <span style={{ color: 'var(--text-muted)' }}>
                {' '}
                · answer: {question.options[question.correct]}
              </span>
            )}

            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--gap-sm)',
                marginTop: 'var(--gap-xs)',
                flexWrap: 'wrap',
              }}
            >
              {/*
                The word as well as the colour. design.md: colour never carries
                meaning alone, so mint and coral are never the only difference
                between a right answer and a wrong one.
              */}
              <span
                style={{
                  background: right ? 'var(--mint)' : 'var(--coral)',
                  border: 'var(--border)',
                  borderRadius: 'var(--radius-pill)',
                  padding: '2px var(--gap-sm)',
                  fontFamily: 'var(--font-display)',
                }}
              >
                {right ? 'Right' : 'Wrong'}
              </span>

              {/*
                aria-pressed rather than two buttons that look selected: a screen
                reader is told which of the two the mark currently is, not just
                that there are two buttons here.
              */}
              <Button
                variant="secondary"
                aria-pressed={right}
                disabled={busyId === answer.id || right}
                onClick={() => onMark(answer.id, 1)}
              >
                Mark right
              </Button>

              <Button
                variant="secondary"
                aria-pressed={!right}
                disabled={busyId === answer.id || !right}
                onClick={() => onMark(answer.id, 0)}
              >
                Mark wrong
              </Button>

              {answer.overridden && (
                <span style={{ color: 'var(--text-muted)' }}>
                  {/*
                    Not stored anywhere. It is `mark != (chosen == correct)`,
                    worked out by the backend when it read the row — which is
                    why marking something back to what Nibble said makes this
                    disappear again. Undo is just marking it back.
                  */}
                  Changed by you
                </span>
              )}
            </div>
          </li>
        )
      })}
    </ol>
  )
}

export function Results({ roomId }) {
  const [data, setData] = useState(null)
  const [status, setStatus] = useState('loading') // loading | ready | failed
  const [error, setError] = useState(null)

  // Which answer is mid-save. One at a time, by id, so two rows cannot both
  // show a spinner while only one of them is really waiting.
  const [busyId, setBusyId] = useState(null)
  const [notice, setNotice] = useState(null)

  // Whose paper is open. A set of user_ids: thirty students each with ten
  // questions is three hundred lines on screen at once, and nobody marks like
  // that. Closed by default, and more than one can be open.
  const [shown, setShown] = useState([])

  /**
   * Fetch the lot.
   *
   * `quiet` skips the loading state, which is what a refresh after an override
   * wants: the table is already on screen and correct apart from one number,
   * and blanking it to "Loading…" for half a second loses the teacher's place.
   *
   * A quiet refresh that fails **rethrows instead of showing the failed screen**.
   * The first load has nothing to keep, so failing replaces the screen; a
   * refresh has a whole marked table on screen and a teacher part way down it,
   * and throwing that away to report a dropped request would lose more than the
   * request did. The caller turns it into a line at the top instead.
   */
  const load = useCallback(
    (quiet = false) => {
      if (!quiet) setStatus('loading')

      return getResults(roomId)
        .then((results) => {
          setData(results)
          setStatus('ready')
          setError(null)
        })
        .catch((problem) => {
          if (quiet) throw problem

          // The backend's own sentence. A fixed line here once sent somebody to
          // check a backend that was running perfectly well — see the note under
          // slice 7 in scope.md.
          setError(problem?.message || null)
          setStatus('failed')
        })
    },
    [roomId],
  )

  useEffect(() => {
    load()
  }, [load])

  /**
   * Change one mark, then refetch.
   *
   * **The refetch is the point, not laziness.** The response to the PATCH
   * carries the answer itself, so applying it in place would be easy — but the
   * per-question counts and the flag would then have to be recomputed here, and
   * the flag rule would exist twice: once in routes.py and once in this file,
   * free to disagree. One extra request, on a screen used after a class rather
   * than during one, buys a single source of truth for the whole table.
   */
  async function handleMark(answerId, mark) {
    setBusyId(answerId)
    setNotice(null)
    try {
      await setMark(roomId, answerId, mark)
      await load(true)
    } catch (problem) {
      setNotice(problem?.message || 'Nibble could not change that mark just then.')
    } finally {
      setBusyId(null)
    }
  }

  /**
   * The Refresh button. Its own function only so the rejection `load(true)` now
   * throws has somewhere to land — an uncaught one is a red line in the console
   * and nothing on screen, which is the opposite of what a failed refresh
   * should do.
   */
  function handleRefresh() {
    setNotice(null)
    load(true).catch((problem) => {
      setNotice(problem?.message || 'Nibble could not refresh this class just then.')
    })
  }

  function toggle(userId) {
    setShown((current) =>
      current.includes(userId) ? current.filter((id) => id !== userId) : [...current, userId],
    )
  }

  if (status === 'loading') {
    return <p style={{ color: 'var(--text-muted)' }}>Loading what came back…</p>
  }

  if (status === 'failed') {
    return (
      <p className="notice-bad">
        <span className="notice-bad__mark" aria-hidden="true">
          !
        </span>
        <span>
          <strong>Problem:</strong> {error || 'Could not load this class.'}
        </span>
      </p>
    )
  }

  const { questions, students } = data
  const handedIn = students.filter((student) => student.submitted).length

  return (
    <section style={{ marginTop: 'var(--gap-lg)', borderTop: 'var(--border)', paddingTop: 'var(--gap)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--gap)', flexWrap: 'wrap' }}>
        <h3 style={{ margin: 0 }}>Marking</h3>

        <Button
          variant="secondary"
          style={{ marginLeft: 'auto' }}
          onClick={handleRefresh}
        >
          Refresh
        </Button>
      </div>

      {/*
        No poll on this screen, deliberately. Classroom.jsx already asks about
        this room every three seconds for the joiner count; a second poll
        dragging every answer in the class across the wire, to keep a table
        current that nobody is reading yet, spends the tenth of a CPU slice 7
        was careful with. Marking happens after the class.
      */}
      <p role="status" style={{ color: 'var(--text-muted)' }}>
        {handedIn} of {students.length} handed in.
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

      {students.length === 0 && (
        <p style={{ color: 'var(--text-muted)' }}>Nobody has joined this class yet.</p>
      )}

      {students.length > 0 && (
        <>
          <h4 style={{ marginBottom: 'var(--gap-sm)' }}>By question</h4>

          <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
            {questions.map((question) => (
              <li
                key={question.id}
                style={{
                  display: 'flex',
                  alignItems: 'baseline',
                  gap: 'var(--gap-sm)',
                  padding: 'var(--gap-xs) 0',
                  borderBottom: 'var(--border)',
                  flexWrap: 'wrap',
                }}
              >
                <span style={{ flex: 1, minWidth: 200 }}>{question.prompt}</span>

                <span style={{ fontFamily: 'var(--font-display)' }}>
                  {question.right} of {question.answered} right
                </span>

                {question.flagged && (
                  // The word carries it, not the colour. A flag is "look at
                  // this question", not "this class is bad" — most of the room
                  // getting something wrong usually says more about how it was
                  // worded than about who answered it.
                  <span
                    style={{
                      background: 'var(--coral)',
                      border: 'var(--border)',
                      borderRadius: 'var(--radius-pill)',
                      padding: '2px var(--gap-sm)',
                      fontFamily: 'var(--font-display)',
                    }}
                  >
                    Most got this wrong
                  </span>
                )}
              </li>
            ))}
          </ul>

          <h4 style={{ marginTop: 'var(--gap-lg)', marginBottom: 'var(--gap-sm)' }}>By student</h4>

          <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
            {students.map((student) => {
              const open = shown.includes(student.user_id)

              return (
                <li
                  key={student.user_id}
                  style={{ padding: 'var(--gap-sm) 0', borderBottom: 'var(--border)' }}
                >
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 'var(--gap-sm)',
                      flexWrap: 'wrap',
                    }}
                  >
                    <span style={{ flex: 1, minWidth: 140 }}>{student.name}</span>

                    {student.submitted ? (
                      <span style={{ fontFamily: 'var(--font-display)' }}>
                        {student.score} / {questions.length}
                      </span>
                    ) : (
                      <span style={{ color: 'var(--text-muted)' }}>Not handed in</span>
                    )}

                    {student.submitted && (
                      <Button
                        variant="secondary"
                        aria-expanded={open}
                        onClick={() => toggle(student.user_id)}
                      >
                        {open ? 'Hide answers' : 'Show answers'}
                      </Button>
                    )}
                  </div>

                  {open && student.submitted && (
                    <StudentAnswers
                      questions={questions}
                      answers={student.answers}
                      busyId={busyId}
                      onMark={handleMark}
                    />
                  )}
                </li>
              )
            })}
          </ul>
        </>
      )}
    </section>
  )
}
