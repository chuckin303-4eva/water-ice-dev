# Roadmap

## PM operating rules

- Revenue-generating features are prioritized first within whatever is currently in scope.
- Every feature carries a rank: **Critical / High / Medium / Low**.
- Before starting any feature, state: business value, estimated complexity, dependencies, risk, expected user impact.
- Phases are built and completed in order — Phase 2 doesn't start before Phase 1 is done. A request that jumps ahead of the current phase or adds scope the phase didn't call for gets flagged, with a recommended sequence, not built silently.
- Optimize for a usable product in customer hands quickly, not for completeness.

**Standing tension worth naming:** "revenue first" and "phases completed in order" pull against each other here, because Subscriptions/Billing (the actual revenue mechanism) are scheduled in Phase 3, after the full MVP and validation workflow. That's fine as a build order — a location-intelligence tool has to be worth paying for before billing infrastructure matters — but it means "revenue-generating" in Phase 1/2 should be read as "features that make the product sellable/demoable," not "features that collect money." If you want actual paying customers before Phase 3, that's handled outside the app (manual invoicing) rather than by reordering the phases.

## Phase 1 — MVP (done)

Goal: usable product in customer hands as fast as possible. Ordered by dependency chain and revenue leverage (what makes the product demoable/sellable soonest), not by the order features were listed.

| # | Feature | Rank | Why this rank |
|---|---|---|---|
| 1 | Database + project scaffold | Critical | Nothing else is buildable without it. |
| 2 | User authentication | Critical | No real customer data gets exposed without it; also the first thing a demo/pilot needs. |
| 3 | Location management (CRUD) | Critical | Done. The core entity of the entire product — built as prospecting (add by pin/address, property/utility/contact fields, geocoding, call notes + calendar follow-up). Power/water utility auto-lookup and property-ownership lookup explicitly deferred/manual (ADR-0006) — see docs/DATABASE.md. |
| 4 | Interactive map | Critical | Done. Primary interface — clustered Leaflet map (raw OSM tiles, dev-only per ADR-0007), status-colored markers, add-prospect by pin or address, detail panel with call notes + calendar follow-up. Tile provider swap before real users tracked in ADR-0007. |
| 5 | Competitor tracking | High | Done (ADR-0008). Not originally a numbered item, pulled forward because it's directly requested and central to "location intelligence" — `competitors` CRUD, orange square map pins distinct from location pins, click-to-view panel (address/inside-outside/brand/size/ice-water/price). No free automated source exists for specific competitor addresses (researched, ADR-0008); populated by hand via the same map-click pattern as prospects, or a future gated paid-API option. |
| 6 | Basic scoring | High | Done (ADR-0009). `competition_score` computed for real from `competitors` proximity (app-level haversine); `opportunity_score` a composite of that plus two newly-exposed manual 1-10 ratings (`visibility_rating`, `traffic_score`) — stays `null`, and the pin stays yellow, until both are rated. Demographic fields (`population`/`median_income`/`growth_rate`) stay unused pending a real data source (Phase 3 Market Refresh Engine), not faked. |
| 7 | Filters | High | Done (ADR-0010). Server-side (not just client-side) filtering on `GET /locations`/`GET /competitors` — status, opt-in ice/water capability, minimum opportunity score, brand — plus a client-side show/hide toggle for the competitor layer. Server-side per the schema's own 100k-location design target, not just today's small dataset. |
| 8 | Import CSV | High | Done (ADR-0011). `POST /locations/import`, minimal column set (address or lat/lng, serves_ice, serves_water, notes), 100-row cap, partial success reported per row. Rows geocode sequentially with a rate-limit delay (real cost of respecting Nominatim's free-tier usage policy at bulk volume, ADR-0004/ADR-0006) — a 100-row import takes ~2 minutes by design, not a bug. |
| 9 | Admin dashboard | Medium | Done (ADR-0012). Self-serve registration (`POST /auth/register`, new org + first admin user, no email verification/CAPTCHA yet), plus a `/admin` "Team" page: list teammates, add a teammate (admin sets their password directly, no email service to invite through), change role (admin/member) or active status. Two system-wide roles only -- no fine-grained permission-slug system, since nothing needs it yet. First real use of the `react-router-dom` dependency installed back in ADR-0007. |
| 10 | Export CSV | Medium | Done (ADR-0013). `GET /locations/export` and `GET /competitors/export`, full field set, same filters as the list endpoints (export-what-you're-looking-at). Synchronous, no row cap -- unlike import there's no geocoding/rate limit to work around. This closes out every item currently on the Phase 1 roadmap. |

## Phase 2 — Validation & Enrichment (in progress)

| Feature | Rank | Why this rank |
|---|---|---|
| Validation workflow | High | Done (ADR-0014). Opt-in per organization (`require_review_for_submissions`, default off) -- when on, a non-admin's `POST`/`PUT /locations` and per-row `POST /locations/import` are queued to `validation_queue` instead of applying directly; admin writes always bypass it. New admin-only Review page (`/admin/review`) to approve/reject. Deliberately narrow scope: locations only, not competitors (which stay "corrected freely, not audited" per ADR-0008) and not archive/recalculate. Default-off specifically to avoid changing behavior for any existing organization (ADR-0005 backward-compat pause condition). |
| Host businesses | High | Done (ADR-0015). `host_businesses` and `locations.host_business_id` were designed and migrated back in ADR-0003 but never built on -- no way to create one or see its name/category anywhere. Real CRUD (`/host-businesses`, with `?search=`), `LocationResponse` now exposes the linked business's name/category, and `host_business_id` is validated on location create/update (422 if it doesn't exist, instead of a raw FK error). Frontend: a search-or-create picker on the location detail panel, matching the "find or add" shape already used for competitor brands -- no standalone host-business directory page, not requested. |
| Opportunity scoring (refined) | High | |
| Photos | Medium | |

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
- Demographics in scoring (ADR-0009) — `population`/`median_income`/`growth_rate` stay out of the `opportunity_score` formula until the Market Refresh Engine (Phase 3, ADR-0004) wires a real data source; not defaulted to zero in the meantime.
- Fine-grained permission slugs, email-based invites, email verification, and CAPTCHA on registration (ADR-0012) — the `permissions`/`role_permissions` tables stay schema-only until a real capability needs finer gating than admin/member; the other three need an email service and/or a CAPTCHA provider this project doesn't have, and weren't silently faked.
