import { useState } from "react";
import Sidebar from "../components/Sidebar";
import { Outlet } from "react-router-dom";

export default function DashboardLayout() {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const toggleSidebar = () => setIsCollapsed(!isCollapsed);

  const sidebarWidth = isCollapsed ? "80px" : "260px";

  return (
    <div>
      {/* FIXED SIDEBAR */}
      <Sidebar isCollapsed={isCollapsed} toggleSidebar={toggleSidebar} sidebarWidth={sidebarWidth} />

      {/* SCROLLABLE MAIN CONTENT */}
      <div
        style={{
          marginLeft: sidebarWidth,
          width: `calc(100% - ${sidebarWidth})`,
          height: "100vh",
          overflowY: "auto",
          backgroundColor: "#f8f9fa",
          transition: "margin-left 0.3s, width 0.3s",
        }}
      >
        <Outlet />
      </div>
    </div>
  );
}
