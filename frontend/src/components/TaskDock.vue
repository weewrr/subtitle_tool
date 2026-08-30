<template>
  <Teleport to="body">
    <div v-if="taskStore.tasks.length > 0" class="task-dock" aria-live="polite">
      <button
        v-if="taskStore.collapsed"
        class="dock-collapsed"
        type="button"
        @click="taskStore.toggleCollapsed()"
      >
        <span class="pulse-dot" :class="taskStore.hasRunning ? 'running' : 'done'"></span>
        <span>{{ taskStore.hasRunning ? `${taskStore.runningCount} 个任务进行中` : '任务已完成' }}</span>
        <el-icon :size="12"><ArrowUp /></el-icon>
      </button>

      <TransitionGroup v-else name="task-card" tag="div" class="dock-list">
        <div
          v-for="task in taskStore.tasks"
          :key="task.id"
          class="dock-card"
          :class="task.status"
        >
          <div class="card-head">
            <span class="status-icon">
              <el-icon v-if="task.status === 'running'" class="spin" :size="14"><Loading /></el-icon>
              <el-icon v-else-if="task.status === 'success'" :size="14"><CircleCheckFilled /></el-icon>
              <el-icon v-else-if="task.status === 'error'" :size="14"><CircleCloseFilled /></el-icon>
              <el-icon v-else :size="14"><RemoveFilled /></el-icon>
            </span>
            <span class="card-title">{{ task.title }}</span>
            <button
              v-if="task.status === 'running' && task.cancel"
              class="cancel-btn"
              type="button"
              @click="taskStore.cancelTask(task.id)"
            >
取消
</button>
            <button
              v-else
              class="dismiss-btn"
              type="button"
              aria-label="移除"
              @click="taskStore.removeTask(task.id)"
            >
              <el-icon :size="12"><Close /></el-icon>
            </button>
          </div>

          <div v-if="task.detail" class="card-detail">{{ task.detail }}</div>

          <el-progress
            v-if="task.status === 'running' && task.progress !== null"
            :percentage="task.progress"
            :stroke-width="4"
            :show-text="false"
            class="card-progress"
          />
        </div>

        <button key="collapse" class="dock-collapse-btn" type="button" @click="taskStore.toggleCollapsed()">
          收起 <el-icon :size="12"><ArrowDown /></el-icon>
        </button>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<script setup>
import { useTaskStore } from '@/stores/taskStore'

const taskStore = useTaskStore()
</script>

<style lang="scss" scoped>
.task-dock {
  position: fixed;
  right: 12px;
  bottom: 34px; // 状态栏高度 + 间距
  z-index: 1900; // 低于模态对话框(2000+),高于内容
  width: 300px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.dock-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.dock-card {
  background: var(--app-surface);
  border: 1px solid var(--app-border);
  border-radius: $border-radius;
  box-shadow: var(--app-shadow-md);
  padding: 10px 12px;

  &.success { border-color: var(--app-success); }
  &.error { border-color: var(--app-danger); }
  &.cancelled { opacity: 0.8; }
}

.card-head {
  display: flex;
  align-items: center;
  gap: 8px;

  .status-icon {
    display: flex;
    align-items: center;
    color: var(--app-primary);

    .spin {
      animation: rotate 1s linear infinite;
    }
  }

  .card-title {
    flex: 1;
    min-width: 0;
    font-size: $font-size-base;
    font-weight: 600;
    color: var(--app-text-primary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .cancel-btn {
    flex-shrink: 0;
    height: 22px;
    padding: 0 8px;
    font-size: $font-size-sm;
    border: 1px solid var(--app-border);
    border-radius: $border-radius-sm;
    background: transparent;
    color: var(--app-text-secondary);
    cursor: pointer;
    transition: $transition-colors;

    &:hover {
      color: var(--app-danger);
      border-color: var(--app-danger);
    }
  }

  .dismiss-btn {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 22px;
    height: 22px;
    border: none;
    border-radius: $border-radius-sm;
    background: transparent;
    color: var(--app-text-muted);
    cursor: pointer;

    &:hover {
      background: var(--app-hover-bg);
      color: var(--app-text-primary);
    }
  }
}

.dock-card.success .status-icon { color: var(--app-success); }
.dock-card.error .status-icon { color: var(--app-danger); }
.dock-card.cancelled .status-icon { color: var(--app-text-muted); }

.card-detail {
  margin-top: 4px;
  font-size: $font-size-sm;
  color: var(--app-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-progress {
  margin-top: 8px;

  :deep(.el-progress-bar__outer) {
    background: var(--app-surface-sunken);
  }
}

.dock-collapsed,
.dock-collapse-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: var(--app-surface);
  border: 1px solid var(--app-border);
  border-radius: $border-radius;
  box-shadow: var(--app-shadow-md);
  color: var(--app-text-secondary);
  font-size: $font-size-sm;
  cursor: pointer;
  transition: $transition-colors;

  &:hover {
    color: var(--app-text-primary);
    border-color: var(--app-border-strong);
  }
}

.dock-collapsed {
  align-self: flex-end;

  .pulse-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;

    &.running {
      background: var(--app-primary);
      animation: pulse 1.4s ease-in-out infinite;
    }

    &.done {
      background: var(--app-success);
    }
  }
}

.dock-collapse-btn {
  align-self: flex-end;
  padding: 4px 10px;
}

@keyframes rotate {
  to { transform: rotate(360deg); }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.35; }
}

.task-card-enter-active,
.task-card-leave-active {
  transition: all $transition-base;
}

.task-card-enter-from,
.task-card-leave-to {
  opacity: 0;
  transform: translateY(8px);
}
</style>
