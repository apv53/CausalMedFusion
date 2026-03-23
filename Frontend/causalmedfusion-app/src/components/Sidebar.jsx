import { NavLink, useNavigate } from "react-router-dom";
import {
  FaSignOutAlt,
  FaTachometerAlt,
  FaUserPlus,
  FaUserCheck,
  FaUserCircle,
  FaBars
} from "react-icons/fa";
import { logout } from "../auth/authService";

export default function Sidebar({ isCollapsed, toggleSidebar, sidebarWidth }) {
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
        width: sidebarWidth,
        transition: "width 0.3s",
        position: "fixed",
        top: 0,
        left: 0,
        height: "100vh",
        zIndex: 1000,
      }}
    >
      {/* ================= BRAND ================= */}
      <div className={`py-4 border-bottom d-flex align-items-center ${isCollapsed ? 'justify-content-center px-0' : 'justify-content-start px-3'}`}>
        <div 
           onClick={toggleSidebar} 
           style={{ cursor: "pointer" }} 
           className={`text-secondary ${isCollapsed ? '' : 'me-3'}`}
           title="Toggle Sidebar"
        >
          <FaBars size={22} className="hover-lift" />
        </div>
        {!isCollapsed && (
          <div>
            <h5 className="fw-bold mb-0 text-dark">CausalMedFusion</h5>
            <small className="text-muted" style={{ fontSize: "0.75rem" }}>
              Clinical Dashboard
            </small>
          </div>
        )}
      </div>

      {/* ================= NAVIGATION ================= */}
      <div className="flex-grow-1 px-3 py-4">
        <ul className="list-unstyled">

          {/* Dashboard */}
          <li className="mb-2">
            <NavLink
              to="/dashboard"
              className={({ isActive }) =>
                `d-flex align-items-center gap-3 py-2 rounded text-decoration-none ${isActive
                  ? "bg-primary text-white"
                  : "text-muted sidebar-hover"
                } ${isCollapsed ? 'justify-content-center px-0 mx-2' : 'px-3'}`
              }
              title="Dashboard"
            >
              <FaTachometerAlt size={20} />
              {!isCollapsed && (
                <span className="fw-semibold">
                  Dashboard
                </span>
              )}
            </NavLink>
          </li>

          {/* Register Patient */}
          <li className="mb-2">
            <NavLink
              to="/register-patient"
              className={({ isActive }) =>
                `d-flex align-items-center gap-3 py-2 rounded text-decoration-none ${isActive
                  ? "bg-primary text-white"
                  : "text-muted sidebar-hover"
                } ${isCollapsed ? 'justify-content-center px-0 mx-2' : 'px-3'}`
              }
              title="Register Patient"
            >
              <FaUserPlus size={20} />
              {!isCollapsed && (
                <span className="fw-semibold">
                  Register Patient
                </span>
              )}
            </NavLink>
          </li>

          {/* ADMIN ONLY - Pending Requests */}
          {isAdmin && (
            <li className="mb-2">
              <NavLink
                to="/approve-signups"
                className={({ isActive }) =>
                  `d-flex align-items-center gap-3 py-2 rounded text-decoration-none ${isActive
                    ? "bg-primary text-white"
                    : "text-muted sidebar-hover"
                  } ${isCollapsed ? 'justify-content-center px-0 mx-2' : 'px-3'}`
                }
                title="Pending Requests"
              >
                <FaUserCheck size={20} />
                {!isCollapsed && (
                  <span className="fw-semibold">
                    Pending Requests
                  </span>
                )}
              </NavLink>
            </li>
          )}

        </ul>
      </div>

      {/* ================= PROFILE SECTION ================= */}
      <div className="px-3 py-3 border-top">

        <div className={`d-flex align-items-center ${isCollapsed ? 'justify-content-center' : 'justify-content-center gap-3'} mb-3`}>
          <FaUserCircle size={40} className="text-muted" title={user?.username || "Profile"} />

          {!isCollapsed && (
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
          )}
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
          className={`btn w-100 d-flex align-items-center ${isCollapsed ? 'justify-content-center p-2' : 'justify-content-center gap-2'} text-danger fw-semibold`}
          title="Logout"
        >
          <FaSignOutAlt size={20} />
          {!isCollapsed && "Logout"}
        </button>

      </div>
    </div>
  );
}
