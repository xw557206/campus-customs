// Handsome Dan, drawn in SVG rather than shipped as an image file.
//
// Two forms, both original artwork — no official Yale logo asset is used:
//
//   BulldogMark   a flat, heraldic head. Inherits `currentColor`, so the same
//                 component works white-on-blue in the navbar, blue-on-cream
//                 in the chat, and at 7% opacity as a hero watermark.
//   BulldogCrest  the head set in a shield with a gold rule and a small
//                 banner. Used once, in the hero, as the brand emblem.
//
// Deliberately geometric rather than illustrative: flat fills, no gradients,
// no cartoon eye highlights. It holds up at 26px in the navbar and at 420px
// as a watermark, which a detailed drawing would not.

export function BulldogMark({
  size = 40,
  className,
  mono = false,
  title = 'Handsome Dan, the Yale bulldog',
}: {
  size?: number
  className?: string
  /** Draw every detail in `currentColor` — for the faint hero watermark,
   *  where fixed dark eyes and a red collar would show as debris. */
  mono?: boolean
  title?: string
}) {
  const detail = mono ? 'currentColor' : 'var(--yale-ink, #00172f)'
  const collar = mono ? 'currentColor' : 'var(--accent, #c8102e)'
  const stud = mono ? 'currentColor' : 'var(--gold, #b08d3f)'
  const face = mono ? 'currentColor' : '#fff'

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      className={className}
      role="img"
      aria-label={title}
    >
      {/* ears — folded, low, the bulldog silhouette tell */}
      <path
        d="M14 9.5c4.2-2.2 8.4 1 11 7.2-3.6 2.2-6.6 5.4-8.4 9.4-3.8-5.6-5.2-13.4-2.6-16.6z"
        fill="currentColor"
      />
      <path
        d="M50 9.5c-4.2-2.2-8.4 1-11 7.2 3.6 2.2 6.6 5.4 8.4 9.4 3.8-5.6 5.2-13.4 2.6-16.6z"
        fill="currentColor"
      />

      {/* head — distinctly wider than tall, flat crown, heavy jowls */}
      <path
        d="M32 11c13.2 0 21.5 6.8 21.5 17.2 0 12.6-9.2 22.3-21.5 22.3S10.5 40.8 10.5 28.2C10.5 17.8 18.8 11 32 11z"
        fill="currentColor"
      />

      {/* muzzle, cut as negative space so the mark stays single-colour */}
      <path
        d="M32 29c7.2 0 11.5 3.9 11.5 9.2S38.6 47.5 32 47.5s-11.5-4-11.5-9.3S24.8 29 32 29z"
        fill={face}
        opacity={mono ? 0.18 : 0.93}
      />

      {/* brow folds */}
      <path
        d="M18.5 24.5c3.4-2.6 7.4-2.6 10.4 0M35.1 24.5c3-2.6 7-2.6 10.4 0"
        stroke={face}
        strokeWidth="2.6"
        strokeLinecap="round"
        fill="none"
        opacity=".55"
      />

      {/* eyes — flat, no highlight */}
      <ellipse cx="23.6" cy="30.2" rx="2.9" ry="3.1" fill={detail} />
      <ellipse cx="40.4" cy="30.2" rx="2.9" ry="3.1" fill={detail} />

      {/* nose and jowl line */}
      <path
        d="M32 33.2c2.9 0 4.8 1.6 4.8 3.4S34.9 39.6 32 39.6s-4.8-1.2-4.8-3S29.1 33.2 32 33.2z"
        fill={detail}
      />
      <path
        d="M32 39.6v3.1M32 42.7c-3 0-5.2-1.5-6.2-3.4M32 42.7c3 0 5.2-1.5 6.2-3.4"
        stroke={detail}
        strokeWidth="2.1"
        strokeLinecap="round"
        fill="none"
      />

      {/* collar */}
      <path
        d="M15.5 47c5.5 5.5 27.5 5.5 33 0"
        stroke={collar}
        strokeWidth="4.2"
        fill="none"
        strokeLinecap="round"
      />
      <circle cx="32" cy="52.4" r="2.5" fill={stud} />
    </svg>
  )
}

/** The head set in a shield. One use: the hero emblem. */
export function BulldogCrest({ size = 128, className }: { size?: number; className?: string }) {
  return (
    <svg
      width={size}
      height={size * 1.18}
      viewBox="0 0 120 142"
      className={className}
      role="img"
      aria-label="Campus Customs crest"
    >
      {/* shield */}
      <path
        d="M60 4 112 18v52c0 30-22 51-52 68C30 121 8 100 8 70V18z"
        fill="rgba(255,255,255,0.06)"
        stroke="var(--gold, #b08d3f)"
        strokeWidth="2"
      />
      <path
        d="M60 12 104 24v46c0 26-19 44-44 59C36 114 16 96 16 70V24z"
        fill="none"
        stroke="rgba(255,255,255,0.22)"
        strokeWidth="1"
      />

      <g transform="translate(26 26) scale(1.06)">
        <BulldogMark size={64} />
      </g>

      {/* banner */}
      <text
        x="60"
        y="112"
        textAnchor="middle"
        fontFamily="var(--serif, Georgia, serif)"
        fontSize="13"
        letterSpacing="3"
        fill="var(--gold, #b08d3f)"
      >
        NEW HAVEN
      </text>
    </svg>
  )
}
