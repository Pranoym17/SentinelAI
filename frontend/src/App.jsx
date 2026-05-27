import { Navigate, Route, Routes } from 'react-router-dom';

import Dashboard from './pages/Dashboard.jsx';
import SetupPage from './pages/SetupPage.jsx';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/setup" replace />} />
      <Route path="/setup" element={<SetupPage />} />
      <Route path="/dashboard" element={<Dashboard />} />
      <Route path="*" element={<Navigate to="/setup" replace />} />
    </Routes>
  );
}
