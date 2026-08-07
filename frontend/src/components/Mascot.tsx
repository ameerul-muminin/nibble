type Props = {
  size?: number
  /** thinking = gentle bob while waiting for an answer */
  mood?: 'idle' | 'thinking'
}

/** Nibble. Inline SVG so it can react to state without loading a second file. */
export function Mascot({ size = 96, mood = 'idle' }: Props) {
  return (
    <svg
      viewBox="0 0 220 220"
      width={size}
      height={size}
      role="img"
      aria-label="Nibble the cat"
      style={{
        animation: mood === 'thinking' ? 'nibble-bob 1.1s ease-in-out infinite' : undefined,
      }}
    >
      <style>{`@keyframes nibble-bob{0%,100%{transform:translateY(0)}50%{transform:translateY(-6px)}}`}</style>
      <g stroke="#0A0A0A" strokeWidth="6" strokeLinecap="round" strokeLinejoin="round">
        <path d="M60 58 46 18 94 42Z" fill="#D8F84B" />
        <path d="M160 58 174 18 126 42Z" fill="#D8F84B" />
        <path d="M66 50 58 30 82 42Z" fill="#F26B3D" strokeWidth="4" />
        <path d="M154 50 162 30 138 42Z" fill="#F26B3D" strokeWidth="4" />
        <circle cx="110" cy="98" r="62" fill="#D8F84B" />
        <ellipse cx="110" cy="122" rx="31" ry="19" fill="#FDF6E3" />
        <ellipse cx="87" cy="86" rx="9" ry="12" fill="#0A0A0A" stroke="none" />
        <ellipse cx="133" cy="86" rx="9" ry="12" fill="#0A0A0A" stroke="none" />
        <circle cx="90" cy="81" r="3.4" fill="#FFFFFF" stroke="none" />
        <circle cx="136" cy="81" r="3.4" fill="#FFFFFF" stroke="none" />
        <path d="M103 112h14l-7 8Z" fill="#F26B3D" strokeWidth="4" />
        <path
          d="M110 120v4M110 124c-5 6-13 4-15-2M110 124c5 6 13 4 15-2"
          fill="none"
          strokeWidth="4.5"
        />
        <path d="M48 110H26M50 126H29M172 110h22M170 126h21" strokeWidth="4.5" />
        <rect x="14" y="168" width="192" height="22" rx="8" fill="#4D4DF5" />
        <path d="M22 158c31-9 64-9 86 0v20c-22-9-55-9-86 0Z" fill="#FDF6E3" />
        <path d="M198 158c-31-9-64-9-86 0v20c22-9 55-9 86 0Z" fill="#FDF6E3" />
      </g>
    </svg>
  )
}
