<template>
  <div class="cr-root">
    <!-- Output area -->
    <div ref="outputEl" class="cr-output">
      <div v-if="entries.length === 0" class="cr-empty">
        Run any shell command. The bench virtualenv is on PATH — <span class="cr-hint">bench</span>, <span class="cr-hint">python</span>, <span class="cr-hint">pip</span> all work.
      </div>
      <div v-for="(entry, i) in entries" :key="i" class="cr-entry">
        <div class="cr-prompt-line">
          <span class="cr-cwd">{{ benchName }}</span>
          <span class="cr-dollar"> $ </span>
          <span class="cr-echoed">{{ entry.command }}</span>
        </div>
        <div
          v-for="(line, j) in entry.lines"
          :key="j"
          :class="['cr-line', lineClass(line)]"
        >{{ line || ' ' }}</div>
        <div
          v-if="entry.done"
          :class="['cr-exit', entry.exitCode === 0 ? 'cr-exit-ok' : 'cr-exit-err']"
        >exit {{ entry.exitCode }}</div>
      </div>
      <div v-if="running" class="cr-cursor">▌</div>
    </div>

    <!-- Input bar -->
    <div class="cr-bar">
      <span class="cr-bar-dollar">$</span>
      <input
        ref="inputEl"
        v-model="command"
        class="cr-bar-input"
        placeholder="bench migrate  /  ls apps  /  python -c 'import frappe'"
        :disabled="running"
        @keydown.enter="submit"
        @keydown.up.prevent="histUp"
        @keydown.down.prevent="histDown"
      />
      <button
        class="cr-run-btn"
        :disabled="running || !command.trim()"
        @click="submit"
      >
        <span v-if="running" class="cr-spin" />
        <span v-else>Run</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, nextTick, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  benchName: { type: String, required: true },
})

const outputEl = ref(null)
const inputEl = ref(null)
const command = ref('')
const running = ref(false)
const entries = reactive([])
const cmdHistory = []
let histIdx = -1
let es = null

function scrollToBottom() {
  nextTick(() => {
    if (outputEl.value) outputEl.value.scrollTop = outputEl.value.scrollHeight
  })
}

function lineClass(line) {
  const l = (line || '').toLowerCase()
  if (l.includes('traceback') || l.includes('exception') || /\berror\b/.test(l)) return 'cr-err'
  if (/\bwarn(ing)?\b/.test(l)) return 'cr-warn'
  return ''
}

function histUp() {
  if (!cmdHistory.length) return
  histIdx = Math.min(histIdx + 1, cmdHistory.length - 1)
  command.value = cmdHistory[histIdx]
}

function histDown() {
  if (histIdx <= 0) { histIdx = -1; command.value = ''; return }
  histIdx--
  command.value = cmdHistory[histIdx]
}

async function submit() {
  const cmd = command.value.trim()
  if (!cmd || running.value) return

  cmdHistory.unshift(cmd)
  histIdx = -1
  command.value = ''
  running.value = true

  const entry = reactive({ command: cmd, lines: [], exitCode: null, done: false })
  entries.push(entry)
  scrollToBottom()

  try {
    const body = new FormData()
    body.append('command', cmd)
    const res = await fetch(`/api/benches/${props.benchName}/exec`, { method: 'POST', body })
    const data = await res.json()
    if (!res.ok) {
      entry.lines.push(data.detail || 'Failed to start command')
      entry.exitCode = 1
      entry.done = true
      running.value = false
      return
    }

    es = new EventSource(`/api/jobs/${data.job_id}/stream`)
    es.onmessage = (e) => {
      const line = e.data
      const m = line.match(/--- Process exited with code (-?\d+) ---/)
      if (m) {
        entry.exitCode = parseInt(m[1])
        entry.done = true
        running.value = false
        es.close()
        es = null
        nextTick(() => inputEl.value?.focus())
      } else if (line.trim()) {
        entry.lines.push(line)
      }
      scrollToBottom()
    }
    es.onerror = () => {
      if (!entry.done) {
        entry.exitCode = -1
        entry.done = true
        running.value = false
      }
      es?.close()
      es = null
    }
  } catch (e) {
    entry.lines.push(e.message)
    entry.exitCode = 1
    entry.done = true
    running.value = false
  }
}

onMounted(() => inputEl.value?.focus())
onUnmounted(() => es?.close())
</script>

<style scoped>
.cr-root {
  display: flex;
  flex-direction: column;
  border-radius: 0.5rem;
  overflow: hidden;
  border: 1px solid var(--outline-gray-2);
  background: #020617;
}

.cr-output {
  min-height: 320px;
  max-height: 520px;
  overflow-y: auto;
  padding: 1rem;
  font-family: 'Fira Mono', 'Cascadia Code', 'Consolas', 'Monaco', monospace;
  font-size: 0.72rem;
  line-height: 1.6;
  color: #94a3b8;
  flex: 1;
}

.cr-empty {
  color: #334155;
  font-style: italic;
}
.cr-hint {
  color: #475569;
  font-style: normal;
}

.cr-entry {
  margin-bottom: 0.75rem;
}

.cr-prompt-line {
  margin-bottom: 0.1rem;
}
.cr-cwd {
  color: #4ade80;
}
.cr-dollar {
  color: #64748b;
}
.cr-echoed {
  color: #e2e8f0;
  font-weight: 600;
}

.cr-line {
  white-space: pre-wrap;
  word-break: break-all;
}
.cr-err  { color: #fca5a5; }
.cr-warn { color: #fcd34d; }

.cr-exit {
  margin-top: 0.2rem;
  font-size: 0.65rem;
  font-weight: 600;
  letter-spacing: 0.05em;
}
.cr-exit-ok  { color: #4ade80; }
.cr-exit-err { color: #f87171; }

.cr-cursor {
  color: #4ade80;
  animation: blink 1s step-end infinite;
}
@keyframes blink { 50% { opacity: 0; } }

/* Input bar */
.cr-bar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  background: #0f172a;
  border-top: 1px solid #1e293b;
  flex-shrink: 0;
}

.cr-bar-dollar {
  color: #4ade80;
  font-family: 'Fira Mono', monospace;
  font-size: 0.8rem;
  flex-shrink: 0;
}

.cr-bar-input {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  color: #e2e8f0;
  font-family: 'Fira Mono', 'Cascadia Code', 'Consolas', monospace;
  font-size: 0.75rem;
  caret-color: #4ade80;
}
.cr-bar-input::placeholder {
  color: #334155;
}
.cr-bar-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.cr-run-btn {
  flex-shrink: 0;
  padding: 0.25rem 0.75rem;
  border-radius: 0.25rem;
  font-size: 0.72rem;
  font-family: 'Fira Mono', monospace;
  font-weight: 600;
  cursor: pointer;
  background: #166534;
  color: #bbf7d0;
  border: 1px solid #15803d;
  transition: background 0.15s;
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
}
.cr-run-btn:hover:not(:disabled) { background: #15803d; }
.cr-run-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.cr-spin {
  display: inline-block;
  width: 0.6rem;
  height: 0.6rem;
  border: 1.5px solid currentColor;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
