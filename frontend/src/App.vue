<script setup lang="ts">
import { Rocket, Settings, LayoutDashboard } from 'lucide-vue-next'
</script>

<template>
  <div class="min-h-screen">
    <nav class="bg-slate-900 text-white shadow-lg">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex items-center justify-between h-16">
          <div class="flex items-center gap-8">
            <router-link to="/" class="flex items-center gap-2">
              <Rocket class="text-blue-400" />
              <span class="font-bold text-xl tracking-tight">CNAIP Jobs</span>
            </router-link>
            <div class="hidden md:flex gap-4">
              <router-link to="/" class="text-gray-300 hover:text-white flex items-center gap-1 text-sm font-medium" active-class="text-white border-b-2 border-blue-500 pb-1">
                <LayoutDashboard :size="16" /> Nástěnka
              </router-link>
              <router-link to="/admin" class="text-gray-300 hover:text-white flex items-center gap-1 text-sm font-medium" active-class="text-white border-b-2 border-blue-500 pb-1">
                <Settings :size="16" /> Admin
              </router-link>
            </div>
          </div>
          <div class="flex items-center gap-4">
            <span class="text-xs bg-green-500/20 text-green-400 px-2 py-1 rounded border border-green-500/30">API: Online</span>
          </div>
        </div>
      </div>
    </nav>

    <main class="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
      <router-view />
    </main>
  </div>
</template>