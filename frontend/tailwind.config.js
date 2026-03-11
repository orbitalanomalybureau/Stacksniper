/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,jsx}", "./public/index.html"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        primary: "#060d08",
        surface: "#0f2218",
        surface2: "#132b1e",
        border: "#1a3d27",
        viper: "#0d3b1e",
        venom: "#00ff88",
        "venom-glow": "#2ecc71",
        gold: "#f0c040",
        fangs: "#ff4444",
        "text-primary": "#eaf5ee",
        "text-secondary": "#d4e8dc",
        "text-muted": "#6b9a7e",
        // Backward-compat aliases
        "surface-light": "#132b1e",
        "surface-lighter": "#1a3d27",
      },
      fontFamily: {
        sans: ["Outfit", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
      keyframes: {
        "pulse-glow": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.5" },
        },
        "fade-in": {
          from: { opacity: "0", transform: "translateY(8px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "crosshair-spin": {
          from: { transform: "rotate(0deg)" },
          to: { transform: "rotate(360deg)" },
        },
      },
      animation: {
        "pulse-glow": "pulse-glow 2s ease-in-out infinite",
        "fade-in": "fade-in 0.3s ease-out",
        "crosshair-spin": "crosshair-spin 20s linear infinite",
      },
    },
  },
  plugins: [],
};
