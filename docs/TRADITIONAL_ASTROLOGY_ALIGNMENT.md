# Traditional Astrology Alignment

This document turns the deep-research report into an implementation brief for The Ark.

## Source of truth

The attached research report is now the doctrinal baseline for how The Ark should conduct astrology:

- traditional astrology is treated as a symbolic and historical interpretive system, not a scientifically proven causal science
- the core engine should prioritize whole-sign houses, seven visible planets, sect, planetary condition, house rulership, Lots of Fortune and Spirit, and repeated testimony
- medieval, comparative, and modern material should be clearly labeled instead of silently merged into one undifferentiated layer

## What The Ark already does well

- uses whole-sign houses in the chart engine
- focuses on the seven visible planets plus Ascendant and Midheaven
- protects users from false precision when birth time is approximate or unknown
- uses a shared aspect policy across natal, synastry, and transit work
- anchors live transits to current location when available

## Main gaps against the report

### Engine gaps

- no sect calculation is exposed to the reading layer
- no Ascendant-ruler or house-ruler judgment
- no essential dignity or accidental condition stack
- no aversion, overcoming, combustion, visibility, or planetary-joy modeling
- no Fortune/Spirit calculation in the reading contract
- no annual profections or traditional timing stack

### Interpretation gaps

- `interpretation_service.py` still overweights Sun/Moon/rising summaries, house concentration, and generic aspect language
- the reading engine does not yet judge topics through house + ruler + occupants + repeated testimony
- confidence is not yet grounded in convergent versus contradictory chart evidence

### Content gaps

- the ontology files still mix traditional meanings with modern psychological and symbolic overlays
- source-lens labels currently make the app sound more uniformly Tetrabiblos-based than it really is
- the mobile guide still teaches some modern shorthand more strongly than the traditional method itself

### Product gaps

- current prediction cards lean on live transits and generic 30/90-day framing instead of traditional time-lord methods
- optional modern layers are not yet separated sharply enough from the traditional core in the default product experience

## Recommended implementation order

1. Expand the chart contract.
   Add sect, sect light, Ascendant ruler, house rulers, essential/accidental condition scaffolding, and Fortune/Spirit.

2. Split doctrine layers in content.
   Separate traditional core data from Jungian, Levi, and imaginal overlays so the UI can label each layer honestly.

3. Rewrite natal interpretation around traditional judgment order.
   Start with chart frame, then planetary condition, then topic-by-topic house/ruler reading, then confidence and caveats.

4. Rework timing.
   Keep live transits as a supplemental sky-weather layer, but make annual profections the first real traditional timing feature.

5. Update the UI and guide.
   Show evidence, doctrine layer, caveat, and confidence instead of only polished narrative summaries.

6. Strengthen tests.
   Add golden-chart coverage for sect, rulers, lots, dignities, and profection activation.

## Suggested file targets

- `apps/api/app/services/chart_engine.py`
- `apps/api/app/models/chart.py`
- `apps/api/app/services/interpretation_service.py`
- `apps/api/app/services/natal_service.py`
- `apps/api/app/services/synastry_service.py`
- `content/ontology/*.json`
- `apps/mobile/src/content/astrologyGuide.ts`
- `apps/mobile/src/screens/ReadingScreen.tsx`

## Immediate product rule

Until the deeper rewrite lands, The Ark should describe Jungian, Levi, and imaginal material as optional or app-synthesis overlays rather than as the historical source core itself.
