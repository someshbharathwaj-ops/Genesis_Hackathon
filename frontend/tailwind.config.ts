import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#FFFBF2",
        foreground: "#17171A",
        ink: {
          DEFAULT: "#17171A",
          muted: "#5A5A62",
          faint: "#8E8E98",
        },
        surface: {
          DEFAULT: "#FFFFFF",
          warm: "#FFFBF2",
          muted: "#F7F2E7",
          border: "#17171A",
        },
        brand: {
          yellow: "#FFC800", // Primary action & learning focus
          coral: "#FF5A4F",  // Alerts, streak energy
          green: "#22C55E",  // Correctness, mastery progress
          cyan: "#2BB8F0",   // Secondary info, links
        },
      },
      boxShadow: {
        hard: "0 4px 0 #17171A",
        "hard-sm": "0 2px 0 #17171A",
        "hard-lg": "0 6px 0 #17171A",
        "hard-pressed": "0 1px 0 #17171A",
      },
      borderRadius: {
        friendly: "16px",
        "friendly-sm": "12px",
        "friendly-lg": "20px",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "-apple-system", "sans-serif"],
        display: ["var(--font-display)", "system-ui", "-apple-system", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
