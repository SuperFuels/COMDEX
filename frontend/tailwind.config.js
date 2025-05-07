/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
    "./app/**/*.{js,ts,jsx,tsx}"
  ],
  theme: {
    extend: {
      fontFamily: {
        // Use Inter throughout
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      colors: {
        // Your softer blue tokens
        primary: '#4A90E2',
        primaryHover: '#357ABD',
      },
    },
  },
  plugins: [],
}

