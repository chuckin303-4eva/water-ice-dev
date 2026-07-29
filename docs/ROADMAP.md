# Roadmap

## PM operating rules

- Revenue-generating features are prioritized first within whatever is currently in scope.
- Every feature carries a rank: **Critical / High / Medium / Low**.
- Before starting any feature, state: business value, estimated complexity, dependencies, risk, expected user impact.
- Phases are built and completed in order — Phase 2 doesn't start before Phase 1 is done. A request that jumps ahead of the current phase or adds scope the phase didn't call for gets flagged, with a recommended sequence, not built silently.
- Optimize for a usable product in customer hands quickly, not for completeness.

**Standing tension worth naming:** "revenue first" and "phases completed in order" pull against each other here, because Subscriptions/Billing (the actual revenue mechanism) are scheduled in Phase 3, after the full MVP and validation workflow. That's fine as a build order — a location-intelligence tool has to be worth paying for before billing infrastructure matters — but it means "revenue-generating" in Phase 1/2 should be read as "features that make the product sellable/demoable," not "features that collect money." If you want actual paying customers before Phase 3, that's handled outside the app (manual invoicing) rather than by reordering the phases.

## Phase 1 — MVP (in progress)

Goal: usable product in customer hands as fast as possible. Ordered by dependency chain and revenue leverage (what makes the product demoable/sellable soonest), not by the order features were listed.

| # | Feature | Rank | Why this rank |
|---|---|---|---|
| 1 | Database + project scaffold | Critical | Nothing else is buildable without it. |
| 2 | User authentication | Critical | No real customer data gets exposed without it; also the first thing a demo/pilot needs. |
| 3 | Location management (CRUD) | Critical | Done. The core entity of the entire product — built as prospecting (add by pin/address, property/utility/contact fields, geocoding, call notes + calendar follow-up). Power/water utility auto-lookup and property-ownership lookup explicitly deferred/manual (ADR-0006) — see docs/DATABASE.md. |
| 4 | Interactive map | Critical | Done. Primary interface — clustered Leaflet map (raw OSM tiles, dev-only per ADR-0007), status-colored markers, add-prospect by pin or address, detail panel with call notes + calendar follow-up. Tile provider swap before real users tracked in ADR-0007. |
| 5 | Competitor tracking | High | Done (ADR-0008). Not originally a numbered item, pulled forward because it's directly requested and central to "location intelligence" — `competitors` CRUD, orange square map pins distinct from location pins, click-to-view panel (address/inside-outside/brand/size/ice-water/price). No free automated source exists for specific competitor addresses (researched, ADR-0008); populated by hand via the same map-click pattern as prospects, or a future gated paid-API option. |
| 6 | Basic scoring | High | The actual differentiator ("intelligence," not just a database), but a first cut can ship once CRUD/map exist — doesn't have to be perfect to demo. Map already reads `locations.opportunity_score` for pin color (ADR-0008) — this feature just needs to start writing to it. |
| 7 | Filters | High | Map/table becomes unusable at real data volume without it. |
| 8 | Import CSV | High | Lets a prospective customer load their existing location list immediately instead of manual entry — directly shortens time-to-value, which is a real revenue lever (faster to a sellable demo). |
| 9 | Admin dashboard | Medium | Org/user management so a paying customer's team can self-serve; not the core value prop but needed once there's more than one user per tenant. |
| 10 | Export CSV | Medium | Portability/trust feature. Valuable, not blocking initial usability. |

## Phase 2 — Validation & Enrichment (not started, gated on Phase 1)

| Feature | Rank |
|---|---|
| Validation workflow | High |
| Host businesses | High |
| Opportunity scoring (refined) | High |
| Photos | Medium |

## Phase 3 — Automation & Monetization (not started, gated on Phase 2)

| Feature | Rank |
|---|---|
| Subscriptions | Critical — this is the actual revenue mechanism |
| Billing | Critical |
| Automated updates (Market Refresh Engine, ADR-0004 — already designed) | High |
| External APIs (free-source providers per ADR-0004) | Medium |

## Phase 4 — Advanced (not started, gated on Phase 3)

| Feature | Rank |
|---|---|
| AI recommendations | Medium |
| Advanced analytics | Medium |
| Enterprise features | Low — until real paying customers signal demand for them |

## Explicitly out of scope (for now)

- Industries beyond ice/water vending, until the module pattern is validated by building two real modules.
- Public API for third-party integrations — internal use only until core stabilizes.
- PostGIS, paid market-refresh providers, and background job infrastructure — all deliberately deferred per ADR-0002/ADR-0004; do not reintroduce without a new ADR and sign-off.
- Power/water utility auto-lookup for prospects (ADR-0006) — free federal data sources confirmed to exist (EIA, OpenEI URDB, EPA), but the exact API integration wasn't built yet; a well-scoped next step, not abandoned. Property ownership and sewer-availability lookups stay manual indefinitely — no free source exists for either.
- Automated competitor-data population (ADR-0008) — confirmed no free, scrapeable source exists for specific ice/water vending machine addresses; a paid Places API remains a future gated option, same treatment as the KMS/LLM-API cost gates on the related project. Manual entry via the map is the current path.
