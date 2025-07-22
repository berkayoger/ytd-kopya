import React from 'react';

interface ProgressProps extends React.HTMLAttributes<HTMLDivElement> {
  value: number;
}

export function Progress({ value, className = '', ...props }: ProgressProps) {
  return (
    <div className={`w-full bg-gray-200 rounded ${className}`} {...props}>
      <div
        data-testid="progress"
        className="h-2 bg-blue-500 rounded"
        style={{ width: `${value}%` }}
      />
    </div>
  );
}
