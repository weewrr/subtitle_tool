<template>
  <el-popover
    placement="bottom-end"
    :width="320"
    trigger="click"
    :teleported="false"
    popper-class="stats-popper"
  >
    <template #reference>
      <button type="button" class="header-icon-btn" title="字幕统计" aria-label="字幕统计">
        <el-icon :size="14"><DataAnalysis /></el-icon>
      </button>
    </template>
    <div class="stats-panel">
      <div class="stats-title">字幕统计</div>
      <div class="stats-grid">
        <div class="stat-cell"><span class="k">总行数</span><span class="v mono">{{ stats.totalRows }}</span></div>
        <div class="stat-cell"><span class="k">总时长</span><span class="v mono">{{ stats.totalDuration }}</span></div>
        <div class="stat-cell"><span class="k">原文字符</span><span class="v mono">{{ stats.totalChars }}</span></div>
        <div class="stat-cell"><span class="k">翻译字符</span><span class="v mono">{{ stats.translationChars }}</span></div>
        <div class="stat-cell"><span class="k">平均 CPS</span><span class="v mono">{{ stats.avgCps }}</span></div>
        <div class="stat-cell"><span class="k">最大 CPS</span><span class="v mono" :class="stats.maxCps > subtitleRules.cpsDanger ? 'danger' : ''">{{ stats.maxCps }} ({{ stats.maxCpsRow }})</span></div>
        <div class="stat-cell"><span class="k">平均行长</span><span class="v mono">{{ stats.avgLineLen }}</span></div>
        <div class="stat-cell"><span class="k">最长行</span><span class="v mono">{{ stats.maxLineLen }} ({{ stats.maxLineLenRow }})</span></div>
        <div class="stat-cell"><span class="k">翻译完成</span><span class="v mono">{{ stats.translationRatio }}</span></div>
        <div class="stat-cell"><span class="k">行长越界</span><span class="v mono" :class="stats.longLineCount > 0 ? 'warn' : ''">{{ stats.longLineCount }} 行</span></div>
      </div>
      <div class="stats-cps-title">CPS 分布（阅读速度）</div>
      <div class="stats-cps-bars">
        <div v-for="(bin, i) in stats.cpsBins" :key="i" class="cps-bin">
          <div class="cps-bar" :style="{ height: bin.height + '%' }" :class="bin.level"></div>
          <div class="cps-label">{{ bin.label }}</div>
          <div class="cps-count" :class="bin.level">{{ bin.count }}</div>
        </div>
      </div>
    </div>
  </el-popover>
</template>

<script setup>
import { computed } from 'vue'
import { DataAnalysis } from '@element-plus/icons-vue'
import { useSubtitleStore } from '@/stores/subtitleStore'
import { useSettingsStore } from '@/stores/settingsStore'

const subtitleStore = useSubtitleStore()
const settingsStore = useSettingsStore()

const subtitleRules = computed(() => settingsStore.settings.subtitleRules)

