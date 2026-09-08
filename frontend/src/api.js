/**
 * The ONLY file in the frontend that knows the backend's address.
 *
 * Every time you add a route in the backend, add a matching function here —
 * then components can just call `getDocuments()` without caring about URLs,
 * and when something changes there is exactly one file to fix.
 *
 * Each function mirrors an endpoint in docs/api.md.
 */

// Where the backend lives. Falls back to localhost, which is what you want
// while developing.
//
// `||` rather than `??`, and the difference bites here. `??` only falls back on
// null and undefined, so a `VITE_API_URL=` line left blank in .env.local — which
// is exactly what .env.example invites you to do — would set this to the empty
// string, and the empty string is not null. Every request would then go to
// `/documents` on the Vite dev server instead of the backend, and come back as
// Vite's own 404 page. `||` treats blank as "not set", which is what a person
// leaving it blank meant.
const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// FastAPI's own words when there is no route at that address at all, and when
// the method is wrong. They are written for a developer reading a log, not for
// a person using the app — see the comment in messageFor below.
const FRAMEWORK_DEFAULTS = ['Not Found', 'Method Not Allowed']

/**
 * How this file asks Clerk for the current sign-in token. Slice 4.5.
 *
 * From slice 4.5 the backend refuses to answer anything about notes unless it
 * knows who is asking, so every request has to carry a token. The awkward part
 * is that only a React component can call Clerk's hooks, and this file is not
 * one — it is plain JavaScript that components import.
 *
 * So App hands the function in, once, and `request` below uses it for every
 * call. That keeps the rule this file already had: components call
 * `getDocuments()` and think about notes, not about headers.
 *
 * It starts as "no token", which is the right answer before anybody has signed
 * in — `getHealth()` runs then, and it is the one route that needs no sign-in.
 */
let getToken = async () => null

/**
 * Tell this file how to get a token. Called once, by App.
 *
 * Clerk's `getToken` returns a *fresh* token each time it is asked, because a
 * session token is short-lived on purpose — it is a thing anyone holding it can
 * use, so it is made to stop working quickly. That is why we keep the function
 * and call it per request, rather than keeping a token and reusing it. A stored
 * token would work for a few minutes and then start failing in a way that looks
 * random.
 */
export function setTokenGetter(fn) {
  getToken = fn
}

/**
 * Turn a failed response into one sentence worth showing somebody.
 *
 * Our own routes write a plain sentence into `detail` for anything a person
 * caused — the wrong file type, a scan too long to read, a blank search box.
 * Those are the best thing to show, and they are shown unchanged.
 *
 * Two kinds of failure do NOT come from our routes, and both were showing the
 * framework's words straight to the user:
 *
 * - **404 "Not Found"** means the backend has no route at that address. That is
 *   never the user's doing. It means the two halves of the app disagree about
 *   what exists — almost always a backend still running older code, which is
 *   exactly what happened the first time the search box was used in a browser.
 * - **422** is FastAPI rejecting the shape of the body, and its `detail` is a
 *   *list of objects*, not a string. `new Error(thatList)` produces
 *   "[object Object]" on screen, which tells nobody anything.
 */
function messageFor(status, detail) {
  if (typeof detail === 'string' && detail && !FRAMEWORK_DEFAULTS.includes(detail)) {
    return detail
  }

  if (status === 404 || status === 405) {
    return 'Nibble’s backend doesn’t know about that yet. It’s probably running an older version — stop it and start it again with: uvicorn app.main:app --reload'
  }

  if (status === 422) {
    return 'Nibble’s backend didn’t understand that request. If you just updated it, restart it and try again.'
  }

  // 401 has its own sentence because the backend's one is written for the case
  // where you were never signed in, and the case that actually happens to a
  // person mid-session is a token that quietly aged out while the tab sat open.
  // "Sign in again" is the fix for both.
  if (status === 401) {
    return 'You’ve been signed out. Sign in again and Nibble will pick up where you left off.'
  }

  return `Nibble’s backend answered with ${status}. Try again in a moment.`
}

/**
 * A small wrapper around fetch that does the boring bits: build the full URL,
 * turn a failure into a real error, and hand back the parsed JSON.
 */
