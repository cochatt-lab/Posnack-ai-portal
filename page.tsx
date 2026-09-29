"use client";
import { useEffect, useState } from "react";

type Session = { email: string; role: string; grade_band: string | null };

export default function Home() {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [prompt, setPrompt] = useState("");
  const [answer, setAnswer] = useState<string>("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    fetch("/api/me", { credentials: "include" })
      .then((r) => (r.ok ? r.json() : null))
      .then(setSession)
      .finally(() => setLoading(false));
  }, []);

  async function ask() {
    setBusy(true);
    setAnswer("");
    const res = await fetch("/api/ask", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt }),
    });
    const data = await res.json();
    setAnswer(data.blocked ? `⚠️ Blocked at ${data.stage}: ${data.reason}` : data.answer);
    setBusy(false);
  }

  if (loading) return <p style={{ padding: "2rem" }}>Loading…</p>;

  if (!session) {
    return (
      <div style={{ padding: "3rem", textAlign: "center" }}>
        <h1>Posnack School AI Learning Portal</h1>
        <p>Sign in with your school Google account to continue.</p>
        <a
          href="/api/auth/login"
          style={{
            display: "inline-block", marginTop: "1rem", padding: "0.6rem 1.4rem",
            background: "#1a73e8", color: "#fff", borderRadius: "6px", textDecoration: "none",
          }}
        >
          Sign in with Google
        </a>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 640, margin: "0 auto", padding: "2rem" }}>
      <h1>Welcome, {session.email}</h1>
      <p>
        Role: <b>{session.role}</b>
        {session.grade_band ? ` (${session.grade_band})` : ""}
      </p>
      <textarea
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        rows={4}
        style={{ width: "100%", padding: "0.6rem", fontSize: "1rem", boxSizing: "border-box" }}
        placeholder="Ask for homework help, a study guide, brainstorming help..."
      />
      <button
        onClick={ask}
        disabled={busy || !prompt.trim()}
        style={{ marginTop: "0.75rem", padding: "0.5rem 1.2rem" }}
      >
        {busy ? "Asking…" : "Ask"}
      </button>
      {answer && (
        <div
          style={{
            marginTop: "1.5rem", background: "#fff", border: "1px solid #ddd",
            borderRadius: 8, padding: "1rem", whiteSpace: "pre-wrap",
          }}
        >
          {answer}
        </div>
      )}
    </div>
  );
}
