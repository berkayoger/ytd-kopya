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
          limits: { test_feature: { limit: 5, used: 2, remaining: 3, percent_used: 40 } },
        }),
    })
  ) as any;
  Storage.prototype.getItem = jest.fn(() => 'token');
});

test('renders limit info after load', async () => {
  render(<PlanLimitCard />);
  expect(await screen.findByText('Kullanım: 2 / 5')).toBeInTheDocument();
  expect(screen.getByTestId('progress')).toHaveStyle({ width: '40%' });
});

test('shows warning icon at 90 percent usage', async () => {
  (global.fetch as jest.Mock).mockImplementationOnce(() =>
    Promise.resolve({
      ok: true,
      json: () =>
        Promise.resolve({
          limits: { warn: { limit: 10, used: 9, remaining: 1, percent_used: 90 } },
        }),
    })
  );
  render(<PlanLimitCard />);
  expect(await screen.findByTitle('%90 kullanım')).toBeInTheDocument();
});

test('shows bell ring icon at full usage', async () => {
  (global.fetch as jest.Mock).mockImplementationOnce(() =>
    Promise.resolve({
      ok: true,
      json: () =>
        Promise.resolve({
          limits: { full: { limit: 10, used: 10, remaining: 0, percent_used: 100 } },
        }),
    })
  );
  render(<PlanLimitCard />);
  expect(await screen.findByTitle('Limit doldu')).toBeInTheDocument();
});
