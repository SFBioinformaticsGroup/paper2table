import React from 'react';
import { getButtonStyle } from './ui';

export default function ControlsPanel({ isDark, setTheme }) {
  const activeOutline = '0 0 0 2px var(--color-accent)';
  return (
    <div
      style={{
        background: 'var(--color-surface-alt)',
        border: '1px solid var(--color-border)',
        padding: '8px 10px 10px',
        borderRadius: 'var(--radius-lg)',
        display: 'inline-flex',
        flexDirection: 'column',
        gap: '6px'
      }}
    >
      <div style={{ fontSize: 9, fontWeight: 600, letterSpacing: '.7px', color: 'var(--color-text-faint)' }}>THEME</div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        {/* Light theme swatch */}
        <button
          type="button"
          onClick={() => setTheme('light')}
            aria-label="Set light theme"
            title="Light theme"
            style={{
            width: 26,
            height: 26,
            borderRadius: '50%',
            border: '1px solid var(--color-border)',
            background: '#fff',
            boxShadow: isDark ? 'none' : activeOutline,
            cursor: 'pointer',
            position: 'relative',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}
        >
          {/* optional inner indicator */}
          {!isDark && <div style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--color-accent)' }} />}
        </button>
        {/* Dark theme swatch */}
        <button
          type="button"
          onClick={() => setTheme('dark')}
          aria-label="Set dark theme"
          title="Dark theme"
          style={{
            width: 26,
            height: 26,
            borderRadius: '50%',
            border: '1px solid var(--color-border)',
            background: '#111',
            boxShadow: isDark ? activeOutline : 'none',
            cursor: 'pointer',
            position: 'relative',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}
        >
          {isDark && <div style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--color-accent)' }} />}
        </button>
      </div>
    </div>
  );
}
