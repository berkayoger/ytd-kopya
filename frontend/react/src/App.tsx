import React from "react";
import LimitStatus from "../components/LimitStatus";

/**
 * Ana uygulama bileşeni; kullanım limitlerini gösterir.
 */
export default function App() {
  return (
    <div className="p-4 max-w-3xl mx-auto">
      <h1 className="text-xl font-semibold mb-4">Dashboard</h1>
      <LimitStatus />
    </div>
  );
}
