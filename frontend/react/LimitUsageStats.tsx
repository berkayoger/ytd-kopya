import React, { useEffect, useState } from 'react';

type Stat = {
  user_id: number;
  username: string;
  action: string;
  count: number;
};

export default function LimitUsageStats() {
  const [stats, setStats] = useState<Stat[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    setLoading(true);
    fetch('/api/admin/limit-usage')
      .then((res) => {
        if (!res.ok) throw new Error('Yükleme başarısız');
        return res.json();
      })
      .then((data) => setStats(data.stats))
      .catch(() => setError('Veri alınamadı'))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="p-6">
      <h2 className="text-xl font-bold mb-4">Kullanım İstatistikleri</h2>
      {loading && <p>Yükleniyor...</p>}
      {error && <p className="text-red-500">{error}</p>}
      <table className="table-auto w-full text-sm">
        <thead>
          <tr>
            <th className="px-4 py-2">Kullanıcı</th>
            <th className="px-4 py-2">İşlem</th>
            <th className="px-4 py-2">Kullanım</th>
          </tr>
        </thead>
        <tbody>
          {stats.map((stat) => (
            <tr key={`${stat.user_id}-${stat.action}`}>
              <td className="border px-4 py-2">{stat.username}</td>
              <td className="border px-4 py-2">{stat.action}</td>
              <td className="border px-4 py-2">{stat.count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
