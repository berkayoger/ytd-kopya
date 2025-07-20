import React, { useEffect, useState } from 'react';
import { Button, Input } from 'reactstrap';

export default function PromoCreateAdvanced() {
  const [code, setCode] = useState('');
  const [desc, setDesc] = useState('');
  const [promoType, setPromoType] = useState('');
  const [discountType, setDiscountType] = useState('');
  const [discount, setDiscount] = useState(0);
  const [feature, setFeature] = useState('');
  const [plans, setPlans] = useState<string[]>([]);
  const [limit, setLimit] = useState(1);
  const [activeDays, setActiveDays] = useState(0);
  const [validityDays, setValidityDays] = useState(0);
  const [userSeg, setUserSeg] = useState('all');
  const [customUsers, setCustomUsers] = useState('');

  const [planOptions, setPlanOptions] = useState<{label:string,value:number}[]>([]);
  const [userSegments, setUserSegments] = useState([
    { label: 'Herkes', value: 'all' },
    { label: 'Yeni Kullanıcılar (Son 1 Ay)', value: 'new_1m' },
    { label: 'Eski Kullanıcılar (6 Ay+)', value: 'old_6m' },
    { label: 'Belirli Kullanıcılar', value: 'custom' },
  ]);
  const [loading, setLoading] = useState(false);
  const [resultMsg, setResultMsg] = useState('');

  useEffect(() => {
    fetch('/api/admin/plans?simple=1')
      .then(r => r.json())
      .then(data => {
        setPlanOptions(data.plans.map((p: any) => ({ label: p.name, value: p.id })));
      });
  }, []);

  const handleSubmit = async () => {
    setLoading(true);
    setResultMsg('');
    try {
      const resp = await fetch('/api/admin/promo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          code,
          description: desc,
          promo_type: promoType,
          discount_type: discountType,
          discount,
          feature,
          plans,
          usage_limit: limit,
          active_days: activeDays,
          validity_days: validityDays,
          user_segment: userSeg,
          custom_users: customUsers ? customUsers.split(',').map(x => x.trim()) : [],
        }),
      });
      const res = await resp.json();
      if (res.ok) setResultMsg('Başarıyla oluşturuldu!');
      else setResultMsg('Hata: ' + (res.error || 'Bilinmeyen'));
    } catch (e) {
      setResultMsg('Sunucu hatası');
    }
    setLoading(false);
  };

  return (
    <div>
      {/* form fields omitted for brevity */}
      <Button className="mt-4" onClick={handleSubmit} disabled={loading}>Promosyon Kodunu Oluştur</Button>
      {resultMsg && <div className="mt-2 text-center text-sm">{resultMsg}</div>}
    </div>
  );
}
