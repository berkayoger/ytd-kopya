import { render, screen } from '@testing-library/react';
import React from 'react';
import '@testing-library/jest-dom';
import AdminPlanManager from '../react/AdminPlanManager';

jest.mock('reactstrap', () => ({
  Card: (p: any) => <div {...p} />,
  CardBody: (p: any) => <div {...p} />,
  Button: (p: any) => <button {...p} />,
  Input: (p: any) => <input {...p} />,
  Spinner: (p: any) => <div {...p} />,
  Alert: (p: any) => <div {...p} />,
  Modal: (p: any) => <div {...p} />,
  ModalBody: (p: any) => <div {...p} />,
  ModalFooter: (p: any) => <div {...p} />,
}));
jest.mock('../react/api', () => ({
  fetchPlans: jest.fn(() =>
    Promise.resolve([{ id: 1, name: 'Basic', price: 0, features: { predict: 1 } }])
  ),
  updatePlanLimits: jest.fn(() => Promise.resolve({})),
  createPlan: jest.fn((p) => Promise.resolve({ ...p, id: 2 })),
  deletePlan: jest.fn(() => Promise.resolve({})),
}));

test('loads and displays plans', async () => {
  render(<AdminPlanManager />);
  expect(await screen.findByText('Basic')).toBeInTheDocument();
});
