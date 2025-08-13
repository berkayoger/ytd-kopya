import { render, screen } from "@testing-library/react";
import React from "react";
import "@testing-library/jest-dom";
import UserDetail from "../react/admin/UserDetail";

beforeEach(() => {
  // CustomFeaturesEditor içindeki GET çağrısını karşılamak için mock
  global.fetch = jest.fn(() =>
    Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ custom_features: { beta_mode: true } }),
    } as any)
  ) as any;
  Storage.prototype.getItem = jest.fn(() => "token");
});

test("renders user detail and loads CustomFeaturesEditor", async () => {
  render(<UserDetail userId={42} />);
  expect(await screen.findByText("Kullanıcı Detayı")).toBeInTheDocument();
  expect(screen.getByText("Kullanıcı ID: 42")).toBeInTheDocument();
  // CustomFeaturesEditor başlığı
  expect(await screen.findByText("Özel Özellikler")).toBeInTheDocument();
});
