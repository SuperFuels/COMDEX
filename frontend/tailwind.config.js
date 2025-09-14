/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ['class'], // ✅ one 'class' is enough
  content: [
    // Frontend app (MOST IMPORTANT so tokens like border-border are generated)
    "./frontend/**/*.{js,ts,jsx,tsx,mdx}",

    // If you also have these folders inside /frontend, keep them too:
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./styles/**/*.{css,js,ts,jsx,tsx,mdx}",

    // (Optional) catch-all if you reference components outside /frontend
    "./**/*.{js,ts,jsx,tsx,mdx}"
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      colors: {
        // shadcn-style tokens (require CSS variables defined in globals.css)
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        primaryHover: '#357ABD',
        text: {
          DEFAULT: '#1F2937',
          light: '#374151',
          muted: '#6B7280',
        },
        background: 'hsl(var(--background))',
        'border-light': '#E5E7EB',
        foreground: 'hsl(var(--foreground))',
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },
        popover: {
          DEFAULT: 'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        // 👇 These three make utilities like `border-border`, `ring-ring`, etc.
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',

        chart: {
          '1': 'hsl(var(--chart-1))',
          '2': 'hsl(var(--chart-2))',
          '3': 'hsl(var(--chart-3))',
          '4': 'hsl(var(--chart-4))',
          '5': 'hsl(var(--chart-5))',
        },
      },
      boxShadow: {
        dropdown: '0 4px 6px rgba(0,0,0,0.1)',
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },
    },
  },
  // Optional: keep a few classes no matter what (helps during refactors)
  safelist: [
    'border-border',
    'bg-background',
    'text-foreground',
  ],
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
    require('tailwindcss-animate'),
  ],
};