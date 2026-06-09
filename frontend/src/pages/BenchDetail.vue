<template>
  <div v-if="loading && !bench" class="flex flex-col items-center justify-center py-20 gap-3">
    <LoadingIndicator class="w-6 h-6 text-ink-gray-4" />
    <p class="text-ink-gray-4 text-sm">Loading bench info...</p>
  </div>

  <div v-else-if="fetchError" class="flex flex-col items-center justify-center py-20 gap-3">
    <p class="text-ink-red-4">{{ fetchError }}</p>
    <Button variant="ghost" size="sm" label="Go Back" @click="$router.back()" />
  </div>

  <div v-else-if="bench">
    <!-- Breadcrumb -->
    <nav class="flex items-center gap-1.5 text-xs text-ink-gray-4 mb-4">
      <router-link to="/" class="hover:text-ink-gray-6 transition-colors">Benches</router-link>
      <span>/</span>
      <span class="text-ink-gray-6">{{ bench.name }}</span>
    </nav>

    <!-- Bench header -->
    <div class="rounded-xl border border-outline-gray-2 bg-surface-gray-2 p-5 mb-4">
      <div class="flex items-start gap-4">
        <div class="min-w-0 flex-1">
          <div class="flex items-center gap-3 flex-wrap">
            <h1 class="text-lg font-semibold text-ink-gray-8">{{ bench.name }}</h1>
            <BenchStatusBadge :status="bench.status" />
          </div>
          <div class="flex items-center gap-4 mt-1.5 text-xs text-ink-gray-4">
            <span v-if="bench.frappe_version">Frappe {{ bench.frappe_version }}</span>
            <span v-if="bench.port">
              Port
              <a
                v-if="bench.status === 'running'"
                :href="bench.url"
                target="_blank"
                class="text-ink-blue-3 hover:underline"
              >{{ bench.port }}</a>
              <span v-else>{{ bench.port }}</span>
            </span>
            <span class="font-mono truncate max-w-xs opacity-50" :title="bench.path">{{ bench.path }}</span>
          </div>
        </div>

        <div class="flex gap-2 flex-shrink-0">
          <button
            v-if="bench.status === 'stopped'"
            class="action-btn action-btn-start"
            :disabled="!!actionLoading"
            @click="handleStart"
          >
            <span v-if="actionLoading === 'start'" class="btn-spin" />
            <span v-else>Start</span>
          </button>
          <button
            v-else
            class="action-btn action-btn-stop"
            :disabled="!!actionLoading"
            @click="handleStop"
          >
            <span v-if="actionLoading === 'stop'" class="btn-spin" />
            <span v-else>Stop</span>
          </button>
          <Button
            variant="ghost"
            icon="refresh-cw"
            :loading="loading"
            @click="fetchBench"
          />
        </div>
      </div>

      <!-- Honcho missing banner -->
      <div v-if="missingHoncho" class="mt-3 p-3 rounded-lg bg-surface-amber-1 border border-outline-amber-1">
        <p class="text-sm font-medium text-ink-amber-3 mb-1">honcho is not installed in this bench</p>
        <p class="text-xs text-ink-amber-2 mb-2">Required to start bench processes.</p>
        <Button
          theme="orange"
          variant="subtle"
          size="sm"
          label="Install honcho"
          :loading="actionLoading === 'honcho'"
          @click="handleInstallHoncho"
        />
      </div>

      <!-- Action error -->
      <p v-if="actionError" class="text-xs text-ink-red-4 mt-2">{{ actionError }}</p>
    </div>

    <!-- Tabs -->
    <div class="rounded-xl border border-outline-gray-2 bg-surface-gray-2 overflow-hidden">
      <div class="flex border-b border-outline-gray-2 bg-surface-gray-1">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          :class="[
            'px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px',
            activeTab === tab.id
              ? 'text-ink-gray-8 border-ink-blue-3'
              : 'text-ink-gray-4 border-transparent hover:text-ink-gray-6',
          ]"
          @click="activeTab = tab.id"
        >
          {{ tab.label }}
          <span
            v-if="tab.count !== undefined"
            :class="[
              'ml-1.5 inline-flex items-center justify-center min-w-[1.25rem] h-5 px-1 rounded text-xs font-semibold',
              activeTab === tab.id ? 'bg-surface-blue-2 text-ink-blue-3' : 'bg-surface-gray-3 text-ink-gray-4',
            ]"
          >{{ tab.count }}</span>
        </button>
      </div>

      <div class="p-4">
        <!-- Sites tab -->
        <div v-show="activeTab === 'sites'">
          <SiteList :bench-name="bench.name" :sites="sites" @refresh="fetchBench" />
        </div>

        <!-- Apps tab -->
        <div v-show="activeTab === 'apps'">
          <div v-if="bench.apps.length === 0" class="text-center py-10 text-ink-gray-4 text-sm">
            No apps installed.
          </div>
          <div v-else class="grid grid-cols-[repeat(auto-fill,minmax(160px,1fr))] gap-2">
            <div
              v-for="app in bench.apps"
              :key="app"
              class="flex items-center gap-2 px-3 py-2.5 rounded-lg border border-outline-gray-2 bg-surface-gray-1 hover:border-outline-gray-3 transition-colors"
            >
              <span class="text-ink-gray-4 text-base">✦</span>
              <span class="text-sm font-medium text-ink-gray-7 font-mono">{{ app }}</span>
            </div>
          </div>
        </div>

        <!-- Logs tab -->
        <div v-show="activeTab === 'logs'">
          <LogViewer :bench-name="bench.name" initial-log-type="web" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Button, LoadingIndicator } from 'frappe-ui'
