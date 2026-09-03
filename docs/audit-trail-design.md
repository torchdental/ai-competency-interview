# Audit Trail for Claim Status Transitions

Design proposal. Not implemented.

## Assumptions

- The branch consolidating `update_claim_status` onto `ClaimService.transition_status()` lands first. Today the route mutates `claim.status` directly with its own inline transition table, which already disagrees with the service's: the route omits `PENDING → REJECTED`. Two tables, two behaviours, and neither can be instrumented once. That divergence is the argument for the chokepoint, and instrumenting the route as it stands would produce a trail that silently misses whatever the service path does.
- No auth layer. `practice_id` is a query parameter; there is no user identity anywhere in the request.

## Recommendation in one line

A dedicated `claim_status_events` table, written synchronously inside the existing transition transaction, read through `GET /api/claims/{id}/history`.

---

## 1. Data model

`src/models/status_event.py`:

| Column | Type | Notes |
|---|---|---|
| `id` | `int` PK autoincrement | Also the ordering key |
| `claim_id` | `int` FK → `claims.id`, not null | |
| `practice_id` | `str`, not null | Denormalized from the claim |
| `from_status` | `SAEnum(ClaimStatus)`, **nullable** | Null for the claim's creation row |
| `to_status` | `SAEnum(ClaimStatus)`, not null | |
| `source` | `SAEnum(EventSource)`, not null | See §2 |
| `actor` | `str`, nullable | Reserved for auth; always null in v1 |
| `note` | `str`, nullable | Free text, e.g. a rejection reason |
| `created_at` | `datetime`, `server_default=func.now()` | |

```python
class EventSource(str, Enum):
    API = "api"
    SYSTEM = "system"
    SEED = "seed"
    BACKFILL = "backfill"
```

Use `SAEnum(ClaimStatus)` rather than `String` so the stored representation matches `claims.status` — SQLAlchemy's `Enum` persists member *names*, and a `String` column holding `.value` would not compare or read back the same way.

**Indexes:** `(claim_id, id)` for the per-claim timeline; `(practice_id, created_at)` for cross-claim audit queries. Order timelines by `id`, never `created_at`: `func.now()` on SQLite has second resolution, and two transitions inside one second are ordinary in tests.

**Relationship:** `Claim.status_events` with `cascade="all, delete-orphan"`, plus a `to_dict()` matching the shape of the other models. Do **not** add events to `Claim.to_dict()` — `list_claims` uses `selectinload(Claim.procedures)` and returns every claim for a practice; embedding history there invites an N+1 or a large unbounded payload on the list endpoint.

`practice_id` is denormalized deliberately. A claim never changes practice, so it cannot drift, and it keeps the history endpoint and any practice-wide audit query join-free — matching how every other query in the service already scopes.

### Deletion

`DELETE /api/claims/{id}` hard-deletes. SQLite does not enforce foreign keys unless `PRAGMA foreign_keys=ON` is set, which this service does not set, so `ondelete="CASCADE"` on the FK would be inert; `Procedure` rows are cleaned up by the ORM cascade, not the database. Recommendation: use the same ORM cascade, so a deleted claim takes its events with it. That is consistent and leaves no orphans, but it means the audit trail cannot outlive the record it audits. If the team wants an audit trail that survives deletion, the fix is to make claim deletion soft — a separate ticket, and worth raising, but not something this design should work around.

## 2. What "triggered it" means

There is no user identity to record, so don't model one. What is actually knowable at the write site:

- **`source`** — which code path performed the transition. `api` for an HTTP request, `system` for a future automated transition (validation-driven `PENDING → VALIDATED`), `seed`/`backfill` for the two synthetic origins in §6. This is honest and useful today: it distinguishes a human clicking through the UI from a batch job.
- **`actor`** — nullable, always null until auth exists. Present in the schema now so that adding auth is a write-site change, not a migration. When an auth layer lands it holds whatever stable identifier that layer produces (a user id); `practice_id` is not an actor — it is a tenant, and it is already on the row.
- **`note`** — the only place a human-supplied reason can go. `VALIDATED → REJECTED` is the case that will want one.

What genuinely requires auth first: attributing a change to a person, distinguishing two users at the same practice, and any non-repudiation claim. Until then the trail answers "what happened and when", not "who did it" — say that in the API docs rather than implying otherwise with a half-populated actor field.

## 3. Where the write happens

Two insertion points, both in `ClaimService`:

1. **`transition_status()`** — the chokepoint. Add the event before the existing `await self.session.commit()`:

   ```python
   async def transition_status(
       self,
       claim: Claim,
       new_status: ClaimStatus,
       *,
       source: EventSource = EventSource.API,
       actor: str | None = None,
       note: str | None = None,
   ) -> Claim:
   ```

   Keyword-only with defaults, so the consolidation branch's callers keep working unchanged.

