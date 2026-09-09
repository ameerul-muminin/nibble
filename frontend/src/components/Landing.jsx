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
import '../styles/landing.css'
import { Button } from './Button'
import { Mascot } from './Mascot'

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

/**
 * Slice 7 — the two doors.
 *
 * `onDoor` says which screen to land on once Clerk is finished. It is
 * **navigation and nothing else**: it never leaves the browser, it grants
 * nothing, and the backend would ignore it if it were sent. Being a teacher is
 * owning a room — see docs/adr/0004-teacher-is-an-owner.md — and if a button on
 * a landing page could make somebody one, a student could press it too.
 *
 * The handler goes on the button itself, inside `SignInButton`. That works
 * because Clerk clones the child and *composes* its own click handler with the
 * child's, calling this one first and then opening sign-in. It is worth knowing
 * that this is Clerk being careful rather than a coincidence: it clones rather
 * than wraps, so a component that named only the props it cared about and threw
 * the rest away would silently drop Clerk's handler instead — which is the trap
 * written up under Slice 5 in scope.md, pointing the other way.
 */
export function Landing({ onDoor }) {
  return (
    <div className="landing">
      <header className="landing-nav">
        <div className="landing-brand">
          <span className="landing-word">Nibble</span>
        </div>
        {/*
          Sign in only. "Start learning" lives in the hero and nowhere else —
          two primary buttons on one screen compete, and the eye has to pick.
          Returning users look to the top right, new ones read the hero.
        */}
        <div className="landing-nav-actions">
          <SignInButton mode="modal">
            <Button variant="secondary">
              Sign in
            </Button>
          </SignInButton>
        </div>
      </header>

      <main className="landing-main">
        {/*
          The deck's cover slide, as a card: near-black, a big white headline,
          and the one-line pitch in a lime pill. `on-dark` is what flips the
          buttons' press edge from ink to light so it is visible against it —
          see global.css.
        */}
        <section className="card landing-hero on-dark">
          <div className="landing-hero-mascot">
            <img
              src="/wave-nibble.svg"
              alt="Nibble, waving"
              className="landing-hero-art"
            />
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
            {/*
              Two doors, one primary. "Start learning" stays the loud one because
              it is what most people are here for; the classroom is a door, not a
              competing pitch. Neither is a partition — a student joins a class
              from inside the regular app, and a teacher quizzes himself from his
              own notes, so whichever you press you can reach the other from the
              header afterwards.
            */}
            <div className="landing-cta">
              <SignUpButton mode="modal">
                <Button
                  variant="primary"
                  className="landing-cta-big"
                  onClick={() => onDoor('notes')}
                >
                  Start learning
                </Button>
              </SignUpButton>

              <SignInButton mode="modal">
                <Button
                  variant="secondary"
                  className="landing-cta-big"
                  onClick={() => onDoor('join')}
                >
                  Join a class
                </Button>
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
              {/*
                The same happy Nibble the signed-in app puts beside a fresh
                answer, so the promise here and the thing itself match. The
                hero above keeps the flat wave-nibble.svg: that is a different,
                richer drawing, and it never has to react to anything.
              */}
              <Mascot size={48} mood="happy" />
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
