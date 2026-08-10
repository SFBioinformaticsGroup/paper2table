import React from 'react';
import { getButtonStyle } from './ui';

export default function ExportButton({ onClick, label = 'Export table (JSON)', disabled = false, isDark = true, textColor = isDark ? '#fff' : '#111' }) {
  const style = { ...getButtonStyle(isDark), opacity: disabled ? 0.45 : 1, cursor: disabled ? 'not-allowed' : 'pointer' };
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6, minHeight: 60, justifyContent: 'center' }}>
      <button type="button" onClick={onClick} style={style} disabled={disabled}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <path d="M12 21V9" stroke={textColor} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          <path d="M8 15l4 4 4-4" stroke={textColor} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          <path d="M20 3H4a2 2 0 0 0-2 2v4" stroke={textColor} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
        <span>{label}</span>
      </button>
    </div>
  );
}
