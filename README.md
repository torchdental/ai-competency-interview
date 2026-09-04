# Claim Processing Service

A backend service for managing dental insurance claims through their processing lifecycle. Claims are submitted with procedure codes, validated against allowed amounts, and transitioned through review states before reaching a terminal status.

---

## Prerequisites

| Tool | Version |
|---|---|
| Python | 3.13 |
| uv | 0.7.0+ |
| Node.js | 20.x LTS |
| pnpm | 9.15.0 |

### Install uv

**Mac / Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Install Node.js 20.x LTS

**Mac (via nvm):**
```bash
nvm install 20
nvm use 20
```

**Windows (via nvm-windows):**
```powershell
nvm install 20
nvm use 20
```

Or download directly from [nodejs.org/en/download](https://nodejs.org/en/download) — select the **20.x LTS** installer.

### Install pnpm 9.15.0

```bash
npm install -g pnpm@9.15.0
```

---

## Setup

### Backend

```bash
uv sync
```

uv will install Python 3.13 if needed and create a `.venv` with pinned dependencies.

### Frontend

```bash
cd frontend
pnpm install --frozen-lockfile
```

`--frozen-lockfile` ensures installed versions match the committed `pnpm-lock.yaml` exactly.

---

## Running the Service

**Backend** (from repo root):
```bash
uv run uvicorn src.app:app --reload
```

API available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

**Frontend** (separate terminal, from `frontend/`):
```bash
pnpm dev
```

UI available at `http://localhost:5173`. The dev server proxies `/api/*` to the backend.

---

## Running Tests

```bash
uv run pytest
```

---

## API Overview

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/claims` | List claims for a practice |
| `POST` | `/api/claims` | Submit a new claim |
| `GET` | `/api/claims/{id}` | Get claim details |
| `PATCH` | `/api/claims/{id}/status` | Transition claim status |
| `DELETE` | `/api/claims/{id}` | Delete a claim |
| `PATCH` | `/api/procedures/{id}` | Void a procedure (`{"voided": true}`) |
| `POST` | `/api/procedures/{id}/restore` | Restore a voided procedure |

All endpoints require a `practice_id` query parameter for scoping. See `http://localhost:8000/docs` for full request/response shapes.
