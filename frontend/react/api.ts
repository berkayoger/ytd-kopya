import { Plan, NewPlan } from './types';

async function handleResponse(res: Response) {
  if (!res.ok) {
    throw new Error('Request failed');
  }
  return res.json();
}

export async function fetchPlans(): Promise<Plan[]> {
  const res = await fetch('/api/plans/all');
  return handleResponse(res);
}

export async function updatePlanLimits(planId: number, features: Record<string, number>) {
  const res = await fetch(`/api/plans/${planId}/update-limits`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(features),
  });
  return handleResponse(res);
}

export async function createPlan(plan: NewPlan): Promise<Plan> {
  const res = await fetch('/api/plans/create', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(plan),
  });
  return handleResponse(res);
}

export async function deletePlan(planId: number) {
  const res = await fetch(`/api/plans/${planId}`, { method: 'DELETE' });
  return handleResponse(res);
}
