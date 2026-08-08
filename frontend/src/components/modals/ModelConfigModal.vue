<template>
  <el-dialog
    v-model="visible"
    title="配置模型"
    width="500px"
    :close-on-click-modal="false"
    style="height: 360px; display: flex; flex-direction: column"
  >
    <div class="config-body">
      <div v-if="configs.length === 0" class="empty-tip">
        暂无配置，请点击下方"添加配置"
      </div>
      <div v-else class="config-list">
        <div
          v-for="item in configs"
          :key="item.id"
          class="config-item"
          :class="{ selected: selectedId === item.id }"
          @click="selectedId = item.id"
        >
          <div class="config-info">
            <span class="config-name">{{ item.label || item.name }}</span>
            <span class="config-model">{{ item.model }}</span>
          </div>
          <el-button
            type="danger"
            size="small"
            text
            @click.stop="onDelete(item)"
          >
            删除
          </el-button>
        </div>
      </div>
      <AddModelConfigModal ref="addModalRef" @confirm="onConfigAdded" @update="onConfigUpdated" />
    </div>
    <template #footer>
      <el-button @click="onEdit" :disabled="!selectedId">编辑</el-button>
      <el-button type="primary" @click="onSave">添加配置</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessageBox } from 'element-plus'
import { useSettingsStore } from '@/stores/settingsStore'
import AddModelConfigModal from './AddModelConfigModal.vue'

const settingsStore = useSettingsStore()

const addModalRef = ref(null)

const visible = computed({
  get: () => settingsStore.modelConfigVisible,
  set: (val) => { if (!val) settingsStore.hideModelConfig() }
})

const configs = computed(() => settingsStore.modelConfigs)
const selectedId = ref(null)

function onConfigAdded(config) {
  settingsStore.addModelConfig(config)
}

function onConfigUpdated(data) {
  settingsStore.updateModelConfig(data.id, data)
  selectedId.value = null
}

async function onDelete(item) {
  try {
    await ElMessageBox.confirm(
      `确定要删除配置「${item.label || item.name}」吗？`,
      '删除确认',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
    if (selectedId.value === item.id) {
      selectedId.value = null
    }
    settingsStore.removeModelConfig(item.id)
  } catch {
    // 取消
  }
}

function onEdit() {
  const item = configs.value.find(c => c.id === selectedId.value)
  if (item) {
    addModalRef.value?.open(item)
  }
}

function onSave() {
  addModalRef.value?.open()
}
</script>

<style scoped>
.config-body {
  flex: 1;
  overflow-y: auto;
}
.empty-tip {
  text-align: center;
  color: var(--app-text-muted, #888);
  padding: 40px 0;
  font-size: 14px;
}
.config-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}
.config-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border: 1px solid var(--app-glass-border, rgba(255,255,255,0.1));
  border-radius: 6px;
  background: var(--app-glass-bg, rgba(255,255,255,0.05));
  width: 100%;
  box-sizing: border-box;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s;
}
.config-item:hover {
  border-color: var(--app-glass-border, rgba(255,255,255,0.25));
}
.config-item.selected {
  border-color: #409eff;
  background: rgba(64, 158, 255, 0.1);
}
.config-info {
  display: flex;
  align-items: center;
  gap: 8px;
}
.config-name {
  font-weight: 500;
}
.config-model {
  color: var(--app-text-muted, #888);
  font-size: 12px;
}
</style>