async function request(path, options = {}) {
  // Ask Clerk for a token, every time. See setTokenGetter above for why this is
  // not cached.
  const token = await getToken()

  // Spread the caller's own headers first, then add ours. uploadDocument sets
  // no Content-Type on purpose and search/ask set one — this leaves both alone
  // and only adds Authorization on top.
  const headers = { ...options.headers }
  if (token) {
    headers.Authorization = `Bearer ${token}`
  }

  const response = await fetch(`${BASE}${path}`, { ...options, headers })

  if (!response.ok) {
    let detail = null
    try {
      detail = (await response.json()).detail
    } catch {
      // Not every failure has a JSON body — a crashed server sends none at all.
      detail = null
    }
    // The status is attached as well as the sentence, because slice 6 has two
    // failures that need telling apart by a caller rather than by a person: a
    // 422 from POST /quizzes means "this note is too old to quiz, delete and
    // re-upload it", which deserves a different offer than a 503 meaning "try
    // again in a moment". Matching on the text of a message to work that out is
    // the habit this avoids — it breaks the moment somebody improves a word.
    const error = new Error(messageFor(response.status, detail))
    error.status = response.status
    throw error
  }

  // 204 means "done, nothing to send back" — there is no JSON to read.
  return response.status === 204 ? null : response.json()
}

/** Slice 0: is the backend awake? */
export function getHealth() {
  return request('/health')
}

/**
 * Slice 1: every note that has been uploaded, newest first.
 *
 * Returns an array of { id, filename, page_count, created_at } — the shape is
 * written down in docs/api.md under "Slice 1", and that contract is what lets
 * this file and routes.py be built without waiting for each other.
 */
export function listDocuments() {
  return request('/documents')
}

/**
 * Slice 1: upload one file and get the created document back.
 *
 * @param {File} file - straight from an <input type="file"> element.
 */
export function uploadDocument(file) {
  // FormData is how a file gets sent over HTTP. The name 'file' has to match
  // the parameter name in routes.py — that is how FastAPI finds it.
  const form = new FormData()
  form.append('file', file)

  // No Content-Type header here, on purpose. It is tempting, because every
  // other POST you will ever write sets one. The browser has to set this one
  // itself, because multipart/form-data needs a boundary string that only the
  // browser knows. Setting it by hand sends a boundary-less header, the
  // backend cannot split the body, and you get a confusing 422 that looks
  // like the file is wrong when the file is fine.
  return request('/documents', { method: 'POST', body: form })
}

/**
 * Slice 1: delete one note by its id.
 *
 * The backend answers 204 with no body, and `request` already turns that into
 * null rather than trying to parse JSON that is not there.
 */
export function deleteDocument(id) {
  return request(`/documents/${id}`, { method: 'DELETE' })
}

/**
 * Slice 2: the pieces one document was cut into, in reading order.
 *
 * Returns an array of { id, page, content }. An empty array is a real answer —
 * the document exists and has no pieces, which is the state everything uploaded
 * before slice 2 is in. A document id that does not exist is a 404, and
 * `request` turns that into a thrown Error with the backend's own sentence.
 */
export function getChunks(id) {
  return request(`/documents/${id}/chunks`)
}

/**
 * Slice 3: find the pieces of your notes closest in meaning to some text.
 *
 * Returns { results, unsearchable_note_ids }. Each result is
 * { document_id, filename, page, content, score }, best match first, and
 * `score` runs 0 to 1. An empty `results` is a real answer: nothing came close.
 *
 * `unsearchable_note_ids` names the notes that can never match anything — either
 * stored before search existed, or embedded by a different model. The UI shows
 * how many there are, because a note that silently never matches is worse than
 * one that says why. They are ids rather than a count so that deleting one can
 * be reflected exactly, the same way it is for results.
 *
 * Note the Content-Type header, which uploadDocument above deliberately does
 * NOT set. The difference is real: a file upload is multipart and the browser
 * has to write that header itself, because only it knows the boundary string.
 * This is plain JSON, so we say so, and FastAPI reads the body as the
 * SearchRequest model in routes.py.
 */
export function search(query) {
  return request('/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
  })
}

