<template>
  <div class="site-list">
    <!-- Toolbar -->
    <div class="flex items-center justify-between mb-4">
      <span class="text-sm text-ink-gray-4">
        {{ sites.length }} {{ sites.length === 1 ? 'site' : 'sites' }}
      </span>
      <Button size="sm" icon-left="plus" label="New Site" @click="openNewSiteDialog" />
    </div>

    <!-- Empty state -->
    <div v-if="sites.length === 0" class="text-center py-10 border border-dashed border-outline-gray-2 rounded-lg">
      <p class="text-ink-gray-4 text-sm">No sites yet.</p>
      <p class="text-ink-gray-3 text-xs mt-1">Create a site to get started.</p>
    </div>

    <!-- Sites table -->
    <div v-else class="rounded-lg border border-outline-gray-2 overflow-hidden">
      <div class="grid grid-cols-[2fr_2fr_2fr_auto] gap-4 px-4 py-2 bg-surface-gray-1 text-xs font-semibold uppercase tracking-wider text-ink-gray-3">
        <span>Site</span>
        <span>Apps</span>
        <span>Database</span>
        <span class="text-right">Actions</span>
      </div>
      <div
        v-for="site in sites"
        :key="site.name"
        class="grid grid-cols-[2fr_2fr_2fr_auto] gap-4 px-4 py-3 items-center border-t border-outline-gray-2 hover:bg-surface-gray-1 transition-colors"
      >
        <span class="font-mono text-sm text-ink-gray-7">{{ site.name }}</span>
        <span class="flex flex-wrap gap-1">
          <span
            v-for="app in site.installed_apps"
            :key="app"
            class="px-1.5 py-0.5 rounded text-xs font-medium bg-surface-blue-2 text-ink-blue-3 border border-outline-gray-2"
          >{{ app }}</span>
          <span v-if="site.installed_apps.length === 0" class="text-ink-gray-3 text-xs">—</span>
        </span>
        <span class="text-xs text-ink-gray-4">
          {{ site.db_name || '—' }}
          <span v-if="site.db_type" class="text-ink-gray-3">({{ site.db_type }})</span>
        </span>
        <div class="flex justify-end gap-1.5">
          <Button
            variant="ghost"
            size="sm"
            :label="useStates[site.name] === 'done' ? '✓ Active' : 'Use'"
            :loading="useStates[site.name] === 'using'"
            :disabled="!!siteActions[site.name] || !!useStates[site.name]"
            @click="handleUse(site)"
          />
          <Button
            variant="ghost"
            size="sm"
            label="Migrate"
            :loading="siteActions[site.name] === 'migrate'"
            :disabled="!!siteActions[site.name]"
            @click="handleMigrate(site)"
          />
          <Button
            variant="ghost"
            size="sm"
            label="Install App"
            :disabled="!!siteActions[site.name]"
            @click="openInstallAppDialog(site)"
          />
          <Button
            variant="ghost"
            size="sm"
            label="Backup"
            :disabled="!!siteActions[site.name]"
            @click="handleBackup(site)"
          />
          <Button
            variant="ghost"
            size="sm"
            label="Restore"
            :disabled="!!siteActions[site.name]"
            @click="openRestoreDialog(site)"
          />
          <Button
            theme="red"
            variant="ghost"
            size="sm"
            label="Drop"
            :loading="siteActions[site.name] === 'drop'"
            :disabled="!!siteActions[site.name]"
            @click="confirmDrop(site)"
          />
        </div>
      </div>
    </div>

    <!-- Error message -->
    <p v-if="errorMessage" class="text-xs text-ink-red-4 mt-3">{{ errorMessage }}</p>

    <!-- Job output (migrate / install-app) -->
    <div v-if="activeJobId" class="mt-4">
      <JobOutput :job-id="activeJobId" :title="activeJobTitle" @done="onJobDone" />
    </div>
  </div>

  <!-- New Site Dialog -->
  <Dialog
    v-model="showNewSiteDialog"
    :options="{ title: 'Create New Site', size: 'sm' }"
  >
    <template #body-content>
      <form @submit.prevent="handleCreateSite" class="flex flex-col gap-3">
        <FormControl label="Site Name" v-model="newSite.site_name" placeholder="mysite.localhost" :required="true" autocomplete="off" />
        <FormControl label="Admin Password" type="password" v-model="newSite.admin_password" placeholder="••••••••" :required="true" />
        <FormControl label="DB Name (optional)" v-model="newSite.db_name" placeholder="Auto-generated" />
        <FormControl label="MariaDB Root Password" type="password" v-model="newSite.db_root_password" placeholder="••••••••" :required="true" />
        <div class="flex justify-end gap-2 pt-2">
          <Button variant="ghost" size="sm" label="Cancel" @click="showNewSiteDialog = false" />
          <Button type="submit" size="sm" label="Create Site" :loading="createLoading" />
        </div>
      </form>
    </template>
  </Dialog>

  <!-- Install App Dialog -->
  <Dialog
    v-model="showInstallAppDialog"
    :options="{ title: `Install App on ${installTarget?.name}`, size: 'sm' }"
  >
    <template #body-content>
      <form @submit.prevent="handleInstallApp" class="flex flex-col gap-3">
        <FormControl label="App Name" v-model="installAppName" placeholder="e.g. erpnext" :required="true" autocomplete="off" />
        <div class="flex justify-end gap-2 pt-2">
          <Button variant="ghost" size="sm" label="Cancel" @click="showInstallAppDialog = false" />
          <Button type="submit" size="sm" label="Install" :loading="installLoading" />
        </div>
      </form>
    </template>
  </Dialog>

  <!-- Drop confirmation dialog -->
  <Dialog
    v-model="showDropDialog"
    :options="{ title: 'Drop site?', size: 'sm' }"
  >
    <template #body-content>
      <form @submit.prevent="handleDrop" class="flex flex-col gap-3">
        <p class="text-sm text-ink-gray-6">
          This will permanently drop
          <span class="font-semibold font-mono text-ink-gray-8">{{ dropTarget?.name }}</span>
          and its database. This cannot be undone.
        </p>
        <FormControl
          label="MariaDB Root Password"
          type="password"
          v-model="dropRootPassword"
          placeholder="••••••••"
          :required="true"
          autocomplete="off"
        />
        <p v-if="dropError" class="text-xs text-ink-red-4">{{ dropError }}</p>
        <div class="flex justify-end gap-2 pt-1">
          <Button variant="ghost" size="sm" label="Cancel" @click="showDropDialog = false" />
          <Button
            type="submit"
            theme="red"
            variant="solid"
            size="sm"
            label="Drop Site"
            :loading="dropTarget && siteActions[dropTarget.name] === 'drop'"
          />
        </div>
      </form>
    </template>
  </Dialog>

  <!-- Backup Dialog -->
  <Dialog
    v-model="showBackupDialog"
    :options="{ title: backupTarget ? `Backup: ${backupTarget.name}` : 'Backup', size: 'lg' }"
  >
    <template #body-content>
      <div class="flex flex-col gap-4">
        <JobOutput
          v-if="backupJobId"
          :job-id="backupJobId"
          :title="`Backing up: ${backupTarget?.name}`"
          @done="onBackupJobDone"
        />
        <div v-if="backupJobDone && backupFiles.length > 0" class="flex flex-col gap-2">
          <p class="text-sm font-medium text-ink-gray-7">Backup files ready for download:</p>
          <ul class="flex flex-col gap-1">
            <li v-for="file in backupFiles" :key="file.filename" class="flex items-center justify-between gap-2 px-3 py-2 rounded border border-outline-gray-2 bg-surface-gray-1">
              <span class="font-mono text-xs text-ink-gray-6 truncate">{{ file.filename }}</span>
              <div class="flex items-center gap-2 shrink-0">
                <span class="text-xs text-ink-gray-3">{{ formatFileSize(file.size) }}</span>
                <a
                  :href="`/api/benches/${props.benchName}/sites/${backupTarget.name}/backups/${file.filename}`"
                  download
                  class="text-xs text-ink-blue-3 hover:underline"
                >Download</a>
              </div>
            </li>
          </ul>
        </div>
        <div v-if="backupJobDone && backupFiles.length === 0" class="text-sm text-ink-gray-4">
          No backup files found.
        </div>
        <div class="flex justify-end pt-1">
          <Button variant="ghost" size="sm" label="Close" @click="showBackupDialog = false" />
        </div>
      </div>
    </template>
  </Dialog>
  <!-- Restore Dialog -->
  <Dialog
    v-model="showRestoreDialog"
    :options="{ title: restoreTarget ? `Restore: ${restoreTarget.name}` : 'Restore Site', size: 'md' }"
  >
    <template #body-content>
      <div class="flex flex-col gap-4">
        <!-- Job output while restoring -->
        <JobOutput
          v-if="restoreJobId"
          :job-id="restoreJobId"
          title="Restoring site..."
          @done="onRestoreJobDone"
        />

        <!-- Upload form (shown before job starts) -->
        <form v-if="!restoreJobId" @submit.prevent="handleRestore" class="flex flex-col gap-4">
          <div>
            <label class="block text-xs font-medium text-ink-gray-6 mb-1.5">
              Database Backup <span class="text-ink-red-3">*</span>
              <span class="font-normal text-ink-gray-3 ml-1">(.sql.gz)</span>
            </label>
            <label class="file-upload-label" :class="{ 'file-selected': !!restoreSqlFile }">
              <input
                type="file"
                accept=".gz,.sql.gz,.sql"
                class="hidden"
                @change="e => restoreSqlFile = e.target.files[0] || null"
              />
              <span class="file-upload-icon">↑</span>
              <span class="truncate">{{ restoreSqlFile ? restoreSqlFile.name : 'Click to select SQL backup file' }}</span>
            </label>
          </div>

          <div>
            <label class="block text-xs font-medium text-ink-gray-6 mb-1.5">
              Public Files
              <span class="font-normal text-ink-gray-3 ml-1">(optional, .tar)</span>
            </label>
            <label class="file-upload-label" :class="{ 'file-selected': !!restorePublicFile }">
              <input
                type="file"
                accept=".tar,.tar.gz,.tgz"
                class="hidden"
                @change="e => restorePublicFile = e.target.files[0] || null"
              />
              <span class="file-upload-icon">↑</span>
              <span class="truncate">{{ restorePublicFile ? restorePublicFile.name : 'Click to select public files archive' }}</span>
            </label>
          </div>

          <div>
            <label class="block text-xs font-medium text-ink-gray-6 mb-1.5">
              Private Files
              <span class="font-normal text-ink-gray-3 ml-1">(optional, .tar)</span>
            </label>
            <label class="file-upload-label" :class="{ 'file-selected': !!restorePrivateFile }">
              <input
                type="file"
                accept=".tar,.tar.gz,.tgz"
                class="hidden"
                @change="e => restorePrivateFile = e.target.files[0] || null"
              />
              <span class="file-upload-icon">↑</span>
              <span class="truncate">{{ restorePrivateFile ? restorePrivateFile.name : 'Click to select private files archive' }}</span>
            </label>
          </div>

          <p v-if="restoreError" class="text-xs text-ink-red-4">{{ restoreError }}</p>

          <div class="flex justify-end gap-2 pt-1">
            <Button variant="ghost" size="sm" label="Cancel" @click="showRestoreDialog = false" />
            <Button
              type="submit"
              size="sm"
              label="Restore Site"
              :loading="restoreLoading"
              :disabled="!restoreSqlFile || restoreLoading"
            />
          </div>
        </form>

        <!-- Close button after job completes -->
        <div v-if="restoreJobId && restoreJobDone" class="flex justify-end pt-1">
          <Button variant="ghost" size="sm" label="Close" @click="showRestoreDialog = false" />
        </div>
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { Button, Dialog, FormControl } from 'frappe-ui'
import JobOutput from './JobOutput.vue'

