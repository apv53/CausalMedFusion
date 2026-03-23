import React, { useState } from "react";
import "./Login.css";
import LoginToon from "../assets/login_toon.avif";
import { Link, useNavigate } from "react-router-dom";
import { login } from "../auth/authService";

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      await login(username, password);
      navigate("/dashboard");
    } catch (err) {
      setError("Invalid username or password");
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* LOGIN SECTION */}
      <div className="container-fluid py-5 px-0">
        <div className="row align-items-center g-0">

          {/* FORM */}
          <div className="col-md-6 px-5">
            <h2 className="fw-bold mb-4">Login</h2>

            <form onSubmit={handleSubmit}>
              <div className="mb-4">
                <label htmlFor="username-input" className="form-label fw-semibold">
                  Enter username:
                </label>
                <input
                  id="username-input"
                  type="text"
                  className="form-control"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                />
              </div>

              <div className="mb-4">
                <label htmlFor="password-input" className="form-label fw-semibold">
                  Enter password:
                </label>
                <input
                  id="password-input"
                  type="password"
                  className="form-control"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </div>

              {error && (
                <div className="alert alert-danger py-2">
                  {error}
                </div>
              )}

              <button
                type="submit"
                className="btn btn-dark px-4 py-2"
                disabled={loading}
              >
                {loading ? "Logging in..." : "Login"}
              </button>
            </form>

            <div className="mt-3">
              <span>Don’t have an account? </span>
              <Link to="/signup">Sign up</Link>
            </div>
          </div>

          {/* IMAGE */}
          <div className="col-md-6 px-5 text-center">
            <div className="login-image-wrapper">
              <img
                src={LoginToon}
                alt="Login"
                className="img-fluid"
              />
            </div>
          </div>

        </div>
      </div>
    </>
  );
}
