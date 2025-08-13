import React from "react";
import CustomFeaturesEditor from "./CustomFeaturesEditor";

/**
 * Admin Kullanıcı Detay Sayfası
 * - Kullanıcıya ait custom_features alanını düzenlemek için CustomFeaturesEditor içerir.
 *
 * Not: Bu bileşen router ile /admin/users/:id gibi bir route'a bağlanacaksa,
 *      userId parametresini route params'tan çekip bu bileşene prop olarak geçin.
 */
export default function UserDetail({
  userId,
  tokenProvider,
}: {
  userId: number | string;
  tokenProvider?: () => string | null;
}) {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold">Kullanıcı Detayı</h1>
        <div className="text-sm text-muted-foreground">Kullanıcı ID: {String(userId)}</div>
      </div>
      <CustomFeaturesEditor userId={userId} tokenProvider={tokenProvider} />
    </div>
  );
}
