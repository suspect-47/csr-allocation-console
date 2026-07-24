"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

// A clean install lands here (spec §5). The console stays empty until a profile
// exists and a run has completed.
export default function ProfilePage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [pillars, setPillars] = useState("");
  const [geographies, setGeographies] = useState("");
  const [budget, setBudget] = useState("");
  const [currency, setCurrency] = useState("USD");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [existing, setExisting] = useState(false);

  useEffect(() => {
    api.getProfile().then((p) => {
      if (!p) return;
      setExisting(true);
      setName(p.name);
      setPillars(p.pillars.join(", "));
      setGeographies(p.geographies.join(", "));
      setBudget(String(p.quarterly_budget));
      setCurrency(p.currency);
    });
  }, []);

  const split = (s: string) => s.split(",").map((x) => x.trim()).filter(Boolean);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    const p = split(pillars);
    const g = split(geographies);
    const b = Number(budget);
    if (!name.trim() || p.length === 0 || g.length === 0 || !(b > 0)) {
      setError("Name, at least one pillar and geography, and a budget above zero are required.");
      return;
    }
    setSaving(true);
    try {
      await api.createProfile({ name: name.trim(), pillars: p, geographies: g, quarterly_budget: b, currency });
      router.push("/");
    } catch (err) {
      setError(String(err));
      setSaving(false);
    }
  }

  return (
    <div className="measure" style={{ margin: "0 auto" }}>
      <h1 style={{ marginBottom: 8 }}>Giving profile</h1>
      <p className="muted" style={{ marginBottom: 24 }}>
        Set your pillars, geography, and quarterly budget. Discovery runs one query per pillar and
        geography pair.
      </p>
      {existing && (
        <div className="chip chip--unknown" style={{ marginBottom: 16 }}>
          A profile already exists — submitting creates another.
        </div>
      )}
      <form onSubmit={submit} noValidate>
        <div style={{ marginBottom: 16 }}>
          <label htmlFor="name">Organization name</label>
          <input id="name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Acme Foundation" />
        </div>
        <div style={{ marginBottom: 16 }}>
          <label htmlFor="pillars">Pillars (comma separated)</label>
          <input id="pillars" value={pillars} onChange={(e) => setPillars(e.target.value)} placeholder="Clean Water, Education, Health" />
        </div>
        <div style={{ marginBottom: 16 }}>
          <label htmlFor="geo">Geographies (comma separated)</label>
          <input id="geo" value={geographies} onChange={(e) => setGeographies(e.target.value)} placeholder="East Africa, South Asia" />
        </div>
        <div className="grid cols-2" style={{ marginBottom: 24 }}>
          <div>
            <label htmlFor="budget">Quarterly budget</label>
            <input id="budget" className="num" inputMode="decimal" value={budget} onChange={(e) => setBudget(e.target.value)} placeholder="250000" />
          </div>
          <div>
            <label htmlFor="currency">Currency</label>
            <input id="currency" value={currency} onChange={(e) => setCurrency(e.target.value.toUpperCase())} maxLength={3} />
          </div>
        </div>
        {error && (
          <div className="chip chip--blocked" role="alert" style={{ marginBottom: 16 }}>
            {error}
          </div>
        )}
        <button className="btn" type="submit" disabled={saving} aria-busy={saving}>
          Save profile
        </button>
      </form>
    </div>
  );
}
