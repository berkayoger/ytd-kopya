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
          limits: { test_feature: { limit: 5, used: 2, remaining: 3, percent_used: 40 } },
        }),
    })
  ) as any;
  Storage.prototype.getItem = jest.fn(() => 'token');
});

test('renders limit info inside dashboard', async () => {
  render(<Dashboard />);
  expect(await screen.findByText('Kullanım: 2 / 5')).toBeInTheDocument();
});
