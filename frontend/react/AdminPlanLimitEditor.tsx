import React, { useState, useEffect } from 'react';
import { Card, CardBody, Button, Input, Spinner, Alert } from 'reactstrap';
import { toast } from 'sonner';
import { Loader2 } from 'lucide-react';
import { Plan } from './types'; // Plan türünü tanımlayarak ekleyin.
import { updatePlanLimits, fetchPlans } from './api'; // API metodlarını oluşturmalısınız.

export default function AdminPlanLimitEditor() {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchPlansData();
  }, []);

  const fetchPlansData = async () => {
    setLoading(true);
    try {
      const plansData = await fetchPlans();
      setPlans(plansData);
    } catch (error) {
      setError('Plans could not be loaded.');
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (planId: number, key: string, value: string) => {
    setPlans((prevPlans) =>
      prevPlans.map((plan) =>
        plan.id === planId ? { ...plan, features: { ...plan.features, [key]: value } } : plan
      )
    );
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      for (const plan of plans) {
        await updatePlanLimits(plan.id, plan.features);
      }
      toast.success('Limits updated successfully');
    } catch (error) {
      toast.error('Failed to update limits');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="d-flex align-items-center">
        <Spinner size="sm" className="mr-2" />
        <span>Loading...</span>
      </div>
    );
  }

  return (
    <div>
      {error && <Alert color="danger">{error}</Alert>}
      <h2>Plan Limit Editor</h2>
      <div className="row">
        {plans.map((plan) => (
          <Card key={plan.id} className="col-md-4">
            <CardBody>
              <h3>{plan.name}</h3>
              {Object.entries(plan.features).map(([key, value]) => (
                <div key={key} className="mb-3">
                  <label>{key}</label>
                  <Input
                    type="number"
                    value={value}
                    onChange={(e) => handleInputChange(plan.id, key, e.target.value)}
                  />
                </div>
              ))}
            </CardBody>
          </Card>
        ))}
      </div>
      <Button onClick={handleSave} disabled={saving}>
        {saving ? <Loader2 className="animate-spin" size={20} /> : 'Save Changes'}
      </Button>
    </div>
  );
}
