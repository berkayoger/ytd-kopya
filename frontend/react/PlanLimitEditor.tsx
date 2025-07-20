import React, { useEffect, useState } from 'react';
import { Button, Input } from 'reactstrap';

export default function PlanLimitEditor() {
  const [plans, setPlans] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [resultMsg, setResultMsg] = useState('');

  useEffect(() => {
    fetch('/api/admin/plans')
      .then(res => res.json())
      .then(data => {
        setPlans(data.plans);
      });
  }, []);

  const updateLimit = (planId: number, field: string, value: any) => {
    setPlans(prev =>
      prev.map(p => (p.id === planId ? { ...p, features: { ...p.features, [field]: value } } : p))
    );
  };

  const saveChanges = async (planId: number) => {
    const plan = plans.find(p => p.id === planId);
    setLoading(true);
    try {
      const resp = await fetch(`/api/admin/plans/${planId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ features: plan!.features })
      });
      const res = await resp.json();
      if (res.ok) setResultMsg('Kaydedildi');
      else setResultMsg('Hata');
    } catch (e) {
      setResultMsg('Sunucu hatası');
    }
    setLoading(false);
  };

  return (
    <div className="p-6">
      <h2 className="text-xl font-bold mb-4">Plan Limitleri</h2>
      {plans.map(plan => (
        <div key={plan.id} className="border p-4 mb-4 rounded">
          <h3 className="font-semibold mb-2">{plan.name}</h3>
          <div className="grid grid-cols-2 gap-4">
            {Object.entries(plan.features).map(([key, val]) => (
              <div key={key}>
                <label className="block text-sm font-medium">{key}</label>
                <Input
                  type="number"
                  value={val}
                  onChange={e => updateLimit(plan.id, key, Number(e.target.value))}
                />
              </div>
            ))}
          </div>
          <Button className="mt-4" onClick={() => saveChanges(plan.id)} disabled={loading}>Kaydet</Button>
        </div>
      ))}
      {resultMsg && <div className="mt-2 text-sm">{resultMsg}</div>}
    </div>
  );
}
