<template>
  <el-dialog
    v-model="visible"
    :title="isEdit ? '编辑模型配置' : '添加模型配置'"
    width="420px"
    :close-on-click-modal="false"
    align-center
  >
    <el-form label-width="80px" size="small">
      <el-form-item label="配置名称">
        <el-select v-model="form.name" placeholder="选择服务商" @change="onNameChange">
          <el-option
            v-for="opt in serviceOptions"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="API Key">
        <el-input v-model="form.apiKey" type="password" show-password placeholder="输入 API Key" />
      </el-form-item>
      <el-form-item label="接口地址">
        <el-input v-model="form.baseUrl" placeholder="自动填充或手动输入" />
      </el-form-item>
      <el-form-item v-if="showModelField" label="模型名称">
        <el-input v-model="form.model" placeholder="如 gpt-4 / deepseek-chat" />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" @click="onConfirm">{{ isEdit ? '保存修改' : '确认添加' }}</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'

const emit = defineEmits(['confirm', 'update'])

const serviceOptions = [
  { label: 'Ollama', value: 'ollama' },
  { label: '百度翻译', value: 'baidu' },
  { label: '谷歌翻译', value: 'google' },
  { label: '微软翻译', value: 'microsoft' },
  { label: 'DeepL', value: 'deepl' },
  { label: 'DeepSeek', value: 'deepseek' },
  { label: '阿里百炼', value: 'aliyun' },
  { label: '自定义', value: 'custom' }
]

const baseUrlMap = {
  ollama: 'http://localhost:11434/v1',
  baidu: 'https://fanyi-api.baidu.com/api/trans/vip/translate',
  google: 'https://translation.googleapis.com/language/translate/v2',
  microsoft: 'https://api.cognitive.microsofttranslator.com',
  deepl: 'https://api-free.deepl.com/v2',
  deepseek: 'https://api.deepseek.com/v1',
  aliyun: 'https://dashscope.aliyuncs.com/api/v1',
  custom: ''
}

const translationServices = ['baidu', 'google', 'microsoft', 'deepl']

const visible = ref(false)
const isEdit = ref(false)
const editId = ref(null)

const form = ref({
  name: '',
  apiKey: '',
  baseUrl: '',
  model: ''
})

const showModelField = computed(() => {
  return form.value.name && !translationServices.includes(form.value.name)
})

function onNameChange(val) {
  form.value.baseUrl = baseUrlMap[val] || ''
  if (translationServices.includes(val)) {
    form.value.model = ''
  }
}

function open(data) {
  if (data) {
    isEdit.value = true
    editId.value = data.id
    form.value = { name: data.name || '', apiKey: data.apiKey || '', baseUrl: data.baseUrl || '', model: data.model || '' }
  } else {
    isEdit.value = false
    editId.value = null
    form.value = { name: '', apiKey: '', baseUrl: '', model: '' }
  }
  visible.value = true
}

function onConfirm() {
  if (!form.value.name || !form.value.apiKey) {
    ElMessage.warning('请选择服务商并填写 API Key')
    return
  }
  const label = serviceOptions.find(o => o.value === form.value.name)?.label || form.value.name
  if (isEdit.value) {
    emit('update', { id: editId.value, ...form.value, label })
    ElMessage.success('配置已更新')
  } else {
    emit('confirm', { ...form.value, label })
    ElMessage.success('配置已添加')
  }
  visible.value = false
}

defineExpose({ open })
</script>