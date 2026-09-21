# Candidate Task - Full Stack Track

## Context

You're joining a small team maintaining a claim processing service for dental insurance. The service has a Python/FastAPI backend and a React frontend. The backend has been the team's focus - the frontend has lagged behind and users have been vocal about it.

Your job today is to bring the UI up to par and extend the product where needed. Below is a working list of things the team has flagged. You won't finish all of it - that's expected. Spend a few minutes reading through the list, decide what you think is highest priority, and start there.

The frontend is the natural starting point, but don't treat the backend as off-limits - you'll likely need to go there.

Use whatever tools you'd normally use. The team expects you to move deliberately but quickly.

## The Backlog

**Claims list and submission flow** Users report two related issues: the claims list sometimes shows up empty with no explanation, and after submitting or updating a claim the list doesn't always reflect the change. Investigate both and fix them.

**Implement procedure voiding** The team wants users to be able to void individual procedures on a claim from the detail view - marking a line item as inactive without deleting the claim. Implement it end to end.

**Implement procedure restore** Voided procedures need a way back. Add a restore action to the UI for voided procedures and wire it to the backend. This is the natural companion to voiding.

**Implement the VALIDATED → PENDING return path** Per the documented business rules, a validated claim can be returned to PENDING if the payer requests additional documentation. This transition is documented but has not been implemented yet. It should be triggerable via the existing status PATCH endpoint.

**Add claim filtering** Users want to filter the claims list by status. A date range filter would also be useful but is lower priority. Keep filter state in the URL so links are shareable. This will need both a UI component and API support.

**Add pagination** GET /api/claims currently returns everything. Add pagination end to end: API support and a UI component. Think through the right approach before building.

**UX audit** Spend time using the application as a user would - submitting claims, navigating, updating statuses. Document what feels missing, broken, or confusing. Propose the top improvements and implement the ones you think are highest value.

## A Few Things to Know

  - The frontend dev server (pnpm dev from frontend/) proxies /api/* to http://localhost:8000 - you don't need to configure anything to connect the two.
  - SubmitClaim.tsx is the most polished page in the frontend — it's a useful reference for the patterns the team intended to use.
  - types/api.ts has the shared TypeScript types for API responses.
  - The backend API is documented at http://localhost:8000/docs.
  - uv run pytest runs the backend test suite if you want to verify backend behavior.
