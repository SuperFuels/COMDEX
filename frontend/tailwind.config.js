/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./pages/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
    "./app/**/*.{js,ts,jsx,tsx}",
    "./styles/**/*.{css,js,ts,jsx,tsx}"  // ✅ Required for global CSS or CSS modules
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      colors: {
        primary: '#4A90E2',
        primaryHover: '#357ABD',
        text: {
          DEFAULT: '#1F2937',
          light: '#374151',
          muted: '#6B7280',
        },
        background: {
          header: '#FFFFFF',
          dark: '#111827',
        },
        'border-light': '#E5E7EB',
      },
      boxShadow: {
        dropdown: '0 4px 6px rgba(0,0,0,0.1)',
      },
    },
  },
  plugins: [
  require('@tailwindcss/forms'),
  require('@tailwindcss/typography'),
],
}