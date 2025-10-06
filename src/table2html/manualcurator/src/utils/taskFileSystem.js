import fs from 'fs';
import path from 'path';

export function createTaskDirectory(taskName) {
  const safeName = taskName.replace(/[^a-z0-9]/gi, '_').toLowerCase();
  const taskPath = path.join(process.cwd(), 'src', 'tasks', safeName);
  
  if (!fs.existsSync(taskPath)) {
    fs.mkdirSync(taskPath, { recursive: true });
  }
  
  return taskPath;
}

export function saveTaskFiles(taskPath, files, originalData) {
  // Save original files
  files.forEach((file, index) => {
    fs.writeFileSync(
      path.join(taskPath, file.name),
      JSON.stringify(originalData[index], null, 2)
    );
  });

  // Initialize log file
  const logFile = path.join(taskPath, 'task_log.jsonl');
  if (!fs.existsSync(logFile)) {
    fs.writeFileSync(logFile, '');
  }
}

export function logSelection(taskPath, selection) {
  const logFile = path.join(taskPath, 'task_log.jsonl');
  const logEntry = {
    timestamp: new Date().toISOString(),
    user: process.env.USER || 'unknown',
    ip: process.env.IP || 'localhost',
    selection
  };

  fs.appendFileSync(logFile, JSON.stringify(logEntry) + '\n');
}

export function saveCuratedVersion(taskPath, fileName, curatedData) {
  const curatedName = fileName.replace('.json', '_curated.json');
  fs.writeFileSync(
    path.join(taskPath, curatedName),
    JSON.stringify(curatedData, null, 2)
  );
}