import BenchStatusBadge from '../components/BenchStatusBadge.vue'
import SiteList from '../components/SiteList.vue'
import LogViewer from '../components/LogViewer.vue'

const props = defineProps({
  name: { type: String, required: true },
})

const bench = ref(null)
const sites = ref([])
const loading = ref(false)
const fetchError = ref('')
const activeTab = ref('sites')
const actionLoading = ref(null)
const actionError = ref('')
const missingHoncho = ref(false)

const tabs = computed(() => [
  { id: 'sites', label: 'Sites', count: sites.value.length },
  { id: 'apps', label: 'Apps', count: bench.value?.apps?.length ?? 0 },
  { id: 'logs', label: 'Logs' },
])

async function fetchBench() {
  loading.value = true
  fetchError.value = ''
  try {
    const res = await fetch(`/api/benches/${props.name}`)
    if (!res.ok) {
      fetchError.value = res.status === 404 ? `Bench "${props.name}" not found.` : `HTTP ${res.status}`
      return
    }
    const data = await res.json()
    bench.value = data.bench
    sites.value = data.sites || []
  } catch (e) {
    fetchError.value = e.message
  } finally {
    loading.value = false
  }
}

async function handleStart() {
  actionLoading.value = 'start'
  actionError.value = ''
  missingHoncho.value = false
  try {
    const res = await fetch(`/api/benches/${props.name}/start`, { method: 'POST' })
    const data = await res.json()
    if (!data.success) {
      actionError.value = data.message || 'Start failed'
      missingHoncho.value = data.missing_honcho || false
    }
    await fetchBench()
  } catch (e) {
    actionError.value = e.message
  } finally {
    actionLoading.value = null
  }
}

async function handleStop() {
  actionLoading.value = 'stop'
  actionError.value = ''
  try {
    await fetch(`/api/benches/${props.name}/stop`, { method: 'POST' })
    await fetchBench()
  } catch (e) {
    actionError.value = e.message
  } finally {
    actionLoading.value = null
  }
}

async function handleInstallHoncho() {
  actionLoading.value = 'honcho'
  actionError.value = ''
  try {
    const res = await fetch(`/api/benches/${props.name}/install-honcho`, { method: 'POST' })
    const data = await res.json()
    if (data.success) {
      missingHoncho.value = false
    } else {
      actionError.value = data.message || 'Install failed'
    }
  } catch (e) {
    actionError.value = e.message
  } finally {
    actionLoading.value = null
  }
}

onMounted(() => fetchBench())
</script>

<style scoped>
.action-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.375rem;
  border-radius: 0.375rem;
  font-size: 0.8rem;
  font-weight: 500;
  cursor: pointer;
  padding: 0.375rem 1rem;
  height: 2rem;
  transition: opacity 0.15s ease, background-color 0.15s ease;
  line-height: 1;
}
.action-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.action-btn-start {
  background-color: #16a34a;
  color: #ffffff;
  border: 1px solid #15803d;
}
.action-btn-start:hover:not(:disabled) { background-color: #15803d; }

.action-btn-stop {
  background-color: transparent;
  color: #e5e7eb;
  border: 1px solid #6b7280;
}
.action-btn-stop:hover:not(:disabled) {
  background-color: rgba(107,114,128,0.15);
  border-color: #9ca3af;
}

.btn-spin {
  display: inline-block;
  width: 0.75rem;
  height: 0.75rem;
  border: 2px solid currentColor;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
