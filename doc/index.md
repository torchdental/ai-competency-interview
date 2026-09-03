# Documentation

Reference documentation for the Claim Processing Service, describing the system as currently
implemented. Setup and run instructions live in the root [README](../README.md); the
high-level design narrative lives in [ARCHITECTURE.md](../ARCHITECTURE.md).

| Page | Contents |
|---|---|
| [API Reference](api.md) | Every HTTP endpoint: parameters, request bodies, response shapes, status codes |
| [Data Model](data-model.md) | `Claim`, `Procedure`, `Payer` tables, columns, relationships, and JSON serialization |
| [Claim Lifecycle](claim-lifecycle.md) | Status states, the transition rules enforced at each layer, and terminal states |
| [Validation](validation.md) | The procedure code reference file, the max-amount rule, and unknown-code behavior |
| [Frontend](frontend.md) | React SPA routes, the dev proxy, and how the UI maps onto the API |
| [Development](development.md) | Tests, linting, seeding and resetting the database, and the worktree convention |

## Reading order

Start with [Data Model](data-model.md) and [Claim Lifecycle](claim-lifecycle.md) — the
lifecycle is the core domain rule, and most of the API exists to move claims through it.
[API Reference](api.md) and [Frontend](frontend.md) are then largely mechanical.

## Scope

These pages describe observed behavior in `src/`, `frontend/src/`, and `scripts/`. Where the
root README or ARCHITECTURE.md describes behavior the code does not implement, the relevant
page notes the difference rather than restating the claim.
