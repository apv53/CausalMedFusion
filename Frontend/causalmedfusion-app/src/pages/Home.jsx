import React from "react";
import "./Home.css";
import RadiologyToon from "../assets/Radiology_Toon.jpg";
import ReportToon from "../assets/report_toon.avif";
import VisitToon from "../assets/visit_toon2.jpg";
import WhatIfToon from "../assets/what_if_toon.jpg";
import {Link} from "react-router-dom";

export default function Home() {
  return (
    <>
    
      {/* Hero Section */}
      <div className="container-fluid py-5 px-5">
        <div className="row align-items-center">
          <div className="col-md-6">
            <h1 className="display-4 fw-bold">
              Explainable multimodal medical analysis powered by causal reasoning.
            </h1>
            <p className="text-muted fs-4">
              CausalMedFusion enables doctors and researchers <br></br>to analyze multimodal
              patient data and generate causally explained medical reports.
            </p>

            <div className="mt-4">
              <Link to="/login" className="btn btn-dark me-3">Login</Link>
              <Link to="/signup" className="btn btn-outline-dark">Signup</Link>
            </div>
          </div>

          <div className="col-md-6 text-center">
            <img
              src={RadiologyToon}
              alt="medical"
              className="img-fluid"
              style={{ maxWidth: "800px", maxHeight: "400px" }}
            />
          </div>
        </div>
      </div>

      {/* Feature Section */}
      <div className="container py-5">
        <div className="row g-4">

          <div className="col-md-6">
            <div className="feature-card-left" style={{aheight: "55%"}}>
              <h4 className="display-7 fw-bold">Explainable report generation</h4>
              <p className="text-muted fs-5">
                Causally explained reports generated from multi-modal
                radiography data and patient vitals.<br></br>
              </p>
              <div><img
                src={ReportToon}
                className="img-fluid d-block mx-auto pt-3"
                style={{maxWidth: "300px", maxHeight: "300px"}}
              /></div>
              </div>
              <div className="feature-card-spacing" ></div>
              <div className="feature-card-left" style={{height: "50%"}}>
              <h4 className="display-7 fw-bold">“What-if” analysis by clinical factor adjustment</h4>
              <p className="text-muted fs-5">
                Analyze outcome changes through intervention on clinical variables.
              </p>
              <img
                src={WhatIfToon}
                className="img-fluid d-block mx-auto pt-3"
                style={{maxWidth: "500px", maxHeight: "200px"}}
              />
            </div>
          </div>

          <div className="col-md-6">
            <div className="feature-card-right">
              <h4 className="display-7 fw-bold">Longitudinal visit comparison and disease risk tracking</h4>
              <p className="text-muted fs-5">
                Compare previous reports and tracks the risk associated with diseases over multiple visits.
              </p>
              <img
                src={VisitToon}
                className="img-fluid d-block mx-auto pt-3"
                style={{maxWidth: "500px", maxHeight: "1000px"}}
              />
            </div>
          </div>
        </div>
      </div>

      <div className="col-md-12" style={{height: "15px"}}></div>

      
    </>
  );
}
