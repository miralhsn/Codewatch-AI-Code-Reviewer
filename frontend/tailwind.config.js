/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#080A0F",
          900: "#0B0E14",
          800: "#12161F",
          700: "#1A1F2C",
          600: "#232938",
          border: "#252B3A",
        },
        text: {
          primary: "#E6E9EF",
          secondary: "#9AA3B8",
          muted: "#6B7386",
        },
        signal: {
          teal: "#2DD4BF",
          violet: "#8B7CF6",
        },
        severity: {
          critical: "#F2545B",
          high: "#F5A623",
          medium: "#E0C341",
          low: "#4FD1A5",
          info: "#7C93FF",
        },
        diff: {
          add: "#2DD4BF",
          addBg: "rgba(45, 212, 191, 0.08)",
          remove: "#F2545B",
          removeBg: "rgba(242, 84, 91, 0.08)",
        },
      },
      fontFamily: {
        display: ["var(--font-space-grotesk)", "sans-serif"],
        body: ["var(--font-ibm-plex-sans)", "sans-serif"],
        mono: ["var(--font-jetbrains-mono)", "monospace"],
      },
      boxShadow: {
        panel: "0 1px 0 0 rgba(255,255,255,0.03) inset, 0 8px 24px -12px rgba(0,0,0,0.6)",
      },
      borderRadius: {
        xl2: "1.25rem",
      },
      keyframes: {
        "pulse-dot": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.35" },
        },
        "slide-up": {
          "0%": { opacity: "0", transform: "translateY(6px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "pulse-dot": "pulse-dot 1.6s ease-in-out infinite",
        "slide-up": "slide-up 0.25s ease-out",
      },
    },
  },
  plugins: [],
};
