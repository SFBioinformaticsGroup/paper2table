import express from 'express';
import cors from 'cors';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import fs from 'fs/promises';
import { extractRowsFromJSON, countTablesAndRows } from './utils.js'; // Utilidades filas/tablas

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const app = express();
app.use(cors());
app.use(express.json());

// Configurar directorio de tareas
const TASKS_DIR = join(__dirname, '..', 'tasks');

// Función para aplicar selecciones a los datos
function applySelectionsToData(originalData, selections) {
  console.log('=== APPLYING SELECTIONS (metadata-aware) ===');
  const selectionKeys = Object.keys(selections || {});
  console.log('Selections row indices:', selectionKeys);

  // Deep clone base data (curated or original)
  const curatedData = JSON.parse(JSON.stringify(originalData));

  if (!selections || selectionKeys.length === 0) {
    console.log('No selections provided, returning data unchanged');
    return curatedData;
  }

  if (!Array.isArray(curatedData.tables)) {
    console.warn('Data has no tables array; cannot apply structured selections');
    return curatedData;
  }

  const hasMetadata = curatedData.tables.length > 1; // table[0] is metadata if more than one table
  const startIdx = hasMetadata ? 1 : 0;
  if (hasMetadata) {
    console.log('Detected metadata table at index 0; it will be excluded from row mapping.');
  }

  // Build a flat mapping from global row index -> { rowRef, tableIdx, fragmentIdx, rowIdx }
  const rowPointerMap = [];
  for (let tableIdx = startIdx; tableIdx < curatedData.tables.length; tableIdx++) {
    const table = curatedData.tables[tableIdx];
    if (!table || !Array.isArray(table.table_fragments)) continue;
    for (let fragmentIdx = 0; fragmentIdx < table.table_fragments.length; fragmentIdx++) {
      const fragment = table.table_fragments[fragmentIdx];
      if (!fragment || !Array.isArray(fragment.rows)) continue;
      for (let rowIdx = 0; rowIdx < fragment.rows.length; rowIdx++) {
        rowPointerMap.push({ rowRef: fragment.rows[rowIdx], tableIdx, fragmentIdx, rowIdx });
      }
    }
  }
  console.log(`Row pointer map built with ${rowPointerMap.length} rows (metadata excluded=${hasMetadata}).`);

  selectionKeys.forEach(rowIndexStr => {
    const rowIndex = parseInt(rowIndexStr, 10);
    if (Number.isNaN(rowIndex)) return;
    const rowSelections = selections[rowIndex];
    const pointer = rowPointerMap[rowIndex];
    if (!pointer) {
      console.warn(`Row index ${rowIndex} out of bounds (map length ${rowPointerMap.length}). Skipping.`);
      return;
    }
    if (!rowSelections || typeof rowSelections !== 'object') {
      console.warn(`Row selections for index ${rowIndex} invalid`, rowSelections);
      return;
    }

    const row = pointer.rowRef;
    console.log(`Applying selections to rowIndex=${rowIndex} -> table[${pointer.tableIdx}].fragment[${pointer.fragmentIdx}].row[${pointer.rowIdx}]`);

    Object.keys(rowSelections).forEach(key => {
      const selectedValue = rowSelections[key];
      if (row[key] === undefined) {
        console.log(`Key ${key} not present in row; skipping.`);
        return;
      }
      if (Array.isArray(row[key])) {
        const options = row[key];
        if (options.length && typeof options[0] === 'object' && options[0] && 'value' in options[0]) {
          row[key] = { value: selectedValue, curated: true };
          console.log(`Converted array field ${key} -> curated object.`);
        } else {
          row[key] = { value: selectedValue, curated: true };
          console.log(`Array field ${key} (non-option) wrapped as curated.`);
        }
      } else if (row[key] && typeof row[key] === 'object' && row[key].curated === true) {
        row[key].value = selectedValue;
        console.log(`Updated existing curated object for key ${key}.`);
      } else {
        row[key] = { value: selectedValue, curated: true };
        console.log(`Wrapped primitive field ${key} as curated.`);
      }
    });
  });

  console.log('=== SELECTIONS APPLIED (metadata-aware) ===');
  return curatedData;
}

