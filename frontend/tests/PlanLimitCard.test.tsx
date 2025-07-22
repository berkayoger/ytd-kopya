import { render, screen } from '@testing-library/react';
import React from 'react';
import '@testing-library/jest-dom';
import PlanLimitCard from '../react/PlanLimitCard';
import useLimitStatus from '../react/hooks/useLimitStatus';

jest.mock('../react/hooks/useLimitStatus', () => ({
  __esModule: true,
  default: jest.fn(),
}));
const mockedHook = useLimitStatus as jest.MockedFunction<typeof useLimitStatus>;

jest.mock('reactstrap', () => ({
  Card: (props: any) => <div {...props} />,
  CardBody: (props: any) => <div {...props} />,
  Progress: (props: any) => <div data-progress={props.value} />,
}));

describe('PlanLimitCard', () => {
  it('shows loading state', () => {
    mockedHook.mockReturnValue({ limits: null, loading: true, error: null });
    render(<PlanLimitCard />);
    expect(screen.getByText('Yükleniyor...')).toBeInTheDocument();
  });

  it('renders limit information', () => {
    mockedHook.mockReturnValue({
      limits: { test: { limit: 5, used: 2, remaining: 3, percent_used: 40 } },
      loading: false,
      error: null,
    });
    render(<PlanLimitCard />);
    expect(screen.getByText('İzin: 2 / 5')).toBeInTheDocument();
    expect(screen.getByText('3 kaldı')).toBeInTheDocument();
  });
});
