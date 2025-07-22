import React from 'react';
import useLimitStatus from './hooks/useLimitStatus';
import { Card, CardBody, Progress } from 'reactstrap';

export default function PlanLimitCard() {
  const { limits, loading, error } = useLimitStatus();

  if (loading) return <div>Yükleniyor...</div>;
  if (error || !limits) return <div>Limit bilgileri alınamadı</div>;

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {Object.entries(limits).map(([key, info]) => (
        <Card key={key} className="shadow-sm border">
          <CardBody className="py-4">
            <div className="text-sm text-muted-foreground font-medium mb-1">
              {key.replace(/_/g, ' ').toUpperCase()}
            </div>
            <div className="flex justify-between text-xs mb-1">
              <span>İzin: {info.used} / {info.limit}</span>
              <span>{info.remaining} kaldı</span>
            </div>
            <Progress value={info.percent_used} />
          </CardBody>
        </Card>
      ))}
    </div>
  );
}
