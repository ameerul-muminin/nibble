/**
 * Landing — the signed-out front door.
 *
 * Duolingo's mechanics, Nibble's voice: chunky cards, one big mascot,
 * one clear CTA. Uses only tokens from tokens.css, never raw hex.
 *
 * Shown when nobody is signed in. Signed-in users skip this entirely
 * and go straight to Your notes in App.jsx.
 */

import { SignInButton, SignUpButton } from '@clerk/react'
import { Mascot } from './Mascot'
import '../styles/landing.css'

const STEPS = [
  {
    n: '1',
    title: 'Upload a chapter',
    body: 'Drop in a PDF, txt, md, or a photo of handwriting. Nibble reads it.',
  },
  {
    n: '2',
    title: 'Ask a question',
    body: 'Ask in plain words, like you would ask a friend in class.',
  },
  {
    n: '3',
    title: 'Get the answer, with the page',
    body: 'Nibble answers from your notes only, and shows where it found it.',
  },
]

export function Landing() {
  return (
    <div className="landing">
      <header className="landing-nav">
        <div className="landing-brand">
          <Mascot size={44} mood="idle" />
          <span className="landing-word">Nibble</span>
        </div>
        <div className="landing-nav-actions">
          <SignInButton mode="modal">
            <button type="button" className="btn btn--secondary">
              Sign in
            </button>
          </SignInButton>
          <SignUpButton mode="modal">
            <button type="button" className="btn btn--primary">
              Start learning
            </button>
          </SignUpButton>
        </div>
      </header>

      <main className="landing-main">
        <section className="card landing-hero">
          <div className="landing-hero-mascot">
            <Mascot size={180} mood="thinking" />
            <span className="streak" aria-label="Study streak">
              ★ 3-day streak
            </span>
          </div>
          <div className="landing-hero-copy">
            <h1>Bite-sized answers from your own notes</h1>
            <p className="landing-sub">
              Upload a chapter, ask a question, get an answer that comes from your
              material — with the page it came from.
            </p>
            <div className="landing-cta">
              <SignUpButton mode="modal">
                <button type="button" className="btn btn--primary landing-cta-big">
                  Start learning
                </button>
              </SignUpButton>
              <SignInButton mode="modal">
                <button type="button" className="btn btn--secondary">
                  I have notes
                </button>
              </SignInButton>
            </div>
            <p className="landing-micro">Free. No card. Your PDFs stay yours.</p>
          </div>
        </section>

        <section aria-label="How it works" className="landing-steps">
          {STEPS.map((s) => (
            <article key={s.n} className="card landing-step">
              <span className="landing-step-n" aria-hidden="true">
                {s.n}
              </span>
              <h2>{s.title}</h2>
              <p>{s.body}</p>
            </article>
          ))}
        </section>

        <section aria-label="Example answer" className="card landing-demo">
          <h2>What it feels like</h2>
          <div className="landing-chat">
            <p className="bubble bubble--user">explain osmosis simply</p>
            <div className="landing-cat-row">
              <Mascot size={48} mood="idle" />
              <div>
                <p className="bubble bubble--cat">
                  Water moves across a membrane toward the side with more solute.
                </p>
                <div className="sources">
                  <span className="source-chip">biology-ch4.pdf · p. 4</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section aria-label="Why Nibble" className="landing-trust">
          <span className="source-chip">✓ Free tier, no card</span>
          <span className="source-chip">✓ Answers only from your notes</span>
          <span className="source-chip">✓ Says when it does not know</span>
        </section>
      </main>

      <footer className="landing-foot">
        <p>Nibble — study with your own notes. Made for students, by students.</p>
      </footer>
    </div>
  )
}
