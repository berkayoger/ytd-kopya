import React, { useEffect, useMemo, useState } from "react";

type Result = {
  exit_code: number;
  suite: string;
  cmd: string;
  summary: { raw: string; passed: number; failed: number; errors: number; skipped: number; xfailed: number; xpassed: number };
  stdout: string;
  stderr: string;
};

export default function AdminTests() {
  const [suite, setSuite] = useState<"unit" | "smoke" | "all">("unit");
  const [extra, setExtra] = useState("");
  const [running, setRunning] = useState(false);
  const [res, setRes] = useState<Result | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [allowed, setAllowed] = useState<boolean | null>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [filterSuite, setFilterSuite] = useState<string>("");
  const [filterExit, setFilterExit] = useState<string>("");
  const [filterUser, setFilterUser] = useState<string>("");
  const [filterDate, setFilterDate] = useState<{ start: string; end: string }>({ start: "", end: "" });

  const headers = useMemo(() => {
    const h: Record<string, string> = { "Content-Type": "application/json" };
    const token = localStorage.getItem("access_token");
    const apiKey = localStorage.getItem("api_key");
    if (token) h["Authorization"] = `Bearer ${token}`;
    if (apiKey) h["X-API-KEY"] = `${apiKey}`;
    return h;
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const r = await fetch("/api/admin/tests/status", { headers, credentials: "include" });
        const j = await r.json();
        if (r.ok) setAllowed(!!j.allowed);
      } catch {
        setAllowed(null);
      }
    })();
  }, [headers]);

  // Geçmiş test çalıştırmalarını getir
  async function fetchHistory() {
    try {
      const params = new URLSearchParams();
      if (filterSuite) params.append("suite", filterSuite);
      if (filterExit) params.append("exit_code", filterExit);
      if (filterUser) params.append("username", filterUser);
      if (filterDate.start) params.append("start", filterDate.start);
      if (filterDate.end) params.append("end", filterDate.end);
      const r = await fetch(`/api/admin/tests/history?${params.toString()}`, { headers, credentials: "include" });
      const j = await r.json();
      if (r.ok) setHistory(j);
    } catch {
      setHistory([]);
    }
  }

  useEffect(() => {
    fetchHistory();
  }, [headers, res, filterSuite, filterExit, filterUser, filterDate]);

  async function run() {
    setRunning(true);
    setError(null);
    setRes(null);
    try {
      const r = await fetch("/api/admin/tests/run", {
        method: "POST",
        headers,
        credentials: "include",
        body: JSON.stringify({ suite, extra }),
      });
      const j = await r.json();
      if (!r.ok && ![202].includes(r.status)) throw new Error(j?.error || `HTTP ${r.status}`);
      setRes(j);
    } catch (e: any) {
      setError(e.message || String(e));
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="p-3 space-y-3">
      <h1 className="text-xl font-semibold">Admin: Test Çalıştır</h1>
      <div className="border rounded p-3 space-y-2 bg-gray-50">
        <div className="flex gap-2 items-center">
          <label className="text-sm">Suite</label>
          <select className="border rounded px-2 py-1 text-sm" value={suite} onChange={(e) => setSuite(e.target.value as any)}>
            <option value="unit">Unit (default)</option>
            <option value="smoke">Smoke</option>
            <option value="all">All (not e2e)</option>
          </select>
          <input
            className="border rounded px-2 py-1 text-sm flex-1"
            placeholder="Ek pytest argümanları (opsiyonel)"
            value={extra}
            onChange={(e) => setExtra(e.target.value)}
          />
          <button disabled={running || allowed === false} onClick={run} className="border rounded px-3 py-1 text-sm bg-white">
            {running ? "Çalışıyor…" : "Testleri Çalıştır"}
          </button>
        </div>
        <div className="text-xs text-gray-600">
          Not: Bu özellik sadece <code>ALLOW_ADMIN_TEST_RUN=true</code> iken çalışır. Üretimde kapalı tutmanız önerilir.
        </div>
      </div>
      {allowed === false && (
        <div className="border rounded p-2 text-sm text-orange-700 bg-orange-50">
          Uyarı: Sunucu, test çalıştırmayı devre dışı bırakmış görünüyor (<code>ALLOW_ADMIN_TEST_RUN=false</code>). Bu sayfa sadece sonuç görüntüler; çalıştırma yapılamaz.
        </div>
      )}
      {error && <div className="border rounded p-2 text-sm text-red-600 bg-red-50">Hata: {error}</div>}
      {res && (
        <div className="space-y-3">
          <div className="border rounded p-3">
            <div className="text-sm">
              <b>Komut:</b> <code>{res.cmd}</code>
            </div>
            <div className="text-sm">
              <b>Çıkış Kodu:</b> {res.exit_code}
            </div>
            <div className="text-sm">
              <b>Özet:</b> {res.summary?.raw}</div>
            <div className="grid grid-cols-3 gap-3 mt-2 text-sm">
              <div className="border rounded p-2 bg-gray-50">passed: {res.summary?.passed}</div>
              <div className="border rounded p-2 bg-gray-50">failed: {res.summary?.failed}</div>
              <div className="border rounded p-2 bg-gray-50">errors: {res.summary?.errors}</div>
            </div>
          </div>
          <div className="grid md:grid-cols-2 gap-3">
            <div className="border rounded overflow-hidden">
              <div className="text-sm font-medium bg-gray-100 p-2">STDOUT</div>
              <pre className="p-2 text-xs overflow-auto max-h-[50vh] whitespace-pre-wrap">{res.stdout || "(empty)"}</pre>
            </div>
            <div className="border rounded overflow-hidden">
              <div className="text-sm font-medium bg-gray-100 p-2">STDERR</div>
              <pre className="p-2 text-xs overflow-auto max-h-[50vh] whitespace-pre-wrap">{res.stderr || "(empty)"}</pre>
            </div>
          </div>
        </div>
      )}

      {history.length > 0 && (
        <div className="mt-6">
          <div className="mb-3 space-x-2 flex flex-wrap items-center">
            <select value={filterSuite} onChange={(e) => setFilterSuite(e.target.value)} className="border rounded p-1">
              <option value="">Suite (hepsi)</option>
              <option value="unit">unit</option>
              <option value="smoke">smoke</option>
              <option value="all">all</option>
            </select>
            <select value={filterExit} onChange={(e) => setFilterExit(e.target.value)} className="border rounded p-1">
              <option value="">Exit Code (hepsi)</option>
              <option value="0">0 (başarılı)</option>
              <option value="1">1</option>
            </select>
            <input type="text" placeholder="Kullanıcı" value={filterUser} onChange={(e) => setFilterUser(e.target.value)} className="border rounded p-1" />
            <input type="date" value={filterDate.start} onChange={(e) => setFilterDate({ ...filterDate, start: e.target.value })} className="border rounded p-1" />
            <input type="date" value={filterDate.end} onChange={(e) => setFilterDate({ ...filterDate, end: e.target.value })} className="border rounded p-1" />
            <button onClick={fetchHistory} className="px-2 py-1 bg-blue-600 text-white rounded">Filtrele</button>
          </div>
          <h2 className="text-lg font-semibold mb-2">Geçmiş Çalıştırmalar</h2>
          <table className="w-full text-sm border">
            <thead className="bg-gray-100">
              <tr>
                <th className="p-2 border">Tarih</th>
                <th className="p-2 border">Kullanıcı</th>
                <th className="p-2 border">Suite</th>
                <th className="p-2 border">Exit</th>
                <th className="p-2 border">Özet</th>
              </tr>
            </thead>
            <tbody>
              {history.map((h) => (
                <tr key={h.id} className="odd:bg-white even:bg-gray-50">
                  <td className="p-2 border">{new Date(h.created_at).toLocaleString()}</td>
                  <td className="p-2 border">{h.username || "-"}</td>
                  <td className="p-2 border">{h.suite}</td>
                  <td className="p-2 border">{h.exit_code}</td>
                  <td className="p-2 border">{h.summary_raw}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