// Crear nueva tarea con carpetas original/curated
app.post('/api/tasks', async (req, res) => {
  try {
    const { taskTitle, files, originalData } = req.body;
    const taskDir = join(TASKS_DIR, taskTitle.replace(/[^a-z0-9]/gi, '_'));
    
    await fs.mkdir(taskDir, { recursive: true });
    const originalDir = join(taskDir, 'original');
    const curatedDir = join(taskDir, 'curated');
    await fs.mkdir(originalDir, { recursive: true });
    await fs.mkdir(curatedDir, { recursive: true });
    
    // Guardar archivos originales solamente
    for (let i = 0; i < files.length; i++) {
      const originalPath = join(originalDir, files[i]);
      await fs.writeFile(originalPath, JSON.stringify(originalData[i], null, 2));
    }

    // Crear log file
    await fs.writeFile(join(taskDir, 'task_log.jsonl'), '');
    res.json({ success: true, path: taskDir });
  } catch (err) {
    console.error('Error creating task:', err);
    res.status(500).json({ error: err.message });
  }
});

// Helper para listar archivos originales (compatibilidad con tareas viejas)
async function listOriginalFiles(taskDir) {
  const originalDir = join(taskDir, 'original');
  try {
    const stats = await fs.stat(originalDir);
    if (stats.isDirectory()) {
      return (await fs.readdir(originalDir)).filter(f => f.endsWith('.json'));
    }
  } catch {}
  // fallback legacy
  const all = await fs.readdir(taskDir);
  return all.filter(f => !f.includes('_curated') && f.endsWith('.json'));
}

function cellIsCurated(val) {
  return !!(val && typeof val === 'object' && val.curated === true);
}

// Listar tareas (re-implementado con soporte de carpetas)
app.get('/api/tasks', async (req, res) => {
  try {
    const taskDirs = await fs.readdir(TASKS_DIR);
    const tasksData = [];
    for (const dirName of taskDirs) {
      const taskPath = join(TASKS_DIR, dirName);
      try {
        const stat = await fs.stat(taskPath);
        if (!stat.isDirectory()) continue;
      } catch { continue; }
      // Intentar leer nombre original (con tildes) desde meta.json
      let originalName = null;
      try {
        const metaRaw = await fs.readFile(join(taskPath, 'meta.json'), 'utf-8');
        const meta = JSON.parse(metaRaw);
        if (meta && typeof meta.originalName === 'string' && meta.originalName.trim()) {
          originalName = meta.originalName.trim();
        }
      } catch {}

      const originalFiles = await listOriginalFiles(taskPath);
      let allRows = [];
      for (let fileIndex = 0; fileIndex < originalFiles.length; fileIndex++) {
        const fileName = originalFiles[fileIndex];
        let filePath = join(taskPath, 'original', fileName);
        try { await fs.access(filePath); } catch { filePath = join(taskPath, fileName); }
        try {
          const raw = await fs.readFile(filePath, 'utf-8');
          const json = JSON.parse(raw);
          // Capturar metadata de tabla 0 si existe
          let metadataTable = null;
          if (Array.isArray(json?.tables) && json.tables.length > 1) {
            metadataTable = json.tables[0];
          }
          const citation = json.citation || metadataTable?.citation || null;
          const fileRows = extractRowsFromJSON(json, { treatFirstTableAsMetadata: true });
          // Necesitamos reconstruir el índice real de tabla para cada fila.
          // Como extractRowsFromJSON aplana y omite metadata, iteramos tablas >=1 para mapear filas a su tableIdx real.
          const tableRowToGlobal = [];
          if (Array.isArray(json?.tables) && json.tables.length > 1) {
            for (let t = 1; t < json.tables.length; t++) {
              const tbl = json.tables[t];
              // Obtener filas de cada tabla respetando fragments
              let rowsForTbl = [];
              if (Array.isArray(tbl?.table_fragments)) {
                tbl.table_fragments.forEach(f => { if (Array.isArray(f?.rows)) rowsForTbl.push(...f.rows); });
              } else if (Array.isArray(tbl?.rows)) {
                rowsForTbl = tbl.rows;
              }
              rowsForTbl.forEach(r => tableRowToGlobal.push({ rowRef: r, tableIndex: t }));
            }
          }
          // Construir filas con metadatos únicos
          const rowsWithMetadata = fileRows.map((row, originalIndex) => {
            // Encontrar la misma referencia para obtener tableIndex real
            let tableIndexReal = null;
            const match = tableRowToGlobal.find(entry => entry.rowRef === row);
            if (match) tableIndexReal = match.tableIndex; else tableIndexReal = null;
            return {
              ...row,
              _metadata: {
                sourceFile: fileName,
                originalIndex,
                tableIndex: tableIndexReal, // índice dentro de json.tables (excluyendo metadata si null)
                citation
              }
            };
          });
          allRows.push(...rowsWithMetadata);
        } catch (err) {
          console.error('Error reading original file for task listing:', fileName, err.message);
        }
      }
      tasksData.push({
        name: originalName || dirName.replace(/_/g, ' '),
        path: dirName,
        rows: allRows,
        originalFiles
      });
    }
    res.json(tasksData);
  } catch (err) {
    console.error('Error listing tasks:', err);
    res.status(500).json({ error: err.message });
  }
});

