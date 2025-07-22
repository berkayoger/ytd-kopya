import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import '@testing-library/jest-dom';
import CustomFeaturesEditor from '../react/CustomFeaturesEditor';

describe('CustomFeaturesEditor', () => {
  beforeEach(() => {
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve([
          { id: 1, username: 'test', subscription_level: 'basic', custom_features: '{}' }
        ])
      })
    ) as any;
  });

  it('renders without crashing', async () => {
    render(<CustomFeaturesEditor />);
    expect(await screen.findByText('Kullanıcıya Özel Özellikler')).toBeInTheDocument();
  });

  it.skip('displays error on invalid JSON', async () => {
    render(<CustomFeaturesEditor />);
    const select = await screen.findByRole('combobox');
    fireEvent.change(select, { target: { value: '1' } });
    const input = screen.getByLabelText(/custom_features JSON/i);
    fireEvent.change(input, { target: { value: '{invalid json' } });
    fireEvent.click(screen.getByText('Kaydet'));
    expect(await screen.findByText(/geçersiz json/i)).toBeInTheDocument();
  });
});
