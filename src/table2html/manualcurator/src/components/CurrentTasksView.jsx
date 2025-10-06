import React, { useState, useEffect } from 'react';
import RenderCell from './RenderCell';
import ExportButton from './ExportButton';
import { logCurationAction, getTaskLog, clearTaskLog, getCuratedFiles, getProgress, resetCurated, exportCurated, getOriginalSummary } from '../utils/api';

export default function CurrentTasksView({
  currentTask,
  currentTaskIdx,
  currentRowIdx,
  currentRow,
  totalRows,
  onPrev,
  onNext,
  onSelect,
  onDeleteTask,
  onUpdateCurated,
  onResetSelections,
  onShuffleTaskRows,
  currentSelections,
  isDark,
  textColor,
}) {
  const [curationMode, setCurationMode] = useState('row');
  const [currentCellIdx, setCurrentCellIdx] = useState(0);
  const [taskLog, setTaskLog] = useState([]);
  const [isTaskFinished, setIsTaskFinished] = useState(false);
  const [taskProgress, setTaskProgress] = useState(0);
  const [curatedCellsCount, setCuratedCellsCount] = useState(0);
  const [totalCellsCount, setTotalCellsCount] = useState(0);
  const [originalSummary, setOriginalSummary] = useState([]);
  const [minAgreement, setMinAgreement] = useState(0); // threshold slider
  const [isResetting, setIsResetting] = useState(false);
  const lastCuratedRef = React.useRef(0);
  const stableTotalRef = React.useRef(null);

  console.log('=== RENDER ===', { isTaskFinished, currentTask: currentTask?.name });

  useEffect(() => {
    if (currentTask?.path) {
      loadTaskLog();
      initializeTotalCells();
      calculateTaskProgress();
      loadOriginalSummary();
    }
  }, [currentTask?.path]);

  useEffect(() => {
    setCurrentCellIdx(0);
    setTaskLog([]);
    setIsTaskFinished(false);
    setTaskProgress(0);
    setCuratedCellsCount(0);
    setTotalCellsCount(0);
  }, [currentTask?.path]);

  const initializeTotalCells = () => {
    if (!currentTask || !currentTask.rows) return;
    // Calcular solo una vez por task
    let total = 0;
    for (const row of currentTask.rows) {
      if (!row) continue;
      const keys = Object.keys(row).filter(k => k !== '_metadata');
      total += keys.length; // Cada clave es una celda lógica
    }
    stableTotalRef.current = total;
    setTotalCellsCount(total);
    console.log('[Progress] Total estable de celdas (memorized):', total);
  };

  const loadTaskLog = async () => {
    try {
      const logData = await getTaskLog(currentTask.path);
      setTaskLog(logData.entries || []);
    } catch (err) {
      console.error('Error loading task log:', err);
      setTaskLog([]);
    }
  };

  const calculateTaskProgress = async () => {
    if (!currentTask?.path) return;
    try {
      const { curatedCells, totalCells, progress } = await getProgress(currentTask.path);
      if (curatedCells < lastCuratedRef.current) {
        console.warn('[Progress] curatedCells menor que previo (server). Manteniendo anterior.', { previous: lastCuratedRef.current, computed: curatedCells });
      } else {
        lastCuratedRef.current = curatedCells;
      }
      setCuratedCellsCount(Math.max(curatedCells, lastCuratedRef.current));
      setTotalCellsCount(totalCells);
      setTaskProgress(progress);
      console.log('[Progress] Server =>', { curatedCells, totalCells, progress });
    } catch (err) {
      console.error('Error fetching server progress:', err);
    }
  };

  const handleResetTask = async () => {
    try {
      setIsResetting(true);
      // Reset curated files first
      await resetCurated(currentTask.path);
      // Clear task log
      await clearTaskLog(currentTask.path);
      setIsTaskFinished(false);
      setTaskLog([]);
      setCurrentCellIdx(0);
      setTaskProgress(0);
      setCuratedCellsCount(0);
      setTotalCellsCount(0);
      lastCuratedRef.current = 0;
      // Reset selections
      if (onResetSelections) {
        onResetSelections();
      }
      // Re-mezclar filas para comenzar aleatoriamente de nuevo
      if (onShuffleTaskRows) {
        onShuffleTaskRows();
      }
      // Recalcular progreso (debería ser 0)
      setTimeout(() => {
        initializeTotalCells();
        calculateTaskProgress().finally(() => setIsResetting(false));
      }, 200);
    } catch (err) {
      console.error('Error resetting task:', err);
      setIsResetting(false);
    }
  };

  const loadOriginalSummary = async () => {
    try {
      if (!currentTask?.path) return;
      const data = await getOriginalSummary(currentTask.path);
      setOriginalSummary(data.files || []);
    } catch (err) {
      console.error('Error loading original summary:', err);
      setOriginalSummary([]);
    }
  };

  if (!currentTask || !currentRow || totalRows === 0) {
    return (
      <div style={{ padding: '20px', textAlign: 'center', color: textColor }}>
        <p>Loading task data...</p>
      </div>
    );
  }

  const columns = Object.keys(currentRow).filter(key => key !== '_metadata');
  const totalCells = columns.length;
  const isTaskComplete = totalCellsCount > 0 && curatedCellsCount >= totalCellsCount;

  // Auto marcar finalización cuando todas las celdas están curadas
  useEffect(() => {
    // Evitar marcar completo si totalCellsCount aún no está inicializado (>0) tras un reset
    if (totalCellsCount === 0) return;
    if (isTaskComplete && !isTaskFinished) {
      console.log('[Completion] Marking task finished via progress effect');
      setIsTaskFinished(true);
    }
  }, [isTaskComplete, isTaskFinished, totalCellsCount]);

  const handleCellNext = async () => {
    console.log('=== CELL NEXT ===');
    
    const cellKey = columns[currentCellIdx];
    const cellValue = currentRow[cellKey];
    const metadata = currentRow._metadata || {};
    
  const isLastCell = currentRowIdx >= totalRows - 1 && currentCellIdx >= totalCells - 1;
  console.log('Is last cell?', isLastCell);
    
    const logEntry = {
      sourceFile: metadata.sourceFile || 'unknown',
      tableIndex: metadata.tableIndex || 0,
      page: metadata.page || 1,
      key: cellKey,
      value: cellValue,
      timestamp: new Date().toISOString(),
      mode: 'cell',
      rowIndex: currentRowIdx,
      cellIndex: currentCellIdx
    };
    
    try {
      await logCurationAction(currentTask.path, logEntry);
      await loadTaskLog();
      
      // Update curated file with current cell selection
      if (onUpdateCurated && currentSelections && currentSelections[cellKey]) {
        const originalIndex = currentRow._metadata?.originalIndex ?? currentRowIdx;
        const sourceFile = currentRow._metadata?.sourceFile;
        await onUpdateCurated(originalIndex, { [cellKey]: currentSelections[cellKey] }, sourceFile);
        // Recalculate progress after update
        setTimeout(() => calculateTaskProgress(), 500);
      }
      
      // Ya no se marca finalización inmediata aquí; se hará vía efecto de progreso real.
    } catch (err) {
      console.error('Error logging cell action:', err);
    }

    if (currentCellIdx < totalCells - 1) {
      setCurrentCellIdx(currentCellIdx + 1);
    } else if (currentRowIdx < totalRows - 1) {
      onNext();
      setCurrentCellIdx(0);
    }
  };

  const handleRowNext = async () => {
    console.log('=== ROW NEXT ===');
    
  const isLastRow = currentRowIdx >= totalRows - 1;
  console.log('Is last row?', isLastRow);
    
    const metadata = currentRow._metadata || {};
    const cellEntries = columns.map((cellKey, cellIndex) => ({
      sourceFile: metadata.sourceFile || 'unknown',
      tableIndex: metadata.tableIndex || 0,
      page: metadata.page || 1,
      key: cellKey,
      value: currentRow[cellKey],
      timestamp: new Date().toISOString(),
      mode: 'row',
      rowIndex: currentRowIdx,
      cellIndex: cellIndex
    }));
    
    try {
      for (const entry of cellEntries) {
        await logCurationAction(currentTask.path, entry);
      }
      await loadTaskLog();
      
      // Build full row selections including untouched fields so blanks also become curated
      if (onUpdateCurated) {
        const originalIndex = currentRow._metadata?.originalIndex ?? currentRowIdx;
        const sourceFile = currentRow._metadata?.sourceFile;
        const fullRowSelections = {};
        columns.forEach(colKey => {
          if (currentSelections && Object.prototype.hasOwnProperty.call(currentSelections, colKey)) {
            fullRowSelections[colKey] = currentSelections[colKey];
          } else {
            const cell = currentRow[colKey];
            // Infer value: if array of options -> first option.value, if curated object -> its value, else raw primitive (could be empty string)
            if (Array.isArray(cell)) {
              if (cell.length && typeof cell[0] === 'object' && cell[0] && 'value' in cell[0]) {
                fullRowSelections[colKey] = cell[0].value;
              } else {
                fullRowSelections[colKey] = '';
              }
            } else if (cell && typeof cell === 'object' && cell.curated === true) {
              fullRowSelections[colKey] = cell.value;
            } else {
              fullRowSelections[colKey] = cell === undefined || cell === null ? '' : cell;
            }
          }
        });
        await onUpdateCurated(originalIndex, fullRowSelections, sourceFile);
        // Recalculate progress after update
        setTimeout(() => calculateTaskProgress(), 500);
      }
      
      // No marcar finalización inmediata; depender del progreso consolidado.
    } catch (err) {
      console.error('Error logging row action:', err);
    }
    
    onNext();
    setCurrentCellIdx(0);
  };

  const handleCellPrev = () => {
    if (currentCellIdx > 0) {
      setCurrentCellIdx(currentCellIdx - 1);
    } else if (currentRowIdx > 0) {
      onPrev();
      setCurrentCellIdx(totalCells - 1);
    }
  };

  // Ya no se reemplaza toda la vista al terminar; se muestra banner inline

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-8)' }}>
      {/* Task header removed (now in sidebar).*/}

      {/* Progress / Summary Panel */}
  <div className="panel" style={{ padding: 'var(--space-7)', display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
        {/* Original files summary panel */}
        {originalSummary.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
            <div style={{ fontSize: '11px', fontWeight: 600, letterSpacing: '1px', color: 'var(--color-text-faint)' }}>SOURCE FILES</div>
            <div style={{ display: 'grid', gap: 'var(--space-4)', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))' }}>
              {originalSummary.map(file => {
                const meta = Array.isArray(file.metadataRows) && file.metadataRows.length ? file.metadataRows[0] : null;
                return (
                <div key={file.filename} style={{
                  padding: '10px 12px',
                  border: '1px solid var(--color-border)',
                  borderRadius: 'var(--radius-md)',
                  background: 'var(--color-surface-alt)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 6,
                  boxShadow: 'var(--shadow-xs)'
                }}>
                  <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text)', wordBreak: 'break-all', letterSpacing: '-0.2px' }}>{file.filename}</div>
                  {meta && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 4, fontSize: 10, lineHeight: 1.4, color: 'var(--color-text-soft)' }}>
                      {meta.authors && <div><strong style={{ fontWeight:600, color:'var(--color-text-faint)' }}>Authors:</strong> {meta.authors}</div>}
                      {meta.year && <div><strong style={{ fontWeight:600, color:'var(--color-text-faint)' }}>Year:</strong> {meta.year}</div>}
                      {meta.journal && <div><strong style={{ fontWeight:600, color:'var(--color-text-faint)' }}>Journal:</strong> {meta.journal}</div>}
                      {meta.volume && <div style={{ display:'inline-flex', gap:6 }}>
                        <span><strong style={{ fontWeight:600, color:'var(--color-text-faint)' }}>Vol:</strong> {meta.volume}</span>
                        {meta.issue && <span><strong style={{ fontWeight:600, color:'var(--color-text-faint)' }}>Issue:</strong> {meta.issue}</span>}
                        {meta.pages && <span><strong style={{ fontWeight:600, color:'var(--color-text-faint)' }}>Pages:</strong> {meta.pages}</span>}
                      </div>}
                      {meta.doi && <div><strong style={{ fontWeight:600, color:'var(--color-text-faint)' }}>DOI:</strong> {meta.doi}</div>}
                      {meta.publisher && <div><strong style={{ fontWeight:600, color:'var(--color-text-faint)' }}>Publisher:</strong> {meta.publisher}</div>}
                    </div>
                  )}
                  {!meta && file.citation && (
                    <div style={{ fontSize: '11px', lineHeight: 1.35, color: 'var(--color-text-soft)', maxHeight: 56, overflow: 'hidden' }}>{file.citation}</div>
                  )}
                  {(file.tablesCount !== undefined || file.rowsCount !== undefined) && (
                    <div style={{ fontSize: '11px', color: 'var(--color-text-faint)', display: 'flex', gap: 12 }}>
                      <span style={{ display: 'inline-flex', gap: 4, alignItems: 'center' }}>
                        <strong style={{ fontWeight: 600 }}>T:</strong>{file.tablesCount ?? 0}
                      </span>
                      <span style={{ display: 'inline-flex', gap: 4, alignItems: 'center' }}>
                        <strong style={{ fontWeight: 600 }}>R:</strong>{file.rowsCount ?? 0}
                      </span>
                    </div>
                  )}
                </div>
              );})}
            </div>
          </div>
        )}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '13px', fontWeight: 600, letterSpacing: '.5px', color: 'var(--color-text-soft)' }}>PROGRESS</span>
            <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-text)' }}>{taskProgress.toFixed(1)}% <span style={{ color: 'var(--color-text-faint)', fontWeight: 500 }}>({curatedCellsCount}/{totalCellsCount})</span></span>
          </div>
          <div style={{ position: 'relative', width: '100%', height: 10, background: 'var(--color-surface-alt)', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-pill)', overflow: 'hidden' }}>
            <div style={{
              width: `${taskProgress}%`,
              height: '100%',
              background: taskProgress === 100 ? 'linear-gradient(90deg,#24d453,#1eba48)' : 'linear-gradient(90deg,#3b82f6,#2563eb)',
              boxShadow: 'inset 0 0 0 1px rgba(0,0,0,0.06)',
              transition: 'width var(--transition-med)'
            }} />
          </div>
        </div>
        {isTaskFinished && (
          <div style={{ marginTop: 'var(--space-4)', display: 'flex', flexWrap: 'wrap', gap: 'var(--space-5)', alignItems: 'flex-start' }}>
            <div style={{ flex: '1 1 320px', display: 'flex', flexDirection: 'column', gap: 6, background: 'var(--color-surface-alt)', padding: '16px 18px', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-lg)' }}>
              <div style={{ fontSize: '12px', fontWeight: 600, letterSpacing: '.5px', color: 'var(--color-text-soft)' }}>TASK COMPLETED</div>
              <div style={{ fontSize: '14px', fontWeight: 600, lineHeight: 1.25, color: 'var(--color-text)' }}>{totalCellsCount} cells curated.</div>
              <div style={{ fontSize: '12px', color: 'var(--color-text-faint)' }}>Export results or reset to start again.</div>
            </div>
            <div style={{ display: 'flex', gap: 'var(--space-4)', alignItems: 'center' }}>
              <button onClick={handleResetTask} className="btn-primary" style={{ padding: '10px 18px', fontSize: '13px', fontWeight: 600 }}>Reset</button>
              <ExportButton
                label="Export curated"
                isDark={isDark}
                textColor={textColor}
                onClick={async () => {
                  try {
                    if (!currentTask?.path) return;
                    const result = await exportCurated(currentTask.path);
                    if (!result?.files?.length) {
                      alert('No curated files to export');
                      return;
                    }
                    result.files.forEach(f => {
                      const blob = new Blob([JSON.stringify(f.data, null, 2)], { type: 'application/json' });
                      const url = URL.createObjectURL(blob);
                      const a = document.createElement('a');
                      a.href = url;
                      a.download = f.filename;
                      document.body.appendChild(a);
                      a.click();
                      document.body.removeChild(a);
                      URL.revokeObjectURL(url);
                    });
                    console.log('Exported curated files:', result.files.map(f => f.filename));
                  } catch (err) {
                    console.error('Error exporting curated files:', err);
                    alert('Export failed: ' + err.message);
                  }
                }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Controles de modo visibles solo si no terminó */}
      {!isTaskFinished && (
        <div style={{ display: 'flex', gap: 'var(--space-5)', alignItems: 'center', flexWrap: 'wrap' }}>
          {['row','cell'].map(mode => (
            <button
              key={mode}
              onClick={() => setCurationMode(mode)}
              style={{
                background: curationMode === mode ? 'var(--color-accent)' : 'var(--color-surface-alt)',
                color: curationMode === mode ? '#fff' : 'var(--color-text-soft)',
                fontWeight: 600,
                padding: '8px 18px',
                fontSize: '13px',
                borderRadius: 'var(--radius-pill)',
                border: curationMode === mode ? '1px solid var(--color-accent)' : '1px solid var(--color-border)',
                letterSpacing: '.3px'
              }}
            >{mode === 'row' ? 'Row by Row' : 'Cell by Cell'}</button>
          ))}
          <div style={{ display: 'flex', alignItems: 'center', gap: 14, padding: '8px 16px', background: 'var(--color-surface-alt)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--color-border)', position: 'relative' }}>
            <label style={{ fontSize: 11, fontWeight: 700, letterSpacing: '.6px', color: 'var(--color-text-soft)' }}>MIN AGREEMENT</label>
            <div style={{ position: 'relative', flex: '1 1 160px', display: 'flex', alignItems: 'center' }}>
              <input
                type="range"
                min={0}
                max={100}
                step={1}
                value={minAgreement}
                onChange={(e) => setMinAgreement(parseInt(e.target.value, 10) || 0)}
                style={{
                  WebkitAppearance: 'none',
                  appearance: 'none',
                  width: '100%',
                  height: 6,
                  borderRadius: 4,
                  background: `linear-gradient(90deg, var(--color-warning) ${minAgreement}%, var(--color-border) ${minAgreement}%)`,
                  outline: 'none',
                  cursor: 'pointer',
                  boxShadow: 'inset 0 0 0 1px rgba(0,0,0,0.05)'
                }}
                className="min-agreement-slider"
              />
            </div>
            <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--color-text)', minWidth: 34, textAlign: 'right' }}>{minAgreement}%</div>
          </div>
        </div>
      )}

      {/* Delete Task button moved to top right */}

      {/* Navigation panel with file/table info and controls */}
  {!isTaskFinished && (
  <div className="panel" style={{ padding: 'var(--space-6)', display: 'flex', flexDirection: 'column', gap: 'var(--space-5)' }}>
        {/* Navigation controls */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: 16,
        }}>
          <button
            onClick={curationMode === 'row' ? onPrev : handleCellPrev}
            disabled={curationMode === 'row' ? currentRowIdx <= 0 : (currentRowIdx === 0 && currentCellIdx === 0)}
            style={{
              padding: '10px 18px',
              fontSize: '13px',
              fontWeight: 600,
              borderRadius: 'var(--radius-md)',
              background: 'var(--color-surface-alt)',
              border: '1px solid var(--color-border)',
              color: 'var(--color-text)',
              opacity: (curationMode === 'row' ? currentRowIdx <= 0 : (currentRowIdx === 0 && currentCellIdx === 0)) ? 0.5 : 1
            }}
          >Previous</button>

          <div style={{
            fontSize: 13,
            color: isDark ? 'rgba(255,255,255,0.8)' : 'rgba(0,0,0,0.8)',
            fontWeight: 600,
          }}>
            {currentRow._metadata ? (
              <span>
                File: {currentRow._metadata.sourceFile || 'unknown'} | Table: {currentRow._metadata.tableIndex || 0}
              </span>
            ) : (
              <span>No metadata available</span>
            )}
          </div>

          <button
            onClick={() => { if (isResetting) return; if (isTaskComplete) { setIsTaskFinished(true); } else { (curationMode === 'row' ? handleRowNext : handleCellNext)(); } }}
            style={{
              padding: '10px 22px',
              fontSize: '13px',
              fontWeight: 600,
              borderRadius: 'var(--radius-md)',
              background: isResetting ? 'var(--color-border)' : (isTaskComplete ? 'var(--color-accent)' : 'var(--color-surface-alt)'),
              color: isTaskComplete ? '#fff' : 'var(--color-text)',
              border: isTaskComplete ? '1px solid var(--color-accent)' : '1px solid var(--color-border)',
              opacity: isResetting ? 0.6 : 1,
              cursor: isResetting ? 'wait' : 'pointer'
            }}
          >{isResetting ? 'Resetting…' : (isTaskComplete ? 'Finish Task' : 'Next')}</button>
        </div>
      </div>
      )}

      {!isTaskFinished && (
  <div className="panel" style={{ padding: 'var(--space-6)', display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
          {curationMode === 'row' ? (
            <div>
              {/* Removed row counter panel as requested */}
              <div style={{ display: 'grid', gap: 'var(--space-5)', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', alignItems: 'start', gridAutoRows: 'minmax(0, auto)' }}>
                {columns.map((col) => {
                  console.log('Rendering column:', col, 'data:', currentRow[col]);
                  return (
                  <div key={col} style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-lg)', padding: '10px 12px 12px', boxShadow: 'var(--shadow-xs)', display: 'flex', flexDirection: 'column', gap: 'var(--space-3)', minWidth: 0, overflow: 'hidden', boxSizing: 'border-box' }}>
                    <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-soft)', marginBottom: 6, textTransform: 'capitalize', letterSpacing: '.3px', lineHeight: 1.2 }}>
                      {col.replace(/_/g, ' ')}
                    </div>
                    <RenderCell
                      value={currentRow[col]}
                      onChange={(value) => {
                        console.log('RenderCell onChange:', col, value);
                        onSelect && onSelect(col, value);
                      }}
                      minAgreement={minAgreement}
                      isDark={isDark}
                      textColor={textColor}
                      density="compact"
                    />
                  </div>
                  );
                })}
              </div>
            </div>
          ) : (
            <div>
              <div className="panel" style={{ padding: 'var(--space-6)', display: 'flex', flexDirection: 'column', gap: 'var(--space-5)' }}>
                <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-text-soft)', marginBottom: 14, textTransform: 'capitalize', letterSpacing: '.3px' }}>
                  {columns[currentCellIdx] ? columns[currentCellIdx].replace(/_/g,' ') : ''}
                </div>
                <RenderCell
                  value={currentRow[columns[currentCellIdx]]}
                  onChange={(value) => onSelect && onSelect(columns[currentCellIdx], value)}
                  minAgreement={minAgreement}
                  isDark={isDark}
                  textColor={textColor}
                />
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}