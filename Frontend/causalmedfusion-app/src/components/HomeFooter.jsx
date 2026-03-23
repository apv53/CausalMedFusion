export default function HomeFooter(){
    return(
        <>
            {/* Footer */}
      <footer className="py-4 mt-5"><div className="row" style={{paddingTop: "10px"}}>
        <div className="col-md-12" style={{height: "100%", borderTop: "2px solid #f2f2f2"}}>
        <div className="spacing" style={{height: "10px"}}></div>
        <div className="container d-flex justify-content-between">
          <div style={{width: "70%"}}>
            <br />
            <h4 className="display-7">CausalMedFusion<span className="text-danger">*</span></h4>
            <p className="text-muted small">
              <i>By Anuroop P V </i><br /><div className="spacing" style={{height: "100px"}}></div>
              <span className="text-danger">*<i>For research and educational purposes only</i>
            </span></p>
          </div>

          <div style={{padding: "2px"}}>
            <p className="fw-bold">Features</p>
            <p className="text-muted mb-1">Multimodal</p>
            <p className="text-muted mb-1">Causal Explanations</p>
            <p className="text-muted mb-1">Report Generation</p>
          </div>

          <div>
            <p className="fw-bold">Data Input</p>
            <p className="text-muted mb-1">Chest Radiography Images</p>
            <p className="text-muted mb-1">Clinical Notes</p>
            <p className="text-muted mb-1">Patient Vitals</p>
          </div>

          <div>
            <p className="fw-bold">Logins</p>
            <p className="text-muted mb-1">Doctor</p>
            <p className="text-muted mb-1">Researcher</p>
          </div>

        </div></div></div>
      </footer>
        </>
    )
}