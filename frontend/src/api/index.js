import axios from 'axios'

import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE || '/api'

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000
})

// 同步状态
export const getSyncStatus = () => api.get('/sync/status')

export const triggerSync = () => api.post('/sync')

// 订阅源
export const getSources = () => api.get('/sources')

export const createSource = (data) => api.post('/sources', data)

export const updateSource = (id, data) => api.put(`/sources/${id}`, data)

export const deleteSource = (id) => api.delete(`/sources/${id}`)

// Skills
export const getSkills = (status) => {
  const params = status ? { status } : {}
  return api.get('/skills', { params })
}

export const getSkill = (id) => api.get(`/skills/${id}`)

// 冲突
export const getConflicts = () => api.get('/conflicts')

export const getConflict = (id) => api.get(`/conflicts/${id}`)

export const resolveConflict = (id, data) => api.post(`/conflicts/${id}/resolve`, data)

// 元数据
export const getMetadata = () => api.get('/metadata')

// 下载
export const downloadSkills = (scope = 'ready') => api.get('/download', { params: { scope } })
