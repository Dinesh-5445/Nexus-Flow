import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";

// Day 8: minimal Vite entry point. None existed in the repository yet
// (only App.tsx/DashboardLayout.tsx and their panels), so the dashboard
// could not actually be built or run to validate today's live-data wiring.
// Added as a small, standard Vite+React bootstrap — no styling/framework
// decisions beyond what index.html/vite.config.ts already assumed.
const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("Root element #root not found in index.html");
}

createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>
);