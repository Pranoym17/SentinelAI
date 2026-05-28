import { useEffect, useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';

import { api } from '../api.js';

const nav = [
  { to: '/dashboard', label: 'Dashboard', glyph: '◎' },
  { to: '/incidents', label: 'Incidents', glyph: '△' },
  { to: '/services', label: 'Services', glyph: '◇' },
  { to: '/runbooks', label: 'Runbooks', glyph: '≡' },
  { to: '/analytics', label: 'Analytics', glyph: '▦' },
  { to: '/settings', label: 'Settings', glyph: '⚙' },
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
          <span className="brand-mark">S</span>
          SentinelAI
        </NavLink>

        {activeCount > 0 && (
          <NavLink to="/incidents" className="incident-alert">
            <span className="status-dot critical" />
            {activeCount} active incident{activeCount === 1 ? '' : 's'}
          </NavLink>
        )}

        <nav className="sidebar-nav">
          {nav.map((item) => (
            <NavLink className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} to={item.to} key={item.to}>
              <span className="nav-glyph">{item.glyph}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="oncall-card">
          <span>On-call</span>
          <strong>{oncall?.name || 'Unassigned'}</strong>
          <small>{oncall?.slack_handle || 'No active schedule'}</small>
        </div>
      </aside>
      <div className="content-shell">
        <Outlet />
      </div>
    </div>
  );
}
