<template>
  <Badge
    :theme="status === 'running' ? 'green' : 'gray'"
    :label="status === 'running' ? 'Running' : 'Stopped'"
    size="md"
  />
</template>

<script setup>
import { Badge } from 'frappe-ui'

defineProps({
  status: {
    type: String,
    required: true,
    validator: (v) => ['running', 'stopped'].includes(v),
  },
})
</script>
