import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

type Health = { status: string; service: string; environment: string };
const API = "http://127.0.0.1:8765";
function App() {
  const [health, setHealth] = useState<Health | null>(null);
  useEffect(() => { fetch(`${API}/health`).then(r => r.json()).then(setHealth).catch(() => setHealth(null)); }, []);
  const online = health?.status === "online";
  return <main className="shell">
    <header><div><small>JARVIS OS</small><h1>System Core</h1></div><div className={online ? "status online" : "status"}><i/> {online ? "ONLINE" : "OFFLINE"}</div></header>
    <section className="core"><div className="ring a"/><div className="ring b"/><div className="node">J</div><span>NEURAL CORE</span></section>
    <section className="grid"><article><small>CORE</small><b>{health?.service ?? "Python Core"}</b></article><article><small>ENVIRONMENT</small><b>{health?.environment ?? "—"}</b></article><article><small>API</small><b>{API}</b></article></section>
  </main>;
}
createRoot(document.getElementById("root")!).render(<React.StrictMode><App/></React.StrictMode>);
