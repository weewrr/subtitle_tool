import { defineStore } from 'pinia'
import { ref } from 'vue'

// 命令中心:命令面板(Ctrl+K)与快捷键速查(?)的共享状态
export const useCommandStore = defineStore('command', () => {
  const commands = ref([])
  const paletteVisible = ref(false)
  const shortcutsVisible = ref(false)

  function register(list) {
    commands.value = list
  }

  function execute(id) {
    const cmd = commands.value.find(c => c.id === id)
    if (cmd?.action) {
      cmd.action()
      return true
    }
    return false
  }

  function togglePalette(value) {
    paletteVisible.value = value ?? !paletteVisible.value
  }

  function toggleShortcuts(value) {
    shortcutsVisible.value = value ?? !shortcutsVisible.value
  }

  return {
    commands,
    paletteVisible,
    shortcutsVisible,
    register,
    execute,
    togglePalette,
    toggleShortcuts
  }
})
