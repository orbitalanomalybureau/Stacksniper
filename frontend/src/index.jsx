import { createRoot } from "react-dom/client";
import { HashRouter as BrowserRouter } from "react-router-dom";
import App from "./App";
import { AuthProvider } from "./context/AuthContext";
import { SportProvider } from "./context/SportContext";
import { ToastProvider } from "./components/ui/Toast";
import ErrorBoundary from "./components/ErrorBoundary";
import ApiErrorToast from "./components/ApiErrorToast";

const root = createRoot(document.getElementById("root"));
root.render(
  <ErrorBoundary>
    <BrowserRouter>
      <AuthProvider>
        <SportProvider>
          <ToastProvider>
            <ApiErrorToast />
            <App />
          </ToastProvider>
        </SportProvider>
      </AuthProvider>
    </BrowserRouter>
  </ErrorBoundary>
);
