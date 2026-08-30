<template>
  <Teleport to="body">
    <Transition name="palette-fade">
      <div v-if="commandStore.paletteVisible" class="palette-overlay" @mousedown.self="close">
        <div class="palette-card" role="dialog" aria-label="命令面板">
          <div class="palette-input-row">
            <el-icon :size="16" class="search-icon"><Search /></el-icon>
            <input
              ref="inputRef"
              v-model="query"
              type="text"
              class="palette-input"
              placeholder="搜索命令,回车执行…"
              aria-label="搜索命令"
              @keydown.down.prevent="move(1)"
              @keydown.up.prevent="move(-1)"
              @keydown.enter.prevent="runActive"
              @keydown.esc.prevent="close"
            />
            <kbd class="kbd">Esc</kbd>
          </div>

          <div v-if="filtered.length === 0" class="palette-empty">没有匹配的命令</div>

          <div v-else class="palette-list" ref="listRef" role="listbox">
            <template v-for="group in grouped" :key="group.name">
              <div class="palette-group-label">{{ group.name }}</div>
              <div
                v-for="cmd in group.items"
                :key="cmd.id"
                class="palette-item"
                :class="{ active: cmd.id === activeId }"
                role="option"
                :aria-selected="cmd.id === activeId"
                @mouseenter="activeId = cmd.id"
                @click="execute(cmd)"
              >
                <span class="item-label">{{ cmd.label }}</span>
                <kbd v-if="cmd.shortcut" class="kbd">{{ cmd.shortcut }}</kbd>
              </div>
            </template>
          </div>

          <div class="palette-footer">
            <span><kbd class="kbd">↑</kbd><kbd class="kbd">↓</kbd> 选择</span>
            <span><kbd class="kbd">Enter</kbd> 执行</span>
            <span><kbd class="kbd">Esc</kbd> 关闭</span>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { useCommandStore } from '@/stores/commandStore'

const commandStore = useCommandStore()
const query = ref('')
const activeId = ref(null)
const inputRef = ref(null)
const listRef = ref(null)

// 模糊评分:前缀 > 包含 > 关键词 > 子序列
function score(cmd, q) {
  const label = cmd.label.toLowerCase()
  if (label.startsWith(q)) return 100
  if (label.includes(q)) return 80
  if ((cmd.keywords || []).some(k => k.toLowerCase().includes(q))) return 60
  let i = 0
  for (const ch of label) {
    if (ch === q[i]) i++
    if (i === q.length) return 40
  }
  return -1
}

const filtered = computed(() => {
  const q = query.value.trim().toLowerCase()
  const list = q
    ? commandStore.commands
        .map(c => ({ c, s: score(c, q) }))
        .filter(x => x.s > 0)
        .sort((a, b) => b.s - a.s)
        .map(x => x.c)
    : commandStore.commands
  return list
})

const grouped = computed(() => {
  const groups = []
  let current = null
  for (const cmd of filtered.value) {
    if (!current || current.name !== cmd.group) {
      current = { name: cmd.group, items: [] }
      groups.push(current)
    }
    current.items.push(cmd)
  }
  return groups
})

watch(() => commandStore.paletteVisible, async (open) => {
  if (open) {
    query.value = ''
    await nextTick()
    inputRef.value?.focus()
    activeId.value = filtered.value[0]?.id || null
  }
})

watch(filtered, () => {
  if (!filtered.value.some(c => c.id === activeId.value)) {
    activeId.value = filtered.value[0]?.id || null
  }
})

function move(delta) {
  const idx = filtered.value.findIndex(c => c.id === activeId.value)
  const next = Math.max(0, Math.min(filtered.value.length - 1, idx + delta))
  activeId.value = filtered.value[next]?.id || null
  // 保持激活项可见
  nextTick(() => {
    const el = listRef.value?.querySelector('.palette-item.active')
    el?.scrollIntoView({ block: 'nearest' })
  })
}

function runActive() {
  const cmd = filtered.value.find(c => c.id === activeId.value)
  if (cmd) execute(cmd)
}

function execute(cmd) {
  close()
  cmd.action?.()
}

function close() {
  commandStore.togglePalette(false)
}
</script>

<style lang="scss" scoped>
.palette-overlay {
  position: fixed;
  inset: 0;
  z-index: 2100;
  background: var(--el-mask-color);
  display: flex;
  justify-content: center;
  align-items: flex-start;
  padding-top: 12vh;
}

.palette-card {
  width: min(560px, calc(100vw - 48px));
  background: var(--app-surface);
  border: 1px solid var(--app-border);
  border-radius: $border-radius-lg;
  box-shadow: var(--app-shadow-lg);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.palette-input-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  border-bottom: 1px solid var(--app-border);

  .search-icon {
    color: var(--app-text-muted);
    flex-shrink: 0;
  }
}

.palette-input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  font-size: 15px;
  color: var(--app-text-primary);

  &::placeholder {
    color: var(--app-text-muted);
  }
}

.kbd {
  font-family: $font-family-mono;
  font-size: 11px;
  color: var(--app-text-secondary);
  background: var(--app-surface-sunken);
  border: 1px solid var(--app-border);
  border-radius: 4px;
  padding: 1px 5px;
  line-height: 1.4;
}

.palette-empty {
  padding: 28px 0;
  text-align: center;
  color: var(--app-text-muted);
  font-size: $font-size-base;
}

.palette-list {
  max-height: 46vh;
  overflow-y: auto;
  padding: 6px;
}

.palette-group-label {
  padding: 8px 10px 4px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.05em;
  color: var(--app-text-muted);
}

.palette-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 10px;
  border-radius: $border-radius-sm;
  cursor: pointer;
  color: var(--app-text-primary);
  font-size: $font-size-base;

  .item-label {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  &.active {
    background: var(--app-primary-subtle);
    color: var(--app-primary);

    .kbd {
      border-color: var(--app-primary-subtle-strong);
    }
  }
}

.palette-footer {
  display: flex;
  gap: 16px;
  padding: 8px 14px;
  border-top: 1px solid var(--app-border);
  background: var(--app-surface-muted);
  font-size: $font-size-sm;
  color: var(--app-text-muted);

  .kbd {
    margin-right: 2px;
  }
}

.palette-fade-enter-active,
.palette-fade-leave-active {
  transition: opacity $transition-base;
}

.palette-fade-enter-from,
.palette-fade-leave-to {
  opacity: 0;
}
</style>
