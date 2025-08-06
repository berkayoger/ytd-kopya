import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

// Tailwind sınıf isimlerini birleştirir
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
