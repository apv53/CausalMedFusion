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
  Legend,
  ResponsiveContainer
} from "recharts";

export default function AssessmentResults() {
  const { patientId, visitId } = useParams();
  const navigate = useNavigate();

  const [pastResults, setPastResults] = useState([]);
  const [engineRun, setEngineRun] = useState(false);
  const [loading, setLoading] = useState(true);
  const [engineStage, setEngineStage] = useState('idle'); // 'idle' | 'aggregating' | 'inferencing' | 'done'
  const [expandedRows, setExpandedRows] = useState({});

  const toggleRow = (index) => {
    setExpandedRows(prev => ({ ...prev, [index]: !prev[index] }));
  };

  const getBandBadge = (prob) => {
     if (prob === undefined || prob === null) return null;
     if (prob < 0.20) return <span className="badge bg-success">Low</span>;
     if (prob < 0.50) return <span className="badge bg-warning text-dark">Moderate</span>;
     if (prob < 0.75) return <span className="badge bg-orange text-dark" style={{backgroundColor: '#fd7e14'}}>High</span>;
     return <span className="badge bg-danger">Critical</span>;
  };

  const fetchResults = async () => {
    try {
      const response = await API.get(`analysisresults/?visit=${visitId}`);
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
  }, [visitId]);

  const runSeverityEngine = async () => {
    setEngineStage('aggregating');
    try {
       // Small delay so the user actually sees "aggregating" stage
       await new Promise(r => setTimeout(r, 500));
       
       setEngineStage('inferencing');
       await API.post("analysisresults/run_engine/", { visit: visitId });

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
        score: r.severity_score,
        mortality: r.mortality_risk,
        global: r.global_sev_prob
     };
  });
  
  // The plot will now naturally start from the first computed severity hour
  // without artificially pushing an hour: 0 value.

  const currentResult = pastResults.length > 0 ? pastResults[0] : null;

  if (loading) return <div className="p-4">Loading analysis results...</div>;

  return (
    <div className="p-4">

      {/* ================= TOP CARD ================= */}
      <div className="card p-3 mb-4 shadow-sm">
        <h5 className="fw-bold mb-2">Severity Analysis</h5>

        <div className="row text-muted small">
          <div className="col-md-6">
            <strong>Patient ID: {String(patientId).padStart(6, '0')}</strong>
          </div>
          <div className="col-md-6">
            <strong>Visit ID: {String(visitId).padStart(6, '0')}</strong>
          </div>
        </div>
      </div>

      {/* ================= PREVIOUS ANALYSES TABLE ================= */}
      <div className="card border-0 rounded-4 shadow-sm mb-4">
        <div className="card-body p-4">
          <h6 className="fw-bold mb-3 text-secondary">
            🕒 Previous Severity Scores
          </h6>
          
          {pastResults.length === 0 ? (
              <p className="text-muted text-center py-4">No severity calculations have been processed for this assessment yet.</p>
          ) : (
            <div className="table-responsive">
            <table className="table table-hover align-middle border-light">
              <thead className="text-muted">
                <tr>
                  <th>Analysis ID</th>
                  <th>Window Considered</th>
                  <th>Severity Score</th>
                  <th>Mortality Score</th>
                  <th>Time Created</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {pastResults.map((r, index) => (
                  <div style={{display: 'contents'}} key={index}>
                  <tr>
                    <td className="fw-semibold">{r.analysis_id}</td>
                    <td>Window {r.severity_index || "?"}</td>
                    <td className="text-danger fw-bold">
                      {r.severity_score?.toFixed(2) || "N/A"}
                    </td>
                    <td className="text-warning fw-bold">
                      {r.mortality_risk ? (r.mortality_risk * 100).toFixed(1) + "%" : "N/A"}
                    </td>
                    <td className="text-muted">{new Date(r.created_at).toLocaleString()}</td>
                    <td>
                      <button 
                        className="btn btn-sm btn-outline-info"
                        onClick={() => toggleRow(index)}
                      >
                        {expandedRows[index] ? "Hide" : "View"} Interventions & Report
                      </button>
                    </td>
                  </tr>
                  {expandedRows[index] && (
                    <tr className="bg-light">
                      <td colSpan="6" className="p-3">
                         <div className="row">
                           <div className="col-md-6 mb-3 mb-md-0">
                             <div className="card shadow-sm border-0 h-100">
                               <div className="card-body">
                                 <h6 className="fw-bold mb-3">Intervention Risks</h6>
                                 <table className="table table-sm table-borderless mb-0">
                                   <tbody>
                                     <tr>
                                       <td>Global Severity:</td>
                                       <td className="fw-bold">{(r.global_sev_prob * 100).toFixed(1)}%</td>
                                       <td>{getBandBadge(r.global_sev_prob)}</td>
                                     </tr>
                                     <tr>
                                       <td>Mechanical Ventilation:</td>
                                       <td className="fw-bold">{(r.vent_prob * 100).toFixed(1)}%</td>
                                       <td>{getBandBadge(r.vent_prob)}</td>
                                     </tr>
                                     <tr>
                                       <td>Cardiac Support:</td>
                                       <td className="fw-bold">{(r.cardiac_prob * 100).toFixed(1)}%</td>
                                       <td>{getBandBadge(r.cardiac_prob)}</td>
                                     </tr>
                                     <tr>
                                       <td>Mechanical Support:</td>
                                       <td className="fw-bold">{(r.mechanical_prob * 100).toFixed(1)}%</td>
                                       <td>{getBandBadge(r.mechanical_prob)}</td>
                                     </tr>
                                     <tr>
                                       <td>Dialysis:</td>
                                       <td className="fw-bold">{(r.dialysis_prob * 100).toFixed(1)}%</td>
                                       <td>{getBandBadge(r.dialysis_prob)}</td>
                                     </tr>
                                   </tbody>
                                 </table>
                               </div>
                             </div>
                           </div>
                           <div className="col-md-6">
                             <div className="card shadow-sm border-0 h-100">
                               <div className="card-body">
                                 <h6 className="fw-bold mb-3">Assessment Report</h6>
                                 <p className="small text-muted mb-0" style={{ whiteSpace: "pre-wrap" }}>
                                   {r.assessment_report || "No narrative available."}
                                 </p>
                               </div>
                             </div>
                           </div>
                         </div>
                      </td>
                    </tr>
                  )}
                  </div>
                ))}
              </tbody>
            </table>
            </div>
          )}
        </div>
      </div>

      {/* ================= SEVERITY TREND GRAPH ================= */}
      {(engineRun || currentResult) && severityTrend.length > 0 && (
        <div className="card border-0 rounded-4 shadow-sm p-4 mb-4">
          <h6 className="fw-bold mb-4 text-secondary">
            📈 Severity Progression Based on Windows
          </h6>

          <div style={{ width: "100%", height: 350 }}>
            <ResponsiveContainer>
              <LineChart data={severityTrend} margin={{ top: 20, right: 30, left: 0, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="hour"
                  type="number"
                  domain={[0, 24]}
                  ticks={[0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24]}
                  label={{
                    value: "Hours Since Admission (Last Measurement Charttime)",
                    position: "bottom",
                    offset: 0
                  }}
                />
                <YAxis
                  domain={[0, 1]}
                  label={{
                    value: "Probability / Score",
                    angle: -90,
                    position: "insideLeft"
                  }}
                />
                <Tooltip />
                <Legend verticalAlign="top" height={36}/>
                <Line
                  type="monotone"
                  dataKey="score"
                  name="Severity Score"
                  stroke="#dc3545"
                  strokeWidth={3}
                  activeDot={{ r: 8 }}
                />
                <Line
                  type="monotone"
                  dataKey="mortality"
                  name="Mortality Risk"
                  stroke="#fd7e14"
                  strokeWidth={2}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* ================= ACTION BAR ================= */}
      <div className="d-flex justify-content-end gap-3 mb-4">
        <button
          className="btn btn-primary rounded-pill px-4 shadow-sm d-flex align-items-center gap-2"
          onClick={runSeverityEngine}
          disabled={engineStage === 'aggregating' || engineStage === 'inferencing'}
        >
          {engineStage === 'aggregating' || engineStage === 'inferencing' ? (
             <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
          ) : "▶"} 
          Run Severity Engine
        </button>

        <button
          className="btn btn-outline-secondary rounded-pill px-4"
          onClick={() => navigate(-1)}
        >
          Back
        </button>
      </div>

      {/* ================= PROGRESS BARS ================= */}
      {(engineStage === 'aggregating' || engineStage === 'inferencing') && (
        <div className="card rounded-4 shadow-sm mb-4 border-info">
          <div className="card-body p-4">
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

      {/* ================= CURRENT RESULT CARDS ================= */}
      {engineStage !== 'aggregating' && engineStage !== 'inferencing' && (engineRun || currentResult) && currentResult && (
        <>
          <div className="row mb-4">
            {/* Main Info */}
            <div className="col-lg-6 mb-3">
              <div className="card border-0 rounded-4 shadow-sm h-100 hover-lift">
                <div className="card-body p-4">
                  <h6 className="fw-bold mb-4 text-secondary">
                    📊 Current Severity Score
                  </h6>
                  <div className="row py-2 border-bottom">
                    <div className="col-6"><strong>Analysis ID:</strong></div>
                    <div className="col-6 fw-semibold">{currentResult.analysis_id}</div>
                  </div>
                  <div className="row py-2 border-bottom">
                    <div className="col-6"><strong>Window Considered:</strong></div>
                    <div className="col-6">Window {currentResult.severity_index || "?"}</div>
                  </div>
                  <div className="row py-2 border-bottom">
                    <div className="col-6"><strong>Severity Score:</strong></div>
                    <div className="col-6 fw-bold text-danger fs-5">
                      {currentResult.severity_score?.toFixed(2) || "N/A"}
                    </div>
                  </div>
                  <div className="row py-2">
                    <div className="col-6"><strong>Mortality Risk:</strong></div>
                    <div className="col-6 fw-bold text-warning fs-5">
                      {currentResult.mortality_risk ? (currentResult.mortality_risk * 100).toFixed(1) + "%" : "N/A"}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Intervention Risks */}
            <div className="col-lg-6 mb-3">
              <div className="card border-0 rounded-4 shadow-sm h-100 hover-lift">
                <div className="card-body p-4">
                  <h6 className="fw-bold mb-4 text-secondary">
                    💉 Intervention Risks
                  </h6>
                  <table className="table table-borderless table-sm mb-0">
                    <tbody>
                      <tr>
                        <td className="text-secondary align-middle">Global Severity:</td>
                        <td className="fw-bold align-middle">{(currentResult.global_sev_prob * 100).toFixed(1)}%</td>
                        <td className="text-end align-middle">{getBandBadge(currentResult.global_sev_prob)}</td>
                      </tr>
                      <tr>
                        <td className="text-secondary align-middle">Ventilation:</td>
                        <td className="fw-bold align-middle">{(currentResult.vent_prob * 100).toFixed(1)}%</td>
                        <td className="text-end align-middle">{getBandBadge(currentResult.vent_prob)}</td>
                      </tr>
                      <tr>
                        <td className="text-secondary align-middle">Cardiac:</td>
                        <td className="fw-bold align-middle">{(currentResult.cardiac_prob * 100).toFixed(1)}%</td>
                        <td className="text-end align-middle">{getBandBadge(currentResult.cardiac_prob)}</td>
                      </tr>
                      <tr>
                        <td className="text-secondary align-middle">Mechanical:</td>
                        <td className="fw-bold align-middle">{(currentResult.mechanical_prob * 100).toFixed(1)}%</td>
                        <td className="text-end align-middle">{getBandBadge(currentResult.mechanical_prob)}</td>
                      </tr>
                      <tr>
                        <td className="text-secondary align-middle">Dialysis:</td>
                        <td className="fw-bold align-middle">{(currentResult.dialysis_prob * 100).toFixed(1)}%</td>
                        <td className="text-end align-middle">{getBandBadge(currentResult.dialysis_prob)}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>

          <div className="row mb-4">
            {/* Narrative Report */}
            <div className="col-12 mb-3">
               <div className="card border-0 rounded-4 shadow-sm h-100 hover-lift">
                 <div className="card-body p-4 d-flex flex-column">
                    <h6 className="fw-bold mb-4 text-secondary">📝 Assessment Report</h6>
                    <p className="small text-muted mb-0" style={{ whiteSpace: "pre-wrap", overflowY: "auto", maxHeight: "250px" }}>
                      {currentResult.assessment_report || "No narrative inference data available for this analysis run."}
                    </p>
                 </div>
               </div>
            </div>
          </div>
        </>
      )}

    </div>
  );
}
