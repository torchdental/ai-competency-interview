export interface Procedure {
  id: number;
  claim_id: number;
  code: string;
  description: string;
  amount: number;
}

export interface Claim {
  id: number;
  practice_id: string;
  patient_name: string;
  payer_id: number;
  status: "pending" | "validated" | "rejected" | "accepted";
  total_amount: number;
  created_at: string;
  updated_at: string;
  procedures: Procedure[];
}

export interface ClaimsListResponse {
  claims: Claim[];
  total: number;
}
