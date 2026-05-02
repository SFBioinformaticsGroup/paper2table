import React from 'react';

export default function LeftSidebar({
  tasks = [],
  selectedTab = 'create',
  onTabChange,
  currentTaskIdx,
  onStart,
  taskProgressMap = {},
}) {
  const handleTaskClick = (index) => { if (onStart) onStart(index); };

  return (
    <aside style={{
      width: 240,
      padding: '0 2px 0 0',
      marginRight: 'var(--space-8)',
      position: 'sticky',
      top: '32px',
      alignSelf: 'flex-start',
      display: 'flex',
      flexDirection: 'column',
      gap: '14px'
    }}>
      <div style={{
        border: '1px solid var(--color-border)',
        background: 'var(--color-surface)',
        borderRadius: 'var(--radius-lg)',
        boxShadow: 'var(--shadow-sm)',
        padding: '16px 14px 14px',
        display: 'flex',
        flexDirection: 'column',
        gap: 10,
        maxHeight: 'calc(100vh - 340px)'
      }}>
        <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: '1px', color: 'var(--color-text-faint)', padding: '0 2px' }}>CURRENT TASKS</div>
  <div style={{ flex: '1 1 auto', minHeight: 0, overflowY: 'auto', maxHeight: 320, display: 'flex', flexDirection: 'column', gap: 12 }}>
          {tasks.length === 0 && (
            <div style={{ fontSize: 12, color: 'var(--color-text-soft)', padding: '4px 2px' }}>No tasks yet</div>
          )}
          {tasks.map((t, i) => {
            const isActive = currentTaskIdx === i;
            const progressObj = t.path ? taskProgressMap[t.path] : null;
            const curated = progressObj ? progressObj.curatedCells : 0;
            const total = progressObj ? progressObj.totalCells : 0;
            const safeTotal = total > 0 ? total : (t.rows ? t.rows.reduce((acc, row) => acc + Object.keys(row || {}).filter(k => k !== '_metadata').length, 0) : 0);
            const percentage = safeTotal > 0 ? (curated / safeTotal) * 100 : 0;
            return (
              <button
                key={i}
                onClick={() => handleTaskClick(i)}
                style={{
                  width: '100%',
                  textAlign: 'left',
                  padding: '10px 12px 10px',
                  borderRadius: 'var(--radius-md)',
                  background: isActive ? 'linear-gradient(90deg, rgba(36,212,83,0.18), rgba(36,212,83,0.08))' : 'var(--color-surface-alt)',
                  border: isActive ? '1px solid var(--color-accent)' : '1px solid var(--color-border)',
                  cursor: 'pointer',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'stretch',
                  gap: 8,
                  boxShadow: isActive ? '0 0 0 1px rgba(36,212,83,0.35), var(--shadow-xs)' : 'var(--shadow-xs)'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ width: 8, height: 8, background: isActive ? 'var(--color-accent)' : 'var(--color-border-strong)', borderRadius: '50%', boxShadow: isActive ? '0 0 0 3px rgba(36,212,83,0.25)' : 'none', flexShrink: 0 }} />
                  <span style={{ fontSize: 12, fontWeight: 600, letterSpacing: '-0.2px', color: 'var(--color-text)', flex: 1, minWidth: 0, whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>{t.name}</span>
                  <span style={{ fontSize: 10, fontWeight: 600, color: 'var(--color-text-soft)', background: 'var(--color-surface)', padding: '2px 6px', borderRadius: 'var(--radius-pill)', border: '1px solid var(--color-border)' }}>
                    {curated}/{safeTotal}
                  </span>
                </div>
                <div style={{ position: 'relative', height: 5, borderRadius: 3, background: 'var(--color-surface)', border: '1px solid var(--color-border)' }}>
                  <div style={{ position: 'absolute', top: 0, left: 0, height: '100%', width: `${percentage}%`, background: 'var(--color-accent)', borderRadius: 2, transition: 'width 0.35s ease' }} />
                </div>
              </button>
            );
          })}
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <button
          onClick={() => onTabChange && onTabChange('create')}
          className={selectedTab === 'create' ? 'btn-primary' : ''}
          style={{
            width: '100%',
            padding: '12px 14px',
            fontSize: '13px',
            fontWeight: 600,
            letterSpacing: '-0.2px',
            borderRadius: 'var(--radius-md)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 12
          }}
        >
          <span style={{ flex: 1, textAlign: 'left' }}>Create new task</span>
          <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: 22,
            height: 22,
            borderRadius: '50%',
            fontSize: 16,
            fontWeight: 600,
            background: selectedTab === 'create' ? 'rgba(255,255,255,0.2)' : 'var(--color-surface)',
            color: selectedTab === 'create' ? '#fff' : 'var(--color-text-soft)',
            boxShadow: 'inset 0 0 0 1px var(--color-border)'
          }}>+</span>
        </button>
      </div>
    </aside>
  );
}
// Simplified; removed progress & tips per new spec; delete button moved into task view banner.