// Endpoint para obtener siguiente fila/celda no curada aleatoria
app.get('/api/tasks/:taskName/next', async (req, res) => {
  try {
    const { taskName } = req.params;
    const { mode = 'row' } = req.query;
    const taskDir = join(TASKS_DIR, taskName);
    const curatedDir = join(taskDir, 'curated');
    const originalDir = join(taskDir, 'original');

    const originalFiles = await listOriginalFiles(taskDir);
    if (!originalFiles.length) return res.status(404).json({ error: 'No original files' });

    const candidates = [];

    for (let fileIndex = 0; fileIndex < originalFiles.length; fileIndex++) {
      const fileName = originalFiles[fileIndex];
      // Decidir ruta curated
      let baseData;
      const curatedPathNew = join(curatedDir, fileName);
      try {
        baseData = JSON.parse(await fs.readFile(curatedPathNew, 'utf-8'));
      } catch {
        // fallback a legacy _curated.json
        try {
          baseData = JSON.parse(await fs.readFile(join(taskDir, fileName.replace('.json','_curated.json')), 'utf-8'));
        } catch {
          baseData = JSON.parse(await fs.readFile(join(originalDir, fileName), 'utf-8'));
        }
      }
      const rows = extractRowsFromJSON(baseData, { treatFirstTableAsMetadata: true });
      console.log(`[NEXT] file=${fileName} rows=${rows.length}`);
      rows.forEach((row, rowIndex) => {
        const keys = Object.keys(row).filter(k => k !== '_metadata');
        const uncuratedKeys = keys.filter(k => !cellIsCurated(row[k]));
        if (uncuratedKeys.length === 0) {
          // debug: mostrar si todas están curadas inmediatamente
          console.log(`[NEXT] row ${rowIndex} fully curated?`, keys.length > 0);
        }
        if (uncuratedKeys.length) {
          if (mode === 'row') {
            candidates.push({ fileIndex, fileName, rowIndex, row, uncuratedKeys });
          } else if (mode === 'cell') {
            uncuratedKeys.forEach(cellKey => {
              candidates.push({ fileIndex, fileName, rowIndex, row, cellKey });
            });
          }
        }
      });
    }

    if (!candidates.length) {
      console.log('[NEXT] No candidates found; returning done=true');
      return res.json({ done: true });
    }
    const pick = candidates[Math.floor(Math.random() * candidates.length)];
    res.json({
      mode,
      ...pick
    });
  } catch (err) {
    console.error('Error getting next item:', err);
    res.status(500).json({ error: err.message });
  }
});

// Registrar selección
app.post('/api/tasks/:taskName/log', async (req, res) => {
  try {
    const { taskName } = req.params;
    const { selection } = req.body;
    
    const logEntry = JSON.stringify({
      timestamp: new Date().toISOString(),
      ...selection
    }) + '\n';
    
    await fs.appendFile(
      join(TASKS_DIR, taskName, 'task_log.jsonl'),
      logEntry
    );
    
    res.json({ success: true });
  } catch (err) {
    console.error('Error logging selection:', err);
    res.status(500).json({ error: err.message });
  }
});

