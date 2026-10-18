'use client';

import { useEffect, useState } from 'react';
import { Moon, Sun } from 'lucide-react';

export function DarkModeToggle() {
  const [dark, setDark] = useState(false);

  // Theme is a content-free preference. Follow the operating-system setting
  // on each launch without creating browser-authoritative state.
  useEffect(() => {
    const root = document.documentElement;
    const prefersDark = window.matchMedia?.('(prefers-color-scheme: dark)').matches;

    const enableDark = Boolean(prefersDark);
    root.classList.toggle('dark', enableDark);
    setDark(enableDark);
  }, []);

  function toggle() {
    const next = !dark;
    setDark(next);
    const root = document.documentElement;
    root.classList.toggle('dark', next);
  }

  return (
    <button
      onClick={toggle}
      aria-label={dark ? 'Switch to light mode' : 'Switch to dark mode'}
      title={dark ? 'Switch to light mode' : 'Switch to dark mode'}
      className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-border bg-background/90 text-text shadow-sm transition hover:bg-button-light/60 dark:hover:bg-button-dark/70"
    >
      {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
    </button>
  );
}
