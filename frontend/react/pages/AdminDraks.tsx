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

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, page]);

  return (
    <div className="space-y-3 p-2">
      <h1 className="text-xl font-semibold">DRAKS Monitor</h1>
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
                </tr>
              ))}
              {!items.length && (
                <tr>
                  <td className="p-2" colSpan={5}>
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
    </div>
  );
}

