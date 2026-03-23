import {Link} from "react-router-dom";

export default function HomeHeader() {
    return(
        <>
              {/* Navbar */}
      <nav className="navbar navbar-expand-lg bg-white border-bottom px-4">
        <h1 className="ms-3">
          <Link to="/" className="navbar-brand fw-bold fs-3">CausalMedFusion
            <span className="text-danger">*</span></Link>
          </h1>

        <div className="ms-auto fs-6">
          <Link to="/" className="me-3 text-dark text-decoration-none">Home</Link>
          <Link to="/login" className="me-3 text-dark text-decoration-none">Login</Link>
          <Link to="/signup" className="text-dark text-decoration-none">Signup</Link>
        </div>
      </nav>
        </>
    )
}