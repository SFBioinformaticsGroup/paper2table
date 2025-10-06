import React, { useEffect, useState } from 'react';
import { calcPercentages } from '../utils/tableUtils';

// density: 'normal' | 'compact' para controlar altura/espaciado (row mode => compact)
export default function RenderCell({ value, onChange, selectedProp, minAgreement = 0, agreementColor = 'var(--color-warning)', isDark = true, textColor = isDark ? '#fff' : '#111', density = 'normal' }) {
  const options = Array.isArray(value) ? calcPercentages(value) : [{ value: value == null ? '' : String(value), percentage: 100, agreement_level: 1 }];
  const processed = options.map((o) => ({ ...o, short: String(o.value) }));
  
  // Para compatibilidad, también calcular el majority por porcentaje
  const majorityIdx = processed.length ? processed.reduce((m, o, i, arr) => o.percentage > arr[m].percentage ? i : m, 0) : -1;
  const majorityPct = majorityIdx >= 0 ? processed[majorityIdx].percentage : 0;
  // majorityPct es porcentaje (0-100). minAgreement también (0-100)
  const low = majorityPct < minAgreement;

  // Calcular el índice con mayor agreement_level en un useMemo o useEffect
  const [highestAgreementIdx, setHighestAgreementIdx] = useState(-1);
  const [selected, setSelected] = useState('');
  const [custom, setCustom] = useState('');
  const [activeCustom, setActiveCustom] = useState(false);
  const [hasInitialized, setHasInitialized] = useState(false);

  // Resetear la inicialización cuando cambie el valor (nueva celda)
  useEffect(() => {
    setHasInitialized(false);
    setSelected('');
    setCustom('');
    setActiveCustom(false);
  }, [value]);

  // Calcular el índice con mayor agreement_level cuando cambie el valor
  useEffect(() => {
    if (processed.length > 0) {
      const idx = processed.reduce((maxIdx, option, i, arr) => {
        const currentAgreement = option.agreement_level ?? 0;
        const maxAgreement = arr[maxIdx].agreement_level ?? 0;
        return currentAgreement > maxAgreement ? i : maxIdx;
      }, 0);

      setHighestAgreementIdx(idx);

      // Debug logging
      if (processed.length > 1) {
        console.log('RenderCell options:', processed.map(p => ({ value: p.value, agreement_level: p.agreement_level })));
        console.log('Highest agreement index:', idx, 'Selected value:', processed[idx]?.value);
      }
    }
  }, [value, processed]);

  // Establecer la selección inicial cuando no hay selectedProp
  useEffect(() => {
    if (!hasInitialized && selectedProp !== undefined) {
      setSelected(selectedProp);
      setHasInitialized(true);
    } else if (!hasInitialized && highestAgreementIdx >= 0 && processed[highestAgreementIdx]) {
      // Solo auto-seleccionar una vez al inicializar
      const autoSelectedValue = processed[highestAgreementIdx].value ?? '';
      setSelected(autoSelectedValue);
      setHasInitialized(true);
      if (autoSelectedValue && onChange) {
        console.log('Auto-selecting:', autoSelectedValue);
        onChange(autoSelectedValue);
      }
    }
  }, [selectedProp, highestAgreementIdx, processed, onChange, hasInitialized]);

  const bgSelected = isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.04)';
  const cellTextStyle = { color: textColor };

  const gap = density === 'compact' ? 4 : 6;
  const optPadY = density === 'compact' ? 4 : 8;
  const optPadX = density === 'compact' ? 6 : 8;
  const inputPad = density === 'compact' ? '6px' : '8px';
  const borderLeftSize = density === 'compact' ? 3 : 4;

  return (
    // ensure the interactive area sits above sticky headers/overlays
  <div style={{ position: 'relative', zIndex: 1, borderLeft: low ? `${borderLeftSize}px solid ${agreementColor}` : `${borderLeftSize}px solid transparent`, paddingLeft: 6, transition: 'border-color 0.2s ease' }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap }}>
        {processed.map((opt, i) => {
          const isSel = !activeCustom && selected === opt.value;
          return (
            <div
              key={i}
              role="button"
              tabIndex={0}
              onClick={() => { setActiveCustom(false); setSelected(opt.value); onChange(opt.value); }}
              onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); setActiveCustom(false); setSelected(opt.value); onChange(opt.value); } }}
              // make each option sit above sticky elements and be fully interactive
              style={{ position: 'relative', zIndex: 2, pointerEvents: 'auto', display: 'flex', alignItems: 'center', gap: 10, padding: `${optPadY}px ${optPadX}px`, borderRadius: 8, cursor: 'pointer', background: isSel ? bgSelected : 'transparent', lineHeight: 1.25 }}
            >
              <div style={{ flex: 1, minWidth: 0, ...cellTextStyle }} title={String(opt.value)}>
                <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{opt.short}</div>
              </div>
              <div style={{ opacity: 0.9, fontSize: 13, flex: '0 0 auto', marginLeft: 8, color: textColor }}>{opt.percentage}% • {opt.agreement_level ?? 0}</div>
            </div>
          );
        })}
        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          <input
            placeholder="Enter different value..."
            value={custom}
            onFocus={() => { setActiveCustom(true); setSelected('__custom__'); }}
            onChange={(e) => { setCustom(e.target.value); setActiveCustom(true); onChange(e.target.value); }}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault();
                // confirm custom value and exit custom mode so options are selectable again
                setActiveCustom(false);
                setSelected(custom);
                onChange(custom);
                // blur to remove focus and allow option selection via click/keys
                if (e.currentTarget && typeof e.currentTarget.blur === 'function') e.currentTarget.blur();
              }
            }}
            // ensure input is interactive even if a sticky overlay exists
            style={{ position: 'relative', zIndex: 2, pointerEvents: 'auto', flex: 1, padding: inputPad, borderRadius: 6, border: isDark ? '1px solid rgba(255,255,255,0.06)' : '1px solid rgba(0,0,0,0.12)', background: 'transparent', color: textColor, fontSize: density === 'compact' ? '12px' : '13px' }}
          />
        </div>
      </div>
    </div>
  );
}
