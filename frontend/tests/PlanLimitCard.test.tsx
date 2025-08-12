import { render, screen } from '@testing-library/react';
import React from 'react';
import '@testing-library/jest-dom';
import PlanLimitCard from '../react/PlanLimitCard';

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

test('renders limit info after load', async () => {
  render(<PlanLimitCard />);
  expect(await screen.findByText('2 / 5 (40%)')).toBeInTheDocument();
  expect(screen.getByTestId('progress')).toHaveStyle({ width: '40%' });
});

test('shows warning text at 90 percent usage', async () => {
  (global.fetch as jest.Mock).mockImplementationOnce(() =>
    Promise.resolve({
      ok: true,
      json: () =>
        Promise.resolve({
          plan: null,
          limits: { warn: { used: 9, max: 10 } },
        }),
    })
  );
  render(<PlanLimitCard />);
  await screen.findByText('9 / 10 (90%)');
  expect(screen.getByText('%90 üzerine çıktınız')).toBeInTheDocument();
});

test('shows error text at full usage', async () => {
  (global.fetch as jest.Mock).mockImplementationOnce(() =>
    Promise.resolve({
      ok: true,
      json: () =>
        Promise.resolve({
          plan: null,
          limits: { full: { used: 10, max: 10 } },
        }),
    })
  );
  render(<PlanLimitCard />);
  await screen.findByText('10 / 10 (100%)');
  expect(screen.getByText('Limit doldu (%100)')).toBeInTheDocument();
});
