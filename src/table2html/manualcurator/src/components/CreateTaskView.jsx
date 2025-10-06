import React, { useRef } from 'react';

export default function CreateTaskView({ 
  taskTitle, 
  setTaskTitle, 
  importedTables, 
  onImportFile, 
  onCreate, 
  isDark, 
  textColor 
}) {
  const importInputRef = useRef(null);

  const isCreateDisabled = !taskTitle || !importedTables || !importedTables.files || importedTables.files.length === 0;

  return (
    <section style={{ marginBottom: 16 }}>
      <h3 style={{ color: textColor }}>Create task</h3>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12, maxWidth: 700 }}>
        <label style={{ fontSize: 13, color: textColor }}>Task title</label>
        <input
          placeholder="Enter task title..."
          value={taskTitle}
          onChange={(e) => setTaskTitle(e.target.value)}
          style={{ padding: '8px 10px', borderRadius: 8, border: '1px solid rgba(0,0,0,0.08)', width: 400 }}
        />

        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <input 
              ref={importInputRef} 
              type="file" 
              accept="application/json" 
              onChange={onImportFile} 
              multiple
              style={{ display: 'none' }} 
            />
            <button
              onClick={() => importInputRef.current?.click()}
              style={{ padding: '8px 12px', borderRadius: 8, cursor: 'pointer' }}
            >
              Import files
            </button>
            <div style={{ fontSize: 13, color: isDark ? 'rgba(255,255,255,0.7)' : '#444' }}>
              {importedTables ? 
                `(${importedTables.files.length} files, ${importedTables.tables.length} tables, ${importedTables.rows.length} rows)` : 
                '(no files)'
              }
            </div>
          </div>

          {importedTables?.files.length > 0 && (
            <div style={{ marginLeft: 12 }}>
              {importedTables.files.map((f, i) => (
                <div key={i} style={{ fontSize: 13, color: isDark ? 'rgba(255,255,255,0.6)' : '#666' }}>
                  • {f}
                </div>
              ))}
            </div>
          )}
        </div>

        <div style={{ marginTop: 8, fontSize: 13, color: isDark ? 'rgba(255,255,255,0.7)' : '#444' }}>
          Use Import to load table(s) JSON; CREATE will generate a task from the imported rows.
        </div>

        <div style={{ marginTop: 16 }}>
          <button
            onClick={onCreate}
            disabled={isCreateDisabled}
            style={{ 
              padding: '10px 14px', 
              borderRadius: 8, 
              background: isCreateDisabled ? '#ccc' : '#24d453', 
              color: '#fff', 
              cursor: isCreateDisabled ? 'not-allowed' : 'pointer',
              opacity: isCreateDisabled ? 0.7 : 1
            }}
          >
            CREATE
          </button>
          {isCreateDisabled && (
            <div style={{ 
              marginTop: 8, 
              fontSize: 13, 
              color: isDark ? 'rgba(255,255,255,0.5)' : 'rgba(0,0,0,0.5)' 
            }}>
              {!taskTitle ? 'Ingresa un título para la tarea' : 'Importa al menos un archivo JSON'}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
