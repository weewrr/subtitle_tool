<template>
  <Teleport to="body">
    <Transition name="cheat-fade">
      <div v-if="commandStore.shortcutsVisible" class="cheat-overlay" @mousedown.self="close">
        <div class="cheat-card" role="dialog" aria-label="键盘快捷键速查">
          <div class="cheat-header">
            <span class="cheat-title">键盘快捷键</span>
            <button class="close-btn" type="button" aria-label="关闭" @click="close">
              <el-icon :size="14"><Close /></el-icon>
            </button>
          </div>

          <div class="cheat-body">
            <section v-for="group in groups" :key="group.name" class="cheat-group">
              <h4>{{ group.name }}</h4>
              <div v-for="item in group.items" :key="item.label" class="cheat-row">
                <span class="row-label">{{ item.label }}</span>
                <span class="row-keys">
                  <kbd v-for="(k, i) in item.keys" :key="i" class="kbd">{{ k }}</kbd>
                </span>
              </div>
            </section>
          </div>

          <div class="cheat-footer">
            拖动波形底部的字幕块边缘可直接调整时间码
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { useCommandStore } from '@/stores/commandStore'

const commandStore = useCommandStore()

const groups = [
  {
    name: '导航与播放',
    items: [
      { label: '选择上一行 / 下一行', keys: ['↑', '↓'] },
      { label: '播放当前字幕行', keys: ['Enter'] },
      { label: '播放 / 暂停', keys: ['Space'] },
      { label: '快退 / 快进 5 秒', keys: ['←', '→'] }
    ]
  },
  {
    name: '时间码微调(当前行)',
    items: [
      { label: '起点 -0.1s / +0.1s', keys: ['Shift', '← / →'] },
      { label: '终点 -0.1s / +0.1s', keys: ['Alt', '← / →'] }
    ]
  },
  {
    name: '编辑',
    items: [
      { label: '聚焦编辑面板', keys: ['Ctrl', 'Enter'] },
      { label: '行内编辑文本', keys: ['双击单元格'] },
      { label: '撤销', keys: ['Ctrl', 'Z'] },
      { label: '重做', keys: ['Ctrl', 'Y'] }
    ]
  },
  {
    name: '文件',
    items: [
      { label: '导出字幕', keys: ['Ctrl', 'S'] },
      { label: '保存项目 (.stproj)', keys: ['Ctrl', 'Shift', 'S'] }
    ]
  },
  {
    name: '全局',
    items: [
      { label: '命令面板', keys: ['Ctrl', 'K'] },
      { label: '本速查表', keys: ['?'] }
    ]
  }
]

function close() {
  commandStore.toggleShortcuts(false)
}
</script>

<style lang="scss" scoped>
.cheat-overlay {
  position: fixed;
  inset: 0;
  z-index: 2100;
  background: var(--el-mask-color);
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 24px;
}

.cheat-card {
  width: min(620px, 100%);
  max-height: 80vh;
  background: var(--app-surface);
  border: 1px solid var(--app-border);
  border-radius: $border-radius-lg;
  box-shadow: var(--app-shadow-lg);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.cheat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--app-border);
  background: var(--app-surface-muted);

  .cheat-title {
    font-size: $font-size-lg;
    font-weight: 600;
    color: var(--app-text-primary);
  }

  .close-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 26px;
    height: 26px;
    border: none;
    border-radius: $border-radius-sm;
    background: transparent;
    color: var(--app-text-muted);
    cursor: pointer;
    transition: $transition-colors;

    &:hover {
      background: var(--app-hover-bg);
      color: var(--app-text-primary);
    }
  }
}

.cheat-body {
  padding: 16px;
  overflow-y: auto;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px 28px;
}

.cheat-group h4 {
  margin: 0 0 8px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.05em;
  color: var(--app-text-muted);
}

.cheat-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 5px 0;

  .row-label {
    font-size: $font-size-base;
    color: var(--app-text-primary);
  }

  .row-keys {
    display: flex;
    gap: 3px;
    flex-shrink: 0;
  }
}

.kbd {
  font-family: $font-family-mono;
  font-size: 11px;
  color: var(--app-text-secondary);
  background: var(--app-surface-sunken);
  border: 1px solid var(--app-border);
  border-bottom-width: 2px;
  border-radius: 4px;
  padding: 1px 6px;
  line-height: 1.4;
}

.cheat-footer {
  padding: 10px 16px;
  border-top: 1px solid var(--app-border);
  background: var(--app-surface-muted);
  font-size: $font-size-sm;
  color: var(--app-text-muted);
}

.cheat-fade-enter-active,
.cheat-fade-leave-active {
  transition: opacity $transition-base;
}

.cheat-fade-enter-from,
.cheat-fade-leave-to {
  opacity: 0;
}

@media (max-width: 720px) {
  .cheat-body {
    grid-template-columns: 1fr;
  }
}
</style>
