export function downloadCurated(data, selections, filename) {
  try {
    const curated = JSON.parse(JSON.stringify(data || {}));
    const tablesList = Array.isArray(curated.tables) ? curated.tables : [];

    for (let tIdx = 1; tIdx < tablesList.length; tIdx++) {
      const table = tablesList[tIdx];
      if (!table || !Array.isArray(table.table_fragments)) continue;

      let globalRow = 0;
      for (const frag of table.table_fragments) {
        if (!Array.isArray(frag.rows)) continue;
        for (let r = 0; r < frag.rows.length; r++) {
          const row = frag.rows[r];
          const selRow = selections?.[tIdx]?.[globalRow];

          for (const col of Object.keys(row || {})) {
            if (selRow && Object.prototype.hasOwnProperty.call(selRow, col)) {
              row[col] = selRow[col];
            } else if (Array.isArray(row[col])) {
              const arr = row[col];
              const majority = Array.isArray(arr) && arr.length
                ? arr.reduce((m, o, i, a) => (o.percentage ?? 0) > (a[m].percentage ?? 0) ? i : m, 0)
                : null;
              if (majority !== null && arr[majority] && (arr[majority].value !== undefined)) {
                row[col] = arr[majority].value;
              }
            }
          }

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
    base = base.replace(/(\.json)+$/i, '');
    base = base.replace(/_curated$/i, '');
    a.download = base + '_curated.json';
    a.click();
    URL.revokeObjectURL(url);
    return true;
  } catch (err) {
    // bubble up or handle error
    throw err;
  }
}
