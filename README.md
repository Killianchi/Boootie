# boootie.com

Single-page pre-order site for boootie. Static HTML + Tailwind v4, no backend. Deploys on Vercel.

## Run it

```bash
npm install
npm run build        # generates doodles, CSS and dist/
npx serve dist       # or any static server
```

## Change copy, prices and links

Everything a human edits lives in `site.config.json`: headlines (three variants, `headlineIndex` picks one;
`?h=1` or `?h=2` previews the others without a rebuild), subtext, price, deposit, Stripe Payment Link,
estimated ship date, Formspree form id, support email, accent colour. Run `npm run build` after editing.

## Where things are

- `src/index.html` page template (`{{key}}` = config value, `{{> name}}` = a doodle from `src/doodles/`)
- `src/css/input.css` tokens, components, doodle styles, motion
- `src/js/main.js` sticky CTA, Stripe passthrough (`client_reference_id` + `utm_*`), analytics events, FAQ, signup form, lazy 3D viewer
- `scripts/doodle-lib.mjs` the hand-drawn motif library (stroke-based, one line weight everywhere)
- `scripts/doodles.mjs` composes the hero fields, section bands and scenes into `src/doodles/*.svg`
- `scripts/render.mjs` renders the product figures from `public/models/boootie.glb` (`npm run renders`, needs Playwright)
- `scripts/og.mjs` renders the Open Graph image (`npm run og`, after a build)
- `scripts/shots.mjs` review screenshots at 390px and 1440px

## Analytics

Vercel Web Analytics (no cookies). Enable it in the Vercel project; events: `cta_click` (placement: hero, sticky, preorder),
`faq_open`, `email_signup`, `model_loaded`.
