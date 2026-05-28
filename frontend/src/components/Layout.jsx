import { useEffect, useState } from 'react';
import {
  Activity,
  BarChart3,
  BookOpen,
  Gauge,
  Settings,
  ShieldCheck,
  TriangleAlert,
} from 'lucide-react';
import { NavLink, Outlet } from 'react-router-dom';

import { api } from '../api.js';

const nav = [
  { to: '/dashboard', label: 'Dashboard', icon: Gauge },
  { to: '/incidents', label: 'Incidents', icon: TriangleAlert },
  { to: '/services', label: 'Services', icon: Activity },
  { to: '/runbooks', label: 'Runbooks', icon: BookOpen },
  { to: '/analytics', label: 'Analytics', icon: BarChart3 },
  { to: '/settings', label: 'Settings', icon: Settings },
];

export default function Layout() {
  const [activeCount, setActiveCount] = useState(0);
  const [oncall, setOncall] = useState(null);

  useEffect(() => {
    let mounted = true;
    async function load() {
      try {
        const [incidents, currentOncall] = await Promise.all([api.getIncidents(), api.getCurrentOncall()]);
        if (!mounted) return;
        setActiveCount(incidents.active?.length || 0);
        setOncall(currentOncall.oncall);
      } catch {
        if (mounted) setActiveCount(0);
      }
    }
    load();
    const interval = window.setInterval(load, 10000);
    return () => {
      mounted = false;
      window.clearInterval(interval);
    };
  }, []);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <NavLink to="/" className="brand">
          <span className="brand-mark">
            <ShieldCheck size={14} strokeWidth={2} />
          </span>
          <span>SentinelAI</span>
        </NavLink>

        {activeCount > 0 && (
          <NavLink to="/incidents" className="incident-alert">
            <span className="status-dot critical" />
            {activeCount} active incident{activeCount === 1 ? '' : 's'}
          </NavLink>
        )}

        <nav className="sidebar-nav">
          {nav.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} to={item.to} key={item.to}>
                <Icon className="nav-icon" size={15} strokeWidth={1.8} />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </nav>

        <div className={`oncall-card ${oncall ? '' : 'unassigned'}`}>
          <span>On-call</span>
          {oncall ? (
            <>
              <strong>{oncall.name}</strong>
              <small>{oncall.slack_handle || 'No active schedule'}</small>
            </>
          ) : (
            <span className="warning-pill">Unassigned / No active schedule</span>
          )}
        </div>
      </aside>
      <div className="content-shell">
        <Outlet />
      </div>
    </div>
  );
}
