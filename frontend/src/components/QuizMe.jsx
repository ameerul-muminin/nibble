/**
 * Slice 6 — Quiz yourself.
 *
 * Pick a note, let Nibble write questions from it, fix the ones that came out
 * wrong, then practise. Contract in docs/api.md under "Slice 6".
 *
 * **This lives in its own file rather than in App.jsx**, which is a small
 * departure from the plan in docs/scope.md and is noted there. App.jsx was
 * already past a thousand lines before this slice; another three hundred would
 * have made the one file nobody wants to open.
 *
 * Three things happen here, and they are three states rather than three screens:
 *
 *   list      - your quizzes, and the form to make another
 *   editing   - one quiz, with every answer visible, each question fixable
 *   taking    - the same quiz, answers hidden until you pick one
 *
 * **Practice stores nothing.** The score lives in this component and closing the
 * tab ends it. That is possible because GET /quizzes/{id} returns `correct` —
 * it is your quiz, made from your notes — so the browser already holds the key
 * and marks as you go. Marks are only ever stored for a classroom, where
 * somebody other than you needs to see them, and that is slice 8.
 */

import { useEffect, useRef, useState } from 'react'
import {
  createQuiz,
  deleteQuestion,
  deleteQuiz,
  getQuiz,
  listQuizzes,
  updateQuestion,
} from '../api'

/** A letter for each option, so a question reads like a real exam paper. */
const LETTERS = ['A', 'B', 'C', 'D']

