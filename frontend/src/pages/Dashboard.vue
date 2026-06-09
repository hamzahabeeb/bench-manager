<template>
  <div>
    <!-- Page header -->
    <div class="flex items-center justify-between mb-5">
      <div>
        <h1 class="text-xl font-semibold text-ink-gray-8">Benches</h1>
        <p class="text-sm text-ink-gray-4 mt-0.5">Manage your Frappe bench environments</p>
      </div>
      <div class="flex items-center gap-2">
        <Button
          variant="ghost"
          icon="refresh-cw"
          size="sm"
          :loading="loading"
          @click="fetchBenches"
        />
        <Button
          label="New Bench"
          icon-left="plus"
          size="sm"
          @click="showNewBenchDialog = true"
        />
      </div>
    </div>

    <!-- Loading skeleton -->
    <div v-if="loading && benches.length === 0" class="bench-grid">
      <div v-for="i in 4" :key="i" class="skeleton-card rounded-xl" />
    </div>

    <!-- Empty state -->
    <div v-else-if="benches.length === 0" class="text-center py-20 border border-dashed border-outline-gray-2 rounded-xl">
      <p class="text-ink-gray-5 text-sm font-medium">No benches found</p>
      <p class="text-ink-gray-3 text-xs mt-1">Create a bench to get started.</p>
      <Button class="mt-4" label="Create First Bench" icon-left="plus" size="sm" @click="showNewBenchDialog = true" />
    </div>

    <!-- Bench grid -->
    <div v-else class="bench-grid">
      <BenchCard
        v-for="bench in benches"
        :key="bench.name"
        :bench="bench"
        @refresh="fetchBenches"
      />
    </div>

    <!-- Error -->
    <div v-if="fetchError" class="flex items-center gap-2 mt-4 px-4 py-3 rounded-lg bg-surface-red-1 border border-outline-red-1">
      <span class="text-ink-red-4 text-sm flex-1">{{ fetchError }}</span>
      <Button variant="ghost" size="sm" icon="x" @click="fetchError = ''" />
    </div>
  </div>

  <!-- New Bench Dialog -->
  <Dialog
    v-model="showNewBenchDialog"
    :options="{ title: 'Create New Bench', size: 'sm' }"
  >
    <template #body-content>
      <form @submit.prevent="handleCreateBench" class="flex flex-col gap-3">
        <FormControl
          label="Bench Name"
          v-model="newBench.bench_name"
          placeholder="e.g. frappe-bench"
          :required="true"
          autocomplete="off"
          description="Alphanumeric, hyphens and underscores only."
        />
        <FormControl
          label="Frappe Branch"
          type="select"
          v-model="newBench.frappe_branch"
          :options="[
            { label: 'version-15 (latest stable)', value: 'version-15' },
            { label: 'version-14', value: 'version-14' },
            { label: 'version-13', value: 'version-13' },
            { label: 'develop (unstable)', value: 'develop' },
          ]"
        />
        <div class="flex justify-end gap-2 pt-2">
          <Button variant="ghost" size="sm" label="Cancel" @click="showNewBenchDialog = false" />
          <Button type="submit" size="sm" label="Create Bench" :loading="createLoading" />
        </div>
      </form>
    </template>
  </Dialog>

  <!-- Job output for bench creation -->
  <Dialog
    v-if="creationJobId"
    v-model="showJobDialog"
    :options="{ title: `Creating: ${creationBenchName}`, size: 'xl' }"
  >
    <template #body-content>
      <JobOutput
        :job-id="creationJobId"
        :title="`bench init ${creationBenchName}`"
        @done="onCreateJobDone"
      />
      <div class="flex justify-end mt-3">
        <Button
          v-if="jobDone"
          variant="ghost"
          size="sm"
          label="Close"
          @click="dismissJob"
        />
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { Button, Dialog, FormControl } from 'frappe-ui'
import BenchCard from '../components/BenchCard.vue'
import JobOutput from '../components/JobOutput.vue'

const benches = ref([])
const loading = ref(false)
const fetchError = ref('')
const showNewBenchDialog = ref(false)
const createLoading = ref(false)
const creationJobId = ref(null)
const creationBenchName = ref('')
const jobDone = ref(false)
const showJobDialog = ref(false)

const newBench = ref({
  bench_name: '',
  frappe_branch: 'version-15',
})

let refreshTimer = null

async function fetchBenches() {
  loading.value = true
  fetchError.value = ''
  try {
    const res = await fetch('/api/benches')
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    benches.value = data.benches || []
  } catch (e) {
    fetchError.value = `Failed to load benches: ${e.message}`
  } finally {
    loading.value = false
  }
}

async function handleCreateBench() {
  if (!newBench.value.bench_name.trim()) return
  createLoading.value = true
  fetchError.value = ''
  try {
    const body = new FormData()
    body.append('bench_name', newBench.value.bench_name)
    body.append('frappe_branch', newBench.value.frappe_branch)

    const res = await fetch('/api/benches/create', { method: 'POST', body })
    const data = await res.json()
    if (!res.ok) {
      fetchError.value = data.detail || 'Create bench failed'
      return
    }
    creationBenchName.value = newBench.value.bench_name
    creationJobId.value = data.job_id
    jobDone.value = false
    showJobDialog.value = true
    showNewBenchDialog.value = false
    newBench.value.bench_name = ''
    newBench.value.frappe_branch = 'version-15'
  } catch (e) {
    fetchError.value = e.message
  } finally {
    createLoading.value = false
  }
}

function onCreateJobDone() {
  jobDone.value = true
  setTimeout(() => fetchBenches(), 2000)
}

function dismissJob() {
  showJobDialog.value = false
  creationJobId.value = null
  creationBenchName.value = ''
  jobDone.value = false
}

onMounted(() => {
  fetchBenches()
  refreshTimer = setInterval(fetchBenches, 10000)
})

onUnmounted(() => {
  clearInterval(refreshTimer)
})
</script>

<style scoped>
.bench-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1rem;
}

.skeleton-card {
  height: 180px;
  background: var(--surface-gray-2);
  animation: pulse 1.8s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
</style>
