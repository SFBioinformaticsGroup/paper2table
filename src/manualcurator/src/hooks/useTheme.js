import { useEffect, useState } from 'react';

const STORAGE_KEY = 'p2t_theme';

export default function useTheme(initial = 'dark') {
  const [theme, setTheme] = useState(() => {
    try { return localStorage.getItem(STORAGE_KEY) || initial; } catch { return initial; }
  });

  useEffect(() => {
    try { localStorage.setItem(STORAGE_KEY, theme); } catch {}
    // Apply data-theme attribute to documentElement for CSS variable scoping
    try {
      const root = document.documentElement;
      root.setAttribute('data-theme', theme);
    } catch {}
  }, [theme]);

  const isDark = theme === 'dark';
  const textColor = isDark ? '#fff' : '#111';

  return { theme, setTheme, isDark, textColor };
}
