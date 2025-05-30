import { useEffect, useState } from 'react';

export function DarkModeToggle() {
  const [isDark, setDark] = useState(
    () => localStorage.theme === 'dark' || false
  );

  useEffect(() => {
    document.documentElement.classList.toggle('dark', isDark);
    localStorage.theme = isDark ? 'dark' : 'light';
  }, [isDark]);

  return (
    <button
      onClick={() => setDark(d => !d)}
      className="ml-4 text-text-light dark:text-gray-300"
    >
      {isDark ? 'Light Mode' : 'Dark Mode'}
    </button>
  );
}