export function QuizMe({ docs, onNoteGone }) {
  // Which quizzes exist, and whether we have managed to load them yet.
  const [quizzes, setQuizzes] = useState([])
  const [listStatus, setListStatus] = useState('loading') // loading | ready | failed
  const [listError, setListError] = useState(null)

  // The quiz currently open, with its questions. null means the list is showing.
  const [open, setOpen] = useState(null)

  // 'editing' or 'taking'. Only meaningful while `open` is set.
  const [mode, setMode] = useState('editing')

  // The form for making a new one.
  const [noteId, setNoteId] = useState('')
  const [title, setTitle] = useState('')
  const [count, setCount] = useState(5)
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState(null)

  // Practice state. `picked` maps a question id to the option index chosen, so
  // it survives scrolling and re-renders without anything being stored.
  const [picked, setPicked] = useState({})

  // Which attempt to change what is on screen is the newest one.
  //
  // Every action that opens, closes or replaces the open quiz takes the next
  // number, and a reply only writes if its number is still current. Without it,
  // a slow request wins over a newer one just by finishing later: click
  // Practise on quiz A, change your mind and click Edit on quiz B, and A's
  // reply lands afterwards and puts A on screen in B's mode. Deleting A while
  // it was loading reopened it. Making a new quiz while one was loading got
  // replaced by the old one.
  //
  // The same guard, and the same reason, as `searchRun` in App.jsx. A ref
  // rather than state because changing it must not cause a render — it is
  // bookkeeping about renders, not something to draw.
  const openRun = useRef(0)

  // Which quiz `handleOpen` is currently fetching, or null when nothing is in
  // flight. It exists so a delete can tell whether it is interfering with a
  // load or is unrelated to it — see handleDeleteQuiz.
  const openingId = useRef(null)

  useEffect(() => {
    let ignore = false

    listQuizzes()
      .then((rows) => {
        if (ignore) return
        setQuizzes(rows)
        setListStatus('ready')
      })
      .catch((error) => {
        if (ignore) return
        // The backend's own sentence, for the reason written into App's notes
        // list: a fixed line here once sent somebody to check a backend that
        // was running perfectly.
        setListError(error?.message || null)
        setListStatus('failed')
      })

    return () => {
      ignore = true
    }
  }, [])

  async function handleCreate(event) {
    event.preventDefault()

    const name = title.trim()
    if (!noteId || !name) return

    // Noted, not claimed. The run is only taken over once the quiz actually
    // exists — see below, and see handleDeleteQuiz for the same rule.
    const runAtStart = openRun.current

    setBusy(true)
    setNotice(null)
    try {
      const quiz = await createQuiz(Number(noteId), name, count)

      // Straight into editing. The whole point of this slice is that the model
      // gets questions wrong and you fix them, so landing on the list would put
      // an extra click in front of the thing you came to do.
      //
      // **The run is claimed here, on success, and not at the top.** Claiming it
      // up front cancelled any quiz that was still opening — on the assumption
      // that this creation would work. Generation is the request in this app
      // most likely NOT to: it calls the model, and a rate limit or a rejected
      // reply is an ordinary afternoon on the free tier. Every one of those
      // failures also threw away an open the person was still waiting for, and
      // told them only about the generation.
      //
      // The `===` is what keeps it honest in the other direction: if something
      // newer was asked for while this was writing — and writing takes seconds,
      // so it is the easiest of all of these to click past — that newer thing
      // keeps the screen and the finished quiz just joins the list below.
      if (openRun.current === runAtStart) {
        openRun.current = runAtStart + 1
        openingId.current = null
        setOpen(quiz)
        setMode('editing')
      }
      setQuizzes((current) => [
        {
          id: quiz.id,
          document_id: quiz.document_id,
          title: quiz.title,
          question_count: quiz.questions.length,
          created_at: quiz.created_at,
        },
        ...current,
      ])
      setTitle('')
    } catch (error) {
      // 422 is the one failure with a different fix: the note predates chunking,
      // so no amount of retrying helps and re-uploading is the answer. This is
      // why request() attaches `status` — matching on message text would break
      // the moment somebody improved a word.
      if (error?.status === 422 && onNoteGone) {
        onNoteGone(Number(noteId))
      }
      setNotice(error?.message || 'Nibble could not write questions just now.')
    } finally {
      setBusy(false)
    }
  }

  async function handleOpen(id, nextMode) {
    const run = openRun.current + 1
    openRun.current = run
    openingId.current = id

    setNotice(null)
    try {
      const quiz = await getQuiz(id)

      // Somebody asked for something else while this was in the air. Their
      // request is the one that should win, whatever order the replies arrive
      // in, so this one is dropped rather than drawn.
      if (openRun.current !== run) return

      setOpen(quiz)
      setMode(nextMode)
      setPicked({})
    } catch (error) {
      if (openRun.current !== run) return
      setNotice(error?.message || 'Nibble could not open that quiz.')
    } finally {
      // Only clear it if this is still the load in progress. A newer open will
      // have overwritten it, and clearing then would tell a later delete that
      // nothing is loading when something is.
      if (openRun.current === run) {
        openingId.current = null
      }
    }
  }

  async function handleDeleteQuiz(id) {
    setNotice(null)
    try {
      await deleteQuiz(id)

      // Cancelling the in-flight open happens **here**, after the delete has
      // actually succeeded, and the position of these four lines is the whole
      // fix.
      //
      // They used to sit above the `await`, which cancelled on the assumption
      // that the delete would work. When it did not — an expired session, a
      // dropped connection, a 500 — the quiz was still there, the open that was
      // already on its way had been thrown away, and the person was left with
      // an error about deleting and a screen that had quietly refused to
      // navigate. Two failures reported as one.
      //
      // Cancelling only on success still closes the original bug, because the
      // only reason to cancel is that the quiz is gone. If its reply already
      // landed while the delete was in flight, it is on screen now and the line
      // below takes it off again.
      if (openingId.current === id) {
        openRun.current += 1
        openingId.current = null
      }

      setQuizzes((current) => current.filter((quiz) => quiz.id !== id))
      setOpen((current) => (current && current.id === id ? null : current))
    } catch (error) {
      // Nothing is cancelled on this path, on purpose: the quiz still exists,
      // so an open of it is still a perfectly good thing to be waiting for.
      setNotice(error?.message || 'Nibble could not delete that quiz.')
    }
  }

  // Both handlers below capture `quizId` before the request and check it again
  // when the reply lands, and that guard is doing real work rather than being
  // defensive out of habit.
  //
  // Press Save and then "← All quizzes" before the reply arrives, and `open` is
  // null by the time it does. The old version spread it — `{...null}` is `{}` —
  // and then read `.questions` off that, which throws during render. Open a
  // DIFFERENT quiz in that window and it was worse than a crash: the reply was
  // applied to whichever quiz happened to be open, so a question from one quiz
  // appeared in another and the change looked saved when it was not.
  //
  // Comparing ids inside the updater is what makes it safe, because the updater
  // is handed the state as it is NOW rather than as it was when the request
  // started.

  async function handleSaveQuestion(questionId, changes) {
    const quizId = open.id
    setNotice(null)
    try {
      const updated = await updateQuestion(quizId, questionId, changes)
      setOpen((current) =>
        current?.id === quizId
          ? {
              ...current,
              questions: current.questions.map((q) => (q.id === questionId ? updated : q)),
            }
          : current,
      )
    } catch (error) {
      setNotice(error?.message || 'Nibble could not save that change.')
    }
  }

  async function handleDeleteQuestion(questionId) {
    const quizId = open.id
    setNotice(null)
    try {
      await deleteQuestion(quizId, questionId)
      setOpen((current) =>
        current?.id === quizId
          ? {
              ...current,
              questions: current.questions.filter((q) => q.id !== questionId),
            }
          : current,
      )
      // The count in the list is corrected whichever quiz is open now — the
      // deletion really happened, so the row should show it even if you have
      // navigated back to the list to look at it.
      setQuizzes((current) =>
        current.map((quiz) =>
          quiz.id === quizId ? { ...quiz, question_count: quiz.question_count - 1 } : quiz,
        ),
      )
    } catch (error) {
      // The backend refuses to delete the last question, with a sentence saying
      // to delete the quiz instead. Showing it unchanged is the whole handling.
      setNotice(error?.message || 'Nibble could not delete that question.')
    }
  }

  const answered = open ? open.questions.filter((q) => picked[q.id] !== undefined) : []
  const score = open
    ? answered.filter((q) => picked[q.id] === q.correct).length
    : 0

  return (
    <section className="card">
      <h2 style={{ marginBottom: 'var(--gap-sm)' }}>Quiz me</h2>
      <p style={{ color: 'var(--text-muted)', marginTop: 0 }}>
        Nibble writes questions from one of your notes, and tells you which page each
        one came from. Fix the ones it got wrong, then test yourself.
      </p>

      {notice && (
        <p role="status" className="notice-bad">
          <span className="notice-bad__mark" aria-hidden="true">
            !
          </span>
          {notice}
        </p>
      )}

      {open === null ? (
        <>
          <form
            onSubmit={handleCreate}
            style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--gap-sm)' }}
          >
            <label htmlFor="quiz-note" className="visually-hidden">
              Which note should Nibble use?
            </label>
            <select
              id="quiz-note"
              className="input"
              value={noteId}
              onChange={(event) => setNoteId(event.target.value)}
              disabled={busy || docs.length === 0}
              style={{ flex: '1 1 200px' }}
            >
              <option value="">Pick a note…</option>
              {docs.map((doc) => (
                <option key={doc.id} value={doc.id}>
                  {doc.filename}
                </option>
              ))}
            </select>

            <label htmlFor="quiz-title" className="visually-hidden">
              What should this quiz be called?
            </label>
            <input
              id="quiz-title"
              className="input"
              placeholder="Call it something"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              disabled={busy}
              style={{ flex: '1 1 200px' }}
            />

            <label htmlFor="quiz-count" className="visually-hidden">
              How many questions?
            </label>
            <select
              id="quiz-count"
              className="input"
              value={count}
              onChange={(event) => setCount(Number(event.target.value))}
              disabled={busy}
            >
              {[3, 5, 10].map((n) => (
                <option key={n} value={n}>
                  {n} questions
                </option>
              ))}
            </select>

            <button
              type="button"
              className="btn btn--primary"
              disabled={busy || !noteId || !title.trim()}
              onClick={handleCreate}
            >
              {busy ? 'Writing…' : 'Write questions'}
            </button>
          </form>

          {docs.length === 0 && (
            <p style={{ color: 'var(--text-muted)' }}>
              Add a note first and Nibble can make a quiz from it.
            </p>
          )}

          {busy && (
            <p role="status" style={{ color: 'var(--text-muted)' }}>
              Reading your note and writing questions. This takes a few seconds.
            </p>
          )}

          {listStatus === 'loading' && (
            <p style={{ color: 'var(--text-muted)' }}>Fetching your quizzes…</p>
          )}

          {listStatus === 'failed' && (
            <p style={{ color: 'var(--text-muted)' }}>
              {listError || 'Could not load your quizzes.'}
            </p>
          )}

          {listStatus === 'ready' && quizzes.length === 0 && (
            <p style={{ color: 'var(--text-muted)' }}>
              No quizzes yet. Pick a note above and Nibble will write some questions.
            </p>
          )}

          {quizzes.map((quiz) => (
            <div
              key={quiz.id}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--gap-sm)',
                padding: 'var(--gap-sm) 0',
                borderBottom: '1px solid var(--text-faint)',
              }}
            >
              <div style={{ flex: 1 }}>
                <strong>{quiz.title}</strong>
                <div style={{ color: 'var(--text-muted)', fontSize: '0.9em' }}>
                  {quiz.question_count}{' '}
                  {quiz.question_count === 1 ? 'question' : 'questions'}
                </div>
              </div>
              <button
                type="button"
                className="btn btn--accent"
                onClick={() => handleOpen(quiz.id, 'taking')}
              >
                Practise
              </button>
              <button
                type="button"
                className="btn btn--secondary"
                onClick={() => handleOpen(quiz.id, 'editing')}
              >
                Edit
              </button>
              <button
                type="button"
                className="btn btn--secondary"
                aria-label={`Delete the quiz ${quiz.title}`}
                onClick={() => handleDeleteQuiz(quiz.id)}
              >
                ×
              </button>
            </div>
          ))}
        </>
      ) : (
        <>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--gap-sm)',
              marginBottom: 'var(--gap)',
            }}
          >
            <button
              type="button"
              className="btn btn--secondary"
              onClick={() => {
                // Going back is an intent too: a quiz still loading must not
                // reopen itself after you have left. Unconditional for the same
                // reason as making one — this is explicitly about what should be
                // on screen. See openRun above.
                openRun.current += 1
                openingId.current = null
                setOpen(null)
              }}
            >
              ← All quizzes
            </button>
            <strong style={{ flex: 1 }}>{open.title}</strong>
            <button
              type="button"
              className="btn btn--secondary"
              onClick={() => {
                setMode(mode === 'taking' ? 'editing' : 'taking')
                setPicked({})
              }}
            >
              {mode === 'taking' ? 'Edit questions' : 'Practise'}
            </button>
          </div>

          {mode === 'taking' && answered.length > 0 && (
            <p className="streak" role="status">
              {score} out of {answered.length} so far.
            </p>
          )}

          {open.questions.map((question, index) => (
            <Question
              key={question.id}
              question={question}
              index={index}
              mode={mode}
              pickedIndex={picked[question.id]}
              onPick={(optionIndex) =>
                setPicked((current) =>
                  // Once answered, it stays answered — changing it after seeing
                  // the mark would make the score meaningless.
                  current[question.id] === undefined
                    ? { ...current, [question.id]: optionIndex }
                    : current,
                )
              }
              onSave={(changes) => handleSaveQuestion(question.id, changes)}
              onDelete={() => handleDeleteQuestion(question.id)}
            />
          ))}
        </>
      )}
    </section>
  )
}

