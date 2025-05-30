// tailwind.config.js
export default {
  darkMode: 'class',
  content: [
    "./pages/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
    "./app/**/*.{js,ts,jsx,tsx}"
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
        },

        /* Header / navbar background */
        background: {
          header: '#F3F4F6',     // light gray (ChatGPT-style)
          dark:   '#111827',     // deep gray for dark-mode header
        },

        /* Button backgrounds */
        btn: {
          dark: '#111827',       // dark-mode primary button
        }
      },
      boxShadow: {
        dropdown: '0 4px 6px rgba(0,0,0,0.1)',
      },
    },
  },
  plugins: [],
}