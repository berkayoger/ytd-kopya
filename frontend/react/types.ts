export interface Plan {
  id: number;
  name: string;
  price: number;
  features: Record<string, number>;
}

export interface NewPlan {
  name: string;
  price: number;
  features: Record<string, number>;
}
