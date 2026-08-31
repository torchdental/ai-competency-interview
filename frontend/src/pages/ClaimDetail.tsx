import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import type { Claim } from "../types/api";

// Status options available for manual review actions
enum ClaimStatus {
  PENDING = "pending",
  REJECTED = "rejected",
  ACCEPTED = "accepted",
}

const PRACTICE_ID = "practice-1";

export function ClaimDetail() {
  const { id } = useParams<{ id: string }>();
  const [claim, setClaim] = useState<Claim | null>(null);

  useEffect(() => {
    fetch(`/api/claims/${id}?practice_id=${PRACTICE_ID}`)
      .then((res) => res.json())
      .then((data) => setClaim(data));
  }, [id]);

  const handleStatusUpdate = async (newStatus: ClaimStatus) => {
    await fetch(`/api/claims/${id}/status?practice_id=${PRACTICE_ID}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: newStatus }),
    });

    fetch(`/api/claims/${id}?practice_id=${PRACTICE_ID}`)
      .then((res) => res.json())
      .then((data) => setClaim(data));
  };

  if (!claim) return <div className="page">Loading...</div>;

  return (
    <div className="page">
      <h1>Claim Detail</h1>
      <div style={{ background: "#fff", padding: "1.25rem", borderRadius: "6px", marginBottom: "1.5rem" }}>
        <p><strong>Patient:</strong> {claim.patient_name}</p>
        <p style={{ marginTop: "0.5rem" }}><strong>Payer:</strong> {claim.payer_id}</p>
        <p style={{ marginTop: "0.5rem" }}>
          <strong>Status:</strong>{" "}
          <span className={`status-badge status-${claim.status}`}>{claim.status}</span>
        </p>
        <p style={{ marginTop: "0.5rem" }}><strong>Total:</strong> ${claim.total_amount.toFixed(2)}</p>
      </div>

      <h2>Procedures</h2>
      <table>
        <thead>
          <tr>
            <th>Code</th>
            <th>Description</th>
            <th>Amount</th>
          </tr>
        </thead>
        <tbody>
          {claim.procedures.map((proc) => (
            <tr key={proc.id}>
              <td>{proc.code}</td>
              <td>{proc.description}</td>
              <td>${proc.amount.toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="actions">
        {claim.status === "pending" && (
          <button type="button" onClick={() => handleStatusUpdate(ClaimStatus.REJECTED)}>
            Reject Claim
          </button>
        )}
        {claim.status === "validated" && (
          <>
            <button type="button" onClick={() => handleStatusUpdate(ClaimStatus.ACCEPTED)}>
              Accept
            </button>
            <button type="button" onClick={() => handleStatusUpdate(ClaimStatus.REJECTED)}>
              Reject
            </button>
          </>
        )}
      </div>
    </div>
  );
}
