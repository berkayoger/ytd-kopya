import { useEffect, useState } from 'react';

interface LimitInfo {
  limit: number;
  used: number;
  remaining: number;
  percent_used: number;
}

export default function useLimitStatus() {
  const [limits, setLimits] = useState<Record<string, LimitInfo> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchLimits = async () => {
      setLoading(true);
      setError(null);
      try {
        const token = localStorage.getItem('access_token');
        const apiKey = localStorage.getItem('api_key');
        const res = await fetch('/api/limits/status', {
          headers: {
            Authorization: `Bearer ${token}`,
            'X-API-KEY': apiKey || '',
            'X-CSRF-TOKEN': 'test',
          },
        });
        if (!res.ok) throw new Error('Failed to load');
        const data = await res.json();
        setLimits(data.limits);
      } catch (err: any) {
        setError(err.message || 'error');
      } finally {
        setLoading(false);
      }
    };

    fetchLimits();
  }, []);

  return { limits, loading, error };
}
