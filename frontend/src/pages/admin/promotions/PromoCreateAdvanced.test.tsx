import { render, screen, fireEvent } from '@testing-library/react';
import PromoCreateAdvanced from '../../../../react/PromoCreateAdvanced';
import React from 'react';
import '@testing-library/jest-dom';

jest.mock('reactstrap', () => ({
  Button: (props: any) => <button {...props} />,
  Input: (props: any) => <input {...props} />,
}));

beforeAll(() => {
  global.fetch = jest.fn(() =>
    Promise.resolve({ json: () => Promise.resolve({ plans: [] }), ok: true })
  ) as any;
});

// Basic form validation test
it('buton render edilir', () => {
  render(<PromoCreateAdvanced />);
  const btn = screen.getByText(/Promosyon Kodunu Oluştur/i);
  fireEvent.click(btn);
  expect(btn).toBeInTheDocument();
});
