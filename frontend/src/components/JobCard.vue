<script setup lang="ts">
import { computed } from 'vue'
import { MapPin, Clock, ExternalLink, Cpu } from 'lucide-vue-next'

const props = defineProps<{
  job: {
    id: number
    title: string
    company: string
    location: string
    summary: string
    keywords: string
    link: string | null
    created_at: string
  }
}>()

const initials = computed(() => {
  return props.job.company
    ? props.job.company.split(' ').map(word => word[0]).join('').toUpperCase().slice(0, 2)
    : '??'
})

const keywordList = computed(() => {
  if (!props.job.keywords) return []
  return props.job.keywords.split(',').map(k => k.trim()).filter(k => k)
})

const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleDateString('cs-CZ')
}
</script>

<template>
  <div class="flex flex-col md:flex-row items-start p-6 mb-4 bg-white border border-gray-100 rounded-2xl transition-all hover:shadow-md hover:border-blue-100 group">
    <!-- Logo / Initials -->
    <div class="w-16 h-16 bg-gray-50 rounded-xl flex items-center justify-center mr-6 shrink-0 mb-4 md:mb-0 border border-gray-50">
      <span class="text-[#002B5C] font-black text-2xl">{{ initials }}</span>
    </div>

    <!-- Job Info -->
    <div class="flex-1 min-w-0">
      <div class="flex justify-between items-start">
        <div class="mb-2">
          <div class="flex items-center gap-2">
            <h3 class="text-xl font-bold text-[#002B5C] tracking-tight">{{ job.title }}</h3>
            <a v-if="job.link" :href="job.link" target="_blank" class="text-gray-300 hover:text-blue-600 transition-colors">
              <ExternalLink :size="18" />
            </a>
          </div>
          <p class="text-gray-600 font-medium text-lg">{{ job.company }}</p>
        </div>
        
        <div class="hidden md:flex items-center gap-4 shrink-0 text-gray-400">
          <span class="flex items-center gap-1.5 px-3 py-1 bg-blue-50/50 rounded-full text-xs font-bold text-blue-800">
            <MapPin :size="14" /> {{ job.location || 'Dle webu' }}
          </span>
          <span class="flex items-center gap-1.5 text-xs font-medium">
            <Clock :size="14" /> {{ formatDate(job.created_at) }}
          </span>
        </div>
      </div>
      
      <!-- Keywords as tags -->
      <div v-if="keywordList.length" class="flex flex-wrap gap-2 mb-4">
        <span v-for="kw in keywordList" :key="kw" class="px-2.5 py-1 rounded bg-gray-50 text-gray-500 text-[10px] font-bold uppercase tracking-wider border border-gray-100">
          {{ kw }}
        </span>
      </div>

      <!-- Summary snippet -->
      <div v-if="job.summary" class="flex items-start gap-3 text-sm text-gray-500 italic mb-4 leading-relaxed">
        <Cpu :size="16" class="text-purple-400 mt-0.5 shrink-0" />
        <p>{{ job.summary }}</p>
      </div>

      <!-- Visible link -->
      <div v-if="job.link" class="pt-2">
        <a :href="job.link" target="_blank" class="text-sm font-bold text-blue-600 hover:underline flex items-center gap-1">
          Zobrazit celý inzerát <ExternalLink :size="14" />
        </a>
      </div>
    </div>
  </div>
</template>