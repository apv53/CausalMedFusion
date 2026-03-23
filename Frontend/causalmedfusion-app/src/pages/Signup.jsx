import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import SignupToon from "../assets/signup_toon.avif";
import "./Signup.css";
import { signup } from "../auth/authService";

export default function Signup() {

  const [form, setForm] = useState({
    username: "",
    email: "",
    password: "",
    confirmPassword: "",
    role: "Doctor"
  });

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const navigate = useNavigate();

  const handleSignup = async () => {
    setError("");
    setSuccess("");

    if (form.password !== form.confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    try {
      await signup(
        form.username,
        form.email,
        form.password,
        form.role
      );

      setSuccess(
        "Signup request submitted. Await admin approval."
      );

      setTimeout(() => {
        navigate("/login");
      }, 2000);

    } catch (err) {
      setError(
        err.response?.data?.detail ||
        "Signup failed"
      );
    }
  };

  return (
    <div className="container-fluid py-3 px-0">
      <div className="row align-items-center g-0">

        {/* FORM */}
        <div className="col-md-6 px-5">
          <h2 className="fw-bold mb-4">Signup</h2>

          {error && (
            <div className="alert alert-danger">
              {error}
            </div>
          )}

          {success && (
            <div className="alert alert-success">
              {success}
            </div>
          )}

          <div className="mb-4">
            <label className="form-label fw-semibold">
              Enter username:
            </label>
            <input
              type="text"
              className="form-control"
              onChange={e =>
                setForm({ ...form, username: e.target.value })
              }
            />
          </div>

          <div className="mb-4">
            <label className="form-label fw-semibold">
              Enter email:
            </label>
            <input
              type="email"
              className="form-control"
              onChange={e =>
                setForm({ ...form, email: e.target.value })
              }
            />
          </div>

          <div className="mb-4">
            <label className="form-label fw-semibold">
              Enter password:
            </label>
            <input
              type="password"
              className="form-control"
              onChange={e =>
                setForm({ ...form, password: e.target.value })
              }
            />
          </div>

          <div className="mb-4">
            <label className="form-label fw-semibold">
              Confirm password:
            </label>
            <input
              type="password"
              className="form-control"
              onChange={e =>
                setForm({ ...form, confirmPassword: e.target.value })
              }
            />
          </div>

          <div className="mb-4">
            <label className="form-label fw-semibold">
              Select role:
            </label>
            <select
              className="form-select"
              onChange={e =>
                setForm({ ...form, role: e.target.value })
              }
            >
              <option value="Doctor">Doctor</option>
              <option value="Admin">Admin</option>
            </select>
          </div>

          <button
            className="btn btn-dark px-4 py-2"
            onClick={handleSignup}
          >
            Signup
          </button>
        </div>

        {/* IMAGE */}
        <div className="col-md-6 px-5 text-center">
          <div className="signup-image-wrapper">
            <img
              src={SignupToon}
              alt="Signup"
              className="img-fluid"
              style={{ maxWidth: "400px", maxHeight: "400px" }}
            />
          </div>
        </div>

      </div>
    </div>
  );
}