/**
 * One question, either being fixed or being answered.
 *
 * Editing keeps its own draft state so typing does not fire a request per
 * keystroke — the draft only leaves here when Save is pressed.
 *
 * **Options and the right answer are saved together, always.** The backend
 * refuses `options` without `correct`, because `correct` is a position in the
 * list: replace the list without restating which entry is right and the key
 * points at whatever now sits in that slot. Sending both every time means this
 * component cannot produce that request even by accident.
 */
function Question({ question, index, mode, pickedIndex, onPick, onSave, onDelete }) {
  const [prompt, setPrompt] = useState(question.prompt)
  const [options, setOptions] = useState(question.options)
  const [correct, setCorrect] = useState(question.correct)

  // If the question changes underneath us — saved, or a different quiz opened —
  // the draft should follow it rather than showing the old text.
  useEffect(() => {
    setPrompt(question.prompt)
    setOptions(question.options)
    setCorrect(question.correct)
  }, [question])

  const changed =
    prompt !== question.prompt ||
    correct !== question.correct ||
    options.some((option, i) => option !== question.options[i])

  if (mode === 'taking') {
    const answered = pickedIndex !== undefined

    return (
      <div style={{ marginBottom: 'var(--gap-lg)' }}>
        <p style={{ fontWeight: 700, marginBottom: 'var(--gap-sm)' }}>
          {index + 1}. {question.prompt}
        </p>

        {question.options.map((option, i) => {
          // Nothing is coloured until an answer is picked. After that the right
          // one is always marked, so a wrong pick teaches the right answer
          // rather than just saying no.
          let background = 'transparent'
          if (answered && i === question.correct) background = 'var(--mint)'
          else if (answered && i === pickedIndex) background = 'var(--coral)'

          return (
            <button
              key={i}
              type="button"
              className="btn btn--secondary"
              disabled={answered}
              onClick={() => onPick(i)}
              style={{
                display: 'block',
                width: '100%',
                textAlign: 'left',
                marginBottom: 'var(--gap-xs)',
                background,
              }}
            >
              <strong>{LETTERS[i]}.</strong> {option}
            </button>
          )
        })}

        {answered && (
          <p style={{ color: 'var(--text-muted)', margin: 0 }}>
            {pickedIndex === question.correct ? 'Right.' : 'Not quite.'} It is on page{' '}
            {question.page}.
          </p>
        )}
      </div>
    )
  }

  return (
    <div
      style={{
        marginBottom: 'var(--gap-lg)',
        paddingBottom: 'var(--gap)',
        borderBottom: '1px solid var(--text-faint)',
      }}
    >
      <label htmlFor={`prompt-${question.id}`} className="visually-hidden">
        Question {index + 1}
      </label>
      <input
        id={`prompt-${question.id}`}
        className="input"
        value={prompt}
        onChange={(event) => setPrompt(event.target.value)}
        style={{ width: '100%', marginBottom: 'var(--gap-sm)' }}
      />

      {options.map((option, i) => (
        <div
          key={i}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--gap-sm)',
            marginBottom: 'var(--gap-xs)',
          }}
        >
          <input
            type="radio"
            name={`correct-${question.id}`}
            checked={correct === i}
            onChange={() => setCorrect(i)}
            aria-label={`Option ${LETTERS[i]} is the right answer`}
          />
          <label htmlFor={`option-${question.id}-${i}`} className="visually-hidden">
            Option {LETTERS[i]}
          </label>
          <input
            id={`option-${question.id}-${i}`}
            className="input"
            value={option}
            onChange={(event) =>
              setOptions((current) =>
                current.map((existing, j) => (j === i ? event.target.value : existing)),
              )
            }
            style={{ flex: 1 }}
          />
        </div>
      ))}

      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--gap-sm)',
          marginTop: 'var(--gap-sm)',
        }}
      >
        <span style={{ color: 'var(--text-muted)', flex: 1 }}>
          From page {question.page} — check it against what the page says.
        </span>
        <button
          type="button"
          className="btn btn--primary"
          disabled={!changed}
          // options and correct always travel together. See the note above.
          onClick={() => onSave({ prompt, options, correct })}
        >
          Save
        </button>
        <button
          type="button"
          className="btn btn--secondary"
          aria-label={`Delete question ${index + 1}`}
          onClick={onDelete}
        >
          Delete
        </button>
      </div>
    </div>
  )
}
