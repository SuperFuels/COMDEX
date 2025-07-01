// frontend/components/DarkModeToggle.tsx
"use client"

import { useEffect, useState } from 'react';

export function DarkModeToggle() {
  const [isDark, setDark] = useState(
    () => typeof window !== 'undefined' && localStorage.theme === 'dark'
  );

  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add('dark');
      localStorage.theme = 'dark';
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.theme = 'light';
    }
  }, [isDark]);

  return (
    <button
      onClick={() => setDark(d => !d)}
      className="ml-2 text-text hover:text-primary transition"
      aria-label="Toggle dark mode"
    >
      {isDark ? '☀️ Light' : '🌙 Dark'}
    </button>
  );
}