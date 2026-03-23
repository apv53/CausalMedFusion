import { useEffect, useState } from "react";
import API from "../api/axios";

export default function StatsCards() {
  const [totalPatients, setTotalPatients] = useState(0);
  const [totalVisits, setTotalVisits] = useState(0);
  const [loading, setLoading] = useState(true);

  const fetchStats = async () => {
    try {
      const patientsRes = await API.get("patients/");
      const visitsRes = await API.get("visits/");

      // If pagination is enabled
      const patientCount =
        patientsRes.data.count ?? patientsRes.data.length;

      const visitCount =
        visitsRes.data.count ?? visitsRes.data.length;

      setTotalPatients(patientCount);
      setTotalVisits(visitCount);

    } catch (error) {
      console.error("Failed to fetch stats");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  return (
    <div className="row mb-4">

      {/* ================= TOTAL PATIENTS ================= */}
      <div className="col-md-6">
        <div className="p-4 bg-white rounded shadow-sm">
          <h6>Total Patients</h6>
          <h3>
            {loading ? "..." : totalPatients.toLocaleString()}
          </h3>
        </div>
      </div>

      {/* ================= TOTAL VISITS ================= */}
      <div className="col-md-6">
        <div className="p-4 bg-white rounded shadow-sm">
          <h6>Total Visits</h6>
          <h3>
            {loading ? "..." : totalVisits.toLocaleString()}
          </h3>
        </div>
      </div>

    </div>
  );
}