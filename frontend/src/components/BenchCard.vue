<template>
  <div
    class="rounded-xl border border-outline-gray-2 bg-surface-gray-2 p-4 flex flex-col gap-3 cursor-pointer transition-all hover:border-outline-gray-3 hover:shadow"
    @click="navigateToDetail"
  >
    <!-- Header -->
    <div class="flex items-start justify-between gap-2">
      <div class="min-w-0">
        <h3 class="text-base font-semibold text-ink-gray-8 truncate">{{ bench.name }}</h3>
        <p v-if="bench.frappe_version" class="text-xs text-ink-gray-4 mt-0.5">
          Frappe {{ bench.frappe_version }}
        </p>
      </div>
      <BenchStatusBadge :status="bench.status" />
    </div>

    <!-- Stats -->
    <div class="flex gap-4 text-sm text-ink-gray-5">
      <span>
        <span class="font-medium text-ink-gray-7">{{ bench.apps.length }}</span> apps
      </span>
      <span>
        <span class="font-medium text-ink-gray-7">{{ bench.sites.length }}</span> sites
      </span>
      <span v-if="bench.port">
        Port
        <a
          v-if="bench.status === 'running'"
          :href="bench.url"
          target="_blank"
          class="font-medium text-ink-blue-3 hover:underline"
          @click.stop
        >{{ bench.port }}</a>
        <span v-else class="font-medium text-ink-gray-5">{{ bench.port }}</span>
      </span>
    </div>

    <!-- Actions -->
    <div class="flex items-center gap-2 pt-2 border-t border-outline-gray-2" @click.stop>
      <button
        v-if="bench.status === 'stopped'"
        class="bench-btn bench-btn-start"
        :disabled="!!actionLoading"
        @click="handleStart"
      >
        <span v-if="actionLoading === 'start'" class="btn-spin" />
        <span v-else>Start</span>
      </button>
      <button
        v-else
        class="bench-btn bench-btn-stop"
        :disabled="!!actionLoading"
        @click="handleStop"
      >
        <span v-if="actionLoading === 'stop'" class="btn-spin" />
        <span v-else>Stop</span>
      </button>
      <span class="flex-1" />
      <Button
        theme="red"
        variant="subtle"
        size="sm"
        label="Delete"
        :loading="actionLoading === 'delete'"
        @click="confirmDelete"
      />
    </div>

    <!-- Error message -->
    <p v-if="errorMessage" class="text-xs text-ink-red-4">{{ errorMessage }}</p>

    <!-- Install honcho prompt -->
    <div v-if="missingHoncho" class="rounded-lg bg-surface-amber-1 border border-outline-amber-1 p-3 text-sm">
      <p class="font-medium text-ink-amber-3 mb-2">honcho is not installed</p>
      <Button
        theme="orange"
        variant="subtle"
        size="sm"
        label="Install honcho"
        :loading="actionLoading === 'honcho'"
        @click.stop="handleInstallHoncho"
      />
    </div>
  </div>

  <!-- Delete confirmation dialog -->
  <Dialog
    v-model="showDeleteDialog"
    :options="{
      title: 'Delete bench?',
      icon: { name: 'trash-2', appearance: 'danger' },
      message: `This will permanently delete all files for ${bench.name}. This cannot be undone.`,
      actions: [
        {
          label: 'Delete',
          theme: 'red',
          variant: 'solid',
          loading: actionLoading === 'delete',
          onClick: ({ close }) => handleDelete(close),
        },
      ],
    }"
  />
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Button, Dialog } from 'frappe-ui'
import BenchStatusBadge from './BenchStatusBadge.vue'

const props = defineProps({
  bench: {
    type: Object,
    required: true,
  },
})

const emit = defineEmits(['refresh'])
const router = useRouter()

const actionLoading = ref(null)
const errorMessage = ref('')
const missingHoncho = ref(false)
const showDeleteDialog = ref(false)

function navigateToDetail() {
  router.push({ name: 'BenchDetail', params: { name: props.bench.name } })
}

async function handleStart() {
  actionLoading.value = 'start'
  errorMessage.value = ''
  missingHoncho.value = false
  try {
    const res = await fetch(`/api/benches/${props.bench.name}/start`, { method: 'POST' })
    const data = await res.json()
    if (!data.success) {
      errorMessage.value = data.message || 'Failed to start bench'
      missingHoncho.value = data.missing_honcho || false
    }
    emit('refresh')
  } catch (e) {
    errorMessage.value = e.message
  } finally {
    actionLoading.value = null
  }
}

async function handleStop() {
  actionLoading.value = 'stop'
  errorMessage.value = ''
  try {
    await fetch(`/api/benches/${props.bench.name}/stop`, { method: 'POST' })
    emit('refresh')
  } catch (e) {
    errorMessage.value = e.message
  } finally {
    actionLoading.value = null
  }
}

function confirmDelete() {
  showDeleteDialog.value = true
}

async function handleDelete(close) {
  actionLoading.value = 'delete'
  try {
    const res = await fetch(`/api/benches/${props.bench.name}`, { method: 'DELETE' })
    if (!res.ok) {
      const data = await res.json()
      errorMessage.value = data.detail || 'Delete failed'
    } else {
      close?.()
      showDeleteDialog.value = false
      emit('refresh')
    }
  } catch (e) {
    errorMessage.value = e.message
  } finally {
    actionLoading.value = null
  }
}

async function handleInstallHoncho() {
  actionLoading.value = 'honcho'
  errorMessage.value = ''
  try {
    const res = await fetch(`/api/benches/${props.bench.name}/install-honcho`, { method: 'POST' })
    const data = await res.json()
    if (data.success) {
      missingHoncho.value = false
    } else {
      errorMessage.value = data.message || 'Install failed'
    }
  } catch (e) {
    errorMessage.value = e.message
  } finally {
    actionLoading.value = null
  }
}
</script>

<style scoped>
.bench-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.375rem;
  border-radius: 0.375rem;
  font-size: 0.75rem;
  font-weight: 500;
  cursor: pointer;
  padding: 0.25rem 0.75rem;
  height: 1.75rem;
  transition: opacity 0.15s ease, background-color 0.15s ease;
  line-height: 1;
}
.bench-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.bench-btn-start {
  background-color: #16a34a;
  color: #ffffff;
  border: 1px solid #15803d;
}
.bench-btn-start:hover:not(:disabled) { background-color: #15803d; }

.bench-btn-stop {
  background-color: transparent;
  color: #e5e7eb;
  border: 1px solid #6b7280;
}
.bench-btn-stop:hover:not(:disabled) {
  background-color: rgba(107,114,128,0.15);
  border-color: #9ca3af;
}

.btn-spin {
  display: inline-block;
  width: 0.625rem;
  height: 0.625rem;
  border: 1.5px solid currentColor;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
