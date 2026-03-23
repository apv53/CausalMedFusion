import { NavLink, useNavigate } from "react-router-dom";
import {
  FaSignOutAlt,
  FaTachometerAlt,
  FaUserPlus,
  FaUserCheck,
  FaUserCircle
} from "react-icons/fa";
import { logout } from "../auth/authService";

export default function Sidebar() {
  const navigate = useNavigate();

  const user = JSON.parse(localStorage.getItem("user"));
  const isAdmin = user?.role === "Admin";

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  return (
    <div
      className="d-flex flex-column bg-white border-end"
      style={{
        width: "260px",
        position: "fixed",
        top: 0,
        left: 0,
        height: "100vh",
        zIndex: 1000,
      }}
    >
      {/* ================= BRAND ================= */}
      <div className="px-4 py-4 border-bottom">
        <h4 className="fw-bold mb-0">CausalMedFusion</h4>
        <small className="text-muted">
          Clinical Dashboard
        </small>
      </div>

      {/* ================= NAVIGATION ================= */}
      <div className="flex-grow-1 px-3 py-4">
        <ul className="list-unstyled">

          {/* Dashboard */}
          <li className="mb-2">
            <NavLink
              to="/dashboard"
              className={({ isActive }) =>
                `d-flex align-items-center gap-3 px-3 py-2 rounded text-decoration-none ${isActive
                  ? "bg-primary text-white"
                  : "text-muted sidebar-hover"
                }`
              }
            >
              <FaTachometerAlt />
              <span className="fw-semibold">
                Dashboard
              </span>
            </NavLink>
          </li>

          {/* Register Patient */}
          <li className="mb-2">
            <NavLink
              to="/register-patient"
              className={({ isActive }) =>
                `d-flex align-items-center gap-3 px-3 py-2 rounded text-decoration-none ${isActive
                  ? "bg-primary text-white"
                  : "text-muted sidebar-hover"
                }`
              }
            >
              <FaUserPlus />
              <span className="fw-semibold">
                Register Patient
              </span>
            </NavLink>
          </li>

          {/* ADMIN ONLY - Pending Requests */}
          {isAdmin && (
            <li className="mb-2">
              <NavLink
                to="/approve-signups"
                className={({ isActive }) =>
                  `d-flex align-items-center gap-3 px-3 py-2 rounded text-decoration-none ${isActive
                    ? "bg-primary text-white"
                    : "text-muted sidebar-hover"
                  }`
                }
              >
                <FaUserCheck />
                <span className="fw-semibold">
                  Pending Requests
                </span>
              </NavLink>
            </li>
          )}

        </ul>
      </div>

      {/* ================= PROFILE SECTION ================= */}
      <div className="px-3 py-3 border-top">

        <div className="d-flex align-items-center justify-content-center gap-3 mb-3">
          <FaUserCircle size={40} className="text-muted" />

          <div className="text-start">
            <div className="fw-semibold">
              {user?.username || ""}
            </div>

            <span
              className={`badge ${isAdmin ? "bg-danger" : "bg-secondary"
                }`}
              style={{ fontSize: "0.75rem" }}
            >
              {user?.role || "Role"}
            </span>
          </div>
        </div>

        {/* Thin grey separator */}
        <div
          style={{
            height: "1px",
            backgroundColor: "#e0e0e0",
            margin: "12px 0"
          }}
        />

        {/* Logout Button */}
        <button
          onClick={handleLogout}
          className="btn w-100 d-flex align-items-center justify-content-center gap-2 text-danger fw-semibold"
        >
          <FaSignOutAlt />
          Logout
        </button>

      </div>
    </div>
  );
}
