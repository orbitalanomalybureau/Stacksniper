import { useEffect } from "react";
import { useToast } from "./ui/Toast";

export default function ApiErrorToast() {
  const addToast = useToast();

  useEffect(() => {
    function handleApiError(e) {
      const { status, message } = e.detail || {};
      if (status === 429) {
        addToast("Rate limit exceeded. Please wait a moment.", "error");
      } else if (status >= 500) {
        addToast("Server error. Please try again later.", "error");
      } else {
        addToast(message || "Something went wrong.", "error");
      }
    }
    window.addEventListener("api-error", handleApiError);
    return () => window.removeEventListener("api-error", handleApiError);
  }, [addToast]);

  return null;
}