// Obtener log de una tarea
app.get('/api/tasks/:taskName/log', async (req, res) => {
  try {
    const { taskName } = req.params;
    const logPath = join(TASKS_DIR, taskName, 'task_log.jsonl');
    
    try {
      const logContent = await fs.readFile(logPath, 'utf-8');
      const logEntries = logContent.trim().split('\n').filter(line => line).map(line => JSON.parse(line));
      res.json({ entries: logEntries });
    } catch (err) {
      // Si el archivo no existe, devolver log vacío
      res.json({ entries: [] });
    }
  } catch (err) {
    console.error('Error reading log:', err);
    res.status(500).json({ error: err.message });
  }
});

// Limpiar log de una tarea
app.delete('/api/tasks/:taskName/log', async (req, res) => {
  try {
    const { taskName } = req.params;
    const logPath = join(TASKS_DIR, taskName, 'task_log.jsonl');
    
    await fs.writeFile(logPath, '');
    console.log('Task log cleared for:', taskName);
    res.json({ success: true, message: 'Log cleared successfully' });
  } catch (err) {
    console.error('Error clearing log:', err);
    res.status(500).json({ error: err.message });
  }
});

// Utilidad para desanidar objetos curados { value, curated:true }
function unwrapCurated(value) {
  if (Array.isArray(value)) {
    return value.map(v => unwrapCurated(v));
  }
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    // Si es exactamente un objeto curado
    if ('curated' in value && value.curated === true && 'value' in value && Object.keys(value).every(k => ['value', 'curated'].includes(k))) {
      return value.value; // devolver sólo el valor
    }
    // Recorremos sus propiedades
    const out = {};
    for (const k of Object.keys(value)) {
      out[k] = unwrapCurated(value[k]);
    }
    return out;
  }
  return value;
}

// Exportar archivos curados desanidando estructura { value, curated }
app.get('/api/tasks/:taskName/export', async (req, res) => {
  try {
    const { taskName } = req.params;
    const taskDir = join(TASKS_DIR, taskName);
    const curatedDir = join(taskDir, 'curated');
    try { await fs.stat(taskDir); } catch { return res.status(404).json({ error: 'Task not found' }); }

    // Obtener lista de archivos curados (legacy fallback si carpeta vacía)
    let curatedFiles = [];
    try {
      const stats = await fs.stat(curatedDir);
      if (stats.isDirectory()) {
        curatedFiles = (await fs.readdir(curatedDir)).filter(f => f.endsWith('.json'));
      }
    } catch {}
    if (!curatedFiles.length) {
      // legacy
      const all = await fs.readdir(taskDir);
      curatedFiles = all.filter(f => f.endsWith('_curated.json'));
      if (!curatedFiles.length) {
        return res.json({ task: taskName, files: [] });
      }
    }

    const exported = [];
    for (const file of curatedFiles) {
      try {
        const legacy = file.endsWith('_curated.json');
        const filePath = legacy ? join(taskDir, file) : join(curatedDir, file);
        const raw = await fs.readFile(filePath, 'utf-8');
        const json = JSON.parse(raw);
        const unwrapped = unwrapCurated(json);
        // Construir nombre con sufijo _curated
        let baseName = file;
        if (legacy) {
          baseName = file; // ya incluye _curated
        } else if (file.endsWith('.json')) {
          const noExt = file.slice(0, -5);
            baseName = noExt + '_curated.json';
        }
        exported.push({ filename: baseName, data: unwrapped });
      } catch (err) {
        console.error('Export: error processing', file, err.message);
      }
    }

    res.json({ task: taskName, files: exported, mode: 'multi-file' });
  } catch (err) {
    console.error('Error exporting curated files:', err);
    res.status(500).json({ error: err.message });
  }
});

