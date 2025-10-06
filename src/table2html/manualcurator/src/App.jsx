import React, { useState, useRef, useEffect } from 'react';
import ControlsPanel from './components/ControlsPanel';
import LeftSidebar from './components/LeftSidebar';
import CreateTaskView from './components/CreateTaskView';
import CurrentTasksView from './components/CurrentTasksView';
import useHeader from './hooks/useHeader';
import useTheme from './hooks/useTheme';
import { createTaskFromImported } from './utils/taskUtils';
import { createTask, getTasks, updateCuratedFile, deleteTask } from './utils/api';

export default function App() {
  const [tasks, setTasks] = useState([]);
  const [currentTaskIdx, setCurrentTaskIdx] = useState(null);
  const [currentRowIdx, setCurrentRowIdx] = useState(0);
  const [selections, setSelections] = useState({});
  const [selectedTab, setSelectedTab] = useState('create');

  const [taskTitle, setTaskTitle] = useState('');
  const [importedTables, setImportedTables] = useState(null);

  const headerRef = useRef(null);
  const { isDark, textColor, setTheme } = useTheme();

  useEffect(() => {
    getTasks()
      .then(serverTasks => {
        const processedTasks = serverTasks.map(task => {
          const { name, rows, path, originalFiles } = task;
          const shuffledRows = [...rows].sort(() => Math.random() - 0.5);
          return { name, rows: shuffledRows, path, originalFiles };
        });
        setTasks(processedTasks);
      })
      .catch(console.error);
  }, []);

  useEffect(() => {
    const currentTask = tasks[currentTaskIdx];
    if (!currentTask?.path || currentTaskIdx == null) return;

    // Only update curated files when task changes, not when selections change
    // Selections will be updated manually when user presses Next
  }, [currentTaskIdx, tasks]);

  function handleImportTablesFile(e) {
    const files = Array.from(e.target.files || []);
    if (files.length === 0) return;

    let processedFiles = 0;
    const fileNames = [];
    const originalData = [];
    const tables = [];
    let allRows = [];

    files.forEach(file => {
      const reader = new FileReader();
      reader.onload = (ev) => {
        try {
          const json = JSON.parse(ev.target.result);
          fileNames.push(file.name);
          originalData.push(json);

          if (Array.isArray(json.tables)) {
            const dataTables = json.tables.slice(1);
            dataTables.forEach((table, tableIdx) => {
              const tableRows = [];
              if (Array.isArray(table.table_fragments)) {
                table.table_fragments.forEach(fragment => {
                  if (Array.isArray(fragment.rows)) {
                    tableRows.push(...fragment.rows);
                  }
                });
              }
              tables.push({
                fileIndex: processedFiles,
                tableIndex: tableIdx + 1,
                rows: tableRows,
              });
              allRows.push(...tableRows);
            });
          }
          processedFiles++;
          if (processedFiles === files.length) {
            setImportedTables({
              files: fileNames,
              tables,
              rows: allRows,
              originalData,
            });
          }
        } catch (err) {
          console.error(`Error parsing ${file.name}:`, err);
          alert(`Error reading JSON from ${file.name}: ${err?.message || String(err)}`);
        }
      };
      reader.readAsText(file);
    });
    e.target.value = '';
  }

  async function handleCreateTask() {
    if (!taskTitle) {
      alert('Por favor, ingresa un título para la tarea');
      return;
    }
    if (!importedTables || !importedTables.files || importedTables.files.length === 0) {
      alert('Por favor, importa al menos un archivo JSON');
      return;
    }
    if (!importedTables.rows || importedTables.rows.length === 0) {
      alert('No se encontraron filas para procesar en los archivos importados');
      return;
    }

    try {
      const result = await createTask(
        taskTitle,
        importedTables.files,
        importedTables.originalData
      );

      // Recargar la lista de tareas desde el servidor para asegurar consistencia
      const serverTasks = await getTasks();
      const processedTasks = serverTasks.map(task => {
        const { name, rows, path, originalFiles } = task;
        const shuffledRows = [...rows].sort(() => Math.random() - 0.5);
        return { name, rows: shuffledRows, path, originalFiles };
      });
      setTasks(processedTasks);

      setImportedTables(null);
      setTaskTitle('');
      setSelectedTab('current');
      
      console.log('Task created successfully, tasks reloaded');
    } catch (err) {
      console.error('Error creating task:', err);
      alert('Error creating task: ' + err.message);
    }
  }

  async function handleDeleteTask(taskIndex) {
    console.log('handleDeleteTask called with taskIndex:', taskIndex);
    try {
      const taskToDelete = tasks[taskIndex];
      if (!taskToDelete?.path) {
        throw new Error('Task path not found');
      }

      console.log('Deleting task:', taskToDelete.name, 'at index:', taskIndex, 'currentTaskIdx:', currentTaskIdx);

      await deleteTask(taskToDelete.path);
      
      // Recargar la lista de tareas desde el servidor para asegurar consistencia
      const serverTasks = await getTasks();
      const processedTasks = serverTasks.map(task => {
        const { name, rows, path, originalFiles } = task;
        const shuffledRows = [...rows].sort(() => Math.random() - 0.5);
        return { name, rows: shuffledRows, path, originalFiles };
      });
      setTasks(processedTasks);

      // Si la tarea eliminada era la actual, limpiar la selección y volver a la pestaña create
      if (currentTaskIdx === taskIndex) {
        setCurrentTaskIdx(null);
        setCurrentRowIdx(0);
        setSelections({});
        // Solo cambiar a create si no hay otras tareas disponibles
        if (processedTasks.length === 0) {
          setSelectedTab('create');
        }
        console.log('Deleted current task, cleared selection');
      } else if (currentTaskIdx > taskIndex) {
        // Ajustar el índice si la tarea eliminada estaba antes de la actual
        const newTaskIdx = currentTaskIdx - 1;
        setCurrentTaskIdx(newTaskIdx);
        console.log('Adjusted currentTaskIdx from', currentTaskIdx, 'to', newTaskIdx);
      }
      // Si currentTaskIdx < taskIndex, no necesitamos hacer nada
      
      console.log('Task deleted successfully, tasks reloaded');
    } catch (err) {
      console.error('Error deleting task:', err);
      alert('Error deleting task: ' + err.message);
    }
  }

  function onSelect(col, val) {
    if (currentTaskIdx == null) return;
    const sourceFile = currentRow?._metadata?.sourceFile || 'unknown_file';
    const originalIndex = currentRow?._metadata?.originalIndex ?? currentRowIdx;
    setSelections(prev => {
      const copy = { ...prev };
      if (!copy[currentTaskIdx]) copy[currentTaskIdx] = {};
      if (!copy[currentTaskIdx][sourceFile]) copy[currentTaskIdx][sourceFile] = {};
      if (!copy[currentTaskIdx][sourceFile][originalIndex]) copy[currentTaskIdx][sourceFile][originalIndex] = {};
      copy[currentTaskIdx][sourceFile][originalIndex][col] = val;
      return copy;
    });
  }

  function goNext() {
    if (currentTaskIdx == null) return;
    const total = tasks[currentTaskIdx]?.rows?.length || 0;
    if (currentRowIdx < total - 1) setCurrentRowIdx(s => s + 1);
  }

  function goPrev() {
    if (currentTaskIdx == null) return;
    if (currentRowIdx > 0) setCurrentRowIdx(s => s - 1);
  }

  const currentTask = currentTaskIdx != null ? tasks[currentTaskIdx] : null;
  const currentRow = currentTask ? (currentTask.rows[currentRowIdx] || {}) : null;
  const totalRows = currentTask ? (currentTask.rows.length || 0) : 0;

  // Fisher-Yates shuffle utility
  function shuffleArray(arr) {
    const a = [...arr];
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  }

  function shuffleCurrentTaskRows(taskIdx) {
    if (taskIdx == null) return;
    setTasks(prev => {
      const copy = [...prev];
      if (!copy[taskIdx] || !Array.isArray(copy[taskIdx].rows)) return prev;
      copy[taskIdx] = { ...copy[taskIdx], rows: shuffleArray(copy[taskIdx].rows) };
      return copy;
    });
    setCurrentRowIdx(0);
  }

  // Debugging para identificar problemas con la selección de tareas
  useEffect(() => {
    console.log('App state update:', {
      currentTaskIdx,
      currentTask: currentTask ? { name: currentTask.name, path: currentTask.path, rowsLength: currentTask.rows?.length } : null,
      tasksLength: tasks.length,
      selectedTab
    });
  }, [currentTaskIdx, currentTask, tasks, selectedTab]);

  const onUpdateCurated = async (rowIdx, rowSelections, sourceFile) => {
    if (currentTaskIdx == null || !currentTask) return;
    try {
      const fileIndex = currentTask.originalFiles.findIndex(f => f === sourceFile);
      if (fileIndex === -1) {
        console.warn('Could not map sourceFile to fileIndex. Aborting curated update.', sourceFile);
        return;
      }
      console.log('=== FRONTEND: Updating curated single file ===', { rowIdx, sourceFile, fileIndex, rowSelections });
      await updateCuratedFile(currentTask.path, fileIndex, { [rowIdx]: rowSelections });
      console.log('=== FRONTEND: Single curated file update completed ===');
    } catch (err) {
      console.error('Error updating curated file:', err);
    }
  };

  return (
    <div style={{ width: '100%', minHeight: '100vh', background: 'var(--color-bg)', color: 'var(--color-text)', fontFamily: 'var(--font-sans)' }}>
      <header ref={headerRef} style={{ width: '100%', boxSizing: 'border-box', padding: '40px clamp(24px,4vw,64px) 28px', position: 'relative' }}>
        <div style={{ maxWidth: 'var(--container-max)', margin: '0 auto', display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 48, flexWrap: 'wrap' }}>
          <div style={{ flex: '1 1 480px', minWidth: 320 }}>
            <h1 className="title-display" style={{ marginBottom: 12 }}>Manual Curator<span style={{ color: 'var(--color-text-faint)', fontWeight: 600 }}> – paper2table</span></h1>
            <p style={{ margin: 0, maxWidth: 640, fontSize: '15px', lineHeight: 1.5, color: 'var(--color-text-soft)', fontWeight: 400 }}>
              A focused interface to curate tabular extractions from research papers. Import JSON files with tables, review rows, and progressively build high-quality curated datasets with confidence.
            </p>
          </div>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 16 }}>
            <ControlsPanel
              isDark={isDark}
              setTheme={setTheme}
            />
          </div>
        </div>
      </header>

      <div style={{ display: 'flex', minHeight: 'calc(100vh - 220px)', padding: '0 clamp(24px,4vw,64px) 64px' }}>
        <LeftSidebar
          tasks={tasks}
          selectedTab={selectedTab}
          onTabChange={setSelectedTab}
          currentTaskIdx={currentTaskIdx}
          currentRowIdx={currentRowIdx}
          totalRows={totalRows}
          onStart={(i) => {
            console.log('Starting task at index:', i, 'Task data:', tasks[i]);
            if (tasks[i] && tasks[i].rows && tasks[i].rows.length > 0) {
              setCurrentTaskIdx(i);
              setCurrentRowIdx(0);
              setSelectedTab('current');
            } else {
              console.error('Invalid task data at index:', i, tasks[i]);
              alert('Error: Task data is invalid. Please try reloading the page.');
            }
          }}
          onDeleteTask={handleDeleteTask}
          isDark={isDark}
          textColor={textColor}
        />
        <main style={{ flex: 1, padding: '0 0 60px', maxWidth: 'var(--container-max)', margin: '0 auto' }}>
          {selectedTab === 'create' && (
            <CreateTaskView
              taskTitle={taskTitle}
              setTaskTitle={setTaskTitle}
              importedTables={importedTables}
              onImportFile={handleImportTablesFile}
              onCreate={handleCreateTask}
              isDark={isDark}
              textColor={textColor}
            />
          )}
          {selectedTab === 'current' && currentTask && currentTask.rows && currentTask.rows.length > 0 && (
            <CurrentTasksView
              currentTask={currentTask}
              currentTaskIdx={currentTaskIdx}
              currentRowIdx={currentRowIdx}
              currentRow={currentRow}
              totalRows={totalRows}
              onPrev={goPrev}
              onNext={goNext}
              onSelect={onSelect}
              onDeleteTask={() => {
                console.log('onDeleteTask called with currentTaskIdx:', currentTaskIdx);
                handleDeleteTask(currentTaskIdx);
              }}
              onUpdateCurated={onUpdateCurated}
              onResetSelections={() => {
                setSelections(prev => {
                  const copy = { ...prev };
                  delete copy[currentTaskIdx];
                  return copy;
                });
              }}
              onShuffleTaskRows={() => shuffleCurrentTaskRows(currentTaskIdx)}
              currentSelections={(() => {
                const sourceFile = currentRow._metadata?.sourceFile || 'unknown_file';
                const originalIndex = currentRow._metadata?.originalIndex ?? currentRowIdx;
                return selections[currentTaskIdx]?.[sourceFile]?.[originalIndex] || {};
              })()}
              // Pasar mapping extra si se necesitara en el futuro
              isDark={isDark}
              textColor={textColor}
            />
          )}
          {selectedTab === 'current' && (!currentTask || !currentTask.rows || currentTask.rows.length === 0) && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              minHeight: '40vh',
              color: 'var(--color-text-soft)',
              fontSize: '15px',
              background: 'var(--color-surface)',
              border: '1px dashed var(--color-border)',
              borderRadius: 'var(--radius-lg)',
              padding: '48px 32px',
              fontWeight: 500
            }}>
              No task selected or the selected task has no rows. Create or select a task from the sidebar to begin.
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
