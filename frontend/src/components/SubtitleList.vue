<template>
  <div class="subtitle-list" ref="rootRef">
    <div class="list-header panel-header">
      <span class="title">字幕列表</span>
      <span v-if="totalCount > 0" class="count">{{ totalCount }} 行</span>

      <!-- #8 统计面板:字数/时长/CPS 分布(独立组件,自读 store) -->
      <SubtitleStatsPanel />

      <!-- #6 冲突徽章:只有检测到重叠时显示(展示组件,修复/跳转逻辑留在此处) -->
      <SubtitleConflictPanel
        v-if="overlapCount > 0"
        :overlap-count="overlapCount"
        :overlap-list="overlapList"
        @jump="jumpToRow"
        @fix="fixConflicts"
      />

      <span class="header-spacer"></span>

      <el-popover
        placement="bottom-end"
        :width="280"
        trigger="click"
        :teleported="false"
        popper-class="history-popper"
      >
        <template #reference>
          <button type="button" class="header-icon-btn" title="撤销历史" aria-label="撤销历史">
            <el-icon :size="14"><Clock /></el-icon>
            <span v-if="historyCount > 0" class="history-badge">{{ historyCount }}</span>
          </button>
        </template>
        <div class="history-panel">
          <div class="history-title">
            <span>撤销历史（点击回退到该操作之前）</span>
            <button
              type="button"
              class="history-redo"
              :disabled="!canRedo"
              title="重做 (Ctrl+Y)"
              @click.stop="redoFromPanel"
            >
