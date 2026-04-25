<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import axios from 'axios'
import { Search, Briefcase, MapPin, Cpu, Clock, ExternalLink } from 'lucide-vue-next'

interface Job {
  id: number
  title: string
  company: string
  location: string
  summary: string
  keywords: string
  link: string | null
  created_at: string
}

const jobs = ref<Job[]>([])
const loading = ref(true)
const searchQuery = ref('')

const fetchJobs = async () => {
  try {
    const response = await axios.get('/api/jobs')
    jobs.value = response.data
  } catch (error) {
    console.error('Chyba při načítání pozic:', error)
  } finally {
    loading.value = false
  }
}

const filteredJobs = computed(() => {
  const query = searchQuery.value.toLowerCase()
  return jobs.value.filter(job => 
    job.title.toLowerCase().includes(query) || 
    job.company.toLowerCase().includes(query) ||
    (job.summary && job.summary.toLowerCase().includes(query))
  )
})

const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleDateString('cs-CZ')
}

onMounted(fetchJobs)
</script>

<template>
  <div class="space-y-6">
    <!-- Search Bar -->
    <div class="relative">
      <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
        <Search class="h-5 w-5 text-gray-400" />
      </div>
      <input 
        v-model="searchQuery"
        type="text" 
        class="block w-full pl-10 pr-3 py-3 border border-gray-300 rounded-xl leading-5 bg-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 sm:text-sm shadow-sm transition-all"
        placeholder="Hledat pozici, firmu nebo klíčové slovo..."
      >
    </div>

    <!-- Job Stats -->
    <div class="flex items-center justify-between">
      <h2 class="text-lg font-semibold text-gray-700">
        Nalezené pozice ({{ filteredJobs.length }})
      </h2>
      <button @click="fetchJobs" class="text-sm text-blue-600 hover:text-blue-800 font-medium">
        Aktualizovat seznam
      </button>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="flex flex-col items-center justify-center py-20 space-y-4">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      <p class="text-gray-500">Načítám pracovní nabídky...</p>
    </div>

    <!-- Jobs List -->
    <div v-else class="grid gap-4">
      <div 
        v-for="job in filteredJobs" 
        :key="job.id" 
        class="bg-white rounded-xl shadow-sm border border-gray-100 p-6 hover:shadow-md transition-all group"
      >
        <div class="flex justify-between items-start">
          <div class="space-y-1">
            <div class="flex items-center gap-2">
              <h3 class="text-xl font-bold text-gray-900 leading-tight">{{ job.title }}</h3>
              <a v-if="job.link" :href="job.link" target="_blank" class="text-blue-400 hover:text-blue-600 transition-colors" title="Otevřít inzerát">
                <ExternalLink :size="18" />
              </a>
            </div>
            <div class="flex flex-wrap items-center gap-4 text-sm text-gray-500">
              <span class="flex items-center gap-1">
                <Briefcase :size="16" /> {{ job.company }}
              </span>
              <span class="flex items-center gap-1">
                <MapPin :size="16" /> {{ job.location || 'Remote' }}
              </span>
              <span class="flex items-center gap-1">
                <Clock :size="16" /> {{ formatDate(job.created_at) }}
              </span>
            </div>
          </div>
          <div v-if="job.keywords" class="hidden sm:flex flex-wrap gap-1 max-w-[200px] justify-end">
             <span 
              v-for="kw in job.keywords.split(',')" 
              :key="kw"
              class="px-2 py-0.5 bg-blue-50 text-blue-700 text-[10px] font-semibold rounded-full border border-blue-100"
            >
              {{ kw.trim() }}
            </span>
          </div>
        </div>

        <div class="mt-4 p-4 bg-gray-50 rounded-lg">
          <div class="flex items-start gap-2">
            <Cpu :size="18" class="text-purple-500 mt-1 shrink-0" />
            <p class="text-sm text-gray-700 leading-relaxed italic">
              {{ job.summary || 'Tato pozice zatím nebyla analyzována pomocí AI.' }}
            </p>
          </div>
        </div>
      </div>

      <div v-if="filteredJobs.length === 0" class="text-center py-20 bg-white rounded-xl border-2 border-dashed border-gray-200">
        <p class="text-gray-500">Žádné pozice neodpovídají vašemu hledání.</p>
      </div>
    </div>
  </div>
</template>