// Resumen de archivos originales: nombre y primera tabla (sin rows pesados) / metadata
app.get('/api/tasks/:taskName/original-summary', async (req, res) => {
  try {
    const { taskName } = req.params;
    const taskDir = join(TASKS_DIR, taskName);
    const originalDir = join(taskDir, 'original');
    try { await fs.stat(taskDir); } catch { return res.status(404).json({ error: 'Task not found' }); }
    const originalFiles = await listOriginalFiles(taskDir);
    const summaries = [];
    for (const file of originalFiles) {
      let filePath = join(originalDir, file);
      try { await fs.access(filePath); } catch { filePath = join(taskDir, file); }
      try {
        const raw = await fs.readFile(filePath, 'utf-8');
        const json = JSON.parse(raw);
        const { tablesCount, rowsCount } = countTablesAndRows(json, { treatFirstTableAsMetadata: true });
        // Derive cellsCount: iterate through all non-metadata tables and sum cell counts per row (excluding _metadata key per cell value object)
        let cellsCount = 0;
        try {
          if (Array.isArray(json?.tables) && json.tables.length) {
            const tables = (json.tables.length > 1 ? json.tables.slice(1) : json.tables); // metadata skip already handled conceptually
            tables.forEach(tbl => {
              const rowObjs = (tbl.table_fragments ? (tbl.table_fragments.flatMap(f => Array.isArray(f.rows) ? f.rows : [])) : (Array.isArray(tbl.rows) ? tbl.rows : [])) || [];
              rowObjs.forEach(r => {
                if (r && typeof r === 'object') {
                  cellsCount += Object.keys(r).filter(k => k !== '_metadata').length;
                }
              });
            });
          } else if (Array.isArray(json?.tasks) && json.tasks.length) {
            json.tasks.forEach(t => {
              const rowObjs = Array.isArray(t.rows) ? t.rows : [];
              rowObjs.forEach(r => {
                if (r && typeof r === 'object') {
                  cellsCount += Object.keys(r).filter(k => k !== '_metadata').length;
                }
              });
            });
          } else {
            const rowObjs = (json && typeof json === 'object') ? ((json.table_fragments ? (json.table_fragments.flatMap(f => Array.isArray(f.rows) ? f.rows : [])) : (Array.isArray(json.rows) ? json.rows : [])) || []) : [];
            rowObjs.forEach(r => {
              if (r && typeof r === 'object') {
                cellsCount += Object.keys(r).filter(k => k !== '_metadata').length;
              }
            });
          }
        } catch (e) {
          console.warn('Error computing cellsCount for', file, e.message);
        }
        let metadataRows = null;
        if (Array.isArray(json?.tables) && json.tables.length > 1) {
          // Extraer filas (flatten) de la tabla de metadata (índice 0)
          const metaTbl = json.tables[0];
          if (Array.isArray(metaTbl?.table_fragments)) {
            metadataRows = metaTbl.table_fragments.flatMap(f => Array.isArray(f?.rows) ? f.rows : []);
          } else if (Array.isArray(metaTbl?.rows)) {
            metadataRows = metaTbl.rows;
          }
        }
  summaries.push({ filename: file, citation: json.citation || null, tablesCount, rowsCount, cellsCount, metadataRows });
      } catch (err) {
        console.error('Error building original summary for', file, err.message);
      }
    }
    res.json({ task: taskName, files: summaries });
  } catch (err) {
    console.error('Error getting original summary:', err);
    res.status(500).json({ error: err.message });
  }
});

// Resetear archivos curados (eliminar carpeta curated y legacy *_curated.json)
app.delete('/api/tasks/:taskName/curated', async (req, res) => {
  try {
    const { taskName } = req.params;
    const taskDir = join(TASKS_DIR, taskName);
    const curatedDir = join(taskDir, 'curated');

    // Verificar existencia de tarea
    try { await fs.stat(taskDir); } catch { return res.status(404).json({ error: 'Task not found' }); }

    // Eliminar carpeta curated si existe
    try {
      await fs.rm(curatedDir, { recursive: true, force: true });
    } catch (err) {
      console.warn('Could not remove curated dir:', err.message);
    }

    // Eliminar archivos legacy *_curated.json
    try {
      const files = await fs.readdir(taskDir);
      const legacyCurated = files.filter(f => f.endsWith('_curated.json'));
      for (const file of legacyCurated) {
        try { await fs.unlink(join(taskDir, file)); } catch (err) { console.warn('Failed removing legacy curated file', file, err.message); }
      }
    } catch (err) {
      console.warn('Scanning legacy curated files failed:', err.message);
    }

    // Recrear carpeta vacía para futuras escrituras
    await fs.mkdir(curatedDir, { recursive: true });

    res.json({ success: true, message: 'Curated data reset' });
  } catch (err) {
    console.error('Error resetting curated data:', err);
    res.status(500).json({ error: err.message });
  }
});

