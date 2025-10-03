import { useEffect, useMemo, useState, useRef } from 'react';

// ---------------- helpers ----------------
function getAllRows(table) {
  let rows = [];
  if (Array.isArray(table.rows)) rows = rows.concat(table.rows);
  if (Array.isArray(table.table_fragments)) {
    for (const frag of table.table_fragments) {
      if (Array.isArray(frag.rows)) rows = rows.concat(frag.rows);
    }
  }
  return rows;
}

function calcPercentages(options) {
  if (!Array.isArray(options)) return [];
  const total = options.reduce((s, o) => s + (o.agreement_level || 0), 0);
  return options.map((o) => ({ ...o, percentage: total > 0 ? Math.round((o.agreement_level / total) * 100) : 0 }));
}

function adjustLightness(hex, deltaPercent) {
  try {
    const h = hex.replace('#', '');
    const bigint = parseInt(h.length === 3 ? h.split('').map((c) => c + c).join('') : h, 16);
    let r = (bigint >> 16) & 255,
      g = (bigint >> 8) & 255,
      b = bigint & 255;
    r /= 255; g /= 255; b /= 255;
    const max = Math.max(r, g, b), min = Math.min(r, g, b);
    let l = (max + min) / 2 * 100;
    const nl = Math.max(0, Math.min(100, l + deltaPercent));
    const scale = nl / 100;
    const nr = Math.round((r * scale) * 255);
    const ng = Math.round((g * scale) * 255);
    const nb = Math.round((b * scale) * 255);
    return '#' + [nr, ng, nb].map((v) => v.toString(16).padStart(2, '0')).join('');
  } catch (e) {
    return hex;
  }
}

// ---------------- small components ----------------
const buttonStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: 8,
  background: 'rgba(255,255,255,0.03)',
  padding: '8px 12px',
  borderRadius: 10,
  cursor: 'pointer',
  border: '1px solid rgba(255,255,255,0.04)',
  color: '#fff',
  fontWeight: 700,
  height: 60,          // forzar altura exacta
  lineHeight: 1,
  boxSizing: 'border-box',
};

function UploadButton({ onFile, label = 'Import table (JSON)', filename }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6, minHeight: 60, justifyContent: 'center' }}>
      <div style={{ position: 'relative' }}>
        <label style={buttonStyle}>
          <input type="file" accept="application/json" onChange={onFile} style={{ display: 'none' }} />
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
            <path d="M12 3v12" stroke="#fff" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            <path d="M8 7l4-4 4 4" stroke="#fff" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            <path d="M20 21H4a2 2 0 0 1-2-2V15" stroke="#fff" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          <span>{label}</span>
        </label>

        {/* filename positioned slightly below without affecting button layout */}
        <div style={{ position: 'absolute', left: 0, right: 0, top: '64px', textAlign: 'left', paddingLeft: 4 }}>
          <span style={{ color: 'rgba(255,255,255,0.8)', fontSize: 12, visibility: filename ? 'visible' : 'hidden', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{filename || ''}</span>
        </div>
      </div>
    </div>
  );
}

function ExportButton({ onClick, label = 'Export table (JSON)', disabled = false }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6, minHeight: 60, justifyContent: 'center' }}>
      <button type="button" onClick={onClick} style={{ ...buttonStyle, opacity: disabled ? 0.45 : 1, cursor: disabled ? 'not-allowed' : 'pointer' }} disabled={disabled}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <path d="M12 21V9" stroke="#fff" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          <path d="M8 15l4 4 4-4" stroke="#fff" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          <path d="M20 3H4a2 2 0 0 0-2 2v4" stroke="#fff" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
        <span>{label}</span>
      </button>
    </div>
  );
}




