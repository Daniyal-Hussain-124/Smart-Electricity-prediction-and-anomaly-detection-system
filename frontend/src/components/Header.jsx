export default function Header({ apiUp }) {
  return (
    <header className="dashboard-header">
      <div className="header-content">
        <div className="logo-badge animated-glow">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="pulse-icon">
            <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"></path>
          </svg>
        </div>
        <div>
          <h1>Smart Grid Analytics</h1>
          <p className="subtitle">Real-time Household Power Forecasting & AI Anomaly Detection</p>
        </div>
      </div>
      <div className="header-right">
        <div className="live-indicator">
          <span className="wave-ring"></span>
          <span className="wave-ring delay"></span>
        </div>
        <span className={`status ${apiUp === true ? "up" : apiUp === false ? "down" : "checking"}`}>
          {apiUp === null ? "Connecting API…" : apiUp ? "API Live & Secure" : "API Offline"}
        </span>
      </div>
    </header>
  );
}