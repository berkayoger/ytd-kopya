import { render, screen } from '@testing-library/react';
import React from 'react';
import '@testing-library/jest-dom';
import Dashboard from '../react/dashboard/Dashboard';

beforeEach(() => {
  global.fetch = jest.fn(() =>
    Promise.resolve({
      ok: true,
      json: () =>
        Promise.resolve({
          plan: null,
          limits: { test_feature: { used: 2, max: 5 } },
        }),
    })
  ) as any;
  Storage.prototype.getItem = jest.fn(() => 'token');
});

test('renders limit info inside dashboard', async () => {
  render(<Dashboard />);
  const els = await screen.findAllByText('2 / 5 (40%)');
  expect(els.length).toBeGreaterThan(0);
});
