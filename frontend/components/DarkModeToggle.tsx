'use client';

import { useEffect, useState } from 'react';
import { Moon, Sun } from 'lucide-react';

export function DarkModeToggle() {
  const [dark, setDark] = useState(false);

  // initialize from localStorage / system
  useEffect(() => {
    const root = document.documentElement;
    const saved = localStorage.getItem('theme');
    const prefers = window.matchMedia?.('(prefers-color-scheme: dark)').matches;
    const enable = saved ? saved === 'dark' : prefers;
    root.classList.toggle('dark', enable);
    setDark(enable);
  }, []);

  function toggle() {
    const next = !dark;
    setDark(next);
    const root = document.documentElement;
    root.classList.toggle('dark', next);
    localStorage.setItem('theme', next ? 'dark' : 'light');
  }

  return (
    <button
      onClick={toggle}
      className="inline-flex items-center gap-2 px-3 py-1 border rounded-lg text-sm hover:bg-gray-100 dark:hover:bg-gray-800"
      aria-label="Toggle theme"
      title="Toggle dark mode"
    >
      {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
      <span className="hidden sm:inline">{dark ? 'Light' : 'Dark'}</span>
    </button>
  );
}