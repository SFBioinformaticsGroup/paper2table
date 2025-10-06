import React from 'react';
import UploadButton from './UploadButton';
import ExportButton from './ExportButton';
import { getButtonStyle } from './ui';

export default function TopControls({ onFile, filename, onExport, exportDisabled, minAgreement, setMinAgreement, isDark, textColor }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 15 }}>
      <UploadButton onFile={onFile} filename={filename} isDark={isDark} textColor={textColor} />
      <ExportButton onClick={onExport} disabled={exportDisabled} isDark={isDark} textColor={textColor} />

      <div style={{ display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6, minHeight: 60, justifyContent: 'center' }}>
          <div style={{ ...getButtonStyle(isDark), padding: '8px 12px', alignItems: 'center' }}>
            <div style={{ display: 'flex', flexDirection: 'column', marginRight: 8 }}>
              <label style={{ fontSize: 12, color: isDark ? 'rgba(255,255,255,0.8)' : 'rgba(0,0,0,0.7)', marginBottom: 6 }}>
                Min agreement
              </label>
              <input
                className="min-agreement-range"
                type="range"
                min="0"
                max="100"
                value={minAgreement}
                onChange={(e) => setMinAgreement(Number(e.target.value))}
                style={{ ['--val']: `${minAgreement}%`, width: 160 }}
              />
            </div>
            <div style={{ fontWeight: 700, color: textColor, minWidth: 36, textAlign: 'right' }}>
              {minAgreement}%
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
