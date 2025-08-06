import { render, screen } from '@testing-library/react';
import React from 'react';
import '@testing-library/jest-dom';
import { Button } from '../react/components/ui/button';

test('varsayılan buton sınıfını uygular', () => {
  render(<Button>Deneme</Button>);
  const btn = screen.getByRole('button');
  // Varsayılan olarak primary arka planı beklenir
  expect(btn).toHaveClass('bg-primary');
});