// Actualizar versión curada de un archivo
app.post('/api/tasks/:taskId/curated/:fileIndex', async (req, res) => {
  try {
    const { taskId, fileIndex } = req.params;
    const { selections } = req.body;
    
    console.log('=== UPDATING CURATED FILE ===');
    console.log('Task ID:', taskId);
    console.log('File Index:', fileIndex);
    console.log('Request body:', JSON.stringify(req.body, null, 2));
    console.log('Selections type:', typeof selections);
    console.log('Selections:', selections);
    
    if (!selections) {
      throw new Error('No selections provided');
    }
    
    const taskDir = join(TASKS_DIR, taskId);
    const curatedDir = join(taskDir, 'curated');
    const originalDir = join(taskDir, 'original');
    await fs.mkdir(curatedDir, { recursive: true });
    const originalFiles = await listOriginalFiles(taskDir);
    const idx = parseInt(fileIndex);
    if (isNaN(idx) || idx < 0 || idx >= originalFiles.length) {
      return res.status(400).json({ error: 'Invalid file index' });
    }
    const originalFile = originalFiles[idx];
    let originalPath = join(originalDir, originalFile);
    try { await fs.access(originalPath); } catch { originalPath = join(taskDir, originalFile); }
    const curatedPath = join(curatedDir, originalFile);
    
    let baseData;
    try {
      // Intentar leer el archivo curado existente como base
      baseData = JSON.parse(await fs.readFile(curatedPath, 'utf-8'));
      console.log('Using existing curated file as base.');
    } catch (error) {
      // Si no existe, usar el archivo original
      console.log('No curated file found, using original file as base.');
      baseData = JSON.parse(await fs.readFile(originalPath, 'utf-8'));
    }

    // Aplicar selecciones a los datos base
    console.log('Applying selections...');
    const curatedData = applySelectionsToData(baseData, selections);
    
    // Guardar versión curada
  const tempPath = join(curatedDir, 'temp_curated_' + Date.now() + '_' + originalFile);
    console.log('Saving to temp file:', tempPath);
    await fs.writeFile(tempPath, JSON.stringify(curatedData, null, 2));
    
    // Renombrar el archivo temporal al final
  await fs.rename(tempPath, curatedPath);
    console.log('Renamed to:', curatedPath);
    
    console.log('=== CURATED FILE UPDATE COMPLETE ===');

    res.json({ success: true });
  } catch (err) {
    console.error('Error updating curated file:', err);
    console.error('Stack:', err.stack);
    res.status(500).json({ error: err.message });
  }
});

