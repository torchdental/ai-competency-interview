# Development

Setup and run commands are in the root [README](../README.md). This page covers the day-to-day
loop: tests, linting, database state, and repo conventions.

## Layout

```
src/
├── app.py          FastAPI app; lifespan calls init_db()
├── api/routes.py   Every HTTP handler
├── services/       Domain logic (claim persistence, validation)
├── models/         SQLAlchemy models
└── common/         Engine and session factory, exceptions, paths
```

The dependency direction is `routes → services → models`, with `common` underneath all three.
Route handlers get a `ClaimService` through FastAPI's `Depends`, which is what makes them
testable without a running server — though the current tests exercise the services directly and
never go through HTTP.

## Tests

```bash
uv run pytest
```

Nine tests in [`tests/`](../tests), split between `ValidationService` (pure, no database) and
`ClaimService` (against SQLite). `asyncio_mode = "auto"` is set in `pyproject.toml`, so `async`
test functions need no `@pytest.mark.asyncio` decorator.

Fixtures live in `tests/conftest.py`:

| Fixture | Provides |
|---|---|
| `session` | An `AsyncSession` on a fresh in-memory SQLite database |
| `claim_service` | A `ClaimService` bound to that session |
| `payer` | One committed `Payer` to satisfy the `payer_id` foreign key |

Each test gets its own engine and its own schema, created and dropped around the test, so tests
are isolated and order-independent. The in-memory database means no cleanup of `claims.db`.

There are no route-level tests. `httpx` is already a dependency, so a FastAPI `TestClient` or
`ASGITransport` suite could be added without new packages — worth knowing, because the transition
rules the API actually enforces live in `routes.py` and are currently untested (see
[Claim Lifecycle](claim-lifecycle.md)).

## Linting

```bash
uv run ruff check .
uv run ruff format .
```

Configured in `pyproject.toml` with `src = ["src"]` and `extend-select = ["I"]`, so import
sorting is enforced alongside the default rule set.

## Database

SQLite at `claims.db` in the repo root, gitignored via the `*.db` pattern. The URL is hardcoded
in `src/common/db.py` — there is no environment-based configuration.

```bash
uv run python scripts/seed.py     # payers + five sample claims
uv run python scripts/reset.py    # delete claims.db, then seed
```

`seed.py` creates three payers (Delta Dental, Cigna, Aetna) and five claims for
`practice-1`, one in each status plus a second `pending` — enough to exercise every badge and
every status action in the UI. Unlike the API, it computes `total_amount` from the procedures it
attaches. It is not idempotent: a second run fails on the unique `payer_code` while flushing the
payers, before any claim is written, so use `reset.py` to start over.

There is no migration tool. `init_db()` only issues `create_all`, which creates missing tables
and never alters existing ones — so a change to a column requires `reset.py`, not just a restart.

## Worktree convention

Feature branches are developed in git worktrees under `.worktrees/<branch-name>`, one directory
per branch, all sharing the main checkout's `.git`. Each worktree needs its own `uv sync` (the
`.venv` is not shared) and its own `frontend/pnpm install`.

```bash
git worktree add .worktrees/my-branch -b my-branch main
git worktree list
```

Branch from the local `main` rather than `origin/main` so the new branch starts with no upstream
set, and push with `-u` when it is ready.
