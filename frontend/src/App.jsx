import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout.jsx";
import ProtectedRoute from "./components/ProtectedRoute.jsx";
import Incidents from "./pages/Incidents.jsx";
import Login from "./pages/Login.jsx";
import Overview from "./pages/Overview.jsx";
import Placeholder from "./pages/Placeholder.jsx";
import Upload from "./pages/Upload.jsx";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route index element={<Overview />} />
          <Route path="incidents" element={<Incidents />} />
          <Route path="upload" element={<Upload />} />
          <Route path="replay" element={<Placeholder title="Replay" note="Replay of processed video with overlays comes in Step 9." />} />
          <Route path="analytics" element={<Placeholder title="Analytics" note="Charts come in Step 9." />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}