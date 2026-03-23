import Home from "./pages/Home";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import HomeLayout from "./layouts/HomeLayout";
import DashboardLayout from "./layouts/DashboardLayout";
import Dashboard from "./pages/Dashboard";
import RegisterPatient from "./pages/RegisterPatient";
import RegisterVisit from "./pages/RegisterVisit";
import VisitDetails from "./pages/VisitDetails";
import AddAssessment from "./pages/AddAssessment";
import AssessmentResults from "./pages/AssessmentResults";
import PatientDetails from "./pages/PatientDetails";
import { Routes, Route } from "react-router-dom";
import ProtectedRoute from "./auth/ProtectedRoute";
import PendingRequests from "./pages/PendingRequests.jsx"


function App() {
  return (
    <Routes>

      {/* PUBLIC PAGES */}
      <Route element={<HomeLayout />}>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
      </Route>

      {/* PROTECTED DASHBOARD */}
      <Route
        element={
          <ProtectedRoute>
            <DashboardLayout />
          </ProtectedRoute>
        }
      >
        <Route path="/dashboard" element={<Dashboard />} />

        {/* USER APPROVALS */}
        <Route path="/approve-signups" element={<PendingRequests />} />

        {/* PATIENTS */}
        <Route path="/register-patient" element={<RegisterPatient />} />
        <Route path="/patients/:patientId" element={<PatientDetails />} />
        <Route
          path="/patients/:patientId/register-visit"
          element={<RegisterVisit />}
        />

        {/* VISITS */}
        <Route
          path="/patients/:patientId/visits/:visitId"
          element={<VisitDetails />}
        />

        {/* ASSESSMENTS */}
        <Route
          path="/patients/:patientId/visits/:visitId/add-assessment"
          element={<AddAssessment />}
        />

        <Route
          path="/patients/:patientId/visits/:visitId/results"
          element={<AssessmentResults />}
        />
      </Route>

    </Routes>
  );
}

export default App;
