import { useEffect, useState } from 'react';
import { fetchPlans, updatePlanLimits, createPlan, deletePlan } from '../api';
import { Plan, NewPlan } from '../types';

export default function useAdminPlans() {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchPlans();
      setPlans(data);
    } catch {
      setError('Planlar yüklenemedi.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const saveAll = async () => {
    for (const plan of plans) {
      await updatePlanLimits(plan.id, plan.features);
    }
  };

  const addPlan = async (plan: NewPlan) => {
    const created = await createPlan(plan);
    setPlans((prev) => [...prev, created]);
    return created;
  };

  const removePlan = async (planId: number) => {
    await deletePlan(planId);
    setPlans((prev) => prev.filter((p) => p.id !== planId));
  };

  return { plans, setPlans, loading, error, load, saveAll, addPlan, removePlan };
}
