import classNames from "classnames"

// Tailwind sınıflarını güvenli şekilde birleştiren yardımcı fonksiyon
export function cn(...inputs: classNames.ArgumentArray) {
  return classNames(...inputs)
}
