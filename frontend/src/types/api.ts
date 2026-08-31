export interface Procedure {
  id: string;
  claim_id: string;
  code: string;
  description: string;
  amount: number;
}

export interface Claim {
  id: string;
  practice_id: string;
  patient_name: string;
  payer_id: string;
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
