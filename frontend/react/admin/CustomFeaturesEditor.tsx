import React, { useEffect, useMemo, useState } from "react";

// Anahtar-değer çifti tipi
type KV = [string, string];

/**
 * Admin panelinde kullanıcı özel özelliklerini düzenlemek için basit editör.
 *
 * Props:
 * - userId: Özellikleri düzenlenecek kullanıcının ID'si
 * - tokenProvider: Opsiyonel token sağlayıcı (JWT ya da API key)
 */
export default function CustomFeaturesEditor({
  userId,
  tokenProvider,
}: {
  userId: number | string;
  tokenProvider?: () => string | null; // JWT veya API key için opsiyonel sağlayıcı
}) {
  // Satırlar [key, value] olarak tutulur
  const [items, setItems] = useState<KV[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // API çağrıları için gerekli header'ları hazırla
  const headers = useMemo(() => {
    const h: Record<string, string> = {
      "Content-Type": "application/json",
      "X-CSRF-TOKEN": "admin",
    };
    const token = tokenProvider?.() ?? localStorage.getItem("access_token");
    const apiKey = localStorage.getItem("api_key");
    if (token) h["Authorization"] = `Bearer ${token}`;
    if (apiKey) h["X-API-KEY"] = apiKey;
    return h;
  }, [tokenProvider]);

  // İlk yüklemede kullanıcının özelliklerini getir
  useEffect(() => {
    let mounted = true;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`/api/admin/users/${userId}/custom_features`, {
          method: "GET",
          headers,
          credentials: "include",
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        const cf = data?.custom_features ?? {};
        if (!mounted) return;
        // Gelen nesneyi anahtar-değer listesine çevir
        const kv = Object.entries(cf).map(
          ([k, v]) => [k, normalizeValue(v)] as KV
        );
        setItems(kv.length ? kv : [["", ""]]);
      } catch (e: any) {
        if (mounted) setError(e?.message || "Yüklenemedi");
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, [userId, headers]);

  // Değerleri string'e dönüştür
  function normalizeValue(v: unknown): string {
    if (v === null || v === undefined) return "";
    if (typeof v === "object") {
      try {
        return JSON.stringify(v);
      } catch {
        return String(v);
      }
    }
    return String(v);
  }

  // Yeni satır ekle
  function onAdd() {
    setItems((prev) => [...prev, ["", ""]]);
  }

  // Satır sil
  function onRemove(idx: number) {
    setItems((prev) => prev.filter((_, i) => i !== idx));
  }

  // Hücre değişikliklerini işle
  function onChange(idx: number, which: "k" | "v", value: string) {
    setItems((prev) =>
      prev.map((row, i) =>
        i === idx ? (which === "k" ? [value, row[1]] : [row[0], value]) : row
      )
    );
  }

  // String'i uygun tipte değere çevir
  function parseTyped(val: string): unknown {
    const v = val.trim();
    if (v === "") return "";
    if (v === "true") return true;
    if (v === "false") return false;
    if (!Number.isNaN(Number(v)) && /^\d+(\.\d+)?$/.test(v)) {
      return Number(v);
    }
    // JSON objesi dene
    try {
      const obj = JSON.parse(v);
      return obj;
    } catch {
      return v;
    }
  }

  // Kaydet butonu tıklandığında çalışır
  async function onSave() {
    setError(null);
    try {
      const body: Record<string, unknown> = {};
      for (const [k, v] of items) {
        if (!k.trim()) continue;
        body[k.trim()] = parseTyped(v);
      }
      const res = await fetch(`/api/admin/users/${userId}/custom_features`, {
        method: "PUT",
        headers,
        credentials: "include",
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const t = await res.text();
        throw new Error(`Kaydedilemedi: ${res.status} ${t || ""}`.trim());
      }
    } catch (e: any) {
      setError(e?.message || "Kaydedilemedi");
      return;
    }
    // Basit kullanıcı bildirimi
    alert("Kaydedildi");
  }

  return (
    <div className="border rounded-lg p-4">
      <div className="text-base font-semibold mb-2">Özel Özellikler</div>
      {loading && <div>Yükleniyor…</div>}
      {error && <div className="text-red-600 text-sm mb-2">{error}</div>}
      {!loading && (
        <>
          <div className="space-y-2">
            {items.map(([k, v], idx) => (
              <div key={idx} className="grid grid-cols-12 gap-2 items-center">
                <input
                  className="col-span-5 border rounded px-2 py-1 text-sm"
                  placeholder="anahtar (örn: beta_mode)"
                  value={k}
                  onChange={(e) => onChange(idx, "k", e.target.value)}
                />
                <input
                  className="col-span-6 border rounded px-2 py-1 text-sm"
                  placeholder='değer (örn: true, 50, "gold")'
                  value={v}
                  onChange={(e) => onChange(idx, "v", e.target.value)}
                />
                <button
                  type="button"
                  className="col-span-1 text-xs border rounded px-2 py-1"
                  onClick={() => onRemove(idx)}
                  aria-label={`remove-row-${idx}`}
                >
                  Sil
                </button>
              </div>
            ))}
          </div>
          <div className="flex gap-2 mt-3">
            <button
              type="button"
              className="border rounded px-3 py-1 text-sm"
              onClick={onAdd}
            >
              Satır Ekle
            </button>
            <button
              type="button"
              className="border rounded px-3 py-1 text-sm"
              onClick={onSave}
            >
              Kaydet
            </button>
          </div>
          <div className="text-xs text-muted-foreground mt-3">
            Metin dışı değerler için JSON da yazabilirsiniz. Örn: <code>{"{\"limits\":{\"pro\":true}}"}</code>
          </div>
        </>
      )}
    </div>
  );
}

