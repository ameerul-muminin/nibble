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
const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

// FastAPI's own words when there is no route at that address at all, and when
// the method is wrong. They are written for a developer reading a log, not for
// a person using the app — see the comment in messageFor below.
const FRAMEWORK_DEFAULTS = ['Not Found', 'Method Not Allowed']

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

  return `Nibble’s backend answered with ${status}. Try again in a moment.`
}

/**
 * A small wrapper around fetch that does the boring bits: build the full URL,
 * turn a failure into a real error, and hand back the parsed JSON.
 */
async function request(path, options) {
  const response = await fetch(`${BASE}${path}`, options)

  if (!response.ok) {
    let detail = null
    try {
      detail = (await response.json()).detail
    } catch {
      // Not every failure has a JSON body — a crashed server sends none at all.
      detail = null
    }
    throw new Error(messageFor(response.status, detail))
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
 * Returns { results, unsearchable_notes }. Each result is
 * { document_id, filename, page, content, score }, best match first, and
 * `score` runs 0 to 1. An empty `results` is a real answer: nothing came close.
 *
 * `unsearchable_notes` counts notes stored before search existed, which have no
 * embedding and can never match anything. The UI says so when it is not zero —
 * a note that silently never matches is worse than one that says why.
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
