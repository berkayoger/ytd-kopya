import React from 'react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {}

export function Button({ className = '', ...props }: ButtonProps) {
  return (
    <button
      className={`px-3 py-1 bg-blue-600 text-white rounded disabled:opacity-50 ${className}`}
      {...props}
    />
  );
}
