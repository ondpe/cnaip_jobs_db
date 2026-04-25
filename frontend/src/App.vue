<script setup lang="ts">
import { transition } from 'vue'
</script>

<template>
  <div class="min-h-screen bg-white">
    <!-- Navbar odstraněn pro veřejnou část -->
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