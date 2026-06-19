import React from "react";
import ReactDOM from "react-dom/client";
import "./style.css";

function App() {
  return (
    <main className="app-shell">
      <section className="hero-card">
        <p className="eyebrow">Sprint 1 Scaffold</p>
        <h1>AI Financial Literacy Advisor</h1>
        <p>
          Mobile-first PWA frontend connected to a FastAPI backend and PostgreSQL database through Docker Compose.
        </p>
        <div className="grid">
          <div><h2>Frontend</h2><p>React + Vite + TypeScript</p></div>
          <div><h2>Backend</h2><p>FastAPI API layer</p></div>
          <div><h2>Database</h2><p>PostgreSQL with initial schema</p></div>
        </div>
      </section>
    </main>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode><App /></React.StrictMode>
);
