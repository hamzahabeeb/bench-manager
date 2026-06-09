<template>
  <div class="min-h-screen bg-surface-white">
    <nav class="sticky top-0 z-10 h-12 border-b border-outline-gray-2 bg-surface-white flex items-center px-5 gap-3">
      <router-link to="/" class="text-ink-gray-8 font-semibold text-sm hover:text-ink-gray-6 transition-colors">
        Bench Manager
      </router-link>
    </nav>
    <main class="px-6 py-5">
      <router-view />
    </main>
  </div>
</template>

<script setup>
</script>

<style>
*, *::before, *::after {
  box-sizing: border-box;
}
body {
  margin: 0;
}
a {
  text-decoration: none;
  color: inherit;
}
</style>
