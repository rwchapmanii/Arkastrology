# Implementation Roadmap

## Phase 0 - completed scaffolding
- monorepo structure
- mobile shell
- api shell
- shared types package
- content directories

## Phase 1 - doctrine alignment
- adopt the traditional astrology research report as the doctrinal source of truth
- split ontology content into traditional core, later traditional extensions, optional modern overlays, and app synthesis
- relabel citations and source lenses so ancient, medieval, and modern material are never silently blended
- keep optional Jungian and imaginal layers off by default for new readings

## Phase 2 - core traditional chart contract
- expand the natal chart payload with sect, sect light, ascendant ruler, house rulers, and chart-frame metadata
- add essential and accidental condition scaffolding: domicile, exaltation, triplicity, bounds, face, angularity, visibility, retrogradation, and aversion
- calculate Fortune and Spirit at minimum, with room for additional lots later
- preserve exact-time honesty and fallback behavior for approximate charts

## Phase 3 - interpretation engine rewrite
- replace isolated Sun/Moon/rising summaries with chart-structure-first judgment
- read topics through house + house ruler + occupants + aspect testimony + lot support
- store explicit evidence trails and confidence based on repeated testimony versus contradiction
- keep transits supplemental instead of letting them stand in for the traditional timing stack

## Phase 4 - traditional timing stack
- implement annual profections first
- add solar-return support as the next timing layer
- add distributions, zodiacal releasing, and other advanced timing methods only after the core engine is stable
- label medieval or comparative methods clearly when they are introduced

## Phase 5 - product and UX alignment
- show doctrine layers, evidence, and caveats directly in the reading UI
- update guide content so signs are not confused with houses and symbolic language is not presented as scientific proof
- surface sensitive-topic safeguards and non-deterministic language rules in the response layer
- keep synastry, electional, and relocation work downstream of the natal-core rewrite
