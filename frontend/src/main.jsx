/**
 * The very first thing that runs in the browser.
 *
 * It finds the empty <div id="root"> in index.html and tells React to draw
 * the App component inside it. You will almost never need to change this file.
 *
 * ClerkProvider wraps the whole app so any component inside it can ask "who is
 * signed in?". It reads VITE_CLERK_PUBLISHABLE_KEY from .env.local by itself —
 * that is why no key is passed here.
 */

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { ClerkProvider } from '@clerk/react'
import App from './App'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ClerkProvider afterSignOutUrl="/">
      <App />
    </ClerkProvider>
  </StrictMode>,
)
