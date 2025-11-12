import { getAllRows } from './tableUtils';

export function createTaskFromImported(taskTitle, rows, files, tables) {
  // Añadir metadata a cada fila y randomizar
  const rowsWithMeta = rows.map((row, index) => {
    // Determinar de qué archivo y tabla viene esta fila
    const fileIndex = tables.findIndex(t => t.rows.includes(row));
    return {
      ...row,
      _metadata: {
        sourceFile: files[fileIndex],
        tableIndex: tables[fileIndex].tableIndex,
        originalIndex: tables[fileIndex].rows.indexOf(row)
      }
    };
  });

  // Mezclar filas aleatoriamente
  const shuffledRows = [...rowsWithMeta].sort(() => Math.random() - 0.5);

  return {
    name: taskTitle,
    rows: shuffledRows
  };
}

export function createTasksFromTables(tables) {
  if (!Array.isArray(tables)) return [];
  return tables.slice(1).map((tbl, i) => ({ 
    name: tbl.name || `table_${i + 1}`, 
    rows: getAllRows(tbl) 
  }));
}

export function extractRowsFromJSON(json) {
  const rows = [];
  if (Array.isArray(json.tables) && json.tables.length) {
    json.tables.slice(1).forEach((tbl) => {
      const tableRows = getAllRows(tbl) || [];
      rows.push(...tableRows);
    });
  } else if (Array.isArray(json.tasks) && json.tasks.length) {
    json.tasks.forEach((t) => {
      const taskRows = Array.isArray(t.rows) ? t.rows : [];
      rows.push(...taskRows);
    });
  } else {
    const jsonRows = getAllRows(json) || [];
    rows.push(...jsonRows);
  }
  return rows;
}

export function makeCuratedFilename(base) {
  let b = base || 'curated';
  b = b.replace(/(\.json)+$/i, '');
  b = b.replace(/_curated$/i, '');
  return b + '_curated.json';
}
