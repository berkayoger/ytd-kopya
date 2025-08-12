import React, { useEffect, useMemo, useState } from 'react';
import { Card, CardContent } from './components/ui/card';

interface LimitInfo {
  used: number;
  max: number;
}

interface LimitData {
  plan: string | null;
  limits: Record<string, LimitInfo>;
}

interface LimitItem {
  key: string;
  label: string;
  used: number;
  max: number;
  pct: number;
}

export default function PlanLimitCard() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<LimitData | null>(null);

  useEffect(() => {
    let isMounted = true;
    async function run() {
      setLoading(true);
      setError(null);
      try {
        const headers: Record<string, string> = {
          'Content-Type': 'application/json',
          'X-CSRF-TOKEN': 'test',
        };
        const token = localStorage.getItem('access_token');
        const apiKey = localStorage.getItem('api_key');
        if (token) headers['Authorization'] = `Bearer ${token}`;
        if (apiKey) headers['X-API-KEY'] = apiKey;

        const resp = await fetch('/api/limits/status', {
          method: 'GET',
          headers,
          credentials: 'include',
        });
        if (!resp.ok) {
          const txt = await resp.text();
          throw new Error(`HTTP ${resp.status} ${txt || ''}`.trim());
        }
        const json = (await resp.json()) as LimitData;
        if (isMounted) setData(json);
      } catch (e: any) {
        if (isMounted) setError(e?.message || 'İstek başarısız oldu.');
      } finally {
        if (isMounted) setLoading(false);
      }
    }
    run();
    return () => {
      isMounted = false;
    };
  }, []);

  const items = useMemo<LimitItem[]>(() => {
    if (!data?.limits) return [];
    return Object.entries(data.limits).map(([key, v]) => {
      const used = Number(v?.used || 0);
      const max = Number(v?.max || 0);
      const pct = max > 0 ? Math.min(100, Math.round((used / max) * 100)) : 0;
      return { key, label: key, used, max, pct };
    });
  }, [data]);

  function badgeColor(pct: number) {
    if (pct >= 100) return 'bg-red-700';
    if (pct >= 90) return 'bg-red-500';
    if (pct >= 75) return 'bg-yellow-500';
    return 'bg-green-500';
  }

  function Warning({ pct }: { pct: number }) {
    if (pct >= 100) return <span className="text-red-700">Limit doldu (%100)</span>;
    if (pct >= 90) return <span className="text-red-500">%90 üzerine çıktınız</span>;
    if (pct >= 75) return <span className="text-yellow-500">%75’e yaklaşıyorsunuz</span>;
    return null;
  }

  return (
    <Card>
      <CardContent className="p-6">
        <div className="text-sm text-muted-foreground">Plan Limitleri</div>
        {loading && <div>Yükleniyor…</div>}
        {error && <div className="text-red-700">Hata: {error}</div>}
        {!loading && !error && data && (
          <>
            <div className="text-xl font-semibold">{data.plan || '-'}</div>
            <div className="space-y-3 mt-3">
              {items.map((it) => (
                <div key={it.key} className="flex flex-col gap-1">
                  <div className="flex items-center justify-between">
                    <div className="font-semibold text-sm">{labelize(it.label)}</div>
                    <div className="text-xs opacity-70">
                      {it.used} / {it.max} ({it.pct}%)
                    </div>
                  </div>
                  <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                    <div
                      data-testid="progress"
                      className={`h-full rounded-full transition-all ${badgeColor(it.pct)}`}
                      style={{ width: `${it.pct}%` }}
                    />
                  </div>
                  <div className="mt-1 text-xs">
                    <Warning pct={it.pct} />
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

function labelize(raw: string) {
  const s = String(raw || '').replace(/_/g, ' ').trim();
  return s.charAt(0).toUpperCase() + s.slice(1);
}