重做
</button>
          </div>
          <div v-if="historyItems.length === 0" class="history-empty">暂无历史记录</div>
          <div v-else class="history-list">
            <button
              v-for="(item, ri) in historyItemsReversed"
              :key="ri"
              type="button"
              class="history-item"
              @click="undoToHistory(item.rawIndex)"
            >
              <span class="history-desc">{{ item.description }}</span>
              <span class="history-time">{{ formatHistoryTime(item.timestamp) }}</span>
            </button>
          </div>
        </div>
      </el-popover>
    </div>

    <!-- 表头 -->
    <div v-if="totalCount > 0" class="grid-head" role="row">
      <div class="h-cell check-cell">
        <input
          type="checkbox"
          :checked="allSelected"
          :indeterminate.prop="someSelected && !allSelected"
          aria-label="全选"
          @change="toggleSelectAll"
        />
      </div>
      <div class="h-cell num-cell">#</div>
      <div class="h-cell time-cell">起始时间</div>
      <div class="h-cell time-cell">结束时间</div>
      <div class="h-cell dur-cell">时长</div>
      <div class="h-cell cps-cell" title="每秒字符数（阅读速度）">CPS</div>
      <div class="h-cell text-cell">{{ subtitleStore.showTranslation ? '翻译' : '文本' }}</div>
    </div>

    <!-- 虚拟滚动主体 -->
    <div
      v-if="totalCount > 0"
      ref="scrollRef"
      class="v-scroll"
      @scroll.passive="onScroll"
    >
      <div class="v-spacer" :style="{ height: totalCount * ROW_HEIGHT + 'px' }">
        <div class="v-window" :style="{ transform: `translateY(${viewStart * ROW_HEIGHT}px)` }">
          <div
            v-for="(row, vi) in visibleRows"
            :key="viewStart + vi"
            class="grid-row"
            :class="{
              current: viewStart + vi === subtitleStore.selectedParagraphIndex,
              selected: selectedIndexes.has(viewStart + vi),
              conflict: overlapIndexes.has(viewStart + vi)
            }"
            :data-index="viewStart + vi"
            role="row"
            @click="selectRow(viewStart + vi)"
          >
            <div class="cell check-cell" @click.stop>
              <input
                type="checkbox"
                :checked="selectedIndexes.has(viewStart + vi)"
                :aria-label="`选择第 ${row.number} 行`"
                @change="toggleSelect(viewStart + vi)"
              />
            </div>
            <div class="cell num-cell">{{ row.number }}</div>

            <div class="cell time-cell mono">
              <input
                v-if="isEditing(viewStart + vi, 'start')"
                ref="editInputRef"
                v-model="editDraft"
                class="time-input mono"
                @keydown.enter.prevent="commitTime(row, viewStart + vi, 'start')"
                @keydown.esc.prevent="cancelEdit"
                @blur="commitTime(row, viewStart + vi, 'start')"
              />
              <span
                v-else
                class="timecode editable"
                tabindex="0"
                title="双击编辑时间码"
                @dblclick.stop="startEdit(viewStart + vi, 'start', row.startTime.toDisplayString())"
              >{{ row.startTime.toDisplayString() }}</span>
            </div>
            <div class="cell time-cell mono">
              <input
                v-if="isEditing(viewStart + vi, 'end')"
                ref="editInputRef"
                v-model="editDraft"
                class="time-input mono"
                @keydown.enter.prevent="commitTime(row, viewStart + vi, 'end')"
                @keydown.esc.prevent="cancelEdit"
                @blur="commitTime(row, viewStart + vi, 'end')"
              />
              <span
                v-else
                class="timecode editable"
                tabindex="0"
                title="双击编辑时间码"
                @dblclick.stop="startEdit(viewStart + vi, 'end', row.endTime.toDisplayString())"
              >{{ row.endTime.toDisplayString() }}</span>
            </div>
            <div class="cell dur-cell mono">{{ row.duration.toDisplayString() }}</div>
            <div class="cell cps-cell mono">
              <span
                v-if="cpsOf(row) > 0"
                class="cps-value"
                :class="cpsLevel(row)"
                :title="cpsTitle(row)"
              >{{ cpsOf(row).toFixed(1) }}</span>
            </div>

            <div class="cell text-cell">
              <input
                v-if="isEditing(viewStart + vi, 'text') || isEditing(viewStart + vi, 'translation')"
                ref="editInputRef"
                v-model="editDraft"
                class="text-input"
                @keydown.enter.prevent="commitTextField(viewStart + vi)"
                @keydown.esc.prevent="cancelEdit"
                @blur="commitTextField(viewStart + vi)"
              />
              <span
                v-else
                class="cell-text"
                :class="{ 'text-warn': isTextTooLong(row) }"
                tabindex="0"
                :title="isTextTooLong(row) ? '行长偏长，可能超出屏幕宽度' : '双击编辑文本'"
                @dblclick.stop="startEdit(viewStart + vi, subtitleStore.showTranslation ? 'translation' : 'text', subtitleStore.showTranslation ? row.translation : row.text)"
              >{{ subtitleStore.showTranslation ? row.translation : row.text }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else class="empty-wrap">
      <div
        class="empty-placeholder"
        role="button"
        tabindex="0"
        aria-label="打开字幕文件"
        @click="openSubtitleFile"
        @keydown.enter="openSubtitleFile"
        @keydown.space.prevent="openSubtitleFile"
      >
        <el-icon :size="32"><FolderOpened /></el-icon>
        <span>点击或拖入字幕文件</span>
      </div>
    </div>

    <!-- 跟随选中行的悬浮快捷条 -->
    <Transition name="toolbar-pop">
      <div
        v-if="toolbarVisible && selectedRow && selectedIndexes.size === 0"
        class="row-toolbar"
        :style="{ top: toolbarTop + 'px' }"
        role="toolbar"
        aria-label="当前行快捷操作"
      >
        <button type="button" class="tool-btn" title="播放本行 (Enter)" aria-label="播放本行" @click="playRow(selectedRow)">
          <el-icon :size="13"><VideoPlay /></el-icon>
        </button>
        <button type="button" class="tool-btn" title="编辑文本 (双击文本)" aria-label="编辑文本" @click="startEdit(subtitleStore.selectedParagraphIndex, subtitleStore.showTranslation ? 'translation' : 'text', subtitleStore.showTranslation ? selectedRow.translation : selectedRow.text)">
          <el-icon :size="13"><Edit /></el-icon>
        </button>
        <button
          v-if="subtitleStore.selectedParagraphIndex < totalCount - 1"
          type="button"
          class="tool-btn"
          title="与下一行合并"
          aria-label="与下一行合并"
          @click="mergeWithNext(subtitleStore.selectedParagraphIndex)"
        >
          <el-icon :size="13"><Link /></el-icon>
        </button>
        <button type="button" class="tool-btn danger" title="删除本行" aria-label="删除本行" @click="deleteRow(subtitleStore.selectedParagraphIndex)">
          <el-icon :size="13"><Delete /></el-icon>
        </button>
      </div>
    </Transition>

    <!-- 批量操作条:多选后浮现 -->
    <Transition name="toolbar-pop">
      <div v-if="selectedIndexes.size > 0" class="batch-bar" role="toolbar" aria-label="批量操作">
        <span class="batch-count">已选 {{ selectedIndexes.size }} 行</span>
        <button type="button" class="batch-btn" @click="batchMerge">合并</button>
        <el-popover placement="top" :width="300" trigger="click" :teleported="false" popper-class="shift-popper">
          <template #reference>
            <button type="button" class="batch-btn">时间平移</button>
          </template>
          <div class="shift-panel">
            <div class="shift-title">整体平移选中行时间码</div>
            <div class="shift-quick">
              <button type="button" @click="applyShift(-1000)">-1s</button>
              <button type="button" @click="applyShift(-500)">-0.5s</button>
              <button type="button" @click="applyShift(-100)">-0.1s</button>
              <button type="button" @click="applyShift(100)">+0.1s</button>
              <button type="button" @click="applyShift(500)">+0.5s</button>
              <button type="button" @click="applyShift(1000)">+1s</button>
            </div>
            <div class="shift-custom">
              <el-input-number v-model="shiftSeconds" :step="0.1" :precision="2" size="small" style="width: 140px" />
              <span class="shift-unit">秒</span>
              <el-button size="small" type="primary" @click="applyShift(shiftSeconds * 1000)">应用</el-button>
            </div>
            <div class="shift-hint">负数提前，正数延后。可撤销。</div>
          </div>
        </el-popover>
        <button type="button" class="batch-btn danger" @click="batchDelete">删除</button>
        <span class="batch-sep"></span>
        <button type="button" class="batch-btn" @click="toggleSelectAll">{{ allSelected ? '取消全选' : '全选' }}</button>
        <button type="button" class="batch-btn" @click="clearSelection">清除选择</button>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Clock } from '@element-plus/icons-vue'
