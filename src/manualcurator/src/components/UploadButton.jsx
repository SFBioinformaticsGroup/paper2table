import React from 'react';
import { getButtonStyle } from './ui';

export default function UploadButton({ onFile, label = 'Import table (JSON)', filename, isDark = true, textColor = isDark ? '#fff' : '#111' }) {
  const style = getButtonStyle(isDark);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6, minHeight: 60, justifyContent: 'center' }}>
      <div style={{ position: 'relative' }}>
        <label style={style}>
          <input type="file" accept="application/json" onChange={onFile} style={{ display: 'none' }} />
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
            <path d="M12 3v12" stroke={textColor} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            <path d="M8 7l4-4 4 4" stroke={textColor} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            <path d="M20 21H4a2 2 0 0 1-2-2V15" stroke={textColor} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          <span>{label}</span>
        </label>

        {/* filename positioned slightly below without affecting button layout */}
        <div style={{ position: 'absolute', left: 0, right: 0, top: '64px', textAlign: 'left', paddingLeft: 4 }}>
          <span style={{ color: isDark ? 'rgba(255,255,255,0.8)' : 'rgba(0,0,0,0.7)', fontSize: 12, visibility: filename ? 'visible' : 'hidden', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{filename || ''}</span>
        </div>
      </div>
    </div>
  );
}
