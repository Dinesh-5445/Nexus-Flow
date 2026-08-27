import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Day 3: dev-only proxy so the dashboard can call Sayan's services/api
// (POST /execute, GET /status/:id, WS /stream/:id) as same-origin requests.
// services/api sends no Access-Control-Allow-Origin header today (verified
// against the running service), so a direct cross-origin fetch() from the
// Vite dev server's origin to http://localhost:3000 is blocked by the
// browser. This proxy is a frontend-only, dev-time workaround — it does not
// modify services/api. A real deployment still needs a CORS/proxy decision
// from Sayan.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/execute": "http://localhost:3000",
      "/status": "http://localhost:3000",
      "/stream": {
        target: "ws://localhost:3000",
        ws: true,
      },
    },
  },
});