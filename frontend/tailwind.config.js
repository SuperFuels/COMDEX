/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    // ← your pages & components
    "./pages/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
    "./app/**/*.{js,ts,jsx,tsx}",

    // ← include the styles folder so Tailwind picks up your custom utilities
    "./styles/**/*.{css,js,ts,jsx,tsx}"
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      colors: {
        /* Primary brand blue */
        primary: '#4A90E2',
        primaryHover: '#357ABD',

        /* Text colors */
        text: {
          DEFAULT: '#1F2937',    // dark slate
          light:   '#374151',    // medium slate
          muted:   '#6B7280',    // gray-500 for secondary text
        },

        /* Header / navbar background */
        background: {
          header: '#FFFFFF',     // pure white
          dark:   '#111827',     // deep gray for dark-mode
        },

        /* Button backgrounds */
        btn: {
          dark: '#111827',       // dark-mode primary button
        },
      },
      boxShadow: {
        dropdown: '0 4px 6px rgba(0,0,0,0.1)',
      },
    },
  },
  plugins: [],
}