<script setup lang="ts">
import { computed } from 'vue'
import { MapPin, Clock, ExternalLink, Cpu, Tag } from 'lucide-vue-next'

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
    .split(' ')
    .map(word => word[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)
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
  <div class="flex flex-col md:flex-row items-start md:items-center p-6 mb-3 bg-white border border-gray-100 rounded-xl transition-all hover:shadow-lg hover:border-blue-100 group">
    <!-- Logo / Initials -->
    <div class="w-16 h-16 bg-gray-50 rounded-lg flex items-center justify-center mr-6 shrink-0 mb-4 md:mb-0 border border-gray-50">
      <span class="text-[#002B5C] font-bold text-xl">{{ initials }}</span>
    </div>

    <!-- Job Info -->
    <div class="flex-1 min-w-0 mr-4">
      <div class="flex items-center gap-2 mb-1">
        <h3 class="text-lg font-bold text-[#002B5C] truncate group-hover:text-blue-700 transition-colors">
          {{ job.title }}
        </h3>
        <a v-if="job.link" :href="job.link" target="_blank" class="text-gray-300 hover:text-[#002B5C] transition-colors">
          <ExternalLink :size="16" />
        </a>
      </div>
      <p class="text-md font-medium text-gray-700 mb-2">{{ job.company }}</p>
      
      <!-- Keywords as tags -->
      <div v-if="keywordList.length" class="flex flex-wrap gap-1 mb-3">
        <span v-for="kw in keywordList" :key="kw" class="px-2 py-0.5 rounded bg-slate-50 text-slate-500 text-[10px] font-bold uppercase border border-slate-100">
          {{ kw }}
        </span>
      </div>

      <!-- AI Summary snippet -->
      <div v-if="job.summary" class="flex items-center gap-2 text-xs text-gray-500 italic">
        <Cpu :size="12" class="text-purple-400" />
        <span class="truncate">{{ job.summary }}</span>
      </div>
    </div>

    <!-- Tags & Actions -->
    <div class="flex flex-wrap items-center gap-2 mt-4 md:mt-0 shrink-0">
      <span class="flex items-center gap-1 px-3 py-1 rounded-full text-xs font-semibold bg-blue-50 text-[#002B5C]">
        <MapPin :size="12" /> {{ job.location || 'Remote' }}
      </span>
      <span class="flex items-center gap-1 px-3 py-1 rounded-full text-xs font-semibold bg-gray-50 text-gray-600">
        <Clock :size="12" /> {{ formatDate(job.created_at) }}
      </span>
    </div>
  </div>
</template>