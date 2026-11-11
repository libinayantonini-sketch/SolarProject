/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "media",
  theme: {
    extend: {
      colors: {
        limpo: { DEFAULT: "#15803d", soft: "#dcfce7", dark: "#4ade80", darksoft: "#14341f" },
        moderado: { DEFAULT: "#a16207", soft: "#fef3c7", dark: "#facc15", darksoft: "#3b2f0b" },
        severo: { DEFAULT: "#b91c1c", soft: "#fee2e2", dark: "#f87171", darksoft: "#3f1515" },
      },
    },
  },
  plugins: [],
};