const props = defineProps({
  benchName: { type: String, required: true },
  sites: { type: Array, default: () => [] },
})

const emit = defineEmits(['refresh'])

const errorMessage = ref('')
const siteActions = reactive({})
const useStates = reactive({})
const activeJobId = ref(null)
const activeJobTitle = ref('')

const showNewSiteDialog = ref(false)
const createLoading = ref(false)
const newSite = reactive({ site_name: '', admin_password: '', db_name: '', db_root_password: '' })

const showInstallAppDialog = ref(false)
const installTarget = ref(null)
const installAppName = ref('')
const installLoading = ref(false)

const showDropDialog = ref(false)
const dropTarget = ref(null)
const dropRootPassword = ref('')
const dropError = ref('')

const backupTarget = ref(null)
const showBackupDialog = ref(false)
const backupJobId = ref(null)
const backupJobDone = ref(false)
const backupFiles = ref([])
const backupStartedAt = ref(0)

const restoreTarget = ref(null)
const showRestoreDialog = ref(false)
const restoreJobId = ref(null)
const restoreJobDone = ref(false)
const restoreLoading = ref(false)
const restoreError = ref('')
const restoreSqlFile = ref(null)
const restorePublicFile = ref(null)
const restorePrivateFile = ref(null)

function openNewSiteDialog() {
  Object.assign(newSite, { site_name: '', admin_password: '', db_name: '', db_root_password: '' })
  showNewSiteDialog.value = true
}

