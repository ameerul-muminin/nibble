/**
 * The very first thing that runs in the browser.
 *
 * It finds the empty <div id="root"> in index.html and tells React to draw
 * the App component inside it. You will almost never need to change this file.
 */

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