// Obtener archivos curados de una tarea
app.get('/api/tasks/:taskName/curated-files', async (req, res) => {
  console.log('=== GET CURATED FILES ===', req.params);
  try {
    const { taskName } = req.params;
    const taskDir = join(TASKS_DIR, taskName);
    const curatedDir = join(taskDir, 'curated');
    
    // Verificar que el directorio existe
    try {
      await fs.stat(taskDir);
    } catch (err) {
      return res.status(404).json({ error: 'Task not found' });
    }
    
    let curatedFiles = [];
    try {
      const curatedStats = await fs.stat(curatedDir);
      if (curatedStats.isDirectory()) {
        curatedFiles = (await fs.readdir(curatedDir)).filter(f => f.endsWith('.json'));
      }
    } catch {
      // fallback legacy
      const legacy = await fs.readdir(taskDir);
      curatedFiles = legacy.filter(f => f.includes('_curated') && f.endsWith('.json'));
      const resultLegacy = [];
      for (const file of curatedFiles) {
        try {
          const filePath = join(taskDir, file);
          const data = JSON.parse(await fs.readFile(filePath, 'utf-8'));
          resultLegacy.push({ filename: file, data });
        } catch (err) {
          console.error('Error reading legacy curated file', file, err.message);
        }
      }
      if (resultLegacy.length) return res.json(resultLegacy);
    }
    
    const result = [];
    for (const file of curatedFiles) {
      try {
        const filePath = join(curatedDir, file);
        const data = JSON.parse(await fs.readFile(filePath, 'utf-8'));
        result.push({
          filename: file,
          data: data
        });
      } catch (err) {
        console.error(`Error reading curated file ${file}:`, err);
      }
    }
    
    res.json(result);
  } catch (err) {
    console.error('Error getting curated files:', err);
    res.status(500).json({ error: err.message });
  }
});

// Endpoint de progreso centralizado
app.get('/api/tasks/:taskName/progress', async (req, res) => {
  try {
    const { taskName } = req.params;
    const taskDir = join(TASKS_DIR, taskName);
    const curatedDir = join(taskDir, 'curated');
    const originalDir = join(taskDir, 'original');

    // 1. Calcular totalCells a partir de los originales (estable y completo)
    const originalFiles = await listOriginalFiles(taskDir);
    let totalCells = 0;
    for (const file of originalFiles) {
      let originalPath = join(originalDir, file);
      try { await fs.access(originalPath); } catch { originalPath = join(taskDir, file); }
      try {
        const raw = await fs.readFile(originalPath, 'utf-8');
        const json = JSON.parse(raw);
  const rows = extractRowsFromJSON(json, { treatFirstTableAsMetadata: true });
        rows.forEach(row => {
          const keys = Object.keys(row).filter(k => k !== '_metadata');
          totalCells += keys.length;
        });
      } catch (err) {
        console.error('Progress: error reading original', file, err.message);
      }
    }

    // 2. Calcular curatedCells a partir de los archivos curados existentes
    let curatedCells = 0;
    try {
      const curatedStats = await fs.stat(curatedDir);
      if (curatedStats.isDirectory()) {
        const curatedFiles = (await fs.readdir(curatedDir)).filter(f => f.endsWith('.json'));
        for (const file of curatedFiles) {
          try {
            const data = JSON.parse(await fs.readFile(join(curatedDir, file), 'utf-8'));
            const rows = extractRowsFromJSON(data, { treatFirstTableAsMetadata: true });
            rows.forEach(row => {
              const keys = Object.keys(row).filter(k => k !== '_metadata');
              keys.forEach(key => {
                const cell = row[key];
                if (cell && typeof cell === 'object' && cell.curated === true) curatedCells++;
              });
            });
          } catch (err) {
            console.error('Progress: error reading curated', file, err.message);
          }
        }
      }
    } catch {
      // No curated dir yet => curatedCells = 0
    }

  const progress = totalCells > 0 ? (curatedCells / totalCells) * 100 : 0;
  console.log('[PROGRESS] Computed', { taskName, curatedCells, totalCells, progress });
  res.json({ curatedCells, totalCells, progress });
  } catch (err) {
    console.error('Error computing progress:', err);
    res.status(500).json({ error: err.message });
  }
});

// Eliminar tarea
app.delete('/api/tasks/:taskName', async (req, res) => {
  try {
    const { taskName } = req.params;
    const taskDir = join(TASKS_DIR, taskName);
    
    // Verificar que el directorio existe
    try {
      await fs.stat(taskDir);
    } catch (err) {
      return res.status(404).json({ error: 'Task not found' });
    }
    
    // Eliminar todo el directorio de la tarea
    await fs.rm(taskDir, { recursive: true, force: true });
    
    res.json({ success: true, message: 'Task deleted successfully' });
  } catch (err) {
    console.error('Error deleting task:', err);
    res.status(500).json({ error: err.message });
  }
});

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
  console.log('Tasks directory:', TASKS_DIR);
});