import { useSubtitleStore } from '@/stores/subtitleStore'
import { useUIStore } from '@/stores/uiStore'
import { useSettingsStore } from '@/stores/settingsStore'
import { useAppActions } from '@/composables/useAppActions'
import SubtitleStatsPanel from './SubtitleStatsPanel.vue'
import SubtitleConflictPanel from './SubtitleConflictPanel.vue'

const subtitleStore = useSubtitleStore()
const uiStore = useUIStore()
const settingsStore = useSettingsStore()
const { openSubtitleFile: openSubtitleAction } = useAppActions()

const subtitleRules = computed(() => settingsStore.settings.subtitleRules)

const rootRef = ref(null)
const scrollRef = ref(null)
const editInputRef = ref(null)

const totalCount = computed(() => subtitleStore.paragraphCount)
const selectedRow = computed(() => {
  const i = subtitleStore.selectedParagraphIndex
  return i >= 0 ? subtitleStore.currentSubtitle.paragraphs[i] : null
})

function openSubtitleFile() {
  openSubtitleAction()
}

// ============================================================
// 虚拟滚动:固定行高,只渲染可视窗口 ± buffer
// ============================================================
const ROW_HEIGHT = 32
const BUFFER = 8
const viewStart = ref(0)
const viewCount = ref(30)

function onScroll() {
  computeView()
}

function computeView() {
  const el = scrollRef.value
  if (!el) return
  const start = Math.max(0, Math.floor(el.scrollTop / ROW_HEIGHT) - BUFFER)
  const count = Math.ceil(el.clientHeight / ROW_HEIGHT) + BUFFER * 2
  viewStart.value = start
  viewCount.value = Math.min(count, totalCount.value - start)
}

const visibleRows = computed(() => {
  const ps = subtitleStore.currentSubtitle.paragraphs
  return ps.slice(viewStart.value, viewStart.value + viewCount.value)
})

function scrollToIndex(index) {
  const el = scrollRef.value
  if (!el || index < 0) return
  const top = index * ROW_HEIGHT
  const viewTop = el.scrollTop
  const viewBottom = viewTop + el.clientHeight
  if (top < viewTop) {
    el.scrollTop = top
  } else if (top + ROW_HEIGHT > viewBottom) {
    el.scrollTop = top + ROW_HEIGHT - el.clientHeight
  }
}

function selectRow(index) {
  subtitleStore.selectParagraph(index)
}

// ============================================================
// CPS / 行长实时警告(阈值来自设置的字幕规则)
// ============================================================

function cpsOf(row) {
  const dur = (row.endTime.totalMilliseconds - row.startTime.totalMilliseconds) / 1000
  if (dur <= 0.1) return 0
  const chars = (row.text || '').replace(/\s/g, '').length
  return chars / dur
}

