import React from 'react';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {}

export function Card({ children, className = '', ...props }: CardProps) {
  return (
    <div className={`rounded border shadow-sm ${className}`} {...props}>
      {children}
    </div>
  );
}

export interface CardContentProps extends React.HTMLAttributes<HTMLDivElement> {}

export function CardContent({ children, className = '', ...props }: CardContentProps) {
  return (
    <div className={`p-4 ${className}`} {...props}>
      {children}
    </div>
  );
}
