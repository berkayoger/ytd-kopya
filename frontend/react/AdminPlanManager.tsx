import React, { useState } from 'react';
import {
  Card,
  CardBody,
  Button,
  Input,
  Spinner,
  Alert,
  Modal,
  ModalBody,
  ModalFooter,
} from 'reactstrap';
import { toast } from 'sonner';
import useAdminPlans from './hooks/useAdminPlans';
import { NewPlan } from './types';
import { Trash2, Plus, Save, XCircle } from 'lucide-react';
import { ProtectedRoute } from './ProtectedRoute';

export default function AdminPlanManager() {
  const { plans, setPlans, loading, error, load, saveAll, addPlan, removePlan } =
    useAdminPlans();
  const [saving, setSaving] = useState(false);
  const [deleteModal, setDeleteModal] = useState<{ visible: boolean; planId: number | null }>({
    visible: false,
    planId: null,
  });
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
    const planData = { ...newPlan };
    if (newFeatureKey) {
      planData.features = {
        ...planData.features,
        [newFeatureKey]: newFeatureValue,
      };
    }
    try {
      const created = await addPlan(planData);
      toast.success(`${created.name} başarıyla oluşturuldu.`);
      setNewPlan({ name: '', price: 0, features: { predict: 0 } });
      setNewFeatureKey('');
      setNewFeatureValue(0);
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
          <Card key={plan.id} className="col-md-4 mb-4 shadow-sm border">
            <CardBody>
              <div className="d-flex justify-content-between align-items-center mb-2">
                <h5 className="mb-0 fw-bold">{plan.name}</h5>
                <Button size="sm" color="danger" onClick={() => setDeleteModal({ visible: true, planId: plan.id })}>
                  <Trash2 size={16} />
                </Button>
              </div>
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
              <div className="mt-3 d-flex gap-2 align-items-end">
                <Input
                  type="text"
                  bsSize="sm"
                  placeholder="Yeni özellik"
                  className="w-50"
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
                  bsSize="sm"
                  placeholder="Başlangıç"
                  className="w-25"
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
                  <Plus size={16} />
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
        {saving ? 'Kaydediliyor...' : (
          <>
            <Save size={16} className="me-1" /> Tümünü Kaydet
          </>
        )}
      </Button>

      <Modal
        isOpen={deleteModal.visible}
        toggle={() => setDeleteModal({ visible: false, planId: null })}
      >
        <ModalBody>Bu planı silmek istediğinize emin misiniz?</ModalBody>
        <ModalFooter>
          <Button
            color="danger"
            onClick={() => {
              if (deleteModal.planId) handleDeletePlan(deleteModal.planId);
              setDeleteModal({ visible: false, planId: null });
            }}
          >
            Sil
          </Button>
          <Button
            color="secondary"
            onClick={() => setDeleteModal({ visible: false, planId: null })}
          >
            <XCircle size={16} className="me-1" /> Vazgeç
          </Button>
        </ModalFooter>
      </Modal>

      <h4>Yeni Plan Oluştur</h4>
      <div className="row g-2 align-items-end mt-4">
        <div className="col-md-3">
          <label className="form-label">Plan Adı</label>
          <Input value={newPlan.name} onChange={(e) => handleNewPlanChange('name', e.target.value)} />
        </div>
        <div className="col-md-2">
          <label className="form-label">Fiyat</label>
          <Input type="number" value={newPlan.price} onChange={(e) => handleNewPlanChange('price', e.target.value)} />
        </div>
        <div className="col-md-2">
          <label className="form-label">Özellik</label>
          <Input type="text" value={newFeatureKey} onChange={(e) => setNewFeatureKey(e.target.value)} />
        </div>
        <div className="col-md-2">
          <label className="form-label">Değer</label>
          <Input type="number" value={newFeatureValue} onChange={(e) => setNewFeatureValue(parseInt(e.target.value))} />
        </div>
        <div className="col-md-2">
          <Button onClick={handleCreatePlan}>
            <Plus size={16} className="me-1" /> Oluştur
          </Button>
        </div>
      </div>
    </div>
  );
}

export function ProtectedAdminPlanManager() {
  return (
    <ProtectedRoute isAdmin={true}>
      <AdminPlanManager />
    </ProtectedRoute>
  );
}