function cpsLevel(row) {
  const cps = cpsOf(row)
  const warn = subtitleRules.value.cpsWarn
  const danger = subtitleRules.value.cpsDanger
  if (cps > danger) return 'danger'
  if (cps > warn) return 'warn'
  return ''
}

function cpsTitle(row) {
  const cps = cpsOf(row)
  if (cps > subtitleRules.value.cpsDanger) return `阅读速度 ${cps.toFixed(1)} 字符/秒，观众可能读不完`
  if (cps > subtitleRules.value.cpsWarn) return `阅读速度 ${cps.toFixed(1)} 字符/秒，偏快`
  return `阅读速度 ${cps.toFixed(1)} 字符/秒`
}

function isTextTooLong(row) {
  const text = (row.text || '').split('\n').pop() || ''
  return text.length > subtitleRules.value.maxCharsPerLine
}

// ============================================================
// #6 时间轴重叠检测 O(n) + 一键修复
// ============================================================
// 扫描重叠:按 start 升序比较相邻,允许 0 间隔(即 end == next.start 视为 OK)
function findOverlaps() {
  const ps = subtitleStore.currentSubtitle.paragraphs
  const result = []
  for (let i = 1; i < ps.length; i++) {
    const prev = ps[i - 1]
    const curr = ps[i]
    const overlapMs = prev.endTime.totalMilliseconds - curr.startTime.totalMilliseconds
    if (overlapMs > 0) {
      result.push({
        a: i - 1,
        b: i,
        overlapMs,
        aEnd: prev.endTime.toDisplayString(),
        bStart: curr.startTime.toDisplayString()
      })
    }
  }
  return result
}

const overlapList = computed(() => findOverlaps())
const overlapCount = computed(() => overlapList.value.length)
const overlapIndexes = computed(() => {
  const s = new Set()
  for (const p of overlapList.value) {
    s.add(p.a); s.add(p.b)
  }
  return s
})

function jumpToRow(index) {
  subtitleStore.selectParagraph(index)
  scrollToIndex(index)
}

// 修复策略:两种均可撤销(先入栈 saveHistory('修复时间轴重叠') 再改)
function fixConflicts(mode) {
  if (overlapCount.value === 0) return
  const sub = subtitleStore.currentSubtitle
  if (sub.paragraphs.length < 2) return

  sub.saveHistory(mode === 'shift' ? '一键修复重叠(顺延)' : '一键修复重叠(平分)')
  const ps = sub.paragraphs
  const GAP_MS = 10

  if (mode === 'split') {
    // 每一对重叠:在重叠中心切一刀(只影响该对)
    for (const pair of overlapList.value) {
      const prev = ps[pair.a]
      const curr = ps[pair.b]
      const mid = Math.floor((prev.endTime.totalMilliseconds + curr.startTime.totalMilliseconds) / 2)
      prev.endTime.totalMilliseconds = Math.max(prev.startTime.totalMilliseconds + 1, mid - 1)
      curr.startTime.totalMilliseconds = Math.min(curr.endTime.totalMilliseconds - 1, mid)
    }
  } else {
    // 顺延:按顺序遍历,若与前重叠则把自己整体后移到 prev.end + GAP(保持自身时长,级联)
    for (let i = 1; i < ps.length; i++) {
      const prev = ps[i - 1]
      const curr = ps[i]
      const prevEnd = prev.endTime.totalMilliseconds
      const currStart = curr.startTime.totalMilliseconds
      if (currStart < prevEnd + GAP_MS) {
        const delta = (prevEnd + GAP_MS) - currStart
        const dur = curr.endTime.totalMilliseconds - currStart
        curr.startTime.totalMilliseconds = currStart + delta
        curr.endTime.totalMilliseconds = curr.startTime.totalMilliseconds + dur
      }
    }
  }

  sub.renumber()
  subtitleStore.markModified()
  bumpHistory()
  ElMessage.success(`已${mode === 'shift' ? '顺延' : '平分'}修复 ${overlapCount.value} 处重叠`)
}

// ============================================================
// 行内编辑:双击单元格原地修改文本/时间码
// ============================================================
const editing = reactive({ index: -1, field: '' })
const editDraft = ref('')

function isEditing(index, field) {
  return editing.index === index && editing.field === field
}

function startEdit(index, field, value) {
  if (index < 0) return
  editing.index = index
  editing.field = field
  editDraft.value = value || ''
  nextTick(() => {
    const inputs = editInputRef.value
    const el = Array.isArray(inputs) ? inputs[0] : inputs
    el?.focus?.()
  })
}

