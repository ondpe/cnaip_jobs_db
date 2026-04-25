<script setup lang="ts">
import { Settings, LayoutDashboard } from 'lucide-vue-next'
</script>

<template>
  <div class="min-h-screen bg-white">
    <!-- Navbar -->
    <nav class="bg-white border-b border-gray-100 sticky top-0 z-50">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex items-center justify-between h-20">
          <div class="flex items-center gap-12">
            <router-link to="/" class="flex items-center gap-3">
              <div class="w-8 h-8 bg-[#002B5C] rounded-md flex items-center justify-center">
                <span class="text-white font-black text-xs">AI</span>
              </div>
              <span class="font-black text-2xl tracking-tighter text-[#002B5C]">CNAIP JOBS</span>
            </router-link>
            
            <div class="hidden md:flex gap-8">
              <router-link to="/" class="text-sm font-bold transition-colors py-2" active-class="text-[#002B5C] border-b-2 border-[#002B5C]" inactive-class="text-gray-500 hover:text-[#002B5C]">
                Nástěnka
              </router-link>
              <router-link to="/admin" class="text-sm font-bold transition-colors py-2" active-class="text-[#002B5C] border-b-2 border-[#002B5C]" inactive-class="text-gray-500 hover:text-[#002B5C]">
                Admin rozhraní
              </router-link>
            </div>
          </div>
          
          <div class="flex items-center gap-4">
            <div class="hidden sm:flex items-center gap-2 px-3 py-1.5 bg-green-50 rounded-full border border-green-100">
              <div class="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              <span class="text-[10px] font-bold text-green-700 uppercase tracking-widest">Systém Aktivní</span>
            </div>
          </div>
        </div>
      </div>
    </nav>

    <main>
      <router-view v-slot="{ Component }">
        <transition 
          enter-active-class="transition duration-300 ease-out"
          enter-from-class="opacity-0 translate-y-4"
          enter-to-class="opacity-100 translate-y-0"
        >
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
  </div>
</template>