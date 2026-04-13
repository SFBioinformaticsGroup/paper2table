const API_URL = 'http://localhost:3001/api';

export async function createTask(taskTitle, files, originalData) {
  const response = await fetch(`${API_URL}/tasks`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      taskTitle,
      files,
      originalData
    })
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}

export async function logSelection(taskId, selection) {
  const response = await fetch(`${API_URL}/tasks/${taskId}/log`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ selection })
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}

export async function getTasks() {
  const response = await fetch(`${API_URL}/tasks`);
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}

export async function deleteTask(taskPath) {
  const response = await fetch(`${API_URL}/tasks/${taskPath}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}

export async function updateCuratedFile(taskId, fileIndex, selections) {
  const response = await fetch(`${API_URL}/tasks/${taskId}/curated/${fileIndex}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ selections })
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}

export async function logCurationAction(taskName, selection) {
  const response = await fetch(`${API_URL}/tasks/${taskName}/log`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ selection })
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}

export async function getTaskLog(taskName) {
  const response = await fetch(`${API_URL}/tasks/${taskName}/log`);

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}

export async function clearTaskLog(taskName) {
  const response = await fetch(`${API_URL}/tasks/${taskName}/log`, {
    method: 'DELETE'
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}

export async function getCuratedFiles(taskPath) {
  const response = await fetch(`${API_URL}/tasks/${taskPath}/curated-files`);

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}

export async function getProgress(taskPath) {
  const response = await fetch(`${API_URL}/tasks/${taskPath}/progress`);
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}

export async function resetCurated(taskPath) {
  const response = await fetch(`${API_URL}/tasks/${taskPath}/curated`, {
    method: 'DELETE'
  });
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}

export async function exportCurated(taskPath) {
  const response = await fetch(`${API_URL}/tasks/${taskPath}/export`);
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}

export async function getOriginalSummary(taskPath) {
  const response = await fetch(`${API_URL}/tasks/${taskPath}/original-summary`);
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}