function cancelEdit() {
  editing.index = -1
  editing.field = ''
}

function commitText(index) {
  if (!isEditing(index, 'text')) return
  const val = editDraft.value
  cancelEdit()
  if (val !== subtitleStore.currentSubtitle.paragraphs[index]?.text) {
    subtitleStore.updateParagraphText(index, val)
    bumpHistory()
  }
}

function commitTranslation(index) {
  if (!isEditing(index, 'translation')) return
  const val = editDraft.value
  cancelEdit()
  if (val !== subtitleStore.currentSubtitle.paragraphs[index]?.translation) {
    subtitleStore.updateParagraphTranslation(index, val)
  }
}

function commitTextField(index) {
  if (isEditing(index, 'text')) return commitText(index)
  if (isEditing(index, 'translation')) return commitTranslation(index)
}

// 解析 "HH:MM:SS.mmm" / "MM:SS.mmm" / "SS.mmm" / "SS,mmm"
function parseTimeInput(str) {
  const s = String(str || '').trim().replace(/,/g, '.')
  if (!s) return null
  const parts = s.split(':')
  if (parts.length > 3) return null
  if (parts.some(p => p === '' || isNaN(parseFloat(p)))) return null
  let ms = 0
  if (parts.length === 3) ms = parseFloat(parts[0]) * 3600000 + parseFloat(parts[1]) * 60000 + parseFloat(parts[2]) * 1000
  else if (parts.length === 2) ms = parseFloat(parts[0]) * 60000 + parseFloat(parts[1]) * 1000
  else ms = parseFloat(parts[0]) * 1000
  return Math.round(ms)
}

function commitTime(row, index, field) {
  if (!isEditing(index, field)) return
  const ms = parseTimeInput(editDraft.value)
  cancelEdit()
  if (ms === null) return

  const start = field === 'start' ? ms : row.startTime.totalMilliseconds
  const end = field === 'end' ? ms : row.endTime.totalMilliseconds
  subtitleStore.updateParagraphTime(index, start, end)
  bumpHistory()
}

// ============================================================
// 悬浮快捷条:跟随当前选中行(行高固定,直接计算位置)
// ============================================================
const toolbarVisible = ref(false)
const toolbarTop = ref(0)
const HEADER_HEIGHT = 30

function updateToolbarPosition() {
  const index = subtitleStore.selectedParagraphIndex
  const el = scrollRef.value
  if (index < 0 || !el || !rootRef.value) {
    toolbarVisible.value = false
    return
  }
  const rowTop = HEADER_HEIGHT + index * ROW_HEIGHT - el.scrollTop
  const rowBottom = rowTop + ROW_HEIGHT
  const listHeight = rootRef.value.clientHeight
  // 行在可视区域内才显示
  if (rowBottom < HEADER_HEIGHT || rowTop > listHeight) {
    toolbarVisible.value = false
    return
  }
  const top = Math.max(38, Math.min(rowTop + ROW_HEIGHT / 2, listHeight - 28))
  toolbarTop.value = top
  toolbarVisible.value = true
}

function playRow(row) {
  const video = subtitleStore.videoElement
  if (!video || !row) return
  video.currentTime = row.startTime.totalMilliseconds / 1000
  video.play().catch(() => {})
}

function mergeWithNext(index) {
  if (index < 0 || index >= totalCount.value - 1) return
  subtitleStore.mergeParagraphs(index, index + 1)
  bumpHistory()
}

function deleteRow(index) {
  if (index < 0) return
  const row = subtitleStore.currentSubtitle.paragraphs[index]
  uiStore.showConfirmDialog({
    title: '删除字幕行',
    message: `确定删除第 ${row.number } 行吗?此操作可通过撤销恢复。`,
    onConfirm: () => {
      subtitleStore.removeParagraph(index)
      bumpHistory()
      subtitleStore.selectParagraph(Math.min(index, totalCount.value - 1))
    }
  })
}

// ============================================================
// 多选 + 批量操作
// ============================================================
const selectedIndexes = ref(new Set())

const allSelected = computed(() => totalCount.value > 0 && selectedIndexes.value.size === totalCount.value)
const someSelected = computed(() => selectedIndexes.value.size > 0)

function toggleSelect(index) {
  const s = new Set(selectedIndexes.value)
  if (s.has(index)) s.delete(index)
  else s.add(index)
  selectedIndexes.value = s
}

