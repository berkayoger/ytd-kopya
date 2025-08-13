import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import React from 'react';
import '@testing-library/jest-dom';
import CustomFeaturesEditor from '../react/admin/CustomFeaturesEditor';

describe('CustomFeaturesEditor', () => {
  beforeEach(() => {
    window.alert = jest.fn();
  });

  it('fetches and renders', async () => {
    const fetchMock = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ custom_features: { test: '1' } }),
    });
    global.fetch = fetchMock as any;

    render(<CustomFeaturesEditor userId={1} />);

    expect(await screen.findByText('Özel Özellikler')).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/admin/users/1/custom_features',
      expect.objectContaining({ method: 'GET' })
    );
  });

  it('saves non-empty fields with typed values and alerts on success', async () => {
    const fetchMock = jest.fn().mockImplementation((url, opts) => {
      if (!opts || opts.method === 'GET') {
        return Promise.resolve({
          ok: true,
          json: async () => ({ custom_features: {} }),
        });
      }
      return Promise.resolve({ ok: true, json: async () => ({}) });
    });
    global.fetch = fetchMock as any;

    render(<CustomFeaturesEditor userId={1} />);

    await screen.findByPlaceholderText('anahtar (örn: beta_mode)');

    const addBtn = await screen.findByRole('button', { name: 'Satır Ekle' });
    for (let i = 0; i < 4; i++) {
      await userEvent.click(addBtn);
    }

    const keyInputs = screen.getAllByPlaceholderText('anahtar (örn: beta_mode)');
    const valueInputs = screen.getAllByPlaceholderText(
      'değer (örn: true, 50, "gold")'
    );

    await userEvent.type(keyInputs[0], 'beta_mode');
    await userEvent.type(valueInputs[0], 'true');

    await userEvent.type(keyInputs[1], 'limit');
    await userEvent.type(valueInputs[1], '50');

    await userEvent.type(keyInputs[2], 'prefs');
    fireEvent.change(valueInputs[2], { target: { value: '{"gold":true}' } });

    await userEvent.type(valueInputs[3], 'skip');

    await userEvent.type(keyInputs[4], 'bad');
    fireEvent.change(valueInputs[4], { target: { value: '{"broken"}' } });

    await userEvent.click(screen.getByRole('button', { name: 'Kaydet' }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    const putCall = fetchMock.mock.calls[1];
    expect(putCall[0]).toBe('/api/admin/users/1/custom_features');
    const sentBody = JSON.parse(putCall[1].body);
    expect(sentBody).toEqual({
      beta_mode: true,
      limit: 50,
      prefs: { gold: true },
      bad: '{"broken"}',
    });
    expect(window.alert).toHaveBeenCalledWith('Kaydedildi');
  });

  it('shows error when save request rejects', async () => {
    const fetchMock = jest.fn().mockImplementation((url, opts) => {
      if (!opts || opts.method === 'GET') {
        return Promise.resolve({
          ok: true,
          json: async () => ({ custom_features: {} }),
        });
      }
      return Promise.reject(new Error('fail'));
    });
    global.fetch = fetchMock as any;

    render(<CustomFeaturesEditor userId={1} />);
    await screen.findByPlaceholderText('anahtar (örn: beta_mode)');

    const keyInput = screen.getByPlaceholderText('anahtar (örn: beta_mode)');
    const valueInput = screen.getByPlaceholderText('değer (örn: true, 50, "gold")');

    await userEvent.type(keyInput, 'a');
    await userEvent.type(valueInput, '1');

    await userEvent.click(screen.getByRole('button', { name: 'Kaydet' }));

    expect(await screen.findByText('fail')).toBeInTheDocument();
    expect(window.alert).not.toHaveBeenCalled();
  });

  it('shows error when save response is not ok', async () => {
    const fetchMock = jest.fn().mockImplementation((url, opts) => {
      if (!opts || opts.method === 'GET') {
        return Promise.resolve({
          ok: true,
          json: async () => ({ custom_features: {} }),
        });
      }
      return Promise.resolve({
        ok: false,
        status: 500,
        text: async () => 'bad',
      });
    });
    global.fetch = fetchMock as any;

    render(<CustomFeaturesEditor userId={1} />);
    await screen.findByPlaceholderText('anahtar (örn: beta_mode)');

    const keyInput = screen.getByPlaceholderText('anahtar (örn: beta_mode)');
    const valueInput = screen.getByPlaceholderText('değer (örn: true, 50, "gold")');

    await userEvent.type(keyInput, 'a');
    await userEvent.type(valueInput, '1');

    await userEvent.click(screen.getByRole('button', { name: 'Kaydet' }));

    expect(
      await screen.findByText('Kaydedilemedi: 500 bad')
    ).toBeInTheDocument();
    expect(window.alert).not.toHaveBeenCalled();
  });
});

