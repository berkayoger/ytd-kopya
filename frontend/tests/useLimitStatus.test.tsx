import { renderHook, waitFor } from '@testing-library/react';
import React from 'react';
import useLimitStatus from '../react/hooks/useLimitStatus';

describe('useLimitStatus', () => {
  beforeEach(() => {
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ limits: { test: { limit: 5, used: 0, remaining: 5, percent_used: 0 } } })
      })
    ) as any;
    Storage.prototype.getItem = jest.fn(() => 'token');
  });

  it('fetches limits on mount', async () => {
    const { result } = renderHook(() => useLimitStatus());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.limits).toHaveProperty('test');
  });
});
