import Navbar from "../components/HomeNavbar.jsx";
import Footer from "../components/HomeFooter.jsx";
import { Outlet } from "react-router-dom";

export default function HomeLayout() {
  return (
    <div
      className="d-flex flex-column bg-light"
      style={{ minHeight: "100vh" }}
    >
      {/* Navbar */}
      <Navbar />

      {/* Page Content */}
      <main className="flex-grow-1">
        <Outlet />
      </main>

      {/* Footer */}
      <Footer />
    </div>
  );
}
