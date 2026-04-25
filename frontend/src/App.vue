<script setup lang="ts">
import JobBoard from './components/JobBoard.vue'
import { Rocket } from 'lucide-vue-next'
</script>

<template>
  <div class="min-h-screen">
    <nav class="bg-slate-900 text-white shadow-lg">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex items-center justify-between h-16">
          <div class="flex items-center gap-2">
            <Rocket class="text-blue-400" />
            <span class="font-bold text-xl tracking-tight">Job Scraper Pro</span>
          </div>
          <div class="flex items-center gap-4">
            <span class="text-xs bg-green-500/20 text-green-400 px-2 py-1 rounded border border-green-500/30">API: Online</span>
          </div>
        </div>
      </div>
    </nav>

    <main class="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
      <JobBoard />
    </main>
  </div>
</template>