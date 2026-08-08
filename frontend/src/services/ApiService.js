import axios from 'axios'
import { getBackendBaseUrl } from '@/utils/runtime'

const api = axios.create({
  baseURL: `${getBackendBaseUrl()}/api`,
  timeout: 300000
})

export class ApiService {
  async downloadModel(modelName) {
    const response = await api.post('/models/download', { model: modelName })
    return response.data
  }

  async getModelStatus() {
    const response = await api.get('/models/status')
    return response.data
  }

  async listModels() {
    const response = await api.get('/models/list')
    return response.data
  }

  async openModelFolder() {
    const response = await api.post('/models/open-folder')
    return response.data
  }

  async listWhisperCppModels() {
    const response = await api.get('/models/whisper-cpp/list')
    return response.data
  }

  async downloadWhisperCppModel(modelName) {
    const response = await api.post('/models/whisper-cpp/download', { model: modelName })
    return response.data
  }

  async getWhisperCppModelStatus() {
    const response = await api.get('/models/whisper-cpp/status')
    return response.data
  }

  async listWhisperCTranslate2Models() {
    const response = await api.get('/models/whisper-ctranslate2/list')
    return response.data
  }

  async downloadWhisperCTranslate2Model(modelName) {
    const response = await api.post('/models/whisper-ctranslate2/download', { model: modelName })
    return response.data
  }

  async getWhisperCTranslate2ModelStatus() {
    const response = await api.get('/models/whisper-ctranslate2/status')
    return response.data
  }

  async listVoskModels() {
    const response = await api.get('/models/vosk/list')
    return response.data
  }

  async downloadVoskModel(modelCode) {
    const response = await api.post('/models/vosk/download', { model_code: modelCode })
    return response.data
  }

  async getVoskDownloadStatus() {
    const response = await api.get('/models/vosk/status')
    return response.data
  }

  async transcribe(file, model, language, engine = 'openai', useGpu = true) {
    const formData = new FormData()
    formData.append('model', model)
    formData.append('engine', engine)
    formData.append('use_gpu', useGpu ? 'true' : 'false')
    if (language && language !== 'Auto-detect') {
      formData.append('language', language.toLowerCase())
    }

    // 支持文件路径字符串（Electron）和 File 对象（浏览器）
    if (typeof file === 'string') {
      formData.append('file_path', file)
    } else {
      formData.append('file', file)
    }

    const response = await api.post('/transcribe', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    return response.data
  }

  async getTranscribeStatus(taskId) {
    const response = await api.get(`/transcribe/${taskId}`)
    return response.data
  }

  async getTranscribeResult(taskId) {
    const response = await api.get(`/transcribe/${taskId}/result`)
    return response.data
  }

  async cancelTranscribe(taskId) {
    const response = await api.post(`/transcribe/${taskId}/cancel`)
    return response.data
  }

  async saveOriginalSubtitle(srtContent, filename, overwrite = false) {
    const response = await api.post('/subtitle/save-original', { srt: srtContent, filename, overwrite })
    return response.data
  }

  async saveTranslationSubtitle(srtContent, filename, overwrite = false) {
    const response = await api.post('/subtitle/save-translation', { srt: srtContent, filename, overwrite })
    return response.data
  }

  async translate(data) {
    const response = await api.post('/translate', data)
    return response.data
  }

  async checkSpelling(text) {
    const response = await api.post('/spell-check', { text })
    return response.data
  }

  async spellCheckAI(data) {
    const response = await api.post('/spell-check/ai', data)
    return response.data
  }

  async getSpellingSuggestions(word) {
    const response = await api.post('/spell-check/suggestions', { word })
    return response.data
  }

  async addToDictionary(word) {
    const response = await api.post('/spell-check/dictionary/add', { word })
    return response.data
  }

  async removeFromDictionary(word) {
    const response = await api.post('/spell-check/dictionary/remove', { word })
    return response.data
  }

  async addToNames(name) {
    const response = await api.post('/spell-check/names/add', { name })
    return response.data
  }

  async removeFromNames(name) {
    const response = await api.post('/spell-check/names/remove', { name })
    return response.data
  }

  async getDictionary() {
    const response = await api.get('/spell-check/dictionary')
    return response.data
  }

  async getNames() {
    const response = await api.get('/spell-check/names')
    return response.data
  }

  // ============= 设置 / 诊断 =============

  async getDiagnostics() {
    const response = await api.get('/diagnostics')
    return response.data
  }

  async getDiagnosticText() {
    const response = await api.get('/diagnostics/text')
    return response.data
  }

  async getVersionInfo() {
    const response = await api.get('/version')
    return response.data
  }

  async getHealthCheck() {
    const response = await api.get('/health')
    return response.data
  }

  // ============= 缓存管理 =============

  async getCacheStats() {
    const response = await api.get('/cache/stats')
    return response.data
  }

  async cleanTempAudio() {
    const response = await api.post('/cache/clean/audio')
    return response.data
  }

  async cleanWaveformCache() {
    const response = await api.post('/cache/clean/waveform')
    return response.data
  }

  async cleanTaskResults() {
    const response = await api.post('/cache/clean/task-results')
    return response.data
  }

  // ============= 目录操作 =============

  async openDirectory(type) {
    const response = await api.post('/open-directory', { type })
    return response.data
  }

  async openLogsDirectory() {
    const response = await api.post('/open-logs')
    return response.data
  }

  async generateWaveform(file, samplesPerSecond = 100) {
    if (typeof file === 'string') {
      const response = await api.post('/waveform/generate-from-path', {
        file_path: file,
        samples_per_second: samplesPerSecond
      }, {
        timeout: 120000
      })
      return response.data
    } else {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('samples_per_second', samplesPerSecond)
      
      const response = await api.post('/waveform/generate', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 120000
      })
      return response.data
    }
  }
}

export const apiService = new ApiService()
