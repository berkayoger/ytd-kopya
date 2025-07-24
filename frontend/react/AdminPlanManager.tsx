import React, { useState } from 'react';
import { Card, CardBody, Button, Input, Spinner, Alert } from 'reactstrap';
import { toast } from 'sonner';
import useAdminPlans from './hooks/useAdminPlans';
import { NewPlan } from './types';

export default function AdminPlanManager() {
  const { plans, setPlans, loading, error, load, saveAll, addPlan, removePlan } =
    useAdminPlans();
  const [saving, setSaving] = useState(false);
  const [newPlan, setNewPlan] = useState<NewPlan>({
    name: '',
    price: 0,
    features: { predict: 0 },
  });
  const [newFeatureKeys, setNewFeatureKeys] = useState<Record<number, { key: string; value: number }>>({});
  const [newFeatureKey, setNewFeatureKey] = useState('');
  const [newFeatureValue, setNewFeatureValue] = useState(0);

  const handleInputChange = (
    planId: number,
    key: string,
    value: string | number
  ) => {
    setPlans((prev) =>
      prev.map((p) =>
        p.id === planId
          ? { ...p, features: { ...p.features, [key]: Number(value) } }
          : p
      )
    );
  };

  const handleSaveAll = async () => {
    setSaving(true);
    try {
      await saveAll();
      toast.success('Tüm limitler güncellendi.');
    } catch {
      toast.error('Güncelleme sırasında hata oluştu.');
    } finally {
      setSaving(false);
    }
  };

  const handleNewPlanChange = (key: string, value: string) => {
    if (key.startsWith('features.')) {
      const featureKey = key.split('.')[1];
      setNewPlan((prev) => ({
        ...prev,
        features: { ...prev.features, [featureKey]: parseInt(value) || 0 },
      }));
    } else {
      setNewPlan((prev) => ({ ...prev, [key]: value }));
    }
  };

  const handleCreatePlan = async () => {
    try {
      const created = await addPlan(newPlan);
      toast.success(`${created.name} başarıyla oluşturuldu.`);
      setNewPlan({ name: '', price: 0, features: { predict: 0 } });
    } catch {
      toast.error('Plan oluşturulamadı.');
    }
  };

  const handleDeletePlan = async (planId: number) => {
    try {
      await removePlan(planId);
      toast.success('Plan silindi.');
    } catch {
      toast.error('Plan silinemedi.');
    }
  };

  if (loading) {
    return (
      <div className="d-flex align-items-center">
        <Spinner size="sm" className="me-2" /> Yükleniyor...
      </div>
    );
  }

  return (
    <div>
      <h2>Plan Yönetimi</h2>
      {error && <Alert color="danger">{error}</Alert>}

      <div className="row">
        {plans.map((plan) => (
          <Card key={plan.id} className="col-md-4 mb-4">
            <CardBody>
              <h5>
                {plan.name}{' '}
                <Button
                  size="sm"
                  color="danger"
                  onClick={() => handleDeletePlan(plan.id)}
                >
                  Sil
                </Button>
              </h5>
              {Object.entries(plan.features).map(([key, value]) => (
                <div key={key} className="mb-2">
                  <label>{key}</label>
                  <Input
                    type="number"
                    value={value}
                    onChange={(e) =>
                      handleInputChange(plan.id, key, e.target.value)
                    }
                  />
                </div>
              ))}
              {/* Yeni özellik ekleme alanı */}
              <div className="mt-3">
                <Input
                  type="text"
                  placeholder="Yeni özellik adı"
                  value={newFeatureKeys[plan.id]?.key || ''}
                  onChange={(e) =>
                    setNewFeatureKeys((prev) => ({
                      ...prev,
                      [plan.id]: {
                        ...prev[plan.id],
                        key: e.target.value,
                      },
                    }))
                  }
                />
                <Input
                  type="number"
                  placeholder="Başlangıç değeri"
                  value={newFeatureKeys[plan.id]?.value || 0}
                  onChange={(e) =>
                    setNewFeatureKeys((prev) => ({
                      ...prev,
                      [plan.id]: {
                        ...prev[plan.id],
                        value: parseInt(e.target.value) || 0,
                      },
                    }))
                  }
                />
                <Button
                  size="sm"
                  color="success"
                  onClick={() => {
                    const { key, value } = newFeatureKeys[plan.id] || {};
                    if (!key) return toast.error('Özellik adı boş olamaz.');
                    handleInputChange(plan.id, key, value || 0);
                    setNewFeatureKeys((prev) => ({
                      ...prev,
                      [plan.id]: { key: '', value: 0 },
                    }));
                  }}
                >
                  Özellik Ekle
                </Button>
              </div>
            </CardBody>
          </Card>
        ))}
      </div>

      <Button
        onClick={handleSaveAll}
        disabled={saving}
        color="primary"
        className="mb-4"
      >
        {saving ? 'Kaydediliyor...' : 'Tümünü Kaydet'}
      </Button>

      <h4>Yeni Plan Oluştur</h4>
      <div className="row">
        <div className="col-md-3">
          <Input
            placeholder="Plan Adı"
            value={newPlan.name}
            onChange={(e) => handleNewPlanChange('name', e.target.value)}
          />
        </div>
        <div className="col-md-2">
          <Input
            type="number"
            placeholder="Fiyat"
            value={newPlan.price}
            onChange={(e) => handleNewPlanChange('price', e.target.value)}
          />
        </div>
        <div className="col-md-2">
          <Input
            type="text"
            placeholder="Özellik adı"
            value={newFeatureKey}
            onChange={(e) => setNewFeatureKey(e.target.value)}
          />
        </div>
        <div className="col-md-2">
          <Input
            type="number"
            placeholder="Değer"
            value={newFeatureValue}
            onChange={(e) => setNewFeatureValue(parseInt(e.target.value))}
          />
        </div>
        <div className="col-md-2">
          <Button
            onClick={() => {
              if (!newFeatureKey) return toast.error('Özellik adı boş olamaz.');
              setNewPlan((prev) => ({
                ...prev,
                features: {
                  ...prev.features,
                  [newFeatureKey]: newFeatureValue,
                },
              }));
              setNewFeatureKey('');
              setNewFeatureValue(0);
            }}
          >
            Özellik Ekle
          </Button>
        </div>
        <div className="col-md-2">
          <Button onClick={handleCreatePlan}>Oluştur</Button>
        </div>
      </div>
    </div>
  );
}
