import React from 'react';
import { Card, CardContent } from '../components/ui/card';
import { BarChart } from 'lucide-react';
import PlanLimitCard from '../PlanLimitCard';
import LimitStatus from '../components/LimitStatus';

export default function Dashboard() {
  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Genel Bakış</h1>

      {/* Kullanım limitleri */}
      <PlanLimitCard />

      {/* Kullanım limitleri bileşeni */}
      <LimitStatus />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardContent className="flex items-center gap-4 p-6">
            <BarChart className="w-6 h-6 text-muted-foreground" />
            <div>
              <div className="text-sm text-muted-foreground">Toplam Tahmin</div>
              <div className="text-xl font-semibold">132</div>
            </div>
          </CardContent>
        </Card>
        {/* Diğer kartlar... */}
      </div>
    </div>
  );
}
