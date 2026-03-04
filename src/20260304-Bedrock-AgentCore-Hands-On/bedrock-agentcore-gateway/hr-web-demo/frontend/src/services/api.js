import axios from 'axios'

const API_BASE_URL = (() => {
    if (window.location.hostname.includes('sagemaker.aws')) {
      return '/proxy/8000'
    }
    if (import.meta.env.VITE_API_BASE_URL) {
      return import.meta.env.VITE_API_BASE_URL
    }
    return 'http://localhost:8000'
})()


const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor for authentication and logging
api.interceptors.request.use(
  (config) => {
    // Add authentication token if available
    const userInfo = localStorage.getItem('userInfo')
    if (userInfo) {
      try {
        const user = JSON.parse(userInfo)
        if (user.access_token) {
          config.headers.Authorization = `Bearer ${user.access_token}`
        }
        // Also add username header for employee self-access
        if (user.username) {
          config.headers['X-User-Name'] = user.username
        }
      } catch (e) {
        console.error('Error parsing user info from localStorage:', e)
      }
    }
    
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`, config.data)
    return config
  },
  (error) => {
    console.error('API Request Error:', error)
    return Promise.reject(error)
  }
)

// Response interceptor for logging and error handling
api.interceptors.response.use(
  (response) => {
    console.log(`API Response: ${response.config.method?.toUpperCase()} ${response.config.url}`, response.data)
    return response
  },
  (error) => {
    console.error('API Response Error:', error.response?.data || error.message)
    return Promise.reject(error)
  }
)

export const hrApi = {
  // Health check
  async healthCheck() {
    const response = await api.get('/health')
    return response.data
  },

  // Authentication
  async login(username, password) {
    const response = await api.post('/auth/login', { username, password })
    return response.data
  },

  // Get deployment info
  async getDeploymentInfo() {
    const response = await api.get('/deployment/info')
    return response.data
  },

  // Get available tools for a role
  async getTools(role) {
    const response = await api.get(`/tools/${role}`)
    return response.data
  },

  // Employee search
  async searchEmployees(role, searchParams) {
    const response = await api.post(`/employees/search/${role}`, searchParams)
    return response.data
  },

  // Leave management (HR only)
  async getLeaveManagement(role, leaveParams) {
    const response = await api.post(`/leave/management/${role}`, leaveParams)
    return response.data
  },

  // Personal leave
  async getPersonalLeave(role, employeeId) {
    const response = await api.post(`/leave/personal/${role}`, { employee_id: employeeId })
    return response.data
  },

  // Generic tool call
  async callTool(role, toolName, args) {
    const response = await api.post(`/tools/call/${role}`, {
      tool_name: toolName,
      arguments: args
    })
    return response.data
  },

  // Get all employees (HR only)
  async getAllEmployees(role) {
    const response = await api.post(`/employees/all/${role}`, {
      list_all: true
    })
    return response.data
  },

  // Get employee list for quick tags
  async getEmployeeList() {
    const response = await api.get('/employees/list')
    return response.data
  }
}

/**
 * Chat with HR Agent via SSE streaming.
 * @param {string} role - User role (hr-manager / employee)
 * @param {string} username - Username
 * @param {string} message - User message
 * @param {function} onEvent - Callback for each SSE event { type, content }
 * @returns {Promise} resolves when stream ends
 */
export async function chatWithAgent(role, username, message, onEvent) {
  const userInfo = localStorage.getItem('userInfo')
  const headers = { 'Content-Type': 'application/json' }
  if (userInfo) {
    try {
      const user = JSON.parse(userInfo)
      if (user.access_token) headers['Authorization'] = `Bearer ${user.access_token}`
    } catch (e) { /* ignore */ }
  }

  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ role, username, message })
  })

  if (!response.ok) {
    throw new Error(`Chat request failed: ${response.status}`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() // keep incomplete line in buffer

    for (const line of lines) {
      const trimmed = line.trim()
      if (trimmed.startsWith('data: ')) {
        try {
          const event = JSON.parse(trimmed.slice(6))
          onEvent(event)
        } catch (e) {
          console.warn('[SSE] Failed to parse event:', trimmed.substring(0, 200), e)
        }
      }
    }
  }
}

export default api