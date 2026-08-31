import { useState } from "react";

interface ProcedureInput {
  code: string;
  amount: string;
}

export function SubmitClaim() {
  const [patientName, setPatientName] = useState("");
  const [payerId, setPayerId] = useState("");
  const [procedures, setProcedures] = useState<ProcedureInput[]>([
    { code: "", amount: "" },
  ]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMessage(null);
    setIsSubmitting(true);

    try {
      const response = await fetch("/api/claims", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          practice_id: "practice-1",
          patient_name: patientName,
          payer_id: payerId,
          procedures: procedures.map((p) => ({
            code: p.code,
            amount: parseFloat(p.amount),
          })),
          total_amount: procedures.reduce(
            (sum, p) => sum + parseFloat(p.amount || "0"),
            0
          ),
        }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail?.message ?? "Failed to submit claim");
      }

      setSuccessMessage("Claim submitted successfully");
      setPatientName("");
      setPayerId("");
      setProcedures([{ code: "", amount: "" }]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setIsSubmitting(false);
    }
  };

  const updateProcedure = (index: number, field: keyof ProcedureInput, value: string) => {
    setProcedures((prev) => {
      const updated = [...prev];
      updated[index] = { ...updated[index], [field]: value };
      return updated;
    });
  };

  return (
    <div className="page">
      <h1>Submit Claim</h1>
      {error && <div className="error-banner">{error}</div>}
      {successMessage && <div className="success-banner">{successMessage}</div>}
      <form onSubmit={handleSubmit}>
        <div className="field">
          <label>Patient Name</label>
          <input
            value={patientName}
            onChange={(e) => setPatientName(e.target.value)}
            required
          />
        </div>
        <div className="field">
          <label>Payer ID</label>
          <input
            value={payerId}
            onChange={(e) => setPayerId(e.target.value)}
            required
          />
        </div>
        <div className="procedures">
          <h2>Procedures</h2>
          {procedures.map((proc, i) => (
            <div key={i} className="procedure-row">
              <input
                placeholder="Code (e.g. D0120)"
                value={proc.code}
                onChange={(e) => updateProcedure(i, "code", e.target.value)}
              />
              <input
                placeholder="Amount"
                type="number"
                step="0.01"
                value={proc.amount}
                onChange={(e) => updateProcedure(i, "amount", e.target.value)}
              />
            </div>
          ))}
          <button
            type="button"
            onClick={() => setProcedures((prev) => [...prev, { code: "", amount: "" }])}
          >
            + Add Procedure
          </button>
        </div>
        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Submitting..." : "Submit Claim"}
        </button>
      </form>
    </div>
  );
}
