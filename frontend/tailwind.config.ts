import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#080b12",
        panel: "#101626",
        border: "#25304a",
        accent: "#4f7cff",
        success: "#12b981",
        warn: "#f59e0b",
        danger: "#ef4444"
      }
    }
  },
  plugins: []
};

export default config;
