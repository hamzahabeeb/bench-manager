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
        <FormControl label="MariaDB Root Password (optional)" type="password" v-model="newSite.db_root_password" placeholder="••••••••" />
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
    :options="{
      title: 'Drop site?',
      icon: { name: 'trash-2', appearance: 'danger' },
      message: dropTarget ? `This will permanently drop ${dropTarget.name} and its database. This cannot be undone.` : '',
      actions: [
        {
          label: 'Drop',
          theme: 'red',
          variant: 'solid',
          loading: dropTarget && siteActions[dropTarget.name] === 'drop',
          onClick: ({ close }) => handleDrop(close),
        },
      ],
    }"
  />

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

const backupTarget = ref(null)
const showBackupDialog = ref(false)
const backupJobId = ref(null)
const backupJobDone = ref(false)
const backupFiles = ref([])

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
  showDropDialog.value = true
}

async function handleDrop(close) {
  if (!dropTarget.value) return
  const siteName = dropTarget.value.name
  siteActions[siteName] = 'drop'
  errorMessage.value = ''
  try {
    const res = await fetch(`/api/benches/${props.benchName}/sites/${siteName}`, { method: 'DELETE' })
    const data = await res.json()
    if (!data.success) {
      errorMessage.value = data.error || 'Drop failed'
    } else {
      close?.()
      showDropDialog.value = false
      dropTarget.value = null
      emit('refresh')
    }
  } catch (e) {
    errorMessage.value = e.message
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
    backupFiles.value = (data.backups || []).slice(0, 4)
  } catch (e) {}
}

function formatFileSize(bytes) {
  if (bytes >= 1024 * 1024) {
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }
  return (bytes / 1024).toFixed(1) + ' KB'
}
</script>
