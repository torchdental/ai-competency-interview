import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { requestJson } from "../apiRequest";
import type { Claim, ClaimsListResponse } from "../types/api";

const PRACTICE_ID = "practice-1";
const STATUSES: Claim["status"][] = ["pending", "validated", "rejected", "accepted"];

export function ClaimList() {
  const [searchParams, setSearchParams] = useSearchParams();
  // An unknown ?status= value (stale or hand-edited link) falls back to showing every claim.
  const status = STATUSES.find((s) => s === searchParams.get("status")) ?? null;

  const [claims, setClaims] = useState<Claim[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let ignore = false;
    const params = new URLSearchParams({ practice_id: PRACTICE_ID });
    if (status) params.set("status", status);

    setIsLoading(true);
    setError(null);
    requestJson<ClaimsListResponse>(`/api/claims?${params}`)
      .then((data) => {
        if (!ignore) setClaims(data.claims);
      })
      .catch((err) => {
        if (!ignore) setError(err instanceof Error ? err.message : "An error occurred");
      })
      .finally(() => {
        if (!ignore) setIsLoading(false);
      });
    // Discard responses for a filter the user has already moved away from.
    return () => {
      ignore = true;
    };
  }, [status]);

  return (
    <div className="page">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
        <h1 style={{ margin: 0 }}>Claims</h1>
        <Link to="/submit">
          <button type="button">Submit New Claim</button>
        </Link>
      </div>
      <div className="field" style={{ maxWidth: "220px" }}>
        <label htmlFor="status-filter">Status</label>
        <select
          id="status-filter"
          value={status ?? ""}
          onChange={(e) => setSearchParams(e.target.value ? { status: e.target.value } : {})}
        >
          <option value="">All statuses</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>
      {error ? (
        <div className="error-banner">Couldn't load claims: {error}</div>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Patient</th>
              <th>Status</th>
              <th>Amount</th>
              <th>Submitted</th>
            </tr>
          </thead>
          <tbody>
            {!isLoading &&
              claims.map((claim) => (
                <tr key={claim.id}>
                  <td>
                    <Link to={`/claims/${claim.id}`}>{claim.patient_name}</Link>
                  </td>
                  <td>
                    <span className={`status-badge status-${claim.status}`}>
                      {claim.status}
                    </span>
                  </td>
                  <td>${claim.total_amount.toFixed(2)}</td>
                  <td>{new Date(claim.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            {(isLoading || claims.length === 0) && (
              <tr>
                <td colSpan={4} style={{ textAlign: "center", color: "#888", padding: "2rem" }}>
                  {isLoading ? "Loading claims..." : status ? `No ${status} claims` : "No claims found"}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      )}
    </div>
  );
}
