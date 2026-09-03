# Frontend

A React 18 SPA in [`frontend/`](../frontend), built with Vite and TypeScript, routed by
`react-router-dom`. It talks to the backend only over the REST API — there is no shared code
between the two halves of the repo.

## Running it

```bash
cd frontend
pnpm install --frozen-lockfile
pnpm dev
```

The dev server listens on `http://localhost:5173` and proxies `/api` to
`http://localhost:8000` (`vite.config.ts`). Because every request is same-origin through the
proxy, the app never needs a backend base URL and the backend needs no CORS configuration. A
production build (`pnpm build`) has no such proxy — deploying it would require serving the
bundle behind something that routes `/api` itself.

## Routes

| Route | Component | Purpose |
|---|---|---|
| `/` | `ClaimList` | Table of claims for the active practice |
| `/claims/:id` | `ClaimDetail` | One claim, its procedures, and status actions |
| `/submit` | `SubmitClaim` | Form for creating a claim |

`App.tsx` renders a two-link nav above the router outlet.

## Practice scoping

There is no authentication and no practice selector. `PRACTICE_ID` is a module-level constant
set to `"practice-1"` — declared separately in `ClaimList` and `ClaimDetail`, and inlined again
in the `SubmitClaim` request body. That value matches the practice used by
[`scripts/seed.py`](../scripts/seed.py), so seeded data is visible immediately.

## Data fetching

Plain `fetch` inside `useEffect`, with no client-side cache or shared state — each page loads
what it needs on mount, and `ClaimDetail` refetches after a status update rather than merging
the response it already received.

Types in [`frontend/src/types/api.ts`](../frontend/src/types/api.ts) are hand-written mirrors of
the backend's `to_dict()` output. They are not generated from the OpenAPI schema, so a backend
field change will not surface as a TypeScript error.

## Behavior worth knowing

- **`ClaimList`** swallows fetch failures with an empty `.catch(() => {})`, so a backend that is
  down renders as "No claims found" rather than an error.
- **`ClaimDetail`** shows a payer's numeric `payer_id` where a name would be expected; no endpoint
  exposes payer names, so the id is all the response carries.
- **`ClaimDetail`** offers a "Reject Claim" button on `pending` claims. The API rejects that
  transition with `400`, and the handler does not check the response, so the button appears to do
  nothing. See [Claim Lifecycle](claim-lifecycle.md) for why the two transition tables disagree.
- **`SubmitClaim`** computes `total_amount` client-side as the sum of the procedure amounts. The
  server stores whatever it is sent, so this is the only thing keeping the total consistent with
  the line items.
- **`SubmitClaim`** reads its error message from `data.detail?.message`, a key the backend never
  returns; every failure therefore shows the generic "Failed to submit claim" fallback instead of
  the specific validation errors described in [Validation](validation.md).
- The submit form sends `code` and `amount` but no `description`, which the backend defaults to
  `""` — so procedures created through the UI show a blank description on the detail page.

## Styling

There is no CSS file and no styling library. The whole stylesheet is an inline `<style>` block
in [`frontend/index.html`](../frontend/index.html), which defines the element defaults and the
class names the components use (`page`, `field`, `procedure-row`, `actions`, `error-banner`,
`success-banner`, `status-badge` and a `status-<status>` colour variant per claim state).
Components add per-element inline styles on top of that.

Because the classes are declared outside `frontend/src`, nothing links a component to its styles
— renaming a status value silently drops its badge colour.
