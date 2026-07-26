import type { Config } from "tailwindcss"

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: "#2D6A4F",
          50: "#D8F3DC",
          100: "#B7E4C7",
          200: "#95D5B2",
          300: "#74C69D",
          400: "#52B788",
          500: "#40916C",
          600: "#2D6A4F",
          700: "#1B4332",
          800: "#081C15",
          900: "#040B07",
        },
        "muted-foreground": "#6B7280",
        "foreground": "#1C1917",
        "card-foreground": "#1C1917",
        "accent-foreground": "#1B4332",
        "primary-foreground": "#FFFFFF",
        accent: {
          warm: "#F5E6D3",
          light: "#FFF8F0",
          DEFAULT: "#E8D5C4",
        },
        glass: {
          light: "rgba(255, 255, 255, 0.7)",
          medium: "rgba(255, 255, 255, 0.5)",
          dark: "rgba(255, 255, 255, 0.15)",
          border: "rgba(255, 255, 255, 0.3)",
        },
        surface: {
          DEFAULT: "#FAF7F2",
          light: "#FFFDF9",
          dark: "#F0EBE3",
        },
      },
      fontFamily: {
        sans: ["Inter", "SF Pro Display", "system-ui", "sans-serif"],
      },
      backdropBlur: {
        xs: "2px",
      },
      boxShadow: {
        glass: "0 8px 32px 0 rgba(31, 38, 135, 0.07)",
        "glass-hover": "0 8px 32px 0 rgba(31, 38, 135, 0.12)",
        card: "0 2px 15px -3px rgba(0, 0, 0, 0.07), 0 10px 20px -2px rgba(0, 0, 0, 0.04)",
        "card-hover": "0 10px 40px -10px rgba(45, 106, 79, 0.2)",
      },
      animation: {
        "fade-in": "fadeIn 0.5s ease-out",
        "slide-up": "slideUp 0.6s ease-out",
        "float": "float 6s ease-in-out infinite",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0", transform: "translateY(10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(30px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-10px)" },
        },
      },
    },
  },
  plugins: [],
}
export default config
