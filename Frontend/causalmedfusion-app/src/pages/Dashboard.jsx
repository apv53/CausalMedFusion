import Sidebar from "../components/Sidebar";
import Topbar from "../components/Topbar";
import StatsCards from "../components/StatsCards";
import PatientTable from "../components/PatientTable";

export default function Dashboard() {
  return (
    
    <div className="d-flex bg-light">

      <div className="flex-grow-1 p-4">
        <Topbar />
        <StatsCards />
        <PatientTable />
      </div>
    </div>
  );
}
