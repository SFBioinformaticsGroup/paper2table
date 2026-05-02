function getAllRows(table) {
  if (!table) return [];
  if (Array.isArray(table.rows)) return table.rows;
  if (Array.isArray(table.table_fragments)) {
    return table.table_fragments.flatMap((f) => (Array.isArray(f.rows) ? f.rows : []));
  }
  return [];
}

export function extractRowsFromJSON(json, options = {}) {
  const { debug = false, treatFirstTableAsMetadata = true } = options;
  const rows = [];
  let tablesCount = 0;
  let metadataSkipped = false;

  if (Array.isArray(json?.tables) && json.tables.length) {
    let tables = json.tables;
    if (treatFirstTableAsMetadata && json.tables.length > 1) {
      metadataSkipped = true;
      tables = json.tables.slice(1); // saltar metadata
    }
    tablesCount = tables.length;
    tables.forEach((tbl, i) => {
      const added = getAllRows(tbl);
      if (debug) console.log(`[extractRowsFromJSON] tableDataIndex=${i} addedRows=${added.length}`);
      rows.push(...(added || []));
    });
  } else if (Array.isArray(json?.tasks) && json.tasks.length) {
    json.tasks.forEach((t, idx) => {
      const added = Array.isArray(t.rows) ? t.rows : [];
      if (debug) console.log(`[extractRowsFromJSON] taskIndex=${idx} addedRows=${added.length}`);
      rows.push(...added);
    });
    tablesCount = json.tasks.length;
  } else {
    const added = getAllRows(json);
    if (debug) console.log(`[extractRowsFromJSON] root addedRows=${added.length}`);
    rows.push(...added);
    tablesCount = added.length ? 1 : 0;
  }

  if (debug) console.log(`[extractRowsFromJSON] totalRows=${rows.length} tablesCount=${tablesCount} metadataSkipped=${metadataSkipped}`);
  return rows;
}

// Helper para contar tablas y filas (excluyendo metadata si corresponde)
export function countTablesAndRows(json, options = {}) {
  const { treatFirstTableAsMetadata = true } = options;
  let tablesCount = 0;
  let rowsCount = 0;
  if (Array.isArray(json?.tables) && json.tables.length) {
    const tables = (treatFirstTableAsMetadata && json.tables.length > 1) ? json.tables.slice(1) : json.tables;
    tablesCount = tables.length;
    tables.forEach(tbl => {
      rowsCount += getAllRows(tbl).length;
    });
  } else if (Array.isArray(json?.tasks) && json.tasks.length) {
    tablesCount = json.tasks.length;
    json.tasks.forEach(t => { rowsCount += (Array.isArray(t.rows) ? t.rows.length : 0); });
  } else {
    const rootRows = getAllRows(json);
    if (rootRows.length) {
      tablesCount = 1;
      rowsCount = rootRows.length;
    }
  }
  return { tablesCount, rowsCount };
}
