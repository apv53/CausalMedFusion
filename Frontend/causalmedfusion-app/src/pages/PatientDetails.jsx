import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import API from "../api/axios";

export default function PatientDetails() {
  const { patientId } = useParams();
  const navigate = useNavigate();

  const [patient, setPatient] = useState(null);
  const [visits, setVisits] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [admitTime, setAdmitTime] = useState(new Date().toLocaleString('sv-SE').slice(0, 16).replace(' ', 'T'));
  const [showTimePicker, setShowTimePicker] = useState(false);

  const fetchData = async () => {
    try {
      const patientRes = await API.get(`patients/${patientId}/`);
      setPatient(patientRes.data);

      const visitsRes = await API.get(`visits/?patient=${patientId}`);

      // Sort newest first
      const sortedVisits = visitsRes.data.sort(
        (a, b) =>
          new Date(b.admit_timestamp) -
          new Date(a.admit_timestamp)
      );

      setVisits(sortedVisits);

    } catch (err) {
      setError("Failed to load patient data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [patientId]);

  const handleCreateVisit = async () => {
    try {
      const res = await API.post("visits/", {
        patient: patient.id,
        admit_timestamp: new Date(admitTime).toISOString(),
      });

      navigate(`/patients/${patient.id}/visits/${res.data.id}`);
    } catch (err) {
      alert("Failed to create visit");
    }
  };

  const handleDischarge = async (visitId) => {
    try {
      await API.patch(`visits/${visitId}/`, {
        discharge_timestamp: new Date().toISOString(),
      });

      fetchData(); // refresh visits
    } catch (err) {
      alert("Failed to discharge patient");
    }
  };

  if (loading) {
    return <div className="container mt-5">Loading...</div>;
  }

  if (error) {
    return <div className="container mt-5 text-danger">{error}</div>;
  }

  if (!patient) {
    return <div className="container mt-5">Patient not found</div>;
  }

  return (
    <div className="container mt-5">
      <div className="card shadow-sm p-4">

        {/* HEADER */}
        <div className="d-flex justify-content-between align-items-center mb-3">
          <h4 className="fw-bold mb-0">
            Patient Details
          </h4>

          <div className="d-flex flex-column align-items-end gap-2">
            {!showTimePicker ? (
              <button
                className="btn btn-primary"
                onClick={() => setShowTimePicker(true)}
              >
                Register Visit
              </button>
            ) : (
              <div className="d-flex gap-2 align-items-center">
                <input
                  type="datetime-local"
                  className="form-control form-control-sm"
                  value={admitTime}
                  onChange={(e) => setAdmitTime(e.target.value)}
                />
                <button
                  className="btn btn-success btn-sm"
                  onClick={handleCreateVisit}
                >
                  Confirm
                </button>
                <button
                  className="btn btn-outline-danger btn-sm"
                  onClick={() => setShowTimePicker(false)}
                >
                  Cancel
                </button>
              </div>
            )}

            <button
              className="btn btn-outline-secondary"
              onClick={() => navigate("/dashboard")}
            >
              Back
            </button>
          </div>
        </div>

        <hr />

        {/* PATIENT INFO */}
        <div className="row mb-3">
          <div className="col-md-6">
            <strong>Patient ID:</strong> {patient.patient_id}
          </div>
          <div className="col-md-6">
            <strong>Name:</strong> {patient.name}
          </div>
        </div>

        <div className="row mb-3">
          <div className="col-md-6">
            <strong>Age:</strong> {patient.age}
          </div>
          <div className="col-md-6">
            <strong>Gender:</strong> {patient.gender}
          </div>
        </div>

        <div className="row mb-4">
          <div className="col-md-6">
            <strong>Phone:</strong> {patient.phone}
          </div>
          <div className="col-md-6">
            <strong>Email:</strong> {patient.email}
          </div>
        </div>

        <hr />

        {/* VISITS */}
        <div className="d-flex justify-content-between align-items-center mb-3">
          <h5 className="fw-bold mb-0">
            Visits ({visits.length})
          </h5>
        </div>

        {visits.length === 0 ? (
          <p className="text-muted">
            No visits recorded yet.
          </p>
        ) : (
          <table className="table table-hover align-middle">
            <thead>
              <tr>
                <th>Visit ID</th>
                <th>Admit Time</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>

            <tbody>
              {visits.map((visit) => {
                const isActive =
                  visit.discharge_timestamp === null;

                return (
                  <tr
                    key={visit.id}
                    style={{ cursor: "pointer" }}
                    onClick={() =>
                      navigate(
                        `/patients/${patient.id}/visits/${visit.id}`
                      )
                    }
                  >
                    <td>{visit.visit_id}</td>

                    <td>
                      {new Date(
                        visit.admit_timestamp
                      ).toLocaleString()}
                    </td>

                    <td>
                      <span
                        className={`badge ${isActive
                            ? "bg-success"
                            : "bg-secondary"
                          }`}
                      >
                        {isActive
                          ? "Active"
                          : "Discharged"}
                      </span>
                    </td>

                    <td
                      onClick={(e) =>
                        e.stopPropagation()
                      }
                    >
                      {isActive && (
                        <button
                          className="btn btn-sm btn-outline-danger"
                          onClick={() =>
                            handleDischarge(visit.id)
                          }
                        >
                          Discharge
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}

      </div>
    </div>
  );
}
