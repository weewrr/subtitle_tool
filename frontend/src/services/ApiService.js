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

  async transcribe(file, model, language, engine = 'openai') {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('model', model)
    formData.append('engine', engine)
    if (language && language !== 'Auto-detect') {
      formData.append('language', language.toLowerCase())
    }

    const response = await api.post('/transcribe', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    return response.data
  }

  async getTranscribeStatus() {
    const response = await api.get('/transcribe/status')
    return response.data
  }

  async getTranscribeResult() {
    const response = await api.get('/transcribe/result')
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