2. **`create_claim()`** — writes `from_status=None → to_status=PENDING`. Without this the trail begins mid-story and a claim that was never transitioned has no rows at all, which is indistinguishable from a claim whose events were lost.

Putting the write in the route handler instead would leave `create_claim` and any future internal caller untracked, and would need duplicating for every new route. Putting it in a SQLAlchemy event hook (`before_update` on `Claim`) catches more paths — including the seed script — but has no access to `source` or `note` and fires for unrelated column updates; the explicit service call is clearer and the chokepoint makes it sufficient.

Note that `scripts/seed.py` is a third write path: it constructs `Claim(status=...)` directly. It should pass `source=SEED` events for the states it fabricates, or accept that seeded claims start with a backfilled row (§6).

## 4. API surface

**Expose it.** `ClaimDetail.tsx` already exists and is the obvious consumer; a trail nobody can read is a table that will silently rot.

```
GET /api/claims/{claim_id}/history?practice_id=...
→ {"events": [ ... ], "total": N}
```

Scoping and errors mirror `get_claim`: fetch the claim scoped by `practice_id`, return 404 if it is not found for that practice. Deliberately *not* `delete_claim`'s pattern of fetching unrestricted and returning 403 on mismatch — that leaks the existence of another practice's claim.

Events ascending by `id`. No pagination in v1: the lifecycle graph is four states with terminal sinks, so a claim's history is bounded at a handful of rows.

No POST. Events are written only as a side effect of a transition; an endpoint that lets a client insert arbitrary audit rows defeats the purpose.

## 5. Tradeoffs

**Dedicated `claim_status_events` table (recommended)** — typed enum columns, FK to `claims`, indexes that mean something, and the query the UI needs is one `WHERE claim_id = ?`. The cost is that the next auditable entity (procedure voids, payer changes) needs its own table. That cost is real and still worth paying: two purpose-built tables beat one table that is honest about neither.

**Generic polymorphic audit table** (`entity_type`, `entity_id`, `field`, `old_value`, `new_value` as strings) — one table covers everything, at the price of no FK, no enum validation, stringly-typed values, and an index on `(entity_type, entity_id)` that every entity contends for. Worth it in a system with a dozen auditable entities. This service has one.

**Append-only event log as the source of truth** (status derived by replaying events, `claims.status` dropped) — the strongest correctness story: state and history cannot disagree. It also rewrites every read path in the service to fold events, and requires a projection or cache before the list endpoint is usable. Enormous change for a four-state machine. No.

**Synchronous write in the same transaction (recommended)** vs. async — one `session.add()` before the commit that already exists. Atomic for free: no transition can commit without its event, and a rolled-back transition leaves no phantom row. Async (outbox, queue, background task) buys write throughput this service does not need and introduces the exact failure mode an audit trail must not have — a committed state change with a lost event.

**Retention: keep everything, no policy in v1.** Claims are regulated records with a real audit interest; volume is bounded by claim count times a handful of transitions. Revisit if and when the table is measured in millions of rows, not before.

## 6. Backfill and migration

**Schema:** `Base.metadata.create_all` is additive — it creates missing tables and never alters existing ones — so an existing `claims.db` picks up `claim_status_events` on the next startup, with no reset and no migration tool. The one requirement is that `init_db()` imports `src.models.status_event` alongside the other model modules; commit 4bded39 exists because an unimported model breaks mapper registration.

**Data:** existing claims have a status and no history. Write a one-off `scripts/backfill_status_events.py` that inserts a single synthetic row per claim with no events:

```
from_status=None, to_status=<claim.status>, source=BACKFILL,
created_at=claim.updated_at, actor=None
```

Intermediate states are unrecoverable — a claim sitting at `ACCEPTED` passed through `PENDING` and `VALIDATED`, and nothing recorded when. The synthetic row says "this claim was at this status as of this time, provenance unknown", which is the true statement. Using `BACKFILL` rather than inventing plausible transitions keeps derived metrics (time-in-state, transition counts) able to exclude what was never observed.

The script must be idempotent — skip claims that already have events — since it will be run once per environment and probably twice somewhere.

**For production:** introduce Alembic. Not for this change, which `create_all` handles, but for the one after it. Adding a column, renaming an enum member, or backfilling under a lock is exactly what `create_all` cannot do, and discovering that during an incident is worse than adding the dependency now. `scripts/reset.py` is the right answer for local development only — it deletes the database.
