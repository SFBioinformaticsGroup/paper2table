import { useState, useCallback } from 'react';
import { saveCuratedVersion, logSelection } from '../utils/taskFileSystem';

export default function useTaskFiles(taskPath) {
  const [saveError, setSaveError] = useState(null);

  const logUserSelection = useCallback((selection) => {
    try {
      logSelection(taskPath, selection);
    } catch (err) {
      console.error('Error logging selection:', err);
    }
  }, [taskPath]);

  const saveCurated = useCallback((fileName, data) => {
    try {
      saveCuratedVersion(taskPath, fileName, data);
      setSaveError(null);
    } catch (err) {
      console.error('Error saving curated version:', err);
      setSaveError(err.message);
    }
  }, [taskPath]);

  return { logUserSelection, saveCurated, saveError };
}