function RenderCell({ value, onChange, selectedProp, minAgreement = 0, agreementColor = '#e53e3e' }) {
  const options = Array.isArray(value) ? calcPercentages(value) : [{ value: value == null ? '' : String(value), percentage: 100, agreement_level: 1 }];
  // keep the full text in JS and rely on CSS to ellipsize only when it doesn't fit in one line
  const processed = options.map((o) => ({ ...o, short: String(o.value) }));
  const majorityIdx = processed.length ? processed.reduce((m, o, i, arr) => o.percentage > arr[m].percentage ? i : m, 0) : -1;
  const majorityPct = majorityIdx >= 0 ? processed[majorityIdx].percentage : 0;
  const low = majorityPct < minAgreement;

  const [custom, setCustom] = useState('');
  const [activeCustom, setActiveCustom] = useState(false);
  const [selected, setSelected] = useState(() => selectedProp !== undefined ? selectedProp : (processed[majorityIdx]?.value ?? ''));

  useEffect(() => { if (selectedProp !== undefined) setSelected(selectedProp); }, [selectedProp]);

  return (
  <div style={{ borderLeft: low ? `4px solid ${agreementColor}` : '4px solid transparent', paddingLeft: 8 }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {processed.map((opt, i) => {
          const isSel = !activeCustom && selected === opt.value;
          return (
            <div key={i} role="button" tabIndex={0}
              onClick={() => { setSelected(opt.value); onChange(opt.value); }}
              onKeyDown={(e) => { if (e.key === 'Enter') { setSelected(opt.value); onChange(opt.value); } }}
              style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '8px', borderRadius: 8, cursor: 'pointer', background: isSel ? 'rgba(255,255,255,0.06)' : 'transparent' }}>
              <div style={{ flex: 1, minWidth: 0 }} title={String(opt.value)}>
                <div style={{ color: '#fff', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{opt.short}</div>
              </div>
              <div style={{ color: '#fff', opacity: 0.9, fontSize: 13, flex: '0 0 auto', marginLeft: 8 }}>{opt.percentage}% • {opt.agreement_level ?? 0}</div>
            </div>
          );
        })}

        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <input
            placeholder="Enter different value..."
            value={custom}
            onFocus={() => { setActiveCustom(true); setSelected('__custom__'); onChange(custom); }}
            onChange={(e) => { setCustom(e.target.value); setActiveCustom(true); onChange(e.target.value); }}
            style={{ flex: 1, padding: '8px', borderRadius: 6, border: '1px solid rgba(255,255,255,0.06)', background: 'transparent', color: '#fff' }}
          />
        </div>
      </div>
    </div>
  );
}

// ---------------- App ----------------
export default function App() {
  const [data, setData] = useState(null);
  const [filename, setFilename] = useState(null);
  const [accent] = useState('#303030');
  const [agreementColor, setAgreementColor] = useState('#1e6433');
  const [minAgreement, setMinAgreement] = useState(60);
  const [query, setQuery] = useState('');
  const [selections, setSelections] = useState({});

  const headerBg = accent;
  const headerText = '#fff';
  const rowEven = adjustLightness(accent, 44);
  const rowOdd = adjustLightness(accent, 56);
  const borderColor = adjustLightness(accent, 10);
  const headerRef = useRef(null);
  const [headerHeight, setHeaderHeight] = useState(0);
  const [isPinned, setIsPinned] = useState(false);

  useEffect(() => {
    function updateHeight() {
      const h = headerRef.current ? headerRef.current.offsetHeight : 0;
      setHeaderHeight(h);
    }
    function updatePin() {
      const pinned = window.scrollY > (headerRef.current ? headerRef.current.offsetTop : 0);
      setIsPinned(pinned);
    }
    // initial
    updateHeight();
    updatePin();
    window.addEventListener('resize', updateHeight);
    window.addEventListener('scroll', updatePin, { passive: true });
    return () => {
      window.removeEventListener('resize', updateHeight);
      window.removeEventListener('scroll', updatePin, { passive: true });
    };
  }, []);

  function handleFile(e) {
    const f = e.target.files?.[0];
    if (!f) return;
    setFilename(f.name);
    const r = new FileReader();
    r.onload = (ev) => { try { const j = JSON.parse(ev.target.result); setData(j); setSelections({}); } catch (err) { alert('Error leyendo JSON: ' + err.message); } };
    r.readAsText(f);
  }

  function handleSelect(tableIdx, rowIdx, col, val) {
    setSelections((prev) => { const copy = { ...prev }; if (!copy[tableIdx]) copy[tableIdx] = {}; if (!copy[tableIdx][rowIdx]) copy[tableIdx][rowIdx] = {}; copy[tableIdx][rowIdx][col] = val; return copy; });
  }

  function exportCurated() {
    try {
      const curated = JSON.parse(JSON.stringify(data || {}));
      const tablesList = Array.isArray(curated.tables) ? curated.tables : [];

      // iterate tables starting from index 1 (table 0 is paper metadata)
      for (let tIdx = 1; tIdx < tablesList.length; tIdx++) {
        const table = tablesList[tIdx];
        if (!table || !Array.isArray(table.table_fragments)) continue;

        let globalRow = 0;
        for (const frag of table.table_fragments) {
          if (!Array.isArray(frag.rows)) continue;
          for (let r = 0; r < frag.rows.length; r++) {
            const row = frag.rows[r];
            const selRow = selections?.[tIdx]?.[globalRow];

            // for each column in the row, if a selection exists, replace value with the chosen option
            for (const col of Object.keys(row || {})) {
              if (selRow && Object.prototype.hasOwnProperty.call(selRow, col)) {
                row[col] = selRow[col];
              } else if (Array.isArray(row[col])) {
                // if original cell is an array of options and no selection was made, pick the majority by percentage if available
                const arr = row[col];
                const majority = Array.isArray(arr) && arr.length ? arr.reduce((m, o, i, a) => (o.percentage ?? 0) > (a[m].percentage ?? 0) ? i : m, 0) : null;
                if (majority !== null && arr[majority] && (arr[majority].value !== undefined)) {
                  row[col] = arr[majority].value;
                }
              }
            }

            // remove any agreement metadata keys like $agreement_level
            for (const k of Object.keys(row)) {
              if (k && k.startsWith && k.startsWith('$')) delete row[k];
            }

            globalRow++;
          }
        }
      }

      const blob = new Blob([JSON.stringify(curated, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
  let base = filename ? filename : 'curated';
  // remove repeated .json suffixes (case-insensitive) and any trailing _curated
  base = base.replace(/(\.json)+$/i, '');
  base = base.replace(/_curated$/i, '');
  a.download = base + '_curated.json';
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      alert('Error exporting curated JSON: ' + (err && err.message ? err.message : String(err)));
    }
  }

  const tables = Array.isArray(data?.tables) ? data.tables : [];
  // The first table in the file contains paper metadata (authors, year, journal, ...)
  const paperInfo = tables?.[0];
  const paperInfoRows = paperInfo ? getAllRows(paperInfo) : [];
  const paperMeta = paperInfoRows.length ? paperInfoRows[0] : null;
  const flat = useMemo(() => {
    const out = [];
    tables.slice(1).forEach((t, ti) => {
      const tableIdx = ti + 1;
      const rows = getAllRows(t);
      rows.forEach((r, ri) => out.push({ tableIdx, rowIdx: ri, row: r }));
    });
    return out;
  }, [data]);

  const columns = useMemo(() => {
    const s = new Set();
    flat.forEach(({ row }) => { Object.keys(row || {}).forEach((k) => { if (k !== '$agreement_level') s.add(k); }); });
    return Array.from(s);
  }, [flat]);

  const filtered = useMemo(() => {
    if (!query) return flat;
    const q = query.toLowerCase();
    return flat.filter(({ row }) => JSON.stringify(row || {}).toLowerCase().includes(q));
  }, [flat, query]);

  return (
    <div
      style={{
        minHeight: '100vh',
        background: '#121212',
        color: '#fff',
        padding: 0,
        boxSizing: 'border-box',
        fontFamily: 'Inter, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial',
      }}
    >
      {/* Header ocupa todo el ancho */}
      <header
        ref={headerRef}
        style={{
          width: '100%', // ocupa todo el ancho del viewport
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 16,
          position: 'sticky',
          top: 0,
          zIndex: 40,
          background: headerBg,
          padding: '0 20px', // padding interno solo para los elementos del header
          minHeight: 120,
          transition: 'box-shadow 150ms, transform 150ms',
          boxShadow: isPinned ? '0 6px 18px rgba(0,0,0,0.5)' : 'none',
          transform: isPinned ? 'translateY(0)' : 'translateY(-5px)',
          boxSizing: 'border-box',
        }}
      >
        {/* Izquierda: título + controles */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 50 }}>
          <div style={{ marginLeft: 8, display: 'flex', flexDirection: 'column' }}>
            <div style={{ fontSize: 24, fontWeight: 700 }}>Manual Curator — Paper2Table</div>
            <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.75)' }}>
              Review and select values from extracted tables
            </div>
          </div>

          {/* Controles al lado del título */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <UploadButton onFile={handleFile} filename={filename} />
            <ExportButton onClick={exportCurated} disabled={!data} />

            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, minHeight: 60, justifyContent: 'center' }}>
                <div style={{ ...buttonStyle, padding: '8px 12px', alignItems: 'center' }}>
                  <div style={{ display: 'flex', flexDirection: 'column', marginRight: 8 }}>
                    <label style={{ fontSize: 12, color: 'rgba(255,255,255,0.8)', marginBottom: 6 }}>
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
                  <div style={{ fontWeight: 700, color: '#fff', minWidth: 36, textAlign: 'right' }}>
                    {minAgreement}%
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Color picker a la derecha */}
        <input
          aria-label="Min agreement color"
          type="color"
          value={agreementColor}
          onChange={(e) => setAgreementColor(e.target.value)}
          style={{ width: 36, height: 32, border: 'none', background: 'transparent', cursor: 'pointer' }}
        />
      </header>

      {/* Contenido principal con padding lateral */}
      <div style={{ padding: '0 20px' }}>
        {/* Always show the main UI skeleton */}
        <main style={{ marginTop: 48 }}>
          {paperMeta && (
            <section style={{ marginBottom: 12, padding: '10px 12px', background: 'rgba(255,255,255,0.02)', borderRadius: 8 }}>
              <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
                {Object.keys(paperMeta).map((k) => (
                  <div key={k} style={{ minWidth: 120 }}>
                    <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.75)' }}>{k}</div>
                    <div style={{ color: '#fff', fontWeight: 600 }}>{String(paperMeta[k] ?? '')}</div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {data && (
            <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
              <input
                placeholder="Buscar en filas..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                style={{ flex: 1, padding: '10px 12px', borderRadius: 10, border: 'none', background: 'rgba(255,255,255,0.04)', color: '#fff' }}
              />
              <div style={{ color: 'rgba(255,255,255,0.7)' }}>{filtered.length} rows · {columns.length} columns</div>
            </div>
          )}

          <section style={{ marginTop: 18, background: 'rgba(255,255,255,0.02)', borderRadius: 12, padding: 16 }}>
            <div style={{ overflowX: 'auto' }}>
              {columns.length ? (
                <table style={{ width: '100%', borderCollapse: 'collapse', tableLayout: 'fixed', minWidth: 800 }}>
                  <colgroup>
                    {columns.map((c) => (
                      <col key={c} style={{ width: `${100 / columns.length}%` }} />
                    ))}
                  </colgroup>
                  <thead>
                    <tr>
                      {columns.map((col) => (
                        <th
                          key={col}
                          style={{
                            textAlign: 'left',
                            padding: '12px 10px',
                            position: 'sticky',
                            top: isPinned ? (headerHeight ? `${headerHeight}px` : 0) : 0,
                            background: headerBg,
                            color: headerText,
                            fontWeight: 600,
                            fontSize: 13,
                          }}
                        >
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.map(({ tableIdx, rowIdx, row }, ridx) => (
                      <tr key={`${tableIdx}-${rowIdx}`} style={{ background: ridx % 2 === 0 ? rowEven : rowOdd }}>
                        {columns.map((col) => (
                          <td
                            key={col}
                            style={{
                              padding: 14,
                              verticalAlign: 'top',
                              borderBottom: `1px solid ${borderColor}`,
                              whiteSpace: 'normal',
                              wordBreak: 'break-word',
                            }}
                          >
                            <RenderCell
                              value={row[col]}
                              selectedProp={selections?.[tableIdx]?.[rowIdx]?.[col]}
                              onChange={(val) => handleSelect(tableIdx, rowIdx, col, val)}
                              minAgreement={minAgreement}
                              agreementColor={agreementColor}
                            />
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div style={{ padding: 24, textAlign: 'center', color: 'rgba(255,255,255,0.45)' }}>
                  No table data. Load a JSON file to populate the table.
                </div>
              )}
            </div>
          </section>
        </main>

        <footer style={{ marginTop: 28, color: 'rgba(255,255,255,0.6)', fontSize: 13 }}>
          <div>
            File: <strong style={{ color: '#fff' }}>{filename || 'none'}</strong>
          </div>
        </footer>
      </div>

      <style>{`
        .min-agreement-range {
          -webkit-appearance:none;
          appearance:none;
          width:160px;
          height:8px;
          border-radius:999px;
          background: linear-gradient(90deg, ${agreementColor} 0%, ${agreementColor} var(--val,50%), rgba(255,255,255,0.12) var(--val,50%));
          outline:none;
        }
        .min-agreement-range::-webkit-slider-thumb {
          -webkit-appearance:none;
          appearance:none;
          width:16px;height:16px;border-radius:50%;
          background:#fff; border:3px solid ${agreementColor}; cursor:pointer;
        }
        .min-agreement-range::-moz-range-thumb {
          width:16px;height:16px;border-radius:50%;
          background:#fff; border:3px solid ${agreementColor}; cursor:pointer;
        }
      `}</style>
    </div>
  );
}
