# Data Model

Three SQLAlchemy models in [`src/models/`](../src/models), all sharing the declarative `Base` in
`base.py`. Storage is SQLite via `aiosqlite`; the file is `claims.db` at the repo root.

Tables are created by `init_db()` in [`src/common/db.py`](../src/common/db.py), which runs
`Base.metadata.create_all` during application startup. `init_db()` imports every model module
before creating tables — without those imports the mappers are unregistered and the
relationships fail to resolve. There are no migrations: a schema change means deleting
`claims.db` and reseeding (see [Development](development.md)).

## `claims`

`Claim` is the aggregate root. Everything else hangs off it.

| Column | Type | Notes |
|---|---|---|
| `id` | integer | Primary key, autoincrement |
| `practice_id` | string | Tenant key, indexed, not null |
| `patient_name` | string | Not null |
| `payer_id` | integer | FK → `payers.id`, not null |
| `status` | enum | `ClaimStatus`, defaults to `PENDING` |
| `total_amount` | float | Not null; supplied by the client, never recomputed |
| `created_at` | datetime | `server_default=now()` |
| `updated_at` | datetime | `server_default=now()`, `onupdate=now()` |

`practice_id` is indexed because every list query filters on it.

Relationships:

- `payer` → many-to-one `Payer`
- `procedures` → one-to-many `Procedure`, `cascade="all, delete-orphan"`, so deleting a claim
  deletes its procedures and detaching a procedure from the collection deletes the row

`procedures` is not lazy-safe under async SQLAlchemy: `ClaimService` uses
`selectinload(Claim.procedures)` on every read that will serialize a claim. A claim fetched
without that option raises on attribute access outside the session's greenlet context.

## `procedures`

A line item on a claim, one per CDT code billed.

| Column | Type | Notes |
|---|---|---|
| `id` | integer | Primary key, autoincrement |
| `claim_id` | integer | FK → `claims.id`, not null |
| `code` | string | CDT procedure code, e.g. `D0120` |
| `description` | string | Nullable |
| `amount` | float | Billed amount, not null |

`code` is a plain string with no foreign key to the code reference — the allowed set lives in a
JSON file, not a table. See [Validation](validation.md).

## `payers`

An insurance company.

| Column | Type | Notes |
|---|---|---|
| `id` | integer | Primary key, autoincrement |
| `name` | string | Display name, not null |
| `payer_code` | string | Short code, not null, unique |

Payers are created only by the seed script; there is no API for managing them.

## `ClaimStatus`

A `str`-valued `Enum` in `src/models/claim.py`, stored as a SQLAlchemy `Enum` column.

| Member | Serialized value |
|---|---|
| `PENDING` | `"pending"` |
| `VALIDATED` | `"validated"` |
| `REJECTED` | `"rejected"` |
| `ACCEPTED` | `"accepted"` |

Values are lowercase in JSON and in the database. See [Claim Lifecycle](claim-lifecycle.md) for
the permitted transitions.

## Serialization

Each model has a `to_dict()` used directly by the route handlers — there are no Pydantic response
models, so `to_dict()` is the API contract. A claim serializes as:

```json
{
  "id": 1,
  "practice_id": "practice-1",
  "patient_name": "Alice Johnson",
  "payer_id": 1,
  "status": "pending",
  "total_amount": 215.0,
  "created_at": "2026-01-15T10:30:00",
  "updated_at": "2026-01-15T10:30:00",
  "procedures": [
    { "id": 1, "claim_id": 1, "code": "D0120", "description": "Periodic oral evaluation", "amount": 65.0 }
  ]
}
```

Timestamps are ISO 8601 with no timezone offset — `func.now()` on SQLite yields a naive UTC
datetime. `payer` is not embedded; responses carry `payer_id` only, and there is no endpoint to
resolve it to a name.

Because `to_dict()` is hand-written, adding a column does not change the API until the method is
updated too. The frontend's `types/api.ts` mirrors these shapes by hand and has the same
property.

## Naming

The code is `snake_case` throughout — models, JSON keys, and the frontend's TypeScript
interfaces. ARCHITECTURE.md documents several fields in `camelCase` (`patientName`, `claimId`,
`totalAmount`, `payerCode`); those names do not appear anywhere in the codebase.
