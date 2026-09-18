import { Navigate, Route, Routes } from "react-router-dom";

import { ToastProvider } from "./components/Toast";
import Dashboard from "./pages/Dashboard";
import Incidents from "./pages/Incidents";
import Login from "./pages/Login";
import Settings from "./pages/Settings";
import StatusPage from "./pages/StatusPage";
import { tokens } from "./lib/api";

function Protected({ children }: { children: React.ReactNode }) {
  if (!tokens.access) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <ToastProvider>
      <div className="min-h-screen bg-[#f8fafc] text-slate-800">
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/s/:slug" element={<StatusPage />} />
          <Route
            path="/incidents"
            element={
              <Protected>
                <Incidents />
              </Protected>
            }
          />
          <Route
            path="/"
            element={
              <Protected>
                <Dashboard />
              </Protected>
            }
          />
          <Route
            path="/settings"
            element={
              <Protected>
                <Settings />
              </Protected>
            }
          />
        </Routes>
      </div>
    </ToastProvider>
  );
}