/**
 * Slice 4: ask a question and get an answer built from your own notes.
 *
 * `history` is the conversation so far, oldest first, as the same
 * { role, content } turns App already keeps for the transcript. It is optional.
 *
 * **Sending it is what makes follow-up questions work at all.** Without it the
 * backend received "name them" on its own, searched your notes for those two
 * words, and answered from whatever came back — which looked exactly like
 * Nibble making things up, and was really the search being handed a question
 * with the meaning removed. The backend uses the recent questions to work out
 * what to search for. See docs/api.md under POST /ask.
 *
 * Only the last few turns are used, and the backend decides how many. Send the
 * conversation and let it choose; do not trim it here, or the two halves of the
 * app end up with different ideas about what "recent" means.
 *
 * Returns { answer, sources }. Each source is
 * { document_id, filename, page, excerpt } — the pieces of your notes that were
 * put in front of the model.
 *
 * Two things about the shape are worth knowing before building against it.
 *
 * **`sources` is what Nibble read, not what it quoted.** Every page it could
 * possibly have drawn on is in that list, and nothing else was available to it.
 * Working out which pages a particular sentence used would mean parsing the
 * citations back out of the answer, and being wrong there is worse than not
 * guessing — it would either hide a page that was used or claim one that was
 * not. Show them as "what it read" and the claim stays true.
 *
 * **A refusal is a normal answer, not an error.** When your notes do not cover
 * the question, `answer` says so and this resolves exactly like any other reply.
 * That refusal is the most important thing the app does, so it must never be
 * rendered as a failure — it goes in a bubble like everything else.
 *
 * Empty `sources` means nothing was found to answer from at all: no notes yet,
 * or only notes stored before search existed. The backend does not call the
 * model in that case, and the answer says what to do about it.
 */
export function ask(question, history = []) {
  return request('/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    // Only `role` and `content` go up. A turn on screen also carries `sources`,
    // and sending those back would be pointless at best — the backend already
    // knows what it retrieved, and it re-retrieves for every question anyway.
    body: JSON.stringify({
      question,
      history: history.map(({ role, content }) => ({ role, content })),
    }),
  })
}

/**
 * Slice 6: write a quiz from one of your notes.
 *
 * This calls the language model, so it takes a few seconds — show something
 * while it runs. Returns the quiz with its questions, including `correct`.
 *
 * `count` is optional and the backend defaults it. It has to be between 1 and
 * 10; the ceiling is Groq's free tier, not a preference.
 */
export function createQuiz(documentId, title, count) {
  return request('/quizzes', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ document_id: documentId, title, ...(count ? { count } : {}) }),
  })
}

/**
 * Slice 6: every quiz you own, newest first.
 *
 * No questions in these rows — this is the list you pick from, and it carries
 * `question_count` instead. Call getQuiz for the questions themselves.
 */
export function listQuizzes() {
  return request('/quizzes')
}

/**
 * Slice 6: one quiz and all its questions, in order, with the answers.
 *
 * **`correct` is included, and that is the point.** It is your quiz, made from
 * your notes, so the browser holds the answer key and marks as you go. That is
 * why practising alone needs no other route and stores nothing: the score lives
 * on screen and closing the tab ends it.
 */
export function getQuiz(id) {
  return request(`/quizzes/${id}`)
}

/**
 * Slice 6: fix a question the model got wrong. Send only what changed.
 *
 * **Sending `options` requires sending `correct` too, and the backend refuses
 * without it.** `correct` is a position in `options`, not the text of the right
 * answer — so replacing the list without restating which entry is right leaves
 * the key pointing at whatever now sits in that slot. The quiz still renders,
 * still marks, and marks the wrong thing.
 *
 * `correct` on its own is fine: changing which entry is right does not disturb
 * the list it points into.
 */
export function updateQuestion(quizId, questionId, changes) {
  return request(`/quizzes/${quizId}/questions/${questionId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(changes),
  })
}

/** Slice 6: drop a question that came out wrong. Refused for the last one. */
export function deleteQuestion(quizId, questionId) {
  return request(`/quizzes/${quizId}/questions/${questionId}`, { method: 'DELETE' })
}

/** Slice 6: delete a quiz and its questions. */
export function deleteQuiz(id) {
  return request(`/quizzes/${id}`, { method: 'DELETE' })
}
