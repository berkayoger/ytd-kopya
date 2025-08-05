import React from 'react';

export interface SwitchProps extends React.InputHTMLAttributes<HTMLInputElement> {
  checked: boolean;
  onCheckedChange?: (checked: boolean) => void;
}

export function Switch({ checked, onCheckedChange, className = '', ...props }: SwitchProps) {
  return (
    <label className={`relative inline-flex items-center cursor-pointer ${className}`}>
      <input
        type="checkbox"
        className="sr-only peer"
        checked={checked}
        onChange={(e) => onCheckedChange?.(e.target.checked)}
        {...props}
      />
      <div className="w-11 h-6 bg-gray-200 rounded-full peer peer-checked:bg-blue-600 peer-focus:ring-4 peer-focus:ring-blue-300 after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:w-5 after:h-5 after:bg-white after:border after:rounded-full after:transition-all peer-checked:after:translate-x-full" />
    </label>
  );
}

export default Switch;
