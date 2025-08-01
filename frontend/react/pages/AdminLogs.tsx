import React from 'react';

import { useEffect, useState } from 'react';
import axios from 'axios';

const AdminLogs: React.FC = () => {
  const [logs, setLogs] = useState<any[]>([]);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const perPage = 10;

  useEffect(() => {
    axios
      .get(`/api/admin/logs?search=${search}&page=${page}&per_page=${perPage}`)
      .then((res) => {
        setLogs(res.data.logs);
        setTotal(res.data.total);
      });
  }, [search, page]);

  return (
    <div className="p-6">
      <h1 className="text-xl font-semibold mb-4">Log Kayıtları</h1>
      <input
        className="border p-2 mb-4 w-full"
        type="text"
        placeholder="Log ara..."
        value={search}
        onChange={(e) => {
          setSearch(e.target.value);
          setPage(1);
        }}
      />
      <table className="min-w-full bg-white">
        <thead>
          <tr>
            <th className="px-4 py-2">Zaman</th>
            <th className="px-4 py-2">Kullanıcı</th>
            <th className="px-4 py-2">Aksiyon</th>
            <th className="px-4 py-2">Hedef</th>
            <th className="px-4 py-2">Durum</th>
          </tr>
        </thead>
        <tbody>
          {logs.map((log, i) => (
            <tr key={i} className="border-t">
              <td className="px-4 py-2 text-sm">
                {new Date(log.timestamp).toLocaleString()}
              </td>
              <td className="px-4 py-2 text-sm">{log.username}</td>
              <td className="px-4 py-2 text-sm">{log.action}</td>
              <td className="px-4 py-2 text-sm">{log.target}</td>
              <td className="px-4 py-2 text-sm">{log.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="flex justify-between mt-4">
        <button
          disabled={page === 1}
          onClick={() => setPage(page - 1)}
          className="btn"
        >
          &larr; Geri
        </button>
        <span>Sayfa {page}</span>
        <button
          disabled={page * perPage >= total}
          onClick={() => setPage(page + 1)}
          className="btn"
        >
          İleri &rarr;
        </button>
      </div>
    </div>
  );
};

export default AdminLogs;
