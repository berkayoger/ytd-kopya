import React, { useEffect, useState } from 'react';
import { Button, Input } from 'reactstrap';

interface Promo {
  id: number;
  code: string;
  description: string;
  isActive: boolean;
}

export default function PromoListAdvanced() {
  const [promos, setPromos] = useState<Promo[]>([]);
  const [filter, setFilter] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetch('/api/admin/promo?filter=' + encodeURIComponent(filter))
      .then(r => r.json())
      .then(data => setPromos(data.promos || []));
  }, [filter]);

  const handleDelete = async (id: number) => {
    setLoading(true);
    await fetch(`/api/admin/promo/${id}`, { method: 'DELETE' });
    setPromos(promos.filter(p => p.id !== id));
    setLoading(false);
  };

  const handleToggle = async (id: number, isActive: boolean) => {
    setLoading(true);
    await fetch(`/api/admin/promo/${id}/toggle`, { method: 'POST' });
    setPromos(promos.map(p => p.id === id ? { ...p, isActive: !isActive } : p));
    setLoading(false);
  };

  return (
    <div>
      <Input
        className="mb-3"
        placeholder="Koda veya açıklamaya göre filtrele"
        value={filter}
        onChange={e => setFilter(e.target.value)}
      />
      <table>
        <tbody>
          {promos.map(promo => (
            <tr key={promo.id}>
              <td>{promo.code}</td>
              <td>
                <Button size="sm" onClick={() => handleToggle(promo.id, promo.isActive)}>
                  {promo.isActive ? 'Pasif Et' : 'Aktif Et'}
                </Button>
                <Button size="sm" color="danger" onClick={() => handleDelete(promo.id)}>Sil</Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
