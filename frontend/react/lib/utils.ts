import classNames from "classnames"

// Tailwind sınıflarını güvenli şekilde birleştiren yardımcı fonksiyon
export function cn(...inputs: classNames.ArgumentArray) {
  return classNames(...inputs)
}

// Tailwind safelist'e eklenmesi gereken varyant sınıfları
export const safelistVariants = [
  "bg-primary",
  "bg-secondary",
  "bg-destructive",
  "hover:bg-accent",
  "text-primary",
  "text-secondary",
  "text-destructive",
  "text-white",
]
