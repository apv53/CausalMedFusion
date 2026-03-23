import { useParams, useNavigate } from "react-router-dom";
import { useEffect, useState, useMemo } from "react";
import API from "../api/axios";

export default function AddAssessment() {
  const { patientId, visitId } = useParams();
  const navigate = useNavigate();

  const [patient, setPatient] = useState(null);
  const [visit, setVisit] = useState(null);

  const [selectedWindow, setSelectedWindow] = useState("");

  const [radiographyImages, setRadiographyImages] = useState([]);
  const [viewPosition, setViewPosition] = useState("PA");
  const [cxrChartTime, setCxrChartTime] = useState("");

  const [notesFile, setNotesFile] = useState(null);
  const [reportType, setReportType] = useState("AR");
  const [reportChartTime, setReportChartTime] = useState("");

  const [vitalsFile, setVitalsFile] = useState(null);
  const [labsFile, setLabsFile] = useState(null);

  const [loading, setLoading] = useState(false);

  // Fetch patient + visit
  useEffect(() => {
    const fetchData = async () => {
      try {
        const patientRes = await API.get(`patients/${patientId}/`);
        setPatient(patientRes.data);

        const visitRes = await API.get(`visits/${visitId}/`);
        setVisit(visitRes.data);
      } catch (err) {
        console.error("Error fetching IDs");
      }
    };

    fetchData();
  }, [patientId, visitId]);

  // Build the 6 four-hour window options from admit time
  const windowOptions = useMemo(() => {
    if (!visit) return [];
    const admit = new Date(visit.admit_timestamp);
    const fmt = (d) =>
      d.toLocaleString("en-US", {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        hour12: true,
      });

    return Array.from({ length: 6 }, (_, i) => {
      const start = new Date(admit.getTime() + i * 4 * 3600000);
      const end = new Date(admit.getTime() + (i + 1) * 4 * 3600000);
      return {
        id: i + 1,
        label: `Window ${i + 1}: ${fmt(start)} – ${fmt(end)}`,
      };
    });
  }, [visit]);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!selectedWindow) {
      alert("Please select a time window");
      return;
    }

    // Optional validation
    if (radiographyImages.length > 0 && !cxrChartTime) {
      alert("Please enter CXR chart time");
      return;
    }

    if (notesFile && !reportChartTime) {
      alert("Please enter Report chart time");
      return;
    }

    try {
      setLoading(true);

      // Create Assessment
      const assessmentRes = await API.post("assessments/", {
        visit: visitId,
        window_id: parseInt(selectedWindow),
      });

      const assessmentId = assessmentRes.data.id;

      // Upload Files
      const uploadFile = async (file, category) => {
        if (!file) return;

        const formData = new FormData();
        formData.append("assessment", assessmentId);
        formData.append("file", file);
        formData.append("data_category", category);

        // Metadata — convert charttime from local to UTC ISO string
        // so it matches admit_timestamp (which is stored in UTC)
        if (category === "radiography_image") {
          formData.append(
            "metadata",
            JSON.stringify({
              view_label: viewPosition,
              charttime: cxrChartTime
                ? new Date(cxrChartTime).toISOString()
                : "",
            })
          );
        } else if (category === "clinical_notes") {
          formData.append(
            "metadata",
            JSON.stringify({
              type_label: reportType,
              charttime: reportChartTime
                ? new Date(reportChartTime).toISOString()
                : "",
            })
          );
        } else if (category === "labs") {
          formData.append(
            "metadata",
            JSON.stringify({
              type_label: reportType,
            })
          );
        }

        await API.post("assessmentfiles/", formData, {
          headers: {
            "Content-Type": "multipart/form-data",
          },
        });
      };

      // Radiography images
      for (let file of radiographyImages) {
        await uploadFile(file, "radiography_image");
      }

      await uploadFile(notesFile, "clinical_notes");
      await uploadFile(vitalsFile, "vitals");
      await uploadFile(labsFile, "labs");

      navigate(-1);
    } catch (err) {
      console.error("Upload failed:", err);
      alert("Failed to create assessment");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-4">

      {/* HEADER */}
      <div className="card p-3 mb-4 shadow-sm">
        <h5 className="fw-bold mb-1">Add Assessment</h5>
        <small className="text-muted">
          Patient ID: {patient?.patient_id || "—"} |
          Visit ID: {visit?.visit_id || "—"}
        </small>
      </div>

      <form onSubmit={handleSubmit}>

        {/* TIME WINDOW */}
        <div className="card p-4 mb-4 shadow-sm">
          <h6 className="fw-bold mb-3">Assessment Window</h6>

          <div className="mb-3">
            <label className="form-label">Select 4-Hour Window</label>
            <select
              className="form-select"
              value={selectedWindow}
              onChange={(e) => setSelectedWindow(e.target.value)}
              required
            >
              <option value="">— Select a window —</option>
              {windowOptions.map((w) => (
                <option key={w.id} value={w.id}>
                  {w.label}
                </option>
              ))}
            </select>
            <small className="text-muted">
              Windows are 4-hour intervals from ICU admission time
            </small>
          </div>
        </div>

        {/* RADIOGRAPHY */}
        <div className="card p-4 mb-4 shadow-sm">
          <h6 className="fw-bold mb-3">Radiography Images</h6>

          <div className="mb-3">
            <label className="form-label">Upload Images</label>
            <input
              type="file"
              className="form-control"
              multiple
              accept="image/*"
              onChange={(e) => setRadiographyImages(e.target.files)}
            />
            <small className="text-muted">
              Accepted formats: JPG, PNG, JPEG, BMP, TIFF
            </small>
          </div>

          <div className="mb-3">
            <label className="form-label">View Position</label>
            <select
              className="form-select"
              value={viewPosition}
              onChange={(e) => setViewPosition(e.target.value)}
            >
              <option value="LL">LL</option>
              <option value="AP LLD">AP LLD</option>
              <option value="PA">PA</option>
              <option value="LATERAL">LATERAL</option>
              <option value="AP">AP</option>
              <option value="AP RLD">AP RLD</option>
              <option value="NIL">NIL</option>
            </select>
          </div>

          <div>
            <label className="form-label">CXR Chart Time</label>
            <input
              type="datetime-local"
              step="1"
              className="form-control"
              value={cxrChartTime}
              onChange={(e) => setCxrChartTime(e.target.value)}
            />
          </div>
        </div>

        {/* CLINICAL NOTES */}
        <div className="card p-4 mb-4 shadow-sm">
          <h6 className="fw-bold mb-3">Clinical Notes</h6>

          <div className="mb-3">
            <label className="form-label">Upload Report</label>
            <input
              type="file"
              className="form-control"
              accept=".pdf"
              onChange={(e) => setNotesFile(e.target.files[0])}
            />
            <small className="text-muted">Accepted format: PDF</small>
          </div>

          <div className="mb-3">
            <label className="form-label">Report Type</label>
            <select
              className="form-select"
              value={reportType}
              onChange={(e) => setReportType(e.target.value)}
            >
              <option value="AR">AR (Admission Report)</option>
              <option value="RR">RR (Routing Report)</option>
            </select>
          </div>

          <div>
            <label className="form-label">Report Chart Time</label>
            <input
              type="datetime-local"
              step="1"
              className="form-control"
              value={reportChartTime}
              onChange={(e) => setReportChartTime(e.target.value)}
            />
          </div>
        </div>

        {/* VITALS */}
        <div className="card p-4 mb-4 shadow-sm">
          <h6 className="fw-bold mb-3">Vitals</h6>

          <input
            type="file"
            className="form-control"
            accept=".pdf"
            onChange={(e) => setVitalsFile(e.target.files[0])}
          />

          <small className="text-muted">Accepted format: PDF</small>
        </div>

        {/* LABS */}
        <div className="card p-4 mb-4 shadow-sm">
          <h6 className="fw-bold mb-3">Lab Measurements</h6>

          <input
            type="file"
            className="form-control"
            accept=".pdf"
            onChange={(e) => setLabsFile(e.target.files[0])}
          />

          <small className="text-muted">Accepted format: PDF</small>
        </div>

        {/* ACTIONS */}
        <div className="d-flex justify-content-end gap-2">
          <button
            type="button"
            className="btn btn-outline-secondary"
            onClick={() => navigate(-1)}
          >
            Cancel
          </button>

          <button
            type="submit"
            className="btn btn-primary"
            disabled={loading}
          >
            {loading ? "Uploading..." : "Create Assessment"}
          </button>
        </div>

      </form>
    </div>
  );
}
