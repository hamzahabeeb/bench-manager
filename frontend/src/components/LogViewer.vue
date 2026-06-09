<template>
  <div class="log-viewer">
    <!-- Log type selector -->
    <div class="log-toolbar">
      <span class="text-xs text-ink-gray-4 font-mono mr-2">Log:</span>
      <div class="log-tabs">
        <button
          v-for="type in logTypes"
          :key="type"
          :class="['log-tab', selectedType === type ? 'log-tab-active' : '']"
          @click="switchLog(type)"
        >
          {{ type }}
        </button>
      </div>
      <span class="flex-1" />
      <button class="log-clear-btn" @click="clearLines">Clear</button>
      <span
        :class="['log-status-dot', connected ? 'log-status-connected' : 'log-status-disconnected']"
        :title="connected ? 'Connected' : 'Disconnected'"
      />
    </div>

    <!-- Terminal output -->
    <div ref="outputEl" class="log-body">
      <div
        v-for="(line, i) in lines"
        :key="i"
        :class="['log-line', getLineClass(line)]"
      >{{ line || ' ' }}</div>
      <div v-if="lines.length === 0" class="log-empty">
        Waiting for log output...
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick, watch } from 'vue'

const props = defineProps({
  benchName: {
    type: String,
    required: true,
  },
  initialLogType: {
    type: String,
    default: 'web',
  },
})

const logTypes = ['web', 'worker', 'scheduler', 'error', 'bench']
const selectedType = ref(props.initialLogType)
const lines = ref([])
const outputEl = ref(null)
const connected = ref(false)

let es = null

function scrollToBottom() {
  nextTick(() => {
    if (outputEl.value) {
      outputEl.value.scrollTop = outputEl.value.scrollHeight
    }
  })
}

function getLineClass(line) {
  if (!line) return ''
  const lower = line.toLowerCase()
  if (lower.includes('error') || lower.includes('exception') || lower.includes('traceback')) {
    return 'log-line-error'
  }
  if (lower.includes('warning') || lower.includes('warn')) {
    return 'log-line-warn'
  }
  if (lower.includes('info')) {
    return 'log-line-info'
  }
  return ''
}

function clearLines() {
  lines.value = []
}

function disconnect() {
  if (es) {
    es.close()
    es = null
    connected.value = false
  }
}

function connect(logType) {
  disconnect()
  const url = `/api/benches/${props.benchName}/logs/${logType}/stream`
  es = new EventSource(url)
  connected.value = true

  es.onmessage = (event) => {
    connected.value = true
    lines.value.push(event.data)
    // Keep at most 2000 lines to avoid memory bloat
    if (lines.value.length > 2000) {
      lines.value.splice(0, lines.value.length - 2000)
    }
    scrollToBottom()
  }

  es.onerror = () => {
    connected.value = false
    // SSE will auto-reconnect; don't close unless component unmounts
  }
}

function switchLog(type) {
  if (type === selectedType.value) return
  selectedType.value = type
  lines.value = []
  connect(type)
}

onMounted(() => {
  connect(selectedType.value)
})

onUnmounted(() => {
  disconnect()
})
</script>

<style scoped>
.log-viewer {
  border-radius: 0.5rem;
  overflow: hidden;
  border: 1px solid var(--outline-gray-2);
  display: flex;
  flex-direction: column;
}

.log-toolbar {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.5rem 0.75rem;
  background: var(--surface-gray-1);
  border-bottom: 1px solid var(--outline-gray-2);
  flex-shrink: 0;
  flex-wrap: wrap;
  row-gap: 0.5rem;
}

.log-tabs {
  display: flex;
  gap: 0.25rem;
}

.log-tab {
  padding: 0.125rem 0.625rem;
  border-radius: 0.25rem;
  font-size: 0.7rem;
  font-family: 'Fira Mono', monospace;
  font-weight: 500;
  cursor: pointer;
  background: transparent;
  color: var(--ink-gray-4);
  border: 1px solid var(--outline-gray-2);
  transition: all 0.1s ease;
}
.log-tab:hover {
  background: var(--surface-gray-2);
  color: var(--ink-gray-6);
}
.log-tab-active {
  background: var(--surface-blue-2);
  color: var(--ink-blue-3);
  border-color: var(--outline-blue-1);
}

.log-clear-btn {
  padding: 0.125rem 0.5rem;
  border-radius: 0.25rem;
  font-size: 0.7rem;
  font-family: 'Fira Mono', monospace;
  cursor: pointer;
  background: transparent;
  color: var(--ink-gray-3);
  border: 1px solid var(--outline-gray-2);
  transition: all 0.1s ease;
}
.log-clear-btn:hover {
  background: var(--surface-gray-2);
  color: var(--ink-gray-5);
}

.log-status-dot {
  display: inline-block;
  width: 0.5rem;
  height: 0.5rem;
  border-radius: 50%;
}
.log-status-connected {
  background: #4ade80;
}
.log-status-disconnected {
  background: #6b7280;
}

.log-body {
  background: #020617;
  padding: 0.75rem 1rem;
  height: 400px;
  overflow-y: auto;
  font-family: 'Fira Mono', 'Cascadia Code', 'Consolas', 'Monaco', monospace;
  font-size: 0.72rem;
  line-height: 1.6;
  color: #94a3b8;
  flex: 1;
}

.log-line {
  white-space: pre-wrap;
  word-break: break-all;
}
.log-line-error {
  color: #fca5a5;
}
.log-line-warn {
  color: #fcd34d;
}
.log-line-info {
  color: #86efac;
}

.log-empty {
  color: #374151;
  font-style: italic;
  font-size: 0.75rem;
}
</style>
