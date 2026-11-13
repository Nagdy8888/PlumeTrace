import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { AppShell } from "./app/AppShell";
import "./styles/index.css";

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("Root element #root not found in index.html");
}

createRoot(rootElement).render(
  <StrictMode>
    <AppShell />
  </StrictMode>,
);
