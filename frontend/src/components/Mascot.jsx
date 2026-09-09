/**
 * Nibble the cat, drawn directly in code as an SVG.
 *
 * Drawing it here rather than loading an image file is what lets it react to
 * what the app is doing. An <img> is a picture; this is a picture the app can
 * change its mind about.
 *
 * Props:
 *   size  — how big, in pixels (default 96)
 *   mood  — 'idle', 'thinking', 'happy' or 'curious'
 *   label — what a screen reader should call it. Leave it off, which is the
 *           usual case; see the note below.
 *
 * ---------------------------------------------------------------------------
 * Why `label` is off by default.
 *
 * This used to say aria-label="Nibble the cat", always. Two things are wrong
 * with that. It becomes a lie the moment there are moods — a screen reader
 * would announce a still cat and a delighted one identically. And in nearly
 * every place Nibble appears, the sentence right beside it already says the
 * thing: a cat next to "Nothing here yet. Add a chapter and Nibble will read
 * it" adds nothing to hear, it just makes the same point twice, slower.
 *
 * So Nibble is decorative unless told otherwise: aria-hidden, invisible to a
 * screen reader, which is exactly right for a picture that repeats the text
 * next to it. Pass `label` only where the cat is genuinely carrying meaning on
 * its own.
 */

const MOODS = ['idle', 'thinking', 'happy', 'curious']

export function Mascot({ size = 96, mood = 'idle', label }) {
  // A typo in a mood should not silently draw nothing. Fall back to idle.
  const face = MOODS.includes(mood) ? mood : 'idle'
  const happy = face === 'happy'

  return (
    <svg
      viewBox="0 0 220 220"
      width={size}
      height={size}
      /* Decorative by default — see the note above. */
      {...(label ? { role: 'img', 'aria-label': label } : { 'aria-hidden': 'true' })}
      style={{
        // The bob is the only motion. global.css already turns every animation
        // off under prefers-reduced-motion, so this needs no guard of its own.
        animation: face === 'thinking' ? 'nibble-bob 1.1s ease-in-out infinite' : undefined,
      }}
    >
      <style>{`@keyframes nibble-bob{0%,100%{transform:translateY(0)}50%{transform:translateY(-6px)}}`}</style>
      <g stroke="#0A0A0A" strokeWidth="6" strokeLinecap="round" strokeLinejoin="round">
      {/*
        The head is its own group so `curious` can tilt it without tilting the
        book underneath. Rotating the whole drawing was the first attempt and it
        read as the cat falling over rather than leaning in — the book went with
        it. The origin is the chin, so the head pivots on the neck.
      */}
      <g
        style={{
          transform: face === 'curious' ? 'rotate(-9deg)' : undefined,
          transformOrigin: '110px 155px',
        }}
      >
        <path d="M60 58 46 18 94 42Z" fill="#D8F84B" />
        <path d="M160 58 174 18 126 42Z" fill="#D8F84B" />
        <path d="M66 50 58 30 82 42Z" fill="#F26B3D" strokeWidth="4" />
        <path d="M154 50 162 30 138 42Z" fill="#F26B3D" strokeWidth="4" />
        <circle cx="110" cy="98" r="62" fill="#D8F84B" />
        <ellipse cx="110" cy="122" rx="31" ry="19" fill="#FDF6E3" />

        {/*
          The eyes are the whole of the expression. Happy closes them into two
          upward arcs — the ^ ^ everybody reads as delight — and every other
          mood leaves them open with a highlight, which is what stops a black
          oval looking like a hole.
        */}
        {happy ? (
          <path
            d="M78 88c5-9 13-9 18 0M124 88c5-9 13-9 18 0"
            fill="none"
            strokeWidth="5.5"
          />
        ) : (
          <>
            <ellipse cx="87" cy="86" rx="9" ry="12" fill="#0A0A0A" stroke="none" />
            <ellipse cx="133" cy="86" rx="9" ry="12" fill="#0A0A0A" stroke="none" />
            <circle cx="90" cy="81" r="3.4" fill="#FFFFFF" stroke="none" />
            <circle cx="136" cy="81" r="3.4" fill="#FFFFFF" stroke="none" />
          </>
        )}

        <path d="M103 112h14l-7 8Z" fill="#F26B3D" strokeWidth="4" />

        {/* A wider, deeper smile when happy; the small w-shaped mouth otherwise. */}
        <path
          d={
            happy
              ? 'M110 120v5M110 125c-8 9-19 6-22-2M110 125c8 9 19 6 22-2'
              : 'M110 120v4M110 124c-5 6-13 4-15-2M110 124c5 6 13 4 15-2'
          }
          fill="none"
          strokeWidth="4.5"
        />

        <path d="M48 110H26M50 126H29M172 110h22M170 126h21" strokeWidth="4.5" />
      </g>

        <rect x="14" y="168" width="192" height="22" rx="8" fill="#4D4DF5" />
        <path d="M22 158c31-9 64-9 86 0v20c-22-9-55-9-86 0Z" fill="#FDF6E3" />
        <path d="M198 158c-31-9-64-9-86 0v20c22-9 55-9 86 0Z" fill="#FDF6E3" />
      </g>
    </svg>
  )
}
