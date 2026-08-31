import { Link, Route, Routes } from "react-router-dom";
import { ClaimDetail } from "./pages/ClaimDetail";
import { ClaimList } from "./pages/ClaimList";
import { SubmitClaim } from "./pages/SubmitClaim";

export default function App() {
  return (
    <>
      <nav>
        <Link to="/">Claims</Link>
        <Link to="/submit">Submit Claim</Link>
      </nav>
      <Routes>
        <Route path="/" element={<ClaimList />} />
        <Route path="/submit" element={<SubmitClaim />} />
        <Route path="/claims/:id" element={<ClaimDetail />} />
      </Routes>
    </>
  );
}
