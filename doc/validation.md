# Validation

[`ValidationService`](../src/services/validation_service.py) checks the procedures on an incoming
claim against a reference set of CDT codes. It is stateless apart from the loaded code table and
takes no database session.

## The code reference file

Allowed codes live in [`data/procedure_codes.json`](../data/procedure_codes.json), keyed by CDT
code:

```json
{
  "D0120": {
    "description": "Periodic oral evaluation",
    "category": "diagnostic",
    "max_amount": 75.00
  }
}
```

Seven codes are defined, spanning the `diagnostic`, `restorative`, `oral_surgery`, and
`orthodontics` categories. `category` is carried in the file but nothing reads it — only
`max_amount` affects behavior, and `description` is unused by the service (procedure descriptions
come from the request body instead).

The path is resolved in `src/common/constants.py` relative to the repo root, so the file is read
from the source tree rather than from package data.

## When validation runs

Only on `POST /api/claims`, before anything is persisted. The route constructs a
`ValidationService`, calls `validate_claim()` with the submitted procedures, and raises
`422` if any errors come back — so a claim that fails validation is never written.

Nothing revalidates afterwards. Editing procedures is not possible through the API, and status
transitions do not re-check codes or amounts (see [Claim Lifecycle](claim-lifecycle.md)).

A new `ValidationService` is constructed per request, which re-reads and re-parses the JSON file
each time. At seven codes this is not worth caching, but it does mean edits to the file take
effect without a restart.

## The rules

`validate_claim()` returns a list of human-readable error strings, empty when everything passes.
For each procedure it looks up the code and compares the billed amount:

- **Amount over the cap** — `amount > max_amount` produces
  `Procedure D0120: amount $200.00 exceeds maximum $75.00`. The comparison is strictly greater
  than, so billing exactly the maximum passes.
- **Amount is not otherwise constrained** — zero and negative amounts pass, as does a claim with
  no procedures at all.
- **Duplicate codes are allowed** — each line is validated independently; there is no per-claim
  aggregate cap.

Every procedure is checked, so a claim with several bad amounts yields several errors in one
response.

## Unknown codes

`validate_procedure_code()` looks the code up with `self._codes[code]`. An unrecognized code
therefore raises `KeyError`, which no handler catches — the request fails with `500 Internal
Server Error` rather than a `422` naming the bad code.

This is the one validation outcome the API does not report usefully. ARCHITECTURE.md describes
an unrecognized code as a validation failure that rejects the claim, and the README's `/docs`
contract implies a `422`; neither matches the current behavior.

## Payer-specific codes

All payers share one code set. `validate_procedure_code()` carries a comment marking the gap:
the method would need to accept a `payer_id` and select a payer-specific table. Nothing in the
data model supports that today — `payers` has no relationship to codes, and the JSON file has no
payer dimension.

## Error shapes

Two different `422` bodies can come back from `POST /api/claims`, and a client needs to
distinguish them:

```json
{ "detail": { "validation_errors": ["Procedure D0120: amount $200.00 exceeds maximum $75.00"] } }
```

is a domain validation failure, while FastAPI's own request-schema rejection (a missing field, a
non-numeric amount) produces its standard array of field errors under the same `detail` key:

```json
{ "detail": [ { "type": "missing", "loc": ["body", "payer_id"], "msg": "Field required" } ] }
```

The submit form in the frontend reads `data.detail?.message`, which is absent from both shapes,
so it always falls back to its generic "Failed to submit claim" text — see
[Frontend](frontend.md).
