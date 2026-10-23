import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { ApiError } from "./api/client";
import App from "./App";
import "./index.css";

// Ошибки API пользователь уже увидел во всплывающем сообщении — «необработанными» в консоль их не пишем
window.addEventListener("unhandledrejection", (e) => {
  if (e.reason instanceof ApiError) e.preventDefault();
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
