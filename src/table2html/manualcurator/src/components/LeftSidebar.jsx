import React, { useState } from 'react';

export default function LeftSidebar({ tasks = [], selectedTab = 'create', onTabChange, currentTaskIdx, currentRowIdx, totalRows, onStart, onDeleteTask, isDark, textColor }) {
  const [isTasksOpen, setIsTasksOpen] = useState(false);

  const handleTaskClick = (index) => {
    if (onStart) {
      onStart(index);
    }
  };

  return (
    <aside style={{
      width: 240,
      padding: 'var(--space-7) var(--space-5)',
      boxSizing: 'border-box',
      border: `1px solid var(--color-border)`,
      background: 'var(--color-surface)',
      borderRadius: 'var(--radius-lg)',
      marginRight: 'var(--space-8)',
      height: 'fit-content',
      alignSelf: 'flex-start',
      boxShadow: 'var(--shadow-sm)',
      position: 'sticky',
      top: '32px',
      maxHeight: 'calc(100vh - 280px)',
      overflow: 'hidden'
    }}>
      {/* Current Tasks dropdown button */}
      <button
        onClick={() => setIsTasksOpen(!isTasksOpen)}
        style={{
          width: '100%',
          padding: '10px 12px',
          borderRadius: 'var(--radius-md)',
          background: 'var(--color-surface-alt)',
          color: 'var(--color-text)',
          border: '1px solid var(--color-border)',
          textAlign: 'left',
          cursor: 'pointer',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 'var(--space-5)',
          fontSize: 'var(--text-sm)',
          fontWeight: 600,
          letterSpacing: '-0.2px'
        }}
      >
        <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>Tasks</span>
        <span style={{
          transition: 'transform var(--transition-fast)',
          transform: `rotate(${isTasksOpen ? '180deg' : '0deg'})`,
          fontSize: 14,
          color: 'var(--color-text-soft)'
        }}>▾</span>
      </button>

      {/* Tasks dropdown */}
      <div style={{
        maxHeight: isTasksOpen ? `${Math.min(tasks.length * 52, 300)}px` : '0',
        overflowY: 'auto',
        overflowX: 'hidden',
        transition: 'max-height var(--transition-med)',
        marginBottom: 'var(--space-6)',
        paddingRight: isTasksOpen ? 4 : 0
      }}>
        {tasks.map((t, i) => (
          <div key={i} style={{ marginBottom: 4 }}>
            {/* Task item */}
            <div
              onClick={() => handleTaskClick(i)}
              style={{
                padding: '10px 12px',
                borderRadius: 'var(--radius-md)',
                cursor: 'pointer',
                background: currentTaskIdx === i
                  ? 'linear-gradient(90deg, rgba(36,212,83,0.18), rgba(36,212,83,0.08))'
                  : 'var(--color-surface-alt)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                transition: 'background var(--transition-fast), box-shadow var(--transition-fast)',
                border: currentTaskIdx === i
                  ? '1px solid var(--color-accent)'
                  : '1px solid var(--color-border)',
                boxShadow: currentTaskIdx === i ? '0 0 0 1px rgba(36,212,83,0.35), var(--shadow-xs)' : 'var(--shadow-xs)'
              }}
            >
              <div style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--color-text)', letterSpacing: '-0.2px', display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{
                  width: 8,
                  height: 8,
                  background: currentTaskIdx === i ? 'var(--color-accent)' : 'var(--color-border-strong)',
                  borderRadius: '50%',
                  boxShadow: currentTaskIdx === i ? '0 0 0 3px rgba(36,212,83,0.25)' : 'none'
                }} />
                {t.name}
              </div>
              <div style={{
                fontSize: 11,
                fontWeight: 500,
                color: 'var(--color-text-soft)',
                background: 'var(--color-surface)',
                padding: '2px 6px',
                borderRadius: 'var(--radius-pill)',
                border: '1px solid var(--color-border)'
              }}>
                {(t.rows || []).length} rows
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Create task button */}
      <button
        onClick={() => onTabChange && onTabChange('create')}
        className={selectedTab === 'create' ? 'btn-primary' : ''}
        style={{
          width: '100%',
          padding: '12px 14px',
          fontSize: 'var(--text-sm)',
          justifyContent: 'center',
          fontWeight: 600,
          letterSpacing: '-0.2px'
        }}
      >Create task</button>

      {/* Current task info block (moved from main view) */}
      {currentTaskIdx != null && tasks[currentTaskIdx] && (
        <div style={{
          marginTop: 'var(--space-6)',
          padding: '12px 14px 14px',
          background: 'var(--color-surface-alt)',
          border: '1px solid var(--color-border)',
          borderRadius: 'var(--radius-lg)',
          display: 'flex',
          flexDirection: 'column',
          gap: 10
        }}>
          <div style={{ fontSize: '13px', fontWeight: 700, letterSpacing: '-0.3px', color: 'var(--color-text)' }}>
            {tasks[currentTaskIdx].name}
          </div>
          {typeof currentRowIdx === 'number' && typeof totalRows === 'number' && totalRows > 0 && (
            <div style={{ fontSize: '11px', fontWeight: 500, color: 'var(--color-text-soft)', letterSpacing: '.3px' }}>
              Row {currentRowIdx + 1} of {totalRows}
            </div>
          )}
          <button
            onClick={() => onDeleteTask && onDeleteTask(currentTaskIdx)}
            style={{
              background: 'var(--color-danger)',
              color: '#fff',
              border: '1px solid var(--color-danger)',
              padding: '8px 10px',
              fontSize: '11px',
              fontWeight: 600,
              borderRadius: 'var(--radius-md)'
            }}
          >Delete Task</button>
        </div>
      )}
    </aside>
  );
}
