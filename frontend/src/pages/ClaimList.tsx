import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import type { Claim } from "../types/api";

const PRACTICE_ID = "practice-1";

export function ClaimList() {
  const [claims, setClaims] = useState<Claim[]>([]);

  useEffect(() => {
    fetch(`/api/claims?practice_id=${PRACTICE_ID}`)
      .then((res) => res.json())
      .then((data) => setClaims(data.claims))
      .catch(() => {});
  }, []);

  return (
    <div className="page">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
        <h1 style={{ margin: 0 }}>Claims</h1>
        <Link to="/submit">
          <button type="button">Submit New Claim</button>
        </Link>
      </div>
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
          {claims.map((claim) => (
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
          {claims.length === 0 && (
            <tr>
              <td colSpan={4} style={{ textAlign: "center", color: "#888", padding: "2rem" }}>
                No claims found
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
