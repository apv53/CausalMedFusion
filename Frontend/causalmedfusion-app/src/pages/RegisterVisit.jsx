import "./RegisterVisit.css";
import { useParams, useNavigate } from "react-router-dom";
import { useEffect } from "react";

export default function RegisterVisit() {
  const { patientId } = useParams();
  const navigate = useNavigate();

  useEffect(() => {
    // ---- MOCK VISIT CREATION (replace with backend later) ----
    const newVisitId = Math.floor(Math.random() * 100000);

    console.log("New visit registered:", {
      patientId,
      visitId: newVisitId,
      status: "ONGOING",
      admissionTime: new Date().toISOString(),
    });

    // Redirect to Visit Details page
    navigate(`/patients/${patientId}/visits/${newVisitId}`);
  }, [patientId, navigate]);

  return (
    <div className="container-fluid py-5 text-center">
      <div className="card p-4 shadow-sm mx-auto" style={{ maxWidth: "400px" }}>
        <h5 className="fw-bold mb-3">Registering Visit…</h5>
        <p className="text-muted mb-0">
          Please wait while the visit is being created.
        </p>
      </div>
    </div>
  );
}
