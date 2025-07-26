import { render, screen } from '@testing-library/react';
import React from 'react';
import '@testing-library/jest-dom';
import PlanLimitCard from '../react/PlanLimitCard';
import { toast } from 'sonner';

type ExtendedMock = jest.Mock & { error?: jest.Mock; warning?: jest.Mock };
var mockFn: ExtendedMock;

jest.mock('sonner', () => {
  mockFn = jest.fn() as ExtendedMock;
  mockFn.error = jest.fn();
  mockFn.warning = jest.fn();
  return { toast: mockFn };
});

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

test('triggers warning toast at 90 percent usage', async () => {
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
  await screen.findByText('Kullanım: 9 / 10');
  expect(mockFn.warning).toHaveBeenCalled();
});

test('triggers error toast at full usage', async () => {
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
  await screen.findByText('Kullanım: 10 / 10');
  expect(mockFn.error).toHaveBeenCalled();
});
