<template>
  <div class="job-output-wrapper">
    <div class="terminal-header">
      <span class="text-xs text-ink-gray-4 font-mono">{{ title }}</span>
      <span
        :class="[
          'inline-flex items-center gap-1 text-xs font-mono',
          done ? (exitCode === 0 ? 'text-ink-green-3' : 'text-ink-red-4') : 'text-ink-amber-3',
        ]"
      >
        <span
          v-if="!done"
          class="inline-block h-1.5 w-1.5 rounded-full bg-amber-400 animate-pulse"
        />
        {{ done ? (exitCode === 0 ? 'Completed' : `Exited (${exitCode})`) : 'Running...' }}
      </span>
    </div>
    <div ref="outputEl" class="terminal-body">
      <div v-for="(line, i) in lines" :key="i" class="terminal-line">
        <span v-if="line === ''" class="terminal-blank">&nbsp;</span>
        <span v-else>{{ line }}</span>
      </div>
      <div v-if="!done" class="terminal-cursor">_</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick, watch } from 'vue'

const props = defineProps({
  jobId: {
    type: String,
    required: true,
  },
  title: {
    type: String,
    default: 'Job Output',
  },
})

const emit = defineEmits(['done'])

const outputEl = ref(null)
const lines = ref([])
const done = ref(false)
const exitCode = ref(null)

let es = null

function scrollToBottom() {
  nextTick(() => {
    if (outputEl.value) {
      outputEl.value.scrollTop = outputEl.value.scrollHeight
    }
  })
}

function connect() {
  if (!props.jobId) return
  es = new EventSource(`/api/jobs/${props.jobId}/stream`)

  es.onmessage = (event) => {
    const line = event.data

    // Detect completion
    const exitMatch = line.match(/Process exited with code\s+(-?\d+)/)
    if (exitMatch) {
      exitCode.value = parseInt(exitMatch[1], 10)
      done.value = true
      lines.value.push(line)
      scrollToBottom()
      es.close()
      emit('done', exitCode.value)
      return
    }

    lines.value.push(line)
    scrollToBottom()
  }

  es.onerror = () => {
    if (!done.value) {
      done.value = true
      exitCode.value = -1
      lines.value.push('--- Connection lost ---')
      scrollToBottom()
    }
    es.close()
  }
}

onMounted(() => {
  connect()
})

onUnmounted(() => {
  if (es) {
    es.close()
  }
})
</script>

<style scoped>
.job-output-wrapper {
  border-radius: 0.5rem;
  overflow: hidden;
  border: 1px solid var(--outline-gray-2);
}

.terminal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.5rem 0.75rem;
  background: var(--surface-gray-1);
  border-bottom: 1px solid var(--outline-gray-2);
}

.terminal-body {
  background: #020617;
  padding: 0.75rem 1rem;
  height: 320px;
  overflow-y: auto;
  font-family: 'Fira Mono', 'Cascadia Code', 'Consolas', 'Monaco', monospace;
  font-size: 0.75rem;
  line-height: 1.6;
  color: #d1fae5;
}

.terminal-line {
  white-space: pre-wrap;
  word-break: break-all;
}

.terminal-blank {
  display: block;
}

.terminal-cursor {
  display: inline-block;
  color: #6ee7b7;
  animation: blink 1s step-end infinite;
  margin-left: 2px;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.animate-pulse {
  animation: pulse 1.5s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
</style>
