<template>
  <div class="split-pane" :class="{ vertical: vertical, horizontal: !vertical }">
    <div 
      class="pane first-pane" 
      :style="firstPaneStyle"
      ref="firstPaneRef"
    >
      <slot name="first"></slot>
    </div>
    <div 
      class="splitter"
      :class="{ vertical: vertical, horizontal: !vertical }"
      @mousedown="startResize"
    >
      <div class="splitter-line"></div>
    </div>
    <div 
      class="pane second-pane" 
      :style="secondPaneStyle"
      ref="secondPaneRef"
    >
      <slot name="second"></slot>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  vertical: {
    type: Boolean,
    default: false
  },
  initialSplit: {
    type: Number,
    default: 50
  },
  minFirstSize: {
    type: Number,
    default: 200
  },
  minSecondSize: {
    type: Number,
    default: 200
  }
})

const emit = defineEmits(['resize'])

const firstPaneRef = ref(null)
const secondPaneRef = ref(null)
const splitPercent = ref(props.initialSplit)
const isResizing = ref(false)
const containerSize = ref(0)

const firstPaneStyle = computed(() => {
  if (props.vertical) {
    return {
      width: `${splitPercent.value}%`,
      minWidth: `${props.minFirstSize}px`
    }
  } else {
    return {
      height: `${splitPercent.value}%`,
      minHeight: `${props.minFirstSize}px`
    }
  }
})

const secondPaneStyle = computed(() => {
  if (props.vertical) {
    return {
      width: `${100 - splitPercent.value}%`,
      minWidth: `${props.minSecondSize}px`
    }
  } else {
    return {
      height: `${100 - splitPercent.value}%`,
      minHeight: `${props.minSecondSize}px`
    }
  }
})

function startResize(e) {
  e.preventDefault()
  isResizing.value = true
  
  const parent = e.target.closest('.split-pane')
  if (!parent) return
  
  const rect = parent.getBoundingClientRect()
  containerSize.value = props.vertical ? rect.width : rect.height
  
  document.addEventListener('mousemove', handleResize)
  document.addEventListener('mouseup', stopResize)
  document.body.style.cursor = props.vertical ? 'col-resize' : 'row-resize'
  document.body.style.userSelect = 'none'
}

function handleResize(e) {
  if (!isResizing.value) return
  
  const parent = document.querySelector('.split-pane')
  if (!parent) return
  
  const rect = parent.getBoundingClientRect()
  containerSize.value = props.vertical ? rect.width : rect.height
  
  let newPercent
  if (props.vertical) {
    newPercent = ((e.clientX - rect.left) / containerSize.value) * 100
  } else {
    newPercent = ((e.clientY - rect.top) / containerSize.value) * 100
  }
  
  const minFirstPercent = (props.minFirstSize / containerSize.value) * 100
  const minSecondPercent = (props.minSecondSize / containerSize.value) * 100
  const maxPercent = 100 - minSecondPercent
  
  newPercent = Math.max(minFirstPercent, Math.min(maxPercent, newPercent))
  splitPercent.value = newPercent
  
  emit('resize', { percent: newPercent, size: containerSize.value })
  
  window.dispatchEvent(new Event('resize'))
}

function stopResize() {
  isResizing.value = false
  document.removeEventListener('mousemove', handleResize)
  document.removeEventListener('mouseup', stopResize)
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
}

onUnmounted(() => {
  document.removeEventListener('mousemove', handleResize)
  document.removeEventListener('mouseup', stopResize)
})
</script>

<style lang="scss" scoped>
.split-pane {
  display: flex;
  width: 100%;
  height: 100%;
  overflow: hidden;
  
  &.vertical {
    flex-direction: row;
  }
  
  &.horizontal {
    flex-direction: column;
  }
}

.pane {
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.first-pane {
  flex-shrink: 0;
}

.second-pane {
  flex: 1;
  min-width: 0;
  min-height: 0;
}

.splitter {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: transparent;
  z-index: 10;
  
  &.vertical {
    width: 6px;
    cursor: col-resize;
    margin: 0 -3px;
    
    .splitter-line {
      width: 1px;
      height: 100%;
      background-color: $border-color;
    }
    
    &:hover .splitter-line {
      width: 3px;
      background-color: #409eff;
    }
  }
  
  &.horizontal {
    height: 6px;
    cursor: row-resize;
    margin: -3px 0;
    
    .splitter-line {
      height: 1px;
      width: 100%;
      background-color: $border-color;
    }
    
    &:hover .splitter-line {
      height: 3px;
      background-color: #409eff;
    }
  }
  
  &:hover {
    background-color: rgba(64, 158, 255, 0.1);
  }
}
</style>
