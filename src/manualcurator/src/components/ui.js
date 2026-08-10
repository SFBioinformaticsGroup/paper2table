export function getButtonStyle(isDark = true) {
  return {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    background: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.04)',
    padding: '8px 12px',
    borderRadius: 10,
    cursor: 'pointer',
    border: isDark ? '1px solid rgba(255,255,255,0.04)' : '1px solid rgba(0,0,0,0.08)',
    color: isDark ? '#fff' : '#111',
    fontWeight: 700,
    height: 60,
    lineHeight: 1,
    boxSizing: 'border-box',
  };
}