function toggleSelectAll() {
  if (allSelected.value) {
    selectedIndexes.value = new Set()
  } else {
    selectedIndexes.value = new Set(Array.from({ length: totalCount.value }, (_, i) => i))
  }
}

function clearSelection() {
  selectedIndexes.value = new Set()
}

// 行数变化后裁剪越界选择
watch(totalCount, () => {
  const s = new Set([...selectedIndexes.value].filter(i => i < totalCount.value))
  selectedIndexes.value = s
  nextTick(() => {
    computeView()
    updateToolbarPosition()
  })
})

function batchMerge() {
  const sorted = [...selectedIndexes.value].sort((a, b) => a - b)
  if (sorted.length < 2) return ElMessage.warning('请至少选择两行')
  const min = sorted[0]
  const max = sorted[sorted.length - 1]
  if (max - min + 1 !== sorted.length) {
    return ElMessage.warning('合并仅支持连续行，请检查选择')
  }
  subtitleStore.mergeParagraphs(min, max)
  bumpHistory()
  clearSelection()
  ElMessage.success(`已合并 ${sorted.length} 行`)
}

function batchDelete() {
  const count = selectedIndexes.value.size
  uiStore.showConfirmDialog({
    title: '批量删除字幕',
    message: `确定删除选中的 ${count} 行吗?此操作可通过撤销恢复。`,
    onConfirm: () => {
      subtitleStore.removeParagraphs([...selectedIndexes.value])
      bumpHistory()
      clearSelection()
      subtitleStore.selectParagraph(-1)
    }
  })
}

// ============================================================
// 时间码整体平移
// ============================================================
const shiftSeconds = ref(0.5)

function applyShift(deltaMs) {
  if (!deltaMs) return
  const ok = subtitleStore.shiftParagraphTime([...selectedIndexes.value], deltaMs)
  if (ok) {
    bumpHistory()
    ElMessage.success(`已${deltaMs > 0 ? '延后' : '提前'} ${Math.abs(deltaMs) / 1000}s`)
  }
}

// ============================================================
// 撤销历史面板
// ============================================================
const historyTick = ref(0)

function bumpHistory() {
  historyTick.value++
}

const historyItems = computed(() => {
  historyTick.value // 依赖:操作后手动 bump 触发重算
  return subtitleStore.currentSubtitle?.historyItems || []
})

const historyCount = computed(() => historyItems.value.length)

const historyItemsReversed = computed(() => {
  return historyItems.value
    .map((item, rawIndex) => ({ ...item, rawIndex }))
    .reverse()
})

