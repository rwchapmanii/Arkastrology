# The Ark

Internal astrology app built around:
- a source-grounded traditional astrology core using whole-sign houses and the seven visible planets
- explicit doctrine layering so ancient/traditional rules stay distinct from later or modern overlays
- optional Jungian and imaginal prompt layers that do not override the traditional chart structure
- live current-sky timing as a supplemental layer rather than the doctrinal source of truth

## Monorepo structure
- `apps/mobile` — React Native / Expo mobile client
- `apps/api` — FastAPI backend
- `packages/shared` — shared types and constants
- `content` — curated ontology, templates, prompts, and citation data
- `docs` — implementation roadmap and build notes

## Current status
This repo now contains a working mobile/API prototype under the product name **The Ark**, with account flows, history, technical charting, and a traditional-astrology migration now driving the next engine and ontology changes.

## Web baseline
- The Expo client can now be treated as an intentional web target, not only a native shell.
- `apps/mobile` includes:
  - `npm run web` for local browser development
  - `npm run build:web` for static export
- API targeting follows this order:
  - `EXPO_PUBLIC_API_BASE_URL` if provided
  - `http://localhost:8000` or `http://127.0.0.1:8000` when running locally in a browser
- `window.location.origin` for hosted web when no explicit API override is provided
- The auth and onboarding screens now expose the API base URL directly so web testing and deployment do not require hidden draft edits.
- Deployment guidance for `www.arkastrology.app` and `api.arkastrology.app` lives in [docs/WEB_DEPLOYMENT.md](/Users/ronaldchapman/.openclaw/workspace/astrology-app/docs/WEB_DEPLOYMENT.md).

## Next implementation priorities
1. re-baseline the ontology and engine around the traditional astrology source-of-truth report
2. add sect, house rulers, planetary condition, and Fortune/Spirit to the chart contract
3. replace isolated-placement interpretation with house-ruler and repeated-testimony judgment
4. add traditional timing layers, starting with annual profections and then solar-return support
5. keep modern psychological and imaginal layers explicitly optional
