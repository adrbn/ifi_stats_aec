import type { Config } from "tailwindcss";

/**
 * OSCAR design tokens mapped to Tailwind.
 * Source of truth: design-system.css from the Claude Design handoff bundle.
 * Values are wired to CSS variables (defined in globals.css) so the palette
 * stays editable in one place.
 */
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        surface: "var(--surface)",
        page: "var(--page-bg)",
        neutral: {
          50: "var(--neutral-50)",
          100: "var(--neutral-100)",
          200: "var(--neutral-200)",
          300: "var(--neutral-300)",
          400: "var(--neutral-400)",
          500: "var(--neutral-500)",
          600: "var(--neutral-600)",
          700: "var(--neutral-700)",
          800: "var(--neutral-800)",
          900: "var(--neutral-900)",
        },
        accent: {
          50: "var(--accent-50)",
          100: "var(--accent-100)",
          500: "var(--accent-500)",
          600: "var(--accent-600)",
          700: "var(--accent-700)",
        },
        success: { DEFAULT: "var(--success-500)", soft: "var(--success-50)" },
        info: { DEFAULT: "var(--info-500)", soft: "var(--info-50)" },
        warning: { DEFAULT: "var(--warning-500)", soft: "var(--warning-50)" },
        error: { DEFAULT: "var(--error-500)", soft: "var(--error-50)" },
        sede: {
          ifm: "#FF8C00",
          iff: "#8B5CF6",
          ifn: "#22C55E",
          ifp: "#EF4444",
          ifi: "#3B82F6",
        },
      },
      fontFamily: {
        sans: ["var(--font-sans)"],
        mono: ["var(--font-mono)"],
      },
      fontSize: {
        display: ["28px", { lineHeight: "1.1", letterSpacing: "-0.015em" }],
        h1: ["22px", { lineHeight: "1.25", letterSpacing: "-0.01em" }],
        h2: ["17px", { lineHeight: "1.35" }],
        h3: ["15px", { lineHeight: "1.4" }],
        body: ["14px", { lineHeight: "1.5" }],
        "body-sm": ["13px", { lineHeight: "1.5" }],
        caption: ["12px", { lineHeight: "1.4" }],
        eyebrow: ["11px", { lineHeight: "1.4", letterSpacing: "0.08em" }],
      },
      borderRadius: {
        xs: "2px",
        sm: "4px",
        md: "6px",
        lg: "8px",
        xl: "12px",
        pill: "999px",
      },
      boxShadow: {
        xs: "0 1px 2px rgba(15,23,42,0.04)",
        sm: "0 1px 3px rgba(15,23,42,0.06), 0 1px 2px rgba(15,23,42,0.04)",
        md: "0 4px 6px -1px rgba(15,23,42,0.06), 0 2px 4px -2px rgba(15,23,42,0.04)",
        lg: "0 10px 15px -3px rgba(15,23,42,0.07), 0 4px 6px -4px rgba(15,23,42,0.05)",
        focus: "0 0 0 3px rgba(59,130,246,0.25)",
      },
      transitionTimingFunction: {
        "ease-out-soft": "cubic-bezier(0.16, 1, 0.3, 1)",
      },
    },
  },
  plugins: [],
};

export default config;
