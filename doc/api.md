# API Reference

All routes are defined in [`src/api/routes.py`](../src/api/routes.py) under the `/api` prefix.
Interactive OpenAPI docs are served at `http://localhost:8000/docs` while the server is running.

## Conventions

- **Every endpoint requires a `practice_id` query parameter.** It is the tenant key: a claim
  belonging to one practice is invisible to another. On `POST /api/claims` it is part of the
  request body instead.
- Identifiers are integers (`claim_id`, `payer_id`).
- All field names are `snake_case`, in both request bodies and responses.
- Claim responses are produced by `Claim.to_dict()` — see [Data Model](data-model.md#serialization)
  for the exact shape.
- Errors use FastAPI's default envelope, `{"detail": ...}`, where `detail` is a string for most
  failures and an object for validation failures.

## Endpoints

### `GET /api/claims`

List every claim for a practice, newest first (ordered by `created_at` descending). Procedures
are eager-loaded on each claim.

| Parameter | In | Type | Notes |
|---|---|---|---|
| `practice_id` | query | string | Required |

```json
{ "claims": [ /* claim objects */ ], "total": 3 }
```

`total` is the length of the returned list, not a count of all matching rows — this endpoint is
unpaginated, so the two are currently the same.

---

### `GET /api/claims/{claim_id}`

Fetch a single claim with its procedures.

| Parameter | In | Type | Notes |
|---|---|---|---|
| `claim_id` | path | integer | |
| `practice_id` | query | string | Required |

Returns the claim object directly (not wrapped). Responds `404` when no claim matches **both**
the id and the practice — a claim owned by another practice is indistinguishable from one that
does not exist, which is the intended behavior for tenant isolation.

---

### `POST /api/claims`

Submit a new claim. Procedures are validated before anything is persisted; a claim that fails
validation is never written to the database.

```json
{
  "practice_id": "practice-1",
  "patient_name": "Alice Johnson",
  "payer_id": 1,
  "procedures": [
    { "code": "D0120", "description": "Periodic oral evaluation", "amount": 65.00 }
  ],
  "total_amount": 65.00
}
```

`description` defaults to `""` and may be omitted. `total_amount` is supplied by the client and
stored as given — the server does not recompute it from the procedure amounts or reject a
mismatch.

**Success (`200`):**

```json
{ "claim": { /* claim object */ }, "message": "Claim submitted successfully" }
```

The new claim always starts in `pending`; the request cannot set a status.

**Validation failure (`422`):**

```json
{ "detail": { "validation_errors": ["Procedure D0120: amount $200.00 exceeds maximum $75.00"] } }
```

Note that FastAPI also returns `422` for malformed request bodies, with its own
`detail` array of field errors. The two shapes differ — see [Validation](validation.md).

---

### `PATCH /api/claims/{claim_id}/status`

Move a claim to a new status.

| Parameter | In | Type | Notes |
|---|---|---|---|
| `claim_id` | path | integer | |
| `practice_id` | query | string | Required |

```json
{ "status": "validated" }
```

Returns the updated claim object. Responds `404` if the claim is not found within the practice,
and `400` with `"Invalid status transition"` if the requested move is not permitted from the
claim's current status.

The permitted moves are listed in [Claim Lifecycle](claim-lifecycle.md). This handler enforces
its own inline transition table rather than calling `ClaimService.transition_status()`, and the
two tables do not agree — the lifecycle page documents the difference.

---

### `DELETE /api/claims/{claim_id}`

Permanently delete a claim and, via the `delete-orphan` cascade, its procedures.

| Parameter | In | Type | Notes |
|---|---|---|---|
| `claim_id` | path | integer | |
| `practice_id` | query | string | Required |

```json
{ "deleted": true }
```

Unlike the other endpoints, this one loads the claim without practice scoping
(`get_claim_unrestricted`) and then compares `practice_id`, so a cross-practice request gets
`403 Access denied` rather than `404`. That distinction reveals whether a claim id exists in
another practice; the read endpoints deliberately do not.

Deletion is allowed from any status, including the terminal ones.

## Endpoints documented but not implemented

The root README lists two procedure endpoints that do not exist in `routes.py`:

- `PATCH /api/procedures/{id}` — void a procedure
- `POST /api/procedures/{id}/restore` — restore a voided procedure

There is also no `voided` column on the `Procedure` model to support them. Requests to these
paths return `404` from FastAPI's router.
