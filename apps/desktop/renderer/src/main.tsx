import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

type Health = { status: string; service: string; environment: string };
type GarminStatus = {
  connected: boolean;
  checked_at: string;
  device: { device_id: string; model_description: string; software_version: string; mount_point: string } | null;
};
type GarminDiagnostics = {
  connected: boolean;
  device_id: string | null;
  model_description: string | null;
  software_version: string | null;
  total_files: number;
  total_bytes: number;
  extensions: Record<string, number>;
  errors: string[];
};

const API = "http://127.0.0.1:8765";

async function getJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, options);
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json() as Promise<T>;
}

function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [garmin, setGarmin] = useState<GarminStatus | null>(null);
  const [diagnostics, setDiagnostics] = useState<GarminDiagnostics | null>(null);
  const [testing, setTesting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadGarmin = async () => {
    setError(null);
    try {
      const [status, report] = await Promise.all([
        getJson<GarminStatus>(`${API}/integrations/garmin/status`),
        getJson<GarminDiagnostics>(`${API}/integrations/garmin/diagnostics`),
      ]);
      setGarmin(status);
      setDiagnostics(report);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha no teste Garmin");
    }
  };

  const scanGarmin = async () => {
    setTesting(true);
    setError(null);
    try {
      const status = await getJson<GarminStatus>(`${API}/integrations/garmin/scan`, { method: "POST" });
      const report = await getJson<GarminDiagnostics>(`${API}/integrations/garmin/diagnostics`);
      setGarmin(status);
      setDiagnostics(report);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao testar Garmin");
    } finally {
      setTesting(false);
    }
  };

  useEffect(() => {
    getJson<Health>(`${API}/health`).then(setHealth).catch(() => setHealth(null));
    loadGarmin();
  }, []);

  const online = health?.status === "online";
  const garminConnected = garmin?.connected === true;

  return <main className="shell">
    <header>
      <div><small>JARVIS OS</small><h1>System Core</h1></div>
      <div className={online ? "status online" : "status"}><i/> {online ? "ONLINE" : "OFFLINE"}</div>
    </header>

    <section className="core"><div className="ring a"/><div className="ring b"/><div className="node">J</div><span>NEURAL CORE</span></section>

    <section className="grid">
      <article><small>CORE</small><b>{health?.service ?? "Python Core"}</b></article>
      <article><small>ENVIRONMENT</small><b>{health?.environment ?? "—"}</b></article>
      <article><small>API</small><b>{API}</b></article>
    </section>

    <section className="garmin-panel">
      <div className="garmin-heading">
        <div><small>INTEGRATION TEST</small><h2>GARMIN</h2></div>
        <div className={garminConnected ? "status online" : "status"}><i/> {garminConnected ? "CONNECTED" : "NOT DETECTED"}</div>
      </div>
      <div className="garmin-actions">
        <button onClick={scanGarmin} disabled={testing}>{testing ? "TESTING..." : "SCAN DEVICE"}</button>
        <button onClick={loadGarmin} disabled={testing}>REFRESH</button>
      </div>
      <div className="garmin-grid">
        <div><small>DEVICE</small><b>{garmin?.device?.model_description ?? "—"}</b></div>
        <div><small>FIRMWARE</small><b>{garmin?.device?.software_version ?? "—"}</b></div>
        <div><small>FILES</small><b>{diagnostics?.total_files ?? 0}</b></div>
        <div><small>FORMATS</small><b>{diagnostics ? Object.keys(diagnostics.extensions).join(", ") || "—" : "—"}</b></div>
      </div>
      {error && <p className="error">{error}</p>}
      {diagnostics?.errors.map((item) => <p className="error" key={item}>{item}</p>)}
    </section>
  </main>;
}

createRoot(document.getElementById("root")!).render(<React.StrictMode><App /></React.StrictMode>);