async function handleCreateSite() {
  createLoading.value = true
  errorMessage.value = ''
  try {
    const body = new FormData()
    body.append('site_name', newSite.site_name)
    body.append('admin_password', newSite.admin_password)
    if (newSite.db_name) body.append('db_name', newSite.db_name)
    if (newSite.db_root_password) body.append('db_root_password', newSite.db_root_password)

    const res = await fetch(`/api/benches/${props.benchName}/sites`, { method: 'POST', body })
    const data = await res.json()
    if (!res.ok) { errorMessage.value = data.detail || 'Create site failed'; return }
    showNewSiteDialog.value = false
    activeJobId.value = data.job_id
    activeJobTitle.value = `Creating site: ${newSite.site_name}`
  } catch (e) {
    errorMessage.value = e.message
  } finally {
    createLoading.value = false
  }
}

async function handleUse(site) {
  useStates[site.name] = 'using'
  errorMessage.value = ''
  try {
    const res = await fetch(`/api/benches/${props.benchName}/sites/${site.name}/use`, { method: 'POST' })
    const data = await res.json()
    if (!data.success) {
      errorMessage.value = data.error || 'bench use failed'
      delete useStates[site.name]
    } else {
      useStates[site.name] = 'done'
      setTimeout(() => delete useStates[site.name], 3000)
    }
  } catch (e) {
    errorMessage.value = e.message
    delete useStates[site.name]
  }
}