// 统计面板数据:总字数/时长/CPS 分布/行长/翻译比例(阈值来自字幕规则设置)
const stats = computed(() => {
  const ps = subtitleStore.currentSubtitle.paragraphs
  const totalRows = ps.length
  let totalMs = 0
  let totalChars = 0
  let translationChars = 0
  let translatedRows = 0
  let longLineCount = 0
  let sumCps = 0
  let cpsCount = 0
  let maxCps = 0
  let maxCpsRow = '-'
  let sumLineLen = 0
  let maxLineLen = 0
  let maxLineLenRow = '-'
  const bins = [
    { min: -Infinity, max: 4,  count: 0, label: '<4',  level: 'good'   },
    { min: 4,          max: 8,  count: 0, label: '4-8', level: 'good'   },
    { min: 8,          max: 12, count: 0, label: '8-12',level: 'good'   },
    { min: 12,         max: 16, count: 0, label: '12-16',level: 'warn'   },
    { min: 16,         max: Infinity, count: 0, label: '>16', level: 'danger' }
  ]

  for (let i = 0; i < ps.length; i++) {
    const p = ps[i]
    const durMs = p.endTime.totalMilliseconds - p.startTime.totalMilliseconds
    totalMs += Math.max(0, durMs)
    const text = p.text || ''
    const lineLen = text.replace(/\s/g, '').length
    totalChars += lineLen
    sumLineLen += lineLen
    if (lineLen > maxLineLen) { maxLineLen = lineLen; maxLineLenRow = `#${p.number || (i + 1)}` }
    if (lineLen > subtitleRules.value.maxCharsPerLine) longLineCount++
    const trans = p.translation || ''
    if (trans.trim().length > 0) {
      translatedRows++
      translationChars += trans.replace(/\s/g, '').length
    }
    if (durMs > 100) {
      const cps = lineLen / (durMs / 1000)
      if (isFinite(cps)) {
        sumCps += cps
        cpsCount++
        if (cps > maxCps) { maxCps = cps; maxCpsRow = `#${p.number || (i + 1)}` }
        for (const b of bins) {
          if (cps > b.min && cps <= b.max) { b.count++; break }
        }
      }
    }
  }

  const total = Math.max(0, totalMs)
  const h = Math.floor(total / 3600000)
  const m = Math.floor((total % 3600000) / 60000)
  const s = Math.floor((total % 60000) / 1000)
  const ml = total % 1000
  const totalDuration = total > 0
    ? `${h > 0 ? h + ':' : ''}${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}.${String(ml).padStart(3,'0')}`
    : '-'

  const maxBinCount = Math.max(1, ...bins.map(b => b.count))
  const cpsBins = bins.map(b => ({
    ...b,
    height: Math.round((b.count / maxBinCount) * 100)
  }))

  return {
    totalRows,
    totalDuration,
    totalChars,
    translationChars,
    avgCps: cpsCount > 0 ? (sumCps / cpsCount).toFixed(1) : '-',
    maxCps: maxCps > 0 ? maxCps.toFixed(1) : '-',
    maxCpsRow,
    avgLineLen: totalRows > 0 ? Math.round(sumLineLen / totalRows) : 0,
    maxLineLen,
    maxLineLenRow,
    translationRatio: totalRows > 0 ? `${translatedRows}/${totalRows} (${Math.round(translatedRows / totalRows * 100)}%)` : '-',
    longLineCount,
    cpsBins
  }
})
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
}

.stats-panel {
  .stats-title {
    font-size: $font-size-sm;
    font-weight: 600;
    color: var(--app-text-secondary);
    margin-bottom: 10px;
  }

  .stats-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 6px 12px;
    margin-bottom: 14px;
  }

  .stat-cell {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: $font-size-sm;
    padding: 4px 0;
    border-bottom: 1px dashed var(--app-border);

    .k { color: var(--app-text-muted); }
    .v { color: var(--app-text-primary); font-weight: 500; }
    .v.warn  { color: var(--app-warning, #d4880f); font-weight: 600; }
    .v.danger { color: var(--app-danger); font-weight: 700; }
  }

  .stats-cps-title {
    font-size: $font-size-sm;
    font-weight: 600;
    color: var(--app-text-secondary);
    margin-bottom: 8px;
  }

  .stats-cps-bars {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 6px;
    align-items: end;
    height: 100px;
    padding: 8px 4px 0;
    background: var(--app-surface-muted);
    border-radius: $border-radius-sm;

    .cps-bin {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: flex-end;
      height: 100%;
      gap: 4px;

      .cps-bar {
        width: 70%;
        min-height: 2px;
        background: var(--app-primary);
        border-radius: 2px 2px 0 0;
        transition: height .2s ease;

        &.good { background: #10b981; }
        &.warn { background: #f59e0b; }
        &.danger { background: var(--app-danger); }
      }
      .cps-label {
        font-size: 10px;
        color: var(--app-text-muted);
        font-family: $font-family-mono;
      }
      .cps-count {
        font-size: 11px;
        font-weight: 600;
        color: var(--app-text-secondary);
        &.good   { color: #10b981; }
        &.warn   { color: #f59e0b; }
        &.danger { color: var(--app-danger); }
      }
    }
  }
}
</style>
