// components/DarkModeToggle.tsx
import { useEffect, useState } from 'react';

export function DarkModeToggle() {
  // don't read localStorage until we're in the browser
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    // now that we're definitely in the browser:
    const stored = localStorage.getItem('theme');
    const initial = stored === 'dark';
    setIsDark(initial);

    // apply the class
    document.documentElement.classList.toggle('dark', initial);
  }, []);

  useEffect(() => {
    document.documentElement.classList.toggle('dark', isDark);
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
  }, [isDark]);

  return (
    <button
      onClick={() => setIsDark(d => !d)}
      className="ml-4 text-text-light dark:text-gray-300"
    >
      {isDark ? 'Light Mode' : 'Dark Mode'}
    </button>
  );
}