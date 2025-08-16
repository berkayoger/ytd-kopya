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
    </div>
  );
}

