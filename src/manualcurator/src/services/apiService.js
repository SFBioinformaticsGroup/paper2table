import { API_CONFIG } from '../config/config.js';
import { ERROR_MESSAGES } from '../constants/constants.js';

class ApiService {
  constructor() {
    this.baseURL = API_CONFIG.BASE_URL;
    this.timeout = API_CONFIG.TIMEOUT;
  }

  /**
   * Generic HTTP request method
   */
  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const config = {
      timeout: this.timeout,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      },
      ...options
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      if (error.name === 'TypeError' && error.message.includes('fetch')) {
        throw new Error(ERROR_MESSAGES.NETWORK_ERROR);
      }
      throw error;
    }
  }

  /**
   * GET request
   */
  async get(endpoint) {
    return this.request(endpoint, { method: 'GET' });
  }

  /**
   * POST request
   */
  async post(endpoint, data) {
    return this.request(endpoint, {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }

  /**
   * PUT request
   */
  async put(endpoint, data) {
    return this.request(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data)
    });
  }

  /**
   * DELETE request
   */
  async delete(endpoint) {
    return this.request(endpoint, { method: 'DELETE' });
  }

  // Task-specific methods
  
  /**
   * Get all tasks
   */
  async getTasks() {
    return this.get(API_CONFIG.ENDPOINTS.TASKS);
  }

  /**
   * Create a new task
   */
  async createTask(taskData) {
    return this.post(API_CONFIG.ENDPOINTS.TASKS, taskData);
  }

  /**
   * Delete a task
   */
  async deleteTask(taskPath) {
    return this.delete(`${API_CONFIG.ENDPOINTS.TASKS}/${taskPath}`);
  }

  /**
   * Log task selection
   */
  async logSelection(taskId, selection) {
    return this.post(`${API_CONFIG.ENDPOINTS.TASKS}/${taskId}/log`, { selection });
  }

  /**
   * Get curated data for a task
   */
  async getCuratedData(taskPath) {
    return this.get(`${API_CONFIG.ENDPOINTS.TASKS}/${taskPath}/curated`);
  }

  /**
   * Save curated progress
   */
  async saveCuratedProgress(taskPath, curationMode, data) {
    return this.post(`${API_CONFIG.ENDPOINTS.TASKS}/${taskPath}/curated/save`, {
      curationMode,
      data
    });
  }

  /**
   * Update curated file
   */
  async updateCuratedFile(taskId, fileIndex, selections) {
    return this.post(`${API_CONFIG.ENDPOINTS.TASKS}/${taskId}/curated/${fileIndex}`, {
      selections
    });
  }

  /**
   * Health check
   */
  async healthCheck() {
    return this.get(API_CONFIG.ENDPOINTS.HEALTH);
  }
}

// Export singleton instance
export const apiService = new ApiService();

// Export legacy functions for backward compatibility
export const getTasks = () => apiService.getTasks();
export const createTask = (taskTitle, files, originalData) => 
  apiService.createTask({ taskTitle, files, originalData });
export const deleteTask = (taskPath) => apiService.deleteTask(taskPath);
export const logSelection = (taskId, selection) => apiService.logSelection(taskId, selection);
export const saveCuratedProgress = (taskPath, curationMode, data) => 
  apiService.saveCuratedProgress(taskPath, curationMode, data);
export const updateCuratedFile = (taskId, fileIndex, selections) => 
  apiService.updateCuratedFile(taskId, fileIndex, selections);