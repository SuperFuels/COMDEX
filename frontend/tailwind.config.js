/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: "class",
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./styles/**/*.{css,js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
    "./hooks/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/**/*.{js,ts,jsx,tsx,mdx}", // keep only if exists
  ],
  theme: {
    extend: {
      fontFamily: {
        // global type: Canva Sans
        sans: ['"Canva Sans"', "system-ui", "sans-serif"],
      },
      colors: {
        // === your direct palette ===
        text: {
          DEFAULT: "#4a4a4a", // light-mode “ink”
        },

        // background is driven by CSS var so dark mode works:
        // :root { --background: ... } / .dark { --background: ... }
        background: "hsl(var(--background))",

        // simple button tokens you can use explicitly if you want
        button: {
          dark: "#4a4a4a",
          light: "#a1a1a1",
        },

        // === shadcn-style tokens mapped to CSS vars ===
        primary: {
          // keep this neutral + simple for now; used by bg-primary, text-primary, etc.
          DEFAULT: "#4a4a4a",
          foreground: "#ffffff",
        },

        foreground: "hsl(var(--foreground))",

        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },

        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },

        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },

        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },

        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },

        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },

        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",

        chart: {
          1: "hsl(var(--chart-1))",
          2: "hsl(var(--chart-2))",
          3: "hsl(var(--chart-3))",
          4: "hsl(var(--chart-4))",
          5: "hsl(var(--chart-5))",
        },
      },

      boxShadow: {
        dropdown: "0 4px 6px rgba(0,0,0,0.1)",
      },

      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
    },
  },

  safelist: [
    "border-border",
    "bg-background",
    "text-foreground",
    "bg-primary",
    "text-primary",
  ],

  plugins: [
    require("@tailwindcss/forms"),
    // tailwindcss-animate removed to fix build error
  ],
};