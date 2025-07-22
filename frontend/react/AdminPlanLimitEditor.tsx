import React, { useState, useEffect } from 'react';
import { Card, CardContent } from './components/ui/card';
import { Input } from './components/ui/input';
import { Button } from './components/ui/button';
import { toast } from 'sonner';
import { Loader2 } from 'lucide-react';

export default function AdminPlanLimitEditor() {
  const [plans, setPlans] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchPlans();
  }, []);

  const fetchPlans = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/plans/all');
      const data = await res.json();
      setPlans(data);
    } catch (err) {
      toast.error('Planlar yüklenemedi.');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (planIndex: number, key: string, value: string) => {
    const newPlans = [...plans];
    newPlans[planIndex].features[key] = parseInt(value) || 0;
    setPlans(newPlans);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await Promise.all(
        plans.map((plan) =>
          fetch(`/api/plans/${plan.id}/update-limits`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(plan.features),
          })
        )
      );
      toast.success('Plan limitleri güncellendi.');
    } catch {
      toast.error('Güncelleme sırasında hata oluştu.');
    } finally {
      setSaving(false);
    }
  };

  if (loading)
    return (
      <div className="flex items-center text-muted-foreground text-sm">
        <Loader2 className="w-4 h-4 animate-spin mr-2" /> Planlar yükleniyor...
      </div>
    );

  return (
    <section className="space-y-4">
      <h3 className="text-base font-semibold text-muted-foreground">Plan Limitlerini Düzenle</h3>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {plans.map((plan, i) => (
          <Card key={plan.id} className="shadow-sm">
            <CardContent className="space-y-2 py-4">
              <h4 className="text-sm font-medium">{plan.name.toUpperCase()}</h4>
              {Object.entries(plan.features).map(([key, value]) => (
                <div key={key} className="flex items-center justify-between gap-2">
                  <label className="text-xs text-muted-foreground w-1/2">{key}</label>
                  <Input
                    type="number"
                    value={value as any}
                    onChange={(e) => handleChange(i, key, e.target.value)}
                    className="w-24 text-right"
                  />
                </div>
              ))}
            </CardContent>
          </Card>
        ))}
      </div>
      <Button onClick={handleSave} disabled={saving}>
        {saving ? 'Kaydediliyor...' : 'Tümünü Kaydet'}
      </Button>
    </section>
  );
}
