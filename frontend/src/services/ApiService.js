import axios from 'axios'
import { getBackendBaseUrl } from '@/utils/runtime'

/**
 * 统一响应结构(后端所有 /api/* JSON 均返回该结构)
 * @typedef {Object} ApiResponse
 * @property {boolean} success - 是否成功
 * @property {*} data - 业务数据(成功时)
 * @property {number|string} error_code - 0 表示成功,失败时为 HTTP 状态码或业务错误码
 * @property {string} message - 提示信息
 */

/**
 * 转录异步任务对象
 * @typedef {Object} TranscribeTask
 * @property {string} task_id - 任务 ID
 * @property {string} status - 任务状态(pending/processing/completed/failed/cancelled)
 * @property {number} [progress] - 进度 0-100
 * @property {string} [error] - 失败原因
 */

/** 判断是否为后端统一响应结构(三键齐备才算,避免误伤业务数据中的偶发 success 字段) */
function isUnifiedEnvelope(d) {
  return !!d && typeof d === 'object' && 'success' in d && 'error_code' in d && 'data' in d
}

/** 后端 API 业务错误(统一结构中 success=false 时抛出) */
export class ApiError extends Error {
  /**
   * @param {string} message - 错误提示
   * @param {number|string} [errorCode] - 业务/HTTP 错误码
   * @param {*} [data] - 附带数据
   */
  constructor(message, errorCode, data) {
    super(message)
    this.name = 'ApiError'
    this.errorCode = errorCode
    this.data = data
  }
}

const api = axios.create({
  baseURL: `${getBackendBaseUrl()}/api`,
  timeout: 300000
})

// 统一解壳:成功剥出 data,失败转 ApiError;网络/HTTP 错误规范化 message
api.interceptors.response.use(
  (response) => {
    const d = response.data
    if (isUnifiedEnvelope(d)) {
      if (d.success) {
        response.data = d.data
      } else {
        return Promise.reject(new ApiError(d.message || '请求失败', d.error_code, d.data))
      }
    }
    return response
  },
  (error) => {
    const d = error.response?.data
    if (isUnifiedEnvelope(d) && d.success === false) {
      error.apiMessage = d.message || '请求失败'
      error.apiErrorCode = d.error_code
    } else if (d && typeof d === 'object' && (d.error || d.message)) {
      // 兼容未走统一包装的错误体
      error.apiMessage = d.error || d.message
    }
    // 覆盖 axios 默认的 "Request failed with status code xxx",让现有 catch 分支直接拿到可读信息
    if (error.apiMessage) error.message = error.apiMessage
    return Promise.reject(error)
  }
)

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
    // 已合并到统一目录打开接口(type='model' → Whisper 模型缓存目录)
    const response = await api.post('/open-directory', { type: 'model' })
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

  /**
   * 发起异步转录任务
   * @param {File|string} file - 文件对象(浏览器)或本地路径(Electron)
   * @param {string} model - 模型名
   * @param {string} [language] - 语言代码,空则自动检测
   * @param {string} [engine] - 引擎(openai/faster-whisper/whisper-cpp/vosk)
   * @param {boolean} [useGpu] - 是否使用 GPU
   * @param {{signal?: AbortSignal}} [options] - 可选取消信号
   * @returns {Promise<TranscribeTask>}
   */
  async transcribe(file, model, language, engine = 'openai', useGpu = true, options = {}) {
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
      headers: { 'Content-Type': 'multipart/form-data' },
      signal: options.signal
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

  /**
   * 生成波形采样数据
   * @param {File|string} file - 文件对象或本地路径(Electron)
   * @param {number} [samplesPerSecond] - 每秒采样数
   * @param {{signal?: AbortSignal}} [options] - 可选取消信号
   * @returns {Promise<{peaks: number[], duration: number}>}
   */
  async generateWaveform(file, samplesPerSecond = 100, options = {}) {
    if (typeof file === 'string') {
      const response = await api.post('/waveform/generate-from-path', {
        file_path: file,
        samples_per_second: samplesPerSecond
      }, {
        timeout: 120000,
        signal: options.signal
      })
      return response.data
    } else {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('samples_per_second', samplesPerSecond)

      const response = await api.post('/waveform/generate', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 120000,
        signal: options.signal
      })
      return response.data
    }
  }
}

export const apiService = new ApiService()
