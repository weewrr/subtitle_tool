<template>
  <el-popover
    placement="bottom-end"
    :width="340"
    trigger="click"
    :teleported="false"
    popper-class="conflict-popper"
  >
    <template #reference>
      <button type="button" class="header-icon-btn conflict-btn" :title="`检测到 ${overlapCount} 处时间重叠`" aria-label="时间冲突">
        <el-icon :size="14"><Warning /></el-icon>
        <span class="conflict-badge">{{ overlapCount }}</span>
      </button>
    </template>
    <div class="conflict-panel">
      <div class="conflict-title">
        <span>时间轴重叠冲突</span>
        <span class="conflict-count">{{ overlapCount }} 处</span>
      </div>
      <div class="conflict-hint">重叠字幕会同时渲染,导致观众读不清。建议先修复。</div>
      <div v-if="overlapList.length === 0" class="conflict-empty">暂无冲突</div>
      <div v-else class="conflict-list">
        <div
          v-for="(pair, idx) in overlapListPreview"
          :key="idx"
          class="conflict-item"
          role="button"
          tabindex="0"
          :title="`定位到第 ${pair.a + 1} 行`"
          @click="emit('jump', pair.a)"
          @keydown.enter="emit('jump', pair.a)"
        >
          <span class="ci-pair">#{{ pair.a + 1 }} ⇋ #{{ pair.b + 1 }}</span>
          <span class="ci-time">{{ pair.aEnd }} / {{ pair.bStart }}</span>
          <span class="ci-overlap danger">重叠 {{ pair.overlapMs }}ms</span>
        </div>
        <div v-if="overlapList.length > overlapListPreview.length" class="conflict-more">
          另有 {{ overlapList.length - overlapListPreview.length }} 处未显示
        </div>
      </div>
      <div class="conflict-actions">
        <button type="button" class="cf-btn" @click="emit('fix', 'split')">按间隙平分修复</button>
        <button type="button" class="cf-btn primary" @click="emit('fix', 'shift')">顺延修复(推荐)</button>
      </div>
      <div class="conflict-tip">
        <b>平分:</b>在重叠段中间切一刀,时长略变。<br>
        <b>顺延:</b>后段起点 = 前段终点 + 10ms,级联到末尾,不破坏时长结构。
      </div>
    </div>
  </el-popover>
</template>

<script setup>
import { computed } from 'vue'
import { Warning } from '@element-plus/icons-vue'

/**
 * 时间轴重叠冲突面板(纯展示组件)
 * - 数据与修复逻辑由父组件(SubtitleList)持有,修复可撤销
 * @prop {number} overlapCount - 冲突总数
 * @prop {Array<{a:number,b:number,overlapMs:number,aEnd:string,bStart:string}>} overlapList - 冲突对列表
 * @emits jump - 定位到冲突行(参数:行索引)
 * @emits fix - 一键修复(参数:'split' 平分 | 'shift' 顺延)
 */
const props = defineProps({
  overlapCount: { type: Number, required: true },
  overlapList: { type: Array, required: true }
})

const emit = defineEmits(['jump', 'fix'])

const overlapListPreview = computed(() => props.overlapList.slice(0, 8))
</script>

<style lang="scss" scoped>
.header-icon-btn {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  margin-left: 6px;
  border: none;
  border-radius: $border-radius-sm;
  background: transparent;
  color: var(--app-text-muted);
  cursor: pointer;
  transition: $transition-colors;

  &:hover {
    background: var(--app-hover-bg);
    color: var(--app-primary);
  }

  &.conflict-btn:hover {
    color: var(--app-danger);
    background: rgba(239, 68, 68, 0.12);
  }

  .conflict-badge {
    position: absolute;
    top: -4px;
    right: -6px;
    min-width: 14px;
    height: 14px;
    padding: 0 3px;
    font-size: 10px;
    line-height: 14px;
    text-align: center;
    color: #fff;
    background: var(--app-danger);
    border-radius: 999px;
  }
}

.conflict-panel {
  .conflict-title {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: $font-size-sm;
    font-weight: 600;
    color: var(--app-text-secondary);
    margin-bottom: 4px;

    .conflict-count {
      color: var(--app-danger);
      font-family: $font-family-mono;
    }
  }

  .conflict-hint {
    font-size: 11px;
    color: var(--app-text-muted);
    margin-bottom: 10px;
  }

  .conflict-empty {
    padding: 16px 0;
    text-align: center;
    font-size: $font-size-sm;
    color: var(--app-text-muted);
  }

  .conflict-list {
    display: flex;
    flex-direction: column;
    gap: 3px;
    max-height: 180px;
    overflow-y: auto;
    margin-bottom: 10px;
  }

  .conflict-item {
    display: grid;
    grid-template-columns: 72px 1fr auto;
    align-items: center;
    gap: 8px;
    padding: 5px 8px;
    border-radius: $border-radius-sm;
    border: 1px solid transparent;
    cursor: pointer;
    transition: $transition-colors;

    &:hover {
      background: var(--app-hover-bg);
      border-color: var(--app-danger);
    }

    .ci-pair {
      font-family: $font-family-mono;
      font-weight: 600;
      font-size: 12px;
      color: var(--app-text-primary);
    }
    .ci-time {
      font-family: $font-family-mono;
      font-size: 11px;
      color: var(--app-text-muted);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .ci-overlap {
      font-size: 11px;
      font-weight: 600;
      font-family: $font-family-mono;
      color: var(--app-danger);
    }
  }

  .conflict-more {
    font-size: 11px;
    color: var(--app-text-muted);
    padding: 4px 8px;
    text-align: center;
  }

  .conflict-actions {
    display: flex;
    gap: 6px;
    margin-bottom: 8px;

    .cf-btn {
      flex: 1;
      height: 30px;
      padding: 0 8px;
      font-size: $font-size-sm;
      border: 1px solid var(--app-border);
      border-radius: $border-radius-sm;
      background: transparent;
      color: var(--app-text-secondary);
      cursor: pointer;
      transition: $transition-colors;

      &:hover {
        color: var(--app-primary);
        border-color: var(--app-primary);
      }
      &.primary {
        color: #fff;
        background: var(--app-primary);
        border-color: var(--app-primary);
        &:hover { filter: brightness(1.08); }
      }
    }
  }

  .conflict-tip {
    font-size: 11px;
    line-height: 1.6;
    color: var(--app-text-muted);
    padding: 6px 8px;
    background: var(--app-surface-muted);
    border-radius: $border-radius-sm;
  }
}
</style>
