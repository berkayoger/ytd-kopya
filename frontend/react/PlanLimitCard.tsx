import React from 'react';
import useLimitStatus from './hooks/useLimitStatus';
import { Card, CardBody, Progress } from 'reactstrap';
import { Loader2, AlertTriangle } from 'lucide-react';

export default function PlanLimitCard() {
  const { limits, loading, error } = useLimitStatus();

  if (loading) return (
    <div className="flex items-center space-x-2 text-muted-foreground text-sm">
      <Loader2 className="w-4 h-4 animate-spin" />
      <span>Limit bilgileri yükleniyor...</span>
    </div>
  );

  if (error || !limits) return (
    <div className="flex items-center space-x-2 text-red-500 text-sm">
      <AlertTriangle className="w-4 h-4" />
      <span>Limit bilgileri alınamadı</span>
    </div>
  );

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {Object.entries(limits).map(([key, info]) => (
        <Card key={key} className="shadow-sm border">
          <CardBody className="py-4">
            <div className="text-sm text-muted-foreground font-medium mb-1">
              {key.replace(/_/g, ' ').toUpperCase()}
            </div>
            <div className="flex justify-between text-xs mb-1">
              <span>Kullanım: {info.used} / {info.limit}</span>
              <span>{info.remaining} kaldı</span>
            </div>
            <Progress value={info.percent_used} />
          </CardBody>
        </Card>
      ))}
    </div>
  );
}
