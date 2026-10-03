# Campus Customs — Visual Design

A Yale-blue storefront theme: restrained, collegiate, and built on the design
tokens already in `src/index.css` rather than a new styling system.

## Palette and type

| Token | Value | Use |
| --- | --- | --- |
| `--yale` / `--yale-deep` / `--yale-ink` | `#00356b` / `#012048` / `#00172f` | primary, nav and hero, headings |
| `--bg` / `--cream` | `#fbfaf7` / `#f6f2ea` | warm off-white page, product tiles |
| `--gold` | `#b08d3f` | decorative rules, crest, borders |
| `--gold-ink` | `#8a6a22` | small label text on light |
| `--gold-soft` | `#e8dcc0` | label text on dark blue |

The background is a **warm** off-white, not a cool grey. It reads as paper,
which makes the blue look richer and stops the site looking like a default
web app.

**Type:** Fraunces (display serif) for headings, prices and the wordmark;
Inter for body and UI. The pairing does the hierarchy work — a serif price
next to sans-serif body copy reads as a shop, not a dashboard.

**Two golds, chosen by contrast ratio, not by eye.** `--gold` is only 3.1:1
on white, so it is decorative only. Small label text uses `--gold-ink` at
5.2:1. Measured in the running app: eyebrow 4.83:1, product category 5.04:1,
description 5.47:1, nav links 11.6:1 — all pass WCAG AA.

## What changed

**Navigation.** Dark navy with a gold hairline instead of a drop shadow.
Links are uppercase with wide tracking and a gold underline that animates in
on hover and stays on the active page. "Create Account" is a white pill with
a gold focus ring — clearly the primary action. The bulldog tilts on hover.

**Home.** Taller hero with a layered blue gradient, an italic gold "Blue" in
the headline, and the eyebrow-with-gold-rule motif that now repeats across
every page. The four promises below are one continuous card split by
hairlines rather than four tiled boxes.

**Product cards.** Full-bleed square photo, serif product name, gold
category label, and a ruled footer separating price from the stock tag. The
card lifts 6px on hover while the photo scales 1.06 — the photo moves inside
a fixed frame, which is the detail that makes it feel like a real storefront.

**Product detail.** The price sits in the display serif above a hairline
rule, section labels are small-caps gold, and sizes are pills that lift on
hover. Editorial rather than form-like.

**Forms.** One centred card with a gold-to-blue rule across the top, the
bulldog above the heading, small-caps field labels, and inputs that turn
white with a navy border and a soft blue ring on focus.

**Chat widget.** Gradient navy header with the mascot and a gold small-caps
status line; white bubbles with a hairline border against a faint bulldog
watermark in the log; pill input and uppercase Send. The mascot tilts when
you hover the launcher.

**Buttons and chips.** A single shape everywhere — pill, uppercase, 0.1em
tracking. Primary is solid navy and inverts to white on the dark hero.

## The bulldog

Original SVG artwork in `src/components/BulldogMark.tsx` — no official Yale
logo asset is used. Flat and heraldic rather than illustrative: no gradients,
no cartoon eye highlights, so it holds at 26px in the navbar and 420px as a
watermark.

It appears four times, each at a different weight: the navbar wordmark, a
gold-ruled **shield crest** in the hero (`BulldogCrest`), a 4%-opacity
watermark behind the hero, and the chat mascot and log watermark. A `mono`
prop draws every detail in `currentColor` so the watermark doesn't show dark
eyes and a red collar through a faint overlay.

## One decision worth recording

Product tiles were first given a cream backdrop with `mix-blend-mode:
multiply` so cut-out photos would sit on the warm paper tone. Sampling the
catalogue showed that **exactly half the photos are shot on black and half on
white** (20/20 in a 40-product sample), so any tinted backdrop leaves a
visible seam on one half. Every source image is exactly 1:1, so the tiles are
now full-bleed `object-fit: cover` — this crops nothing and both photo styles
read as deliberate photography.

## Why it helps customers

- **Scanning is faster.** A ruled card footer puts price and stock in the
  same place on every card, so comparing 102 products is a vertical scan.
- **Photos are the hero.** Full-bleed square tiles with no seam put the
  garment first, which is what someone is actually shopping for.
- **The primary action is obvious.** One button shape, used consistently, so
  "Create Account", "Shop the catalogue" and "Add to bag" are never ambiguous.
- **It reads as trustworthy.** A shop asking for an account and a password
  has to look established; the collegiate crest and consistent typography do
  more for conversion than any single feature.
- **Nothing was traded for style.** All text passes AA, focus states are
  visible, the bulldog is decorative and hidden from screen readers, and
  `prefers-reduced-motion` already disables every animation added here.

## Verified in the running app

Desktop (1280px): Fraunces and Inter both loading, four-column grid, all 102
cards, two-column detail page. Mobile (375px): hamburger opens with all five
links full-width, crest hidden, hero stacked. Chat still answers and renders
cards — "do you have any crewneks?" returned 8 crewneck cards after the
restyle, so the Problem 9 work is intact.

## Files

Changed `frontend/index.html` (font links), `frontend/src/index.css` (tokens
and base type), `frontend/src/App.css` (all component styling),
`frontend/src/components/BulldogMark.tsx` (refined mark, new `BulldogCrest`
and `mono` prop), and two one-line JSX additions — the crest in
`pages/Home.tsx` and the mark in `pages/Account.tsx`. No routing, data
fetching, auth or chat logic was touched.
