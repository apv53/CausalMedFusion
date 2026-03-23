import { useParams, useNavigate } from "react-router-dom";
import { useState, useEffect } from "react";
import API from "../api/axios";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from "recharts";

export default function AssessmentResults() {
  const { patientId, visitId, assessmentId } = useParams();
  const navigate = useNavigate();

  const [pastResults, setPastResults] = useState([]);
  const [engineRun, setEngineRun] = useState(false);
  const [loading, setLoading] = useState(true);
  const [engineStage, setEngineStage] = useState('idle'); // 'idle' | 'aggregating' | 'inferencing' | 'done'

  const fetchResults = async () => {
    try {
      const response = await API.get(`analysisresults/?visit=${assessmentId}`);
      const data = response.data.results || response.data;
      setPastResults(data);
    } catch (err) {
      console.error("Failed to fetch analysis results", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchResults();
    // eslint-disable-next-line
  }, [assessmentId]);

  const runSeverityEngine = async () => {
    setEngineStage('aggregating');
    try {
       await API.post("analysisresults/trigger_aggregation/", { visit: assessmentId });
       
       setEngineStage('inferencing');
       await API.post("analysisresults/trigger_inference/", { visit: assessmentId });

       setEngineStage('done');
       await fetchResults();
       setEngineRun(true);
    } catch (err) {
       console.error("Failed to start severity engine", err);
       alert("Error starting the causal engine process.");
       setEngineStage('idle');
    }
  };

  const severityTrend = [...pastResults].reverse().map((r, i) => {
     const hour = (r.severity_index || i + 1) * 4;
     return {
        hour: hour,
        score: r.severity_score
     };
  });
  
  if (severityTrend.length > 0 && severityTrend[0].hour !== 0) {
      severityTrend.unshift({ hour: 0, score: 0.40 });
  }

  const currentResult = pastResults.length > 0 ? pastResults[0] : null;

  if (loading) return <div className="p-4">Loading analysis results...</div>;

  return (
    <div className="p-4">

      {/* ================= TOP CARD ================= */}
      <div className="card p-3 mb-4 shadow-sm">
        <h5 className="fw-bold mb-2">Severity Analysis</h5>

        <div className="row text-muted small">
          <div className="col-md-4">
            <strong>Patient ID: {patientId}</strong>
          </div>
          <div className="col-md-4">
            <strong>Visit ID: {visitId}</strong>
          </div>
          <div className="col-md-4">
            <strong>Assessment ID: {assessmentId}</strong>
          </div>
        </div>
      </div>

      {/* ================= PREVIOUS ANALYSES TABLE ================= */}
      <div className="card shadow-sm mb-4">
        <div className="card-body">
          <h6 className="fw-bold mb-3">
            Previous Severity Scores
          </h6>
          
          {pastResults.length === 0 ? (
              <p className="text-muted text-center py-3">No severity calculations have been processed for this assessment yet.</p>
          ) : (
            <table className="table align-middle">
              <thead className="text-muted">
                <tr>
                  <th>Analysis ID</th>
                  <th>Window Considered</th>
                  <th>Severity Score</th>
                  <th>Mortality Score</th>
                  <th>Time Created</th>
                </tr>
              </thead>
              <tbody>
                {pastResults.map((r, index) => (
                  <tr key={index}>
                    <td className="fw-semibold">{r.analysis_id}</td>
                    <td>Window {r.severity_index || "?"}</td>
                    <td className="text-danger fw-bold">
                      {r.severity_score.toFixed(2)}
                    </td>
                    <td className="text-warning fw-bold">
                      {(r.mortality_risk * 100).toFixed(1)}%
                    </td>
                    <td className="text-muted">{new Date(r.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* ================= SEVERITY TREND GRAPH ================= */}
      {(engineRun || currentResult) && severityTrend.length > 0 && (
        <div className="card p-4 shadow-sm mb-4">
          <h6 className="fw-bold mb-3">
            Severity Progression Based on Windows
          </h6>

          <div style={{ width: "100%", height: 300 }}>
            <ResponsiveContainer>
              <LineChart data={severityTrend}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="hour"
                  label={{
                    value: "Hours Since Admission",
                    position: "insideBottom",
                    offset: -5
                  }}
                />
                <YAxis
                  domain={[0, 1]}
                  label={{
                    value: "Severity Score",
                    angle: -90,
                    position: "insideLeft"
                  }}
                />
                <Tooltip />
                <Line
                  type="monotone"
                  dataKey="score"
                  stroke="#dc3545"
                  strokeWidth={3}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* ================= ACTION BAR ================= */}
      <div className="d-flex justify-content-end gap-2 mb-4">
        <button
          className="btn btn-primary d-flex align-items-center gap-2"
          onClick={runSeverityEngine}
          disabled={engineStage === 'aggregating' || engineStage === 'inferencing'}
        >
          {engineStage === 'aggregating' || engineStage === 'inferencing' ? (
             <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
          ) : "▶"} 
          Run Severity Engine
        </button>

        <button
          className="btn btn-outline-secondary"
          onClick={() => navigate(-1)}
        >
          Back
        </button>
      </div>

      {/* ================= PROGRESS BARS ================= */}
      {(engineStage === 'aggregating' || engineStage === 'inferencing') && (
        <div className="card shadow-sm mb-4 border-info">
          <div className="card-body">
            <h6 className="fw-bold text-info mb-3">
              {engineStage === 'aggregating' ? 'Stage 1: Building Window Tensors...' : 'Stage 2: Running ML Inference...'}
            </h6>
            <div className="progress" style={{ height: "20px" }}>
              <div 
                className={`progress-bar progress-bar-striped progress-bar-animated bg-info`} 
                role="progressbar" 
                style={{ width: engineStage === 'aggregating' ? "50%" : "100%" }}
                aria-valuenow={engineStage === 'aggregating' ? 50 : 100} 
                aria-valuemin="0" 
                aria-valuemax="100"
              >
                  {engineStage === 'aggregating' ? 'Aggregating Data (50%)' : 'Inferencing (100%)'}
              </div>
            </div>
            <p className="small text-muted mt-2 mb-0">
              {engineStage === 'aggregating' 
                ? 'Syncing the PyTorch embedding vault with Postgres metadata...' 
                : 'Scoring clinical trajectory matrices across all available modalities...'}
            </p>
          </div>
        </div>
      )}

      {/* ================= CURRENT RESULT ================= */}
      {engineStage !== 'aggregating' && engineStage !== 'inferencing' && (engineRun || currentResult) && currentResult && (
        <div className="card shadow-sm mb-4">
          <div className="card-body">
            <h6 className="fw-bold mb-4">
              Current Severity Score
            </h6>

            {/* Analysis ID */}
            <div className="row py-2 border-bottom">
              <div className="col-md-6">
                <strong>Analysis ID:</strong>
              </div>
              <div className="col-md-6 fw-semibold">
                {currentResult.analysis_id}
              </div>
            </div>

            {/* Window */}
            <div className="row py-2 border-bottom">
              <div className="col-md-6">
                <strong>Window Considered:</strong>
              </div>
              <div className="col-md-6">
                Window {currentResult.severity_index || "?"}
              </div>
            </div>

            {/* Severity */}
            <div className="row py-2 border-bottom">
              <div className="col-md-6">
                <strong>Severity Score:</strong>
              </div>
              <div className="col-md-6 fw-bold text-danger fs-5">
                {currentResult.severity_score.toFixed(2)}
              </div>
            </div>

            {/* Mortality */}
            <div className="row py-2">
              <div className="col-md-6">
                <strong>Mortality Risk:</strong>
              </div>
              <div className="col-md-6 fw-bold text-warning fs-5">
                {(currentResult.mortality_risk * 100).toFixed(1)}%
              </div>
            </div>

          </div>
        </div>
      )}

    </div>
  );
}
