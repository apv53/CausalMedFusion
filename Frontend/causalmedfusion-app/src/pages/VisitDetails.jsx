import { useParams, useNavigate } from "react-router-dom";
import { useEffect, useState, Fragment } from "react";
import { FaDownload } from "react-icons/fa";
import API from "../api/axios";

export default function VisitDetails() {
  const { patientId, visitId } = useParams();
  const navigate = useNavigate();

  const [visit, setVisit] = useState(null);
  const [assessments, setAssessments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expandedAssessments, setExpandedAssessments] = useState({});

  const fetchData = async () => {
    try {
      const visitRes = await API.get(`visits/${visitId}/`);
      setVisit(visitRes.data);

      const assessmentRes = await API.get(
        `assessments/?visit=${visitId}`
      );
      setAssessments(assessmentRes.data);

    } catch (err) {
      console.error("Error loading visit data", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [visitId]);

  // Poll for updates every 5 seconds if there are any processing / pending files
  useEffect(() => {
    const hasProcessing = assessments.some(a => 
      a.files && a.files.some(f => 
        f.processing_status === "processing" || 
        f.processing_status === "pending" ||
        f.embedding_status === "processing" ||
        f.embedding_status === "pending"
      )
    );

    if (hasProcessing) {
      const interval = setInterval(() => {
        fetchData();
      }, 5000);
      return () => clearInterval(interval);
    }
  }, [assessments]);

  const handleAddAssessment = () => {
    navigate(
      `/patients/${patientId}/visits/${visitId}/add-assessment`
    );
  };

  const handleProcessDischarge = async () => {
    const confirmed = window.confirm(
      "Are you sure you want to discharge this visit?"
    );
    if (!confirmed) return;

    try {
      await API.patch(`visits/${visitId}/`, {
        discharge_timestamp: new Date().toISOString(),
      });

      fetchData();
    } catch (err) {
      alert("Failed to discharge visit");
    }
  };

  const handleAnalyze = () => {
    navigate(`/assessment/${visitId}/results`);
  };

  const handleDownload = async (fileId) => {
    try {
      const response = await API.get(
        `download/${fileId}/`,
        { responseType: "blob" }
      );

      let fileName = "download";

      const contentDisposition =
        response.headers["content-disposition"];

      if (contentDisposition) {
        const fileNameMatch =
          contentDisposition.split("filename=")[1];

        if (fileNameMatch) {
          fileName = fileNameMatch
            .replace(/"/g, "")
            .trim();
        }
      }

      const url = window.URL.createObjectURL(response.data);

      const link = document.createElement("a");
      link.href = url;
      link.download = fileName;
      document.body.appendChild(link);
      link.click();
      link.remove();

    } catch (error) {
      console.error("Download failed", error);
      alert("Failed to download file");
    }
  };

  if (loading) return <div className="p-4">Loading...</div>;
  if (!visit) return <div className="p-4">Visit not found</div>;

  const isActive = visit.discharge_timestamp === null;

  const toggleExpand = (assessmentId) => {
    setExpandedAssessments((prev) => ({
      ...prev,
      [assessmentId]: !prev[assessmentId],
    }));
  };

  const handleDeleteAssessment = async (e, assessmentId) => {
    e.preventDefault();
    e.stopPropagation(); // don't open accordion
    const confirmed = window.confirm(
      "Are you sure you want to delete this entire assessment and all its files?"
    );
    if (!confirmed) return;
    try {
      await API.delete(`assessments/${assessmentId}/`);
      fetchData();
    } catch (err) {
      alert("Failed to delete assessment");
    }
  };

  const statusBadge = {
    pending: { bg: "bg-warning", text: "PENDING" },
    processing: { bg: "bg-primary", text: "PROCESSING" },
    completed: { bg: "bg-success", text: "COMPLETED" },
    failed: { bg: "bg-danger", text: "FAILED" },
  };

  return (
    <div className="p-4">

      {/* ================= VISIT HEADER ================= */}
      <div className="card p-3 mb-4 shadow-sm">
        <div className="d-flex justify-content-between align-items-center">
          <div>
            <h5 className="fw-bold mb-1">Visit Details</h5>
            <small className="text-muted">
              Patient ID: {patientId} | Visit ID: {visit.visit_id}
            </small>
          </div>

          <span
            className={`badge ${isActive ? "bg-success" : "bg-secondary"
              }`}
          >
            {isActive ? "ACTIVE" : "DISCHARGED"}
          </span>
        </div>

        <hr />

        <div className="row text-muted small">
          <div className="col-md-6">
            <strong>Admission:</strong>{" "}
            {new Date(visit.admit_timestamp).toLocaleString("en-US", {
              year: "numeric",
              month: "short",
              day: "numeric",
              hour: "2-digit",
              minute: "2-digit",
              hour12: true,
            })}
          </div>

          <div className="col-md-6">
            <strong>Discharge:</strong>{" "}
            {visit.discharge_timestamp
              ? new Date(visit.discharge_timestamp).toLocaleString("en-US", {
                  year: "numeric",
                  month: "short",
                  day: "numeric",
                  hour: "2-digit",
                  minute: "2-digit",
                  hour12: true,
                })
              : "—"}
          </div>
        </div>
      </div>

      {/* ================= ACTION BAR ================= */}
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h5 className="fw-bold mb-0">Assessments</h5>

        <div className="d-flex gap-2">
          <button
            className="btn btn-primary"
            onClick={handleAddAssessment}
            disabled={!isActive}
          >
            ➕ Add Assessment
          </button>

          <button
            className="btn btn-outline-danger"
            onClick={handleProcessDischarge}
            disabled={!isActive}
          >
            🏁 Process Discharge
          </button>

          <button
            className="btn btn-outline-primary"
            onClick={handleAnalyze}
          >
            🔍 Analyze Severity
          </button>

          <button
            className="btn btn-outline-secondary"
            onClick={() =>
              navigate(`/patients/${patientId}`)
            }
          >
            Back
          </button>
        </div>
      </div>

      {/* ================= ASSESSMENTS TABLE ================= */}
      <div className="bg-white rounded shadow-sm">
        <table className="table align-middle mb-0">
          <thead className="text-muted bg-light">
            <tr>
              <th>Assessment ID</th>
              <th>Window</th>
              <th>Files Summary</th>
              <th className="text-end">Actions</th>
            </tr>
          </thead>

          <tbody>
            {assessments.length === 0 ? (
              <tr>
                <td colSpan="4" className="text-center text-muted py-4">
                  No assessments added yet.
                </td>
              </tr>
            ) : (
              assessments.map((a) => {
                const isExpanded = expandedAssessments[a.id];
                const fileCount = a.files ? a.files.length : 0;

                return (
                  <Fragment key={a.id}>
                    {/* Main Assessment Row */}
                    <tr 
                      onClick={() => toggleExpand(a.id)}
                      style={{ cursor: "pointer" }}
                      className={isExpanded ? "table-active" : ""}
                    >
                      <td className="fw-semibold">
                        {isExpanded ? "📂" : "📁"} {a.assessment_id}
                      </td>
                      <td>
                        {"W" + a.window_id + ": "}
                        {a.time_window_start
                          ? new Date(a.time_window_start).toLocaleTimeString("en-US", {
                              hour: "2-digit",
                              minute: "2-digit",
                              hour12: true,
                            })
                          : "—"}
                        {" – "}
                        {a.time_window_end
                          ? new Date(a.time_window_end).toLocaleTimeString("en-US", {
                              hour: "2-digit",
                              minute: "2-digit",
                              hour12: true,
                            })
                          : "—"}
                      </td>
                      <td>
                        <span className="badge bg-secondary rounded-pill">
                          {fileCount} item{fileCount !== 1 && "s"}
                        </span>
                      </td>
                      <td className="text-end">
                        <button
                          className="btn btn-sm btn-outline-secondary py-0 px-2 me-2"
                          style={{ fontSize: "0.75rem" }}
                          onClick={(e) => {
                            e.stopPropagation();
                            toggleExpand(a.id);
                          }}
                        >
                          {isExpanded ? "Hide Files" : "View Files"}
                        </button>
                        <button
                          className="btn btn-sm btn-outline-danger py-0 px-2"
                          style={{ fontSize: "0.75rem" }}
                          onClick={(e) => handleDeleteAssessment(e, a.id)}
                          title="Delete Assessment"
                        >
                          🗑️ Delete
                        </button>
                      </td>
                    </tr>

                    {/* Expandable Files Sub-table */}
                    {isExpanded && (
                      <tr className="bg-light">
                        <td colSpan="4" className="p-0">
                          {fileCount === 0 ? (
                            <div className="p-3 text-center text-muted small">
                              No files attached to this assessment.
                            </div>
                          ) : (
                            <div className="p-3 bg-white border-bottom border-top shadow-inner">
                              <h6 className="mb-2 text-muted fw-bold" style={{ fontSize: "0.85rem" }}>
                                📑 Files for Assessment {a.assessment_id}
                              </h6>
                              <table className="table table-sm table-borderless align-middle mb-0">
                                <thead>
                                  <tr className="border-bottom small text-muted">
                                    <th>File Name</th>
                                    <th>Category</th>
                                    <th>Processing</th>
                                    <th>Embedding</th>
                                    <th className="text-end">Actions</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {a.files.map((file) => {
                                    const fileName = file.file.split("/").pop();
                                    const badge = statusBadge[file.processing_status] || {
                                      bg: "bg-secondary",
                                      text: "UNKNOWN",
                                    };
                                    
                                    const embStatus = file.embedding_status || "not_applicable";
                                    const embBadge = embStatus === "not_applicable" 
                                      ? { bg: "bg-secondary", text: "N/A" }
                                      : statusBadge[embStatus] || { bg: "bg-secondary", text: "UNKNOWN" };


                                    const handleReprocess = async (e, fileId) => {
                                      e.preventDefault();
                                      try {
                                        await API.post(`assessmentfiles/${fileId}/reprocess/`);
                                        alert("Reprocessing started");
                                        fetchData();
                                      } catch (err) {
                                        alert("Failed to start reprocessing");
                                      }
                                    };

                                    const handleDeleteFile = async (e, fileId) => {
                                      e.preventDefault();
                                      const confirmed = window.confirm(
                                        "Are you sure you want to delete this file?"
                                      );
                                      if (!confirmed) return;
                                      try {
                                        await API.delete(`assessmentfiles/${fileId}/`);
                                        fetchData();
                                      } catch (err) {
                                        alert("Failed to delete file");
                                      }
                                    };

                                    return (
                                      <tr key={file.id} className="border-bottom">
                                        <td>
                                          <button
                                            onClick={() => handleDownload(file.id)}
                                            className="btn btn-link p-0 d-inline-flex align-items-center text-decoration-none"
                                            style={{ fontSize: "0.8rem" }}
                                          >
                                            <FaDownload style={{ marginRight: "6px" }} />
                                            {fileName}
                                          </button>
                                        </td>
                                        <td>
                                          <span className="badge border text-dark" style={{ fontSize: "0.7rem", backgroundColor: "#f8f9fa" }}>
                                            {file.data_category?.replace(/_/g, " ").toUpperCase() || "—"}
                                          </span>
                                        </td>
                                        <td>
                                          <span className={`badge ${badge.bg}`} style={{ fontSize: "0.7rem" }}>
                                            {badge.text}
                                          </span>
                                        </td>
                                        <td>
                                          <span className={`badge ${embBadge.bg}`} style={{ fontSize: "0.7rem" }}>
                                            {embBadge.text}
                                          </span>
                                        </td>
                                          <td className="text-end">
                                          {file.processing_status !== "completed" && (
                                            <button
                                              className="btn btn-sm btn-outline-primary py-0 px-2 me-1"
                                              style={{ fontSize: "0.7rem" }}
                                              onClick={(e) => handleReprocess(e, file.id)}
                                              disabled={file.processing_status === "processing" || file.processing_status === "completed"}
                                            >
                                              🔄 Retry
                                            </button>
                                          )}
                                          <button
                                            className="btn btn-sm btn-outline-danger py-0 px-2"
                                            style={{ fontSize: "0.7rem" }}
                                            onClick={(e) => handleDeleteFile(e, file.id)}
                                          >
                                            ❌ Delete
                                          </button>
                                        </td>
                                      </tr>
                                    );
                                  })}
                                </tbody>
                              </table>
                            </div>
                          )}
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
