# Design system

The look: **Duolingo's mechanics, our deck's palette.** Chunky outlined shapes,
buttons you can press, bright accents on clean neutrals — recoloured to the black
and lime scheme from the pitch deck so the app and the presentation match.

## Colour

All colours are defined in `frontend/src/styles/tokens.css`. Never type a raw
hex code in a component.

| Token | Hex | Use for |
|---|---|---|
| `--ink` | `#0A0A0A` | Text, and every border |
| `--lime` | `#D8F84B` | Primary actions, Nibble, streaks |
| `--indigo` | `#4D4DF5` | Secondary actions, the user's chat bubble |
| `--mint` | `#4FDE82` | Correct answers, success |
| `--coral` | `#F26B3D` | Errors, wrong answers, Nibble's nose |
| `--cream` | `#FDF6E3` | Nibble's chat bubble |
| `--haze` | `#EAF4D5` | Source chips, quiet highlights |
| `--page` | `#FBFBF7` | Page background |

Two accents per screen, maximum. Lime and indigo carry the interface; mint and
coral only appear to mean *right* and *wrong*.

## Type

- **Display** — Fredoka, weight 600. Headings and button labels.
- **Body** — Nunito, weight 400 (600 for emphasis). Everything else.

Both are free on Google Fonts and already loaded in `index.html`. Sentence case
everywhere. Never all-caps.

## The signature: solid-edge press

Every button has a 3px black border and a **solid** 4px shadow directly below
it — not a blurry drop shadow. Pressing moves it down onto its own shadow.

```css
box-shadow: 0 4px 0 var(--ink);
/* :active */
transform: translateY(4px);
box-shadow: 0 0 0 var(--ink);
```

This single detail is most of why the app reads as playful rather than corporate.
It is why Duolingo's buttons feel good. Keep it consistent — a button anywhere in
the app that does not do this will look broken.

## Shape

- Borders: always `3px solid var(--ink)`. No grey borders, no hairlines.
- Radius: `16px` for buttons and bubbles, `24px` for cards, `999px` for pills.
- Never sharp corners.

## Nibble

A round lime cat with an open book. Lives in `assets/mascot/nibble.svg`, and as a
React component at `frontend/src/components/Mascot.tsx` so it can animate.

**Where Nibble appears:** the header, empty states, loading states, and after a
finished quiz. **Where Nibble does not appear:** next to every message, or inside
error text about something failing. A mascot that shows up constantly stops being
charming within a day.

Moods to build as you need them: `idle` (still), `thinking` (gentle bob, already
implemented), and later `happy` and `curious`.

## Voice

Nibble is warm and brief. Short sentences, plain words, an occasional cat-ish
touch — never more than one per message.

| Instead of | Write |
|---|---|
| "Submit" | "Ask" |
| "No data available" | "Nothing here yet. Add a PDF and I'll read it." |
| "An error occurred" | "That upload didn't work. Try a PDF under 20 MB." |
| "Upload successful" | "Got it — 18 pages read." |

Errors say what happened and what to do next. They never apologise and never say
"oops". Empty screens are an invitation, not a shrug.

## Accessibility floor

Non-negotiable, and cheap if you do it from the start:

- Every interactive element is reachable by Tab and shows a visible focus ring.
- Colour never carries meaning alone — pair mint and coral with an icon or word.
- Every image and icon has alt text or `aria-label`.
- Respect `prefers-reduced-motion` (already handled in `global.css`).
