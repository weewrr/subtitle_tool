import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

// 任务坞:长任务的非阻塞进度中心。
// 运行中的任务在底部任务坞显示进度/取消;完成的任务短暂停留后自动消失。
export const useTaskStore = defineStore('task', () => {
  const tasks = ref([])
  const collapsed = ref(false)
  let uid = 0

  const hasRunning = computed(() => tasks.value.some(t => t.status === 'running'))
  const runningCount = computed(() => tasks.value.filter(t => t.status === 'running').length)

  function startTask({ title, detail = '', cancel = null }) {
    const id = ++uid
    tasks.value.push({
      id,
      title,
      detail,
      progress: null, // null = 不确定进度(转圈);0-100 = 确定进度
      status: 'running',
      cancel,
      startedAt: Date.now()
    })
    collapsed.value = false
    return id
  }

  function updateTask(id, patch) {
    const t = tasks.value.find(t => t.id === id)
    if (t) Object.assign(t, patch)
  }

  function finishTask(id, status = 'success', detail = '') {
    const t = tasks.value.find(t => t.id === id)
    if (!t) return
    t.status = status
    t.progress = status === 'success' ? 100 : t.progress
    if (detail) t.detail = detail
    t.cancel = null
    // 完成态停留 5 秒后自动移除
    setTimeout(() => removeTask(id), 5000)
  }

  function removeTask(id) {
    tasks.value = tasks.value.filter(t => t.id !== id)
  }

  function cancelTask(id) {
    const t = tasks.value.find(t => t.id === id)
    if (t?.cancel) t.cancel()
  }

  function toggleCollapsed() {
    collapsed.value = !collapsed.value
  }

  return {
    tasks,
    collapsed,
    hasRunning,
    runningCount,
    startTask,
    updateTask,
    finishTask,
    removeTask,
    cancelTask,
    toggleCollapsed
  }
})