function formatHistoryTime(timestamp) {
  const d = new Date(timestamp)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`
}

function undoToHistory(keepCount) {
  if (subtitleStore.undoToStep(keepCount)) {
    bumpHistory()
    clearSelection()
    ElMessage.success('已回退')
  }
}

const canRedo = computed(() => subtitleStore.currentSubtitle?.redoItems?.length > 0)

function redoFromPanel() {
  if (subtitleStore.redo()) {
    bumpHistory()
    ElMessage.success('已重做')
  }
}

// ============================================================
// 选中行变化:滚动跟随 + 快捷条定位
// ============================================================
watch(() => subtitleStore.selectedParagraphIndex, (newIndex) => {
  if (newIndex >= 0) {
    scrollToIndex(newIndex)
  }
  nextTick(() => updateToolbarPosition())
})

// 滚动时快捷条跟随
watch(viewStart, () => updateToolbarPosition())

onMounted(() => {
  nextTick(() => {
    computeView()
    updateToolbarPosition()
  })
})

defineExpose({ toggleSelectAll })
</script>

<style lang="scss" scoped>
.subtitle-list {
  flex: 1;
  display: flex;
  flex-direction: column;
  position: relative;
  border: 1px solid var(--app-border);
  border-radius: $border-radius;
  background: var(--app-surface);
  box-shadow: var(--app-shadow-sm);
  overflow: hidden;

  .list-header {
    .title {
      font-weight: 600;
    }

    .count {
      font-size: $font-size-sm;
      font-weight: 500;
      color: var(--app-primary);
      background: var(--app-primary-subtle);
      border-radius: 999px;
      padding: 0 8px;
      line-height: 18px;
    }

    // 面板头右侧图标按钮(撤销历史;统计/冲突按钮样式在各自子组件内)
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

      .history-badge {
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
        background: var(--app-primary);
        border-radius: 999px;
      }
    }

    // 撤销历史按钮推到最右
    .header-spacer {
      flex: 1;
    }
  }
}

// ============================================================
// 网格表头与行:固定列宽,CSS Grid 对齐
// ============================================================
$col-check: 32px;
$col-num: 44px;
$col-time: 104px;
$col-dur: 76px;
$col-cps: 56px;

.grid-head {
  display: grid;
  grid-template-columns: $col-check $col-num $col-time $col-time $col-dur $col-cps 1fr;
  height: 30px;
  flex-shrink: 0;
  background: var(--app-surface-muted);
  border-bottom: 1px solid var(--app-border);
  font-size: $font-size-sm;
  font-weight: 600;
  color: var(--app-text-secondary);

  .h-cell {
    display: flex;
    align-items: center;
    padding: 0 8px;
    overflow: hidden;
    white-space: nowrap;

    &.text-cell { padding-left: 6px; }
  }
}

.v-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
}

.v-spacer {
  position: relative;
}

.v-window {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  will-change: transform;
}

.grid-row {
  display: grid;
  grid-template-columns: $col-check $col-num $col-time $col-time $col-dur $col-cps 1fr;
  height: 32px;
  align-items: center;
  font-size: $font-size-base;
  border-bottom: 1px solid var(--app-border);
  cursor: default;
  transition: background-color $transition-fast;

  &:hover {
    background: var(--app-hover-bg);
  }

  &.current {
    background: var(--app-primary-subtle);

    .cell { color: var(--app-text-primary); font-weight: 500; }
  }

  &.selected {
    background: var(--app-primary-subtle);
    box-shadow: inset 2px 0 0 var(--app-primary);
  }

  // #6 时间轴冲突行:红色左边框 + 背景浅红,与 selected/current 叠加
  &.conflict {
    background: color-mix(in srgb, var(--app-danger) 10%, var(--app-surface));
    box-shadow: inset 3px 0 0 var(--app-danger);

    .cell { color: var(--app-text-primary); }
  }

  .cell {
    display: flex;
    align-items: center;
    min-width: 0;
    height: 100%;
    padding: 0 8px;
    overflow: hidden;
    color: var(--app-text-primary);

    &.num-cell {
      justify-content: center;
      color: var(--app-text-muted);
      font-variant-numeric: tabular-nums;
      font-size: $font-size-sm;
    }

    &.mono .timecode {
      font-family: $font-family-mono;
      font-size: $font-size-sm;
      color: var(--app-text-secondary);
      font-variant-numeric: tabular-nums;
    }
  }
}

.timecode.editable {
  border-radius: 4px;
  padding: 2px 4px;
  cursor: text;

  &:hover {
    background: var(--app-hover-bg);
    color: var(--app-primary);
  }
}

.cell-text {
  width: 100%;
  cursor: text;
  border-radius: 4px;
  padding: 2px 6px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;

  &:hover {
    background: var(--app-hover-bg);
  }

  &.text-warn {
    color: var(--app-warning, #d4880f);

    &::after {
      content: ' ⚠';
      font-size: 11px;
    }
  }
}

// CPS 警告
.cps-value {
  font-family: $font-family-mono;
  font-size: $font-size-sm;
  font-variant-numeric: tabular-nums;
  color: var(--app-text-muted);

  &.warn {
    color: var(--app-warning, #d4880f);
    font-weight: 600;
  }

  &.danger {
    color: var(--app-danger);
    font-weight: 700;
  }
}

input[type='checkbox'] {
  width: 14px;
  height: 14px;
  cursor: pointer;
  accent-color: var(--app-primary);
}

.time-input,
.text-input {
  width: 100%;
  height: 24px;
  padding: 0 6px;
  font-size: $font-size-sm;
  color: var(--app-text-primary);
  background: var(--app-surface);
  border: 1.5px solid var(--app-primary);
  border-radius: $border-radius-sm;
  outline: none;
  box-shadow: 0 0 0 2px var(--app-primary-subtle);
}

.text-input {
  font-size: $font-size-base;
}

// ============================================================
// 空状态
// ============================================================
.empty-wrap {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;

  .empty-placeholder {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 10px;
    padding: 40px;
    cursor: pointer;
    color: var(--app-text-muted);
    border-radius: $border-radius;
    transition: color $transition-base, background-color $transition-base;

    &:hover,
    &:focus-visible {
      color: var(--app-primary);
      background: var(--app-hover-bg);
    }
  }
}

// ============================================================
// 悬浮快捷条
// ============================================================
.row-toolbar {
  position: absolute;
  right: 10px;
  transform: translateY(-50%);
  display: flex;
  gap: 2px;
  padding: 3px;
  background: var(--app-surface);
  border: 1px solid var(--app-border);
  border-radius: $border-radius;
  box-shadow: var(--app-shadow-md);
  z-index: 5;

  .tool-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 26px;
    height: 26px;
    border: none;
    border-radius: $border-radius-sm;
    background: transparent;
    color: var(--app-text-secondary);
    cursor: pointer;
    transition: $transition-colors;

    &:hover {
      background: var(--app-hover-bg);
      color: var(--app-primary);
    }

    &.danger:hover {
      background: var(--app-primary-subtle);
      color: var(--app-danger);
    }
  }
}

// ============================================================
// 批量操作条
// ============================================================
.batch-bar {
  position: absolute;
  bottom: 10px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  background: var(--app-surface);
  border: 1px solid var(--app-border);
  border-radius: $border-radius;
  box-shadow: var(--app-shadow-md);
  z-index: 6;
  white-space: nowrap;

  .batch-count {
    font-size: $font-size-sm;
    font-weight: 600;
    color: var(--app-primary);
    margin-right: 6px;
  }

  .batch-btn {
    height: 26px;
    padding: 0 10px;
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

    &.danger:hover {
      color: var(--app-danger);
      border-color: var(--app-danger);
    }
  }

  .batch-sep {
    width: 1px;
    height: 16px;
    margin: 0 4px;
    background: var(--app-border);
  }
}

// ============================================================
// 撤销历史 / 平移面板(popover 内容)
// ============================================================
.history-panel {
  .history-title {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: $font-size-sm;
    font-weight: 600;
    color: var(--app-text-secondary);
    margin-bottom: 8px;

    .history-redo {
      padding: 2px 10px;
      font-size: $font-size-sm;
      font-weight: 500;
      border: 1px solid var(--app-border);
      border-radius: $border-radius-sm;
      background: transparent;
      color: var(--app-text-secondary);
      cursor: pointer;
      transition: $transition-colors;

      &:hover:not(:disabled) {
        color: var(--app-primary);
        border-color: var(--app-primary);
      }

      &:disabled {
        opacity: 0.45;
        cursor: not-allowed;
      }
    }
  }

  .history-empty {
    padding: 16px 0;
    text-align: center;
    font-size: $font-size-sm;
    color: var(--app-text-muted);
  }

  .history-list {
    display: flex;
    flex-direction: column;
    gap: 2px;
    max-height: 260px;
    overflow-y: auto;
  }

  .history-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    padding: 6px 8px;
    border: none;
    border-radius: $border-radius-sm;
    background: transparent;
    cursor: pointer;
    text-align: left;
    transition: $transition-colors;

    &:hover {
      background: var(--app-hover-bg);
    }

    .history-desc {
      font-size: $font-size-base;
      color: var(--app-text-primary);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .history-time {
      flex-shrink: 0;
      font-family: $font-family-mono;
      font-size: $font-size-sm;
      color: var(--app-text-muted);
    }
  }
}

.shift-panel {
  .shift-title {
    font-size: $font-size-sm;
    font-weight: 600;
    color: var(--app-text-secondary);
    margin-bottom: 8px;
  }

  .shift-quick {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 4px;
    margin-bottom: 10px;

    button {
      height: 26px;
      font-family: $font-family-mono;
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
    }
  }

  .shift-custom {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;

    .shift-unit {
      font-size: $font-size-sm;
      color: var(--app-text-muted);
    }
  }

  .shift-hint {
    font-size: $font-size-sm;
    color: var(--app-text-muted);
  }
}

// 统计面板与冲突面板样式已拆分至:
// SubtitleStatsPanel.vue / SubtitleConflictPanel.vue

.toolbar-pop-enter-active,
.toolbar-pop-leave-active {
  transition: opacity $transition-fast, transform $transition-fast;
}

.toolbar-pop-enter-from,
.toolbar-pop-leave-to {
  opacity: 0;
  transform: translateY(-50%) translateX(6px);
}

.batch-bar.toolbar-pop-enter-from,
.batch-bar.toolbar-pop-leave-to {
  transform: translateX(-50%) translateY(8px);
}

.batch-bar.toolbar-pop-enter-active,
.batch-bar.toolbar-pop-leave-active {
  transition: opacity $transition-fast, transform $transition-fast;
}
</style>
