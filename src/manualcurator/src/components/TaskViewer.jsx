import React from 'react';
import RenderCell from './RenderCell';

export default function TaskViewer({
  currentTask,
  currentRowIdx,
  currentRow,
  totalRows,
  progress,
  onPrev,
  onNext,
  onExit,
  onCreateCurationTask,
  onSaveCurated,
  onSelect,
  isDark,
  textColor,
  agreementColor,
  minAgreement,
}) {
  return (
    <section>
      {/* Navigation panel with metadata */}
      <div style={{ 
        display: 'flex', 
        alignItems: 'center',
        gap: 20,
        padding: 16,
        background: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.03)',
        borderRadius: 8,
        marginBottom: 20
      }}>
        {/* Metadata */}
        <div style={{ 
          fontSize: 13,
          color: isDark ? 'rgba(255,255,255,0.6)' : 'rgba(0,0,0,0.6)',
          display: 'flex',
          gap: 16,
          marginRight: 'auto'
        }}>
          <span>Source: {currentRow._metadata?.sourceFile || 'Unknown'}</span>
          <span>Table: {currentRow._metadata?.tableIndex || 'Unknown'}</span>
          <span>Row: {currentRow._metadata?.originalIndex || 'Unknown'}</span>
        </div>

        {/* Navigation buttons */}
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            onClick={onPrev}
            disabled={currentRowIdx === 0}
            style={{
              padding: '8px 16px',
              borderRadius: 6,
              border: 'none',
              background: isDark ? 'rgba(255,255,255,0.06)' : '#eee',
              color: textColor,
              cursor: currentRowIdx === 0 ? 'not-allowed' : 'pointer',
              opacity: currentRowIdx === 0 ? 0.5 : 1
            }}
          >
            Previous
          </button>
          <button
            onClick={onNext}
            disabled={currentRowIdx >= totalRows - 1}
            style={{
              padding: '8px 16px',
              borderRadius: 6,
              border: 'none',
              background: isDark ? 'rgba(255,255,255,0.06)' : '#eee',
              color: textColor,
              cursor: currentRowIdx >= totalRows - 1 ? 'not-allowed' : 'pointer',
              opacity: currentRowIdx >= totalRows - 1 ? 0.5 : 1
            }}
          >
            Next
          </button>
        </div>
      </div>

      {/* Row content */}
      <div style={{
        padding: 20,
        background: isDark ? 'rgba(255,255,255,0.02)' : 'rgba(0,0,0,0.02)',
        borderRadius: 8
      }}>
        {currentRow ? (
          Object.keys(currentRow).length ? (
            Object.keys(currentRow).map((col) => (
              <div key={col} style={{ marginBottom: 10 }}>
                <div style={{ fontSize: 12, color: isDark ? 'rgba(255,255,255,0.75)' : '#444' }}>{col}</div>
                <div style={{ marginTop: 6 }}>
                  <RenderCell
                    value={currentRow[col]}
                    selectedProp={undefined}
                    onChange={(val) => onSelect(col, val)}
                    minAgreement={minAgreement}
                    agreementColor={agreementColor}
                    isDark={isDark}
                    textColor={textColor}
                  />
                </div>
              </div>
            ))
          ) : (
            <div style={{ color: isDark ? 'rgba(255,255,255,0.7)' : '#444' }}>No columns in this row.</div>
          )
        ) : (
          <div style={{ color: isDark ? 'rgba(255,255,255,0.7)' : '#444' }}>No row data.</div>
        )}
      </div>
    </section>
  );
}
