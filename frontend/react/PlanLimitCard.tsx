import React, { useEffect, useMemo, useState } from 'react';
import { Card, CardContent } from './components/ui/card';

interface LimitInfo {
  used: number;
  max: number;
}

interface LimitData {
  plan: string | null;
  limits: Record<string, LimitInfo>;
  reset_at?: string | null; // ISO tarih formatında limit reset zamanı
  custom_features?: Record<string, unknown>;
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

  const customEntries = useMemo(() => {
    if (!data?.custom_features) return [];
    try {
      return Object.entries(data.custom_features);
    } catch { return []; }
  }, [data?.custom_features]);

  const resetInfo = useMemo(() => {
    if (!data?.reset_at) return null;
    try {
      const resetDate = new Date(data.reset_at);
      const now = new Date();
      const diffMs = resetDate.getTime() - now.getTime();
      const diffDays = Math.max(0, Math.ceil(diffMs / (1000 * 60 * 60 * 24)));
      return {
        date: resetDate,
        diffDays,
        formatted: resetDate.toLocaleDateString('tr-TR', {
          year: 'numeric',
          month: 'long',
          day: 'numeric',
        }),
      };
    } catch {
      return null;
    }
  }, [data?.reset_at]);

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

            {resetInfo && (
              <div className="text-xs text-muted-foreground mt-1">
                Yenilenme tarihi: <b>{resetInfo.formatted}</b>
                {resetInfo.diffDays > 0 && (
                  <> ({resetInfo.diffDays} gün kaldı)</>
                )}
              </div>
            )}

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

            {/* Özel özellikler (custom_features) */}
            <div className="mt-5">
              <div className="text-sm text-muted-foreground">Özel Özellikler</div>
              {customEntries.length === 0 ? (
                <div className="text-xs opacity-70 mt-1">Tanımlı özel özellik yok.</div>
              ) : (
                <ul className="mt-2 grid gap-2 md:grid-cols-2">
                  {customEntries.map(([k, v]) => (
                    <li key={String(k)} className="flex items-center justify-between text-xs">
                      <span className="font-medium">{labelize(String(k))}</span>
                      <span className="opacity-80">{formatValue(v)}</span>
                    </li>
                  ))}
                </ul>
              )}
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

function formatValue(v: unknown): string {
  if (v === null || v === undefined) return '-';
  if (typeof v === 'boolean') return v ? 'Açık' : 'Kapalı';
  if (typeof v === 'object') {
    try { return JSON.stringify(v); } catch { return '[obj]'; }
  }
  return String(v);
}
