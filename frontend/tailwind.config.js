/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class', // enable class-based dark mode
  content: [
    // look inside pages, components, and app folders:
    "./pages/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
    "./app/**/*.{js,ts,jsx,tsx}",

    // make sure Tailwind also scans your custom CSS files under /styles:
    "./styles/**/*.{css,js,ts,jsx,tsx}"
  ],
  theme: {
    extend: {
      fontFamily: {
        // Your primary sans family:
        sans: ['Inter', 'system-ui', 'sans-serif'],
        // Explicit monospace family (for <pre> code blocks):
        mono: ['"Fira Code"', 'Menlo', 'Monaco', 'Courier New', 'monospace'],
      },
      colors: {
        /* ──────────────── Brand & Primary ──────────────── */
        // Primary brand blue
        primary: '#4A90E2',
        primaryHover: '#357ABD',

        /* ──────────────── Text Palette ──────────────── */
        text: {
          DEFAULT: '#1F2937',   // dark slate
          light:   '#374151',   // medium slate
        },

        /* ──────────────── Backgrounds ──────────────── */
        background: {
          header: '#F3F4F6',    // light gray (ChatGPT-style header)
          dark:   '#111827',    // deep gray for dark-mode header
        },

        /* ──────────────── Button Backgrounds ──────────────── */
        btn: {
          dark: '#111827',      // dark-mode primary button
        },

        /* ──────────────── Chart/Code Highlight Colors ──────────────── */
        // These match "text-blue-600", "text-green-600", etc., but you can reference
        // them by name (e.g. "blue": {600: '#2563eb'} if you want full palette).
        // You still have access to default Tailwind blues/reds/greens/etc.
      },
      boxShadow: {
        dropdown: '0 4px 6px rgba(0, 0, 0, 0.1)', // for dropdown menus
      },
    },
  },
  plugins: [],
}