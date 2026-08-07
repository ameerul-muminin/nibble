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

/**
 * A small wrapper around fetch that does the boring bits: build the full URL,
 * turn a failure into a real error, and hand back the parsed JSON.
 */
async function request(path, options) {
  const response = await fetch(`${BASE}${path}`, options)

  if (!response.ok) {
    throw new Error(`The backend answered with ${response.status}`)
  }

  // 204 means "done, nothing to send back" — there is no JSON to read.
  return response.status === 204 ? null : response.json()
}

/** Slice 0: is the backend awake? */
export function getHealth() {
  return request('/health')
}
