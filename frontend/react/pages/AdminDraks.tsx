import React, { useEffect, useMemo, useState } from "react";

/**
 * DRAKS karar ve sinyal geçmişini gösteren basit admin sayfası.
 * TailwindCSS ile minimal tablo yapısı.
 */

type Row = {
  id: number;
  symbol: string;
  decision?: string;
  timeframe?: string;
  score?: number;
  position_pct?: number;
  stop?: number;
  take_profit?: number;
  created_at: string;
};

export default function AdminDraks() {
  const [tab, setTab] = useState<"decisions" | "signals">("decisions");
  const [items, setItems] = useState<Row[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [symbol, setSymbol] = useState("");
  const [health, setHealth] = useState<{enabled:boolean; advanced:boolean; live_mode:boolean; timeframe?:string} | null>(null);
  const [detail, setDetail] = useState<any | null>(null);
  const [showDetail, setShowDetail] = useState(false);

  const headers = useMemo(() => {
    const h: Record<string, string> = {
      "Content-Type": "application/json",
      "X-CSRF-TOKEN": "admin",
    };
    const token = localStorage.getItem("access_token");
    const apiKey = localStorage.getItem("api_key");
    if (token) h["Authorization"] = `Bearer ${token}`;
    if (apiKey) h["X-API-KEY"] = apiKey;
    return h;
  }, []);

  async function load() {
    setLoading(true);
    try {
      const u = new URL(`/api/admin/draks/${tab}`, window.location.origin);
      u.searchParams.set("page", String(page));
      u.searchParams.set("limit", "25");
      if (symbol.trim()) u.searchParams.set("symbol", symbol.trim());
      const r = await fetch(u.toString(), {
        headers,
        credentials: "include",
      });
      const j = await r.json();
      if (!r.ok) throw new Error(j?.error || `HTTP ${r.status}`);
      setItems(j.items || []);
      setTotal(j.meta?.total || 0);
    } catch (e) {
      console.error(e);
      setItems([]);
    } finally {
      setLoading(false);
    }
  }

  async function loadHealth() {
    try {
      const r = await fetch(`/api/draks/health`, { headers, credentials: "include" });
      const j = await r.json();
      if (r.ok) {
        setHealth({ enabled: !!j.enabled, advanced: !!j.advanced, live_mode: !!j.live_mode, timeframe: j.timeframe });
      }
    } catch (e) { /* noop */ }
  }

  async function openDetail(row: Row) {
    try {
      const endpoint = tab === "decisions" ? `/api/admin/draks/decisions/${row.id}` : `/api/admin/draks/signals/${row.id}`;
      const r = await fetch(endpoint, { headers, credentials: "include" });
      const j = await r.json();
      if (!r.ok) throw new Error(j?.error || `HTTP ${r.status}`);
      setDetail(j);
      setShowDetail(true);
    } catch (e) {
      console.error(e);
    }
  }

  useEffect(() => {
    load(); loadHealth();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, page]);

  return (
    <div className="space-y-3 p-2">
      <h1 className="text-xl font-semibold">DRAKS Monitor</h1>
      {health && (
        <div className="text-xs rounded border p-2 flex gap-4 items-center bg-gray-50">
          <div><b>Enabled:</b> {String(health.enabled)}</div>
          <div><b>Advanced:</b> {String(health.advanced)}</div>
          <div><b>Live mode:</b> {String(health.live_mode)}</div>
          {health.timeframe && <div><b>TF:</b> {health.timeframe}</div>}
          <button className="ml-auto border rounded px-2 py-1" onClick={loadHealth}>Yenile</button>
        </div>
      )}
      <div className="flex gap-2 items-center">
        <button
          className={`border rounded px-2 py-1 text-sm ${tab === "decisions" ? "bg-gray-100" : ""}`}
          onClick={() => {
            setTab("decisions");
            setPage(1);
          }}
        >
          Decisions
        </button>
        <button
          className={`border rounded px-2 py-1 text-sm ${tab === "signals" ? "bg-gray-100" : ""}`}
          onClick={() => {
            setTab("signals");
            setPage(1);
          }}
        >
          Signals
        </button>
        <input
          className="border rounded px-2 py-1 text-sm ml-4"
          placeholder="Symbol filtre (örn: BTC/USDT)"
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
        />
        <button
          className="border rounded px-2 py-1 text-sm"
          onClick={() => {
            setPage(1);
            load();
          }}
        >
          Uygula
        </button>
      </div>
      {loading ? (
        <div>Yükleniyor…</div>
      ) : (
        <div className="overflow-auto border rounded">
          <table className="min-w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-left p-2">ID</th>
                <th className="text-left p-2">Symbol</th>
                {tab === "signals" ? (
                  <th className="text-left p-2">Timeframe</th>
                ) : (
                  <th className="text-left p-2">Decision</th>
                )}
                {tab === "signals" ? (
                  <th className="text-left p-2">Score</th>
                ) : (
                  <th className="text-left p-2">Pos%</th>
                )}
                <th className="text-left p-2">Created</th>
                <th className="text-left p-2">Detay</th>
              </tr>
            </thead>
            <tbody>
              {items.map((r) => (
                <tr key={`${tab}-${r.id}`} className="odd:bg-white even:bg-gray-50">
                  <td className="p-2">{r.id}</td>
                  <td className="p-2">{r.symbol}</td>
                  {tab === "signals" ? (
                    <td className="p-2">{r.timeframe}</td>
                  ) : (
                    <td className="p-2">{r.decision}</td>
                  )}
                  {tab === "signals" ? (
                    <td className="p-2">
                      {typeof r.score === "number" ? r.score.toFixed(3) : "-"}
                    </td>
                  ) : (
                    <td className="p-2">
                      {typeof r.position_pct === "number"
                        ? (r.position_pct * 100).toFixed(2) + "%"
                        : "-"}
                    </td>
                  )}
                  <td className="p-2">{r.created_at}</td>
                  <td className="p-2">
                    <button className="border rounded px-2 py-1 text-xs" onClick={() => openDetail(r)}>Detay</button>
                  </td>
                </tr>
              ))}
              {!items.length && (
                <tr>
                  <td className="p-2" colSpan={6}>
                    Kayıt bulunamadı.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
      <div className="flex gap-2 items-center">
        <button
          className="border rounded px-2 py-1 text-sm"
          disabled={page <= 1}
          onClick={() => setPage((p) => p - 1)}
        >
          Önceki
        </button>
        <div>Sayfa {page}</div>
        <button
          className="border rounded px-2 py-1 text-sm"
          disabled={items.length < 25}
          onClick={() => setPage((p) => p + 1)}
        >
          Sonraki
        </button>
        <div className="text-xs text-muted-foreground ml-2">
          Toplam: {total}
        </div>
      </div>

      {/* Detay Modal */}
      {showDetail && detail && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded shadow-lg w-[90vw] max-w-3xl max-h-[80vh] overflow-auto">
            <div className="p-3 border-b flex items-center">
              <div className="font-semibold text-sm">Detay</div>
              <button className="ml-auto border rounded px-2 py-1 text-xs" onClick={() => setShowDetail(false)}>Kapat</button>
            </div>
            <div className="p-3 space-y-2 text-sm">
              {"decision" in detail && (
                <div className="text-xs">
                  <b>Decision:</b> {detail.decision} &nbsp;|&nbsp; <b>Symbol:</b> {detail.symbol}
                </div>
              )}
              {"score" in detail && (
                <div className="text-xs">
                  <b>Score:</b> {typeof detail.score === "number" ? detail.score.toFixed(4) : String(detail.score)}
                  &nbsp;|&nbsp;<b>Timeframe:</b> {detail.timeframe}
                </div>
              )}
              {"position_pct" in detail && typeof detail.position_pct === "number" && (
                <div className="text-xs">
                  <b>Pos%:</b> {(detail.position_pct * 100).toFixed(2)}% &nbsp;|&nbsp; <b>Stop:</b> {detail.stop} &nbsp;|&nbsp; <b>TP:</b> {detail.take_profit}
                </div>
              )}
              {Array.isArray(detail.reasons) && detail.reasons.length > 0 && (
                <div>
                  <div className="font-medium">Reasons</div>
                  <ul className="list-disc ml-4">
                    {detail.reasons.map((r: string, i: number) => <li key={i}>{r}</li>)}
                  </ul>
                </div>
              )}
              <div>
                <div className="font-medium">Raw</div>
                <pre className="text-xs bg-gray-50 border rounded p-2 overflow-auto">{JSON.stringify(detail, null, 2)}</pre>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