async function handleMigrate(site) {
  siteActions[site.name] = 'migrate'
  errorMessage.value = ''
  try {
    const res = await fetch(`/api/benches/${props.benchName}/sites/${site.name}/migrate`, { method: 'POST' })
    const data = await res.json()
    if (!res.ok) { errorMessage.value = data.detail || 'Migrate failed'; return }
    activeJobId.value = data.job_id
    activeJobTitle.value = `Migrating site: ${site.name}`
  } catch (e) {
    errorMessage.value = e.message
  } finally {
    delete siteActions[site.name]
  }
}

function openInstallAppDialog(site) {
  installTarget.value = site
  installAppName.value = ''
  showInstallAppDialog.value = true
}

async function handleInstallApp() {
  if (!installTarget.value) return
  installLoading.value = true
  errorMessage.value = ''
  try {
    const body = new FormData()
    body.append('app_name', installAppName.value)
    const res = await fetch(`/api/benches/${props.benchName}/sites/${installTarget.value.name}/install-app`, { method: 'POST', body })
    const data = await res.json()
    if (!res.ok) { errorMessage.value = data.detail || 'Install failed'; return }
    showInstallAppDialog.value = false
    activeJobId.value = data.job_id
    activeJobTitle.value = `Installing ${installAppName.value} on ${installTarget.value.name}`
  } catch (e) {
    errorMessage.value = e.message
  } finally {
    installLoading.value = false
  }
}

