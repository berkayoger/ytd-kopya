// Basit sınıf birleştirme yardımcı fonksiyonu
export function cn(...classes: Array<string | false | undefined | null>) {
  // Boş olmayan sınıfları birleştirir
  return classes.filter(Boolean).join(" ");
}

