import React, { useState } from "react";

const planOptions = [
  { label: "1. Plan", value: "plan1" },
  { label: "2. Plan", value: "plan2" },
  { label: "Tüm Planlar", value: "all" },
];
const userSegments = [
  { label: "Herkes", value: "all" },
  { label: "Yeni Kullanıcılar (Son 1 Ay)", value: "new_1m" },
  { label: "Eski Kullanıcılar (6 Ay+)", value: "old_6m" },
  { label: "Belirli Kullanıcılar", value: "custom" },
];
const promoTypes = [
  { label: "Plan İndirimi", value: "discount" },
  { label: "Ekstra Özellik", value: "feature" },
];

type PromoType = "discount" | "feature";

export default function PromoCreateAdvanced() {
  const [code, setCode] = useState("");
  const [desc, setDesc] = useState("");
  const [discount, setDiscount] = useState(0);
  const [discountType, setDiscountType] = useState("%");
  const [plans, setPlans] = useState<string[]>(["plan1"]);
  const [promoType, setPromoType] = useState<PromoType>("discount");
  const [feature, setFeature] = useState("");
  const [limit, setLimit] = useState(10);
  const [activeDays, setActiveDays] = useState(3);
  const [validityDays, setValidityDays] = useState(7);
  const [userSeg, setUserSeg] = useState("all");
  const [customUsers, setCustomUsers] = useState("");

  const togglePlan = (value: string) => {
    setPlans(prev =>
      prev.includes(value) ? prev.filter(p => p !== value) : [...prev, value]
    );
  };

  return (
    <div className="p-6 shadow-xl max-w-2xl mx-auto bg-white rounded">
      <h2 className="text-xl font-bold mb-3">Yeni Promosyon Kodu Oluştur</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <input className="border p-2 rounded" placeholder="Kod" value={code} onChange={e => setCode(e.target.value)} />
        <input className="border p-2 rounded" placeholder="Açıklama" value={desc} onChange={e => setDesc(e.target.value)} />
        <div>
          <label className="block text-sm font-medium mb-1">Etkilenen Plan(lar)</label>
          {planOptions.map(opt => (
            <label key={opt.value} className="mr-2 text-sm">
              <input type="checkbox" className="mr-1" checked={plans.includes(opt.value)} onChange={() => togglePlan(opt.value)} />
              {opt.label}
            </label>
          ))}
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Kod Türü</label>
          <select className="border p-2 rounded w-full" value={promoType} onChange={e => setPromoType(e.target.value as PromoType)}>
            {promoTypes.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>
        {promoType === "discount" ? (
          <>
            <input type="number" className="border p-2 rounded" placeholder="İndirim" value={discount} onChange={e => setDiscount(Number(e.target.value))} />
            <select className="border p-2 rounded" value={discountType} onChange={e => setDiscountType(e.target.value)}>
              <option value="%">%</option>
              <option value="TL">₺</option>
            </select>
          </>
        ) : (
          <input className="border p-2 rounded" placeholder="Özellik açıklaması" value={feature} onChange={e => setFeature(e.target.value)} />
        )}
        <input type="number" className="border p-2 rounded" placeholder="Kullanım Limiti" value={limit} onChange={e => setLimit(Number(e.target.value))} />
        <input type="number" className="border p-2 rounded" placeholder="Aktiflik Süresi (gün)" value={activeDays} onChange={e => setActiveDays(Number(e.target.value))} />
        <input type="number" className="border p-2 rounded" placeholder="Kullanıldıktan Sonra Geçerlilik (gün)" value={validityDays} onChange={e => setValidityDays(Number(e.target.value))} />
        <div>
          <label className="block text-sm font-medium mb-1">Kullanıcı Segmenti</label>
          <select className="border p-2 rounded w-full" value={userSeg} onChange={e => setUserSeg(e.target.value)}>
            {userSegments.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>
        {userSeg === "custom" && (
          <input className="border p-2 rounded" placeholder="Kullanıcı e-mail(lerini) virgülle yaz" value={customUsers} onChange={e => setCustomUsers(e.target.value)} />
        )}
      </div>
      <button className="mt-4 bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded">Promosyon Kodunu Oluştur</button>
    </div>
  );
}