function confirmDrop(site) {
  dropTarget.value = site
  dropRootPassword.value = ''
  dropError.value = ''
  showDropDialog.value = true
}

async function handleDrop() {
  if (!dropTarget.value) return
  const siteName = dropTarget.value.name
  siteActions[siteName] = 'drop'
  dropError.value = ''
  try {
    const params = dropRootPassword.value
      ? `?root_password=${encodeURIComponent(dropRootPassword.value)}`
      : ''
    const res = await fetch(`/api/benches/${props.benchName}/sites/${siteName}${params}`, { method: 'DELETE' })
    const data = await res.json()
    if (!data.success) {
      dropError.value = data.error || 'Drop failed'
    } else {
      showDropDialog.value = false
      dropTarget.value = null
      emit('refresh')
    }
  } catch (e) {
    dropError.value = e.message
  } finally {
    delete siteActions[siteName]
  }
}

function onJobDone() {
  setTimeout(() => emit('refresh'), 1500)
}

function handleBackup(site) {
  backupTarget.value = site
  backupJobId.value = null
  backupJobDone.value = false
  backupFiles.value = []
  backupStartedAt.value = Date.now() / 1000 - 2  // 2s buffer for clock skew
  showBackupDialog.value = true
  startBackup(site)
}

async function startBackup(site) {
  try {
    const res = await fetch(`/api/benches/${props.benchName}/sites/${site.name}/backup`, { method: 'POST' })
    const data = await res.json()
    backupJobId.value = data.job_id
  } catch (e) {
    errorMessage.value = e.message
  }
}

async function onBackupJobDone() {
  backupJobDone.value = true
  try {
    const res = await fetch(`/api/benches/${props.benchName}/sites/${backupTarget.value.name}/backups`)
    const data = await res.json()
    backupFiles.value = (data.backups || []).filter(f => f.modified >= backupStartedAt.value)
  } catch (e) {}
}

function openRestoreDialog(site) {
  restoreTarget.value = site
  restoreJobId.value = null
  restoreJobDone.value = false
  restoreError.value = ''
  restoreSqlFile.value = null
  restorePublicFile.value = null
  restorePrivateFile.value = null
  showRestoreDialog.value = true
}

async function handleRestore() {
  if (!restoreSqlFile.value) return
  restoreLoading.value = true
  restoreError.value = ''
  try {
    const body = new FormData()
    body.append('sql_file', restoreSqlFile.value)
    if (restorePublicFile.value) body.append('public_file', restorePublicFile.value)
    if (restorePrivateFile.value) body.append('private_file', restorePrivateFile.value)
    const res = await fetch(
      `/api/benches/${props.benchName}/sites/${restoreTarget.value.name}/restore`,
      { method: 'POST', body },
    )
    const data = await res.json()
    if (!res.ok) { restoreError.value = data.detail || 'Restore failed'; return }
    restoreJobId.value = data.job_id
  } catch (e) {
    restoreError.value = e.message
  } finally {
    restoreLoading.value = false
  }
}

function onRestoreJobDone() {
  restoreJobDone.value = true
}

function formatFileSize(bytes) {
  if (bytes >= 1024 * 1024) {
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }
  return (bytes / 1024).toFixed(1) + ' KB'
}
</script>

<style scoped>
.file-upload-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  border-radius: 0.375rem;
  border: 1px dashed var(--outline-gray-3);
  background: var(--surface-gray-1);
  color: var(--ink-gray-4);
  font-size: 0.75rem;
  cursor: pointer;
  transition: all 0.15s ease;
  overflow: hidden;
}
.file-upload-label:hover {
  border-color: var(--outline-gray-4);
  background: var(--surface-gray-2);
  color: var(--ink-gray-6);
}
.file-upload-label.file-selected {
  border-color: var(--outline-blue-1);
  border-style: solid;
  background: var(--surface-blue-1);
  color: var(--ink-blue-3);
}
.file-upload-icon {
  flex-shrink: 0;
  font-size: 0.875rem;
}
</style>
