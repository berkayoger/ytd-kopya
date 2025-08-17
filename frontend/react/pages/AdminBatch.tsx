import React, { useEffect, useMemo, useState } from "react";

type Status = {
  job_id: string;
  total: number;
  pending: string[];
  done: string[];
  failed: string[];
  started_at: number;
};

type ResultItem = {
  symbol: string;
  status: "ok" | "error";
  decision?: "LONG" | "SHORT" | "HOLD";
  score?: number;
  draks?: any;
};

export default function AdminBatch() {
  const [asset, setAsset] = useState<"crypto" | "equity">("crypto");
  const [timeframe, setTimeframe] = useState("1h");
  const [limit, setLimit] = useState(500);
  const [symbols, setSymbols] = useState("BTC/USDT\nETH/USDT");
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<Status | null>(null);
  const [results, setResults] = useState<ResultItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filterDecision, setFilterDecision] = useState<string>("");
  const [filterStatus, setFilterStatus] = useState<string>("");
  const [filterSymbol, setFilterSymbol] = useState<string>("");

  const headers = useMemo(() => {
    const h: Record<string, string> = { "Content-Type": "application/json" };
    const token = localStorage.getItem("access_token");
    const apiKey = localStorage.getItem("api_key");
    if (token) h["Authorization"] = `Bearer ${token}`;
    if (apiKey) h["X-API-KEY"] = `${apiKey}`;
    return h;
  }, []);

  async function submit() {
    setLoading(true);
    setError(null);
    setResults([]);
    setStatus(null);
    setJobId(null);
    try {
      const body = {
        asset,
        timeframe,
        limit,
        symbols: symbols.split(/\r?\n/).map((s) => s.trim()).filter(Boolean),
      };
      const r = await fetch("/api/draks/batch/submit", {
        method: "POST",
        headers,
        credentials: "include",
        body: JSON.stringify(body),
      });
      const j = await r.json();
      if (!r.ok) throw new Error(j?.error || `HTTP ${r.status}`);
      setJobId(j.job_id);
    } catch (e: any) {
      setError(e.message || String(e));
    } finally {
      setLoading(false);
    }
  }

  async function pollStatus(id: string) {
    try {
      const r = await fetch(`/api/draks/batch/status/${id}`, {
        headers,
        credentials: "include",
      });
      const j = await r.json();
      if (r.ok) setStatus(j);
      else setError(j?.error || `HTTP ${r.status}`);
    } catch (e: any) {
      setError(e.message || String(e));
    }
  }

  async function loadResults(id: string) {
    const qs = new URLSearchParams();
    if (filterDecision) qs.set("decision", filterDecision);
    if (filterStatus) qs.set("status", filterStatus);
    if (filterSymbol) qs.set("symbol", filterSymbol);
    const url = `/api/draks/batch/results/${id}?` + qs.toString();
    try {
      const r = await fetch(url, { headers, credentials: "include" });
      const j = await r.json();
      if (r.ok) setResults(j.items || []);
    } catch {
      /* noop */
    }
  }

  useEffect(() => {
    if (!jobId) return;
    const t = setInterval(() => {
      pollStatus(jobId);
    }, 2000);
    return () => clearInterval(t);
  }, [jobId, headers]);

  useEffect(() => {
    if (!jobId) return;
    loadResults(jobId);
  }, [jobId, filterDecision, filterStatus, filterSymbol, headers]);

  const progress = status
    ? Math.round(
        ((status.done.length + status.failed.length) / Math.max(1, status.total)) *
          100,
      )
    : 0;

  return (
    <div className="p-3 space-y-3">
      <h1 className="text-xl font-semibold">DRAKS Batch (Toplu Analiz)</h1>
      <div className="border rounded p-3 space-y-2 bg-gray-50">
        <div className="grid md:grid-cols-4 gap-2 items-center">
          <div>
            <label className="text-xs">Varlık</label>
            <select
              className="w-full border rounded px-2 py-1 text-sm"
              value={asset}
              onChange={(e) => setAsset(e.target.value as any)}
            >
              <option value="crypto">crypto</option>
              <option value="equity">equity</option>
            </select>
          </div>
          <div>
            <label className="text-xs">Timeframe</label>
            <select
              className="w-full border rounded px-2 py-1 text-sm"
              value={timeframe}
              onChange={(e) => setTimeframe(e.target.value)}
            >
              {[
                "1m",
                "3m",
                "5m",
                "15m",
                "30m",
                "1h",
                "2h",
                "4h",
                "6h",
                "12h",
                "1d",
                "1w",
              ].map((tf) => (
                <option key={tf} value={tf}>
                  {tf}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs">Limit</label>
            <input
              className="w-full border rounded px-2 py-1 text-sm"
              type="number"
              value={limit}
              onChange={(e) => setLimit(parseInt(e.target.value || "0", 10))}
            />
          </div>
          <div className="flex items-end">
            <button
              disabled={loading}
              onClick={submit}
              className="border rounded px-3 py-1 text-sm bg-white w-full"
            >
              {loading ? "Gönderiliyor…" : "Gönder"}
            </button>
          </div>
        </div>
        <div>
          <label className="text-xs">Semboller (satır başına bir)</label>
          <textarea
            className="w-full border rounded px-2 py-1 text-sm"
            rows={6}
            value={symbols}
            onChange={(e) => setSymbols(e.target.value)}
          />
        </div>
        <div className="text-xs text-gray-600">
          Not: Rate-limit uygulanır, maksimum sembol sayısı ve mum sayısı backend
          tarafından sınırlıdır.
        </div>
      </div>
      {error && (
        <div className="border rounded p-2 text-sm text-red-600 bg-red-50">
          Hata: {error}
        </div>
      )}
      {jobId && (
        <div className="border rounded p-3 space-y-2">
          <div className="text-sm">
            <b>Job:</b> {jobId}
          </div>
          <div className="w-full bg-gray-100 rounded h-3">
            <div
              className="h-3 bg-green-500 rounded"
              style={{ width: progress + "%" }}
            />
          </div>
          {status && (
            <div className="text-sm">
              Toplam: {status.total} • Tamamlanan: {status.done.length} • Hata: {" "}
              {status.failed.length} • Bekleyen: {status.pending.length}
            </div>
          )}
        </div>
      )}
      {jobId && (
        <div className="border rounded p-3 space-y-2">
          <div className="flex gap-2 items-center">
            <select
              className="border rounded px-2 py-1 text-sm"
              value={filterDecision}
              onChange={(e) => setFilterDecision(e.target.value)}
            >
              <option value="">Decision: all</option>
              <option value="LONG">LONG</option>
              <option value="SHORT">SHORT</option>
              <option value="HOLD">HOLD</option>
            </select>
            <select
              className="border rounded px-2 py-1 text-sm"
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
            >
              <option value="">Status: all</option>
              <option value="ok">ok</option>
              <option value="error">error</option>
            </select>
            <input
              className="border rounded px-2 py-1 text-sm"
              placeholder="Symbol filtre"
              value={filterSymbol}
              onChange={(e) => setFilterSymbol(e.target.value)}
            />
            <button
              onClick={() => jobId && loadResults(jobId)}
              className="border rounded px-2 py-1 text-sm"
            >
              Yenile
            </button>
          </div>
          <div className="overflow-auto border rounded">
            <table className="min-w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left p-2">Symbol</th>
                  <th className="text-left p-2">Status</th>
                  <th className="text-left p-2">Decision</th>
                  <th className="text-left p-2">Score</th>
                </tr>
              </thead>
              <tbody>
                {results.map((r, i) => (
                  <tr key={r.symbol + i} className="odd:bg-white even:bg-gray-50">
                    <td className="p-2">{r.symbol}</td>
                    <td className="p-2">{r.status}</td>
                    <td className="p-2">{r.decision || "-"}</td>
                    <td className="p-2">
                      {typeof r.score === "number" ? r.score.toFixed(3) : "-"}
                    </td>
                  </tr>
                ))}
                {!results.length && (
                  <tr>
                    <td className="p-2" colSpan={4}>
                      Sonuç yok.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

