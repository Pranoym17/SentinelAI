import { Navigate, Route, Routes } from 'react-router-dom';

import Layout from './components/Layout.jsx';
import AnalyticsPage from './pages/AnalyticsPage.jsx';
import Dashboard from './pages/Dashboard.jsx';
import IncidentDetailPage from './pages/IncidentDetailPage.jsx';
import IncidentsPage from './pages/IncidentsPage.jsx';
import LandingPage from './pages/LandingPage.jsx';
import OnboardingPage from './pages/OnboardingPage.jsx';
import RunbooksPage from './pages/RunbooksPage.jsx';
import ServicesPage from './pages/ServicesPage.jsx';
import SettingsPage from './pages/SettingsPage.jsx';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/setup" element={<Navigate to="/onboarding" replace />} />
      <Route path="/onboarding" element={<OnboardingPage />} />
      <Route element={<Layout />}>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/incidents" element={<IncidentsPage />} />
        <Route path="/incidents/:id" element={<IncidentDetailPage />} />
        <Route path="/services" element={<ServicesPage />} />
        <Route path="/runbooks" element={<RunbooksPage />} />
        <Route path="/analytics" element={<AnalyticsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
