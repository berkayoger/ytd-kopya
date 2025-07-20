import { render, screen } from '@testing-library/react';
import PlanLimitEditor from '../../../react/PlanLimitEditor';
import React from 'react';
import '@testing-library/jest-dom';

jest.mock('reactstrap', () => ({
  Button: (props: any) => <button {...props} />,
  Input: (props: any) => <input {...props} />,
}));

beforeAll(() => {
  global.fetch = jest.fn(() =>
    Promise.resolve({
      json: () => Promise.resolve({ plans: [{ id: 1, name: 'Basic', features: { a: 1 } }] }),
      ok: true,
    })
  ) as any;
});

test('renders save button', async () => {
  render(<PlanLimitEditor />);
  const btn = await screen.findByText(/Kaydet/i);
  expect(btn).toBeInTheDocument();
});
