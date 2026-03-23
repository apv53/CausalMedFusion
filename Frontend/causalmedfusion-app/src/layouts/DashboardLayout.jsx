import Sidebar from "../components/Sidebar";
import { Outlet } from "react-router-dom";

export default function DashboardLayout() {
  return (
    <div>
      {/* FIXED SIDEBAR */}
      <Sidebar />

      {/* SCROLLABLE MAIN CONTENT */}
      <div
        style={{
          marginLeft: "260px",
          width: "calc(100% - 260px)",
          height: "100vh",
          overflowY: "auto",
          backgroundColor: "#f8f9fa",
        }}
      >
        <Outlet />
      </div>
    </div>
  );
}
