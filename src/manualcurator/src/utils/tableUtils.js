export function getAllRows(table) {
  let rows = [];
  if (Array.isArray(table.rows)) rows = rows.concat(table.rows);
  if (Array.isArray(table.table_fragments)) {
    for (const frag of table.table_fragments) {
      if (Array.isArray(frag.rows)) rows = rows.concat(frag.rows);
    }
  }
  return rows;
}

export function calcPercentages(options) {
  if (!Array.isArray(options)) return [];
  const total = options.reduce((s, o) => s + (o.agreement_level || 0), 0);
  return options.map((o) => ({ ...o, percentage: total > 0 ? Math.round((o.agreement_level / total) * 100) : 0 }));
}

export function adjustLightness(hex, deltaPercent) {
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
