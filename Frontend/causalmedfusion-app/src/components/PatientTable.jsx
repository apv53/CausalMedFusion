import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import API from "../api/axios";

export default function PatientTable() {
  const [patients, setPatients] = useState([]);
  const [page, setPage] = useState(1);
  const navigate = useNavigate();

  const pageSize = 5;

  // Fetch patients from backend
  useEffect(() => {
    const fetchPatients = async () => {
      try {
        const res = await API.get("patients/");
        setPatients(res.data);
      } catch (err) {
        console.error("Error fetching patients:", err);
      }
    };

    fetchPatients();
  }, []);

  // Pagination logic
  const startIndex = (page - 1) * pageSize;
  const paginatedData = patients.slice(
    startIndex,
    startIndex + pageSize
  );

  const totalPages = Math.ceil(patients.length / pageSize) || 1;

  const handleRowClick = (patientId) => {
    navigate(`/patients/${patientId}`);
  };

  return (
    <div className="bg-white p-4 rounded shadow-sm">

      {/* HEADER */}
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h5 className="fw-bold">Patients List</h5>
      </div>

      {/* TABLE */}
      <table className="table align-middle">
        <thead className="text-muted">
          <tr>
            <th>Patient ID</th>
            <th>Patient Name</th>
            <th>Age</th>
            <th>Gender</th>
          </tr>
        </thead>

        <tbody>
          {paginatedData.map((patient) => (
            <tr
              key={patient.id}
              onClick={() => handleRowClick(patient.id)}
              style={{ cursor: "pointer" }}
              className="table-row-hover"
            >
              <td>{patient.patient_id}</td>
              <td className="fw-semibold">{patient.name}</td>
              <td>{patient.age}</td>
              <td>{patient.gender}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* PAGINATION */}
      <div className="d-flex justify-content-end align-items-center gap-2">
        <button
          className="btn btn-sm btn-outline-secondary"
          disabled={page === 1}
          onClick={() => setPage(page - 1)}
        >
          Prev
        </button>

        <span className="fw-semibold">
          {page} / {totalPages}
        </span>

        <button
          className="btn btn-sm btn-outline-secondary"
          disabled={page === totalPages}
          onClick={() => setPage(page + 1)}
        >
          Next
        </button>
      </div>
    </div>
  );
}
