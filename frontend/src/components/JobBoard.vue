<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import axios from 'axios'
import { Search, Loader2 } from 'lucide-vue-next'
import JobCard from './JobCard.vue'

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
const activeTag = ref('Všechny pozice')

// Dynamicky extrahované kategorie/tagy
const availableTags = computed(() => {
  const tags = new Set<string>(['Všechny pozice'])
  jobs.value.forEach(job => {
    if (job.keywords) {
      job.keywords.split(',').forEach(k => {
        const trimmed = k.trim()
        if (trimmed && trimmed.length < 20) tags.add(trimmed)
      })
    }
  })
  // Vrátíme prvních 6 nejčastějších nebo zajímavých
  return Array.from(tags).slice(0, 8)
})

const fetchJobs = async () => {
  loading.value = true
  try {
    const response = await axios.get('/api/jobs')
    jobs.value = response.data.filter((j: Job) => j.link)
  } catch (error) {
    console.error('Chyba při načítání pozic:', error)
  } finally {
    loading.value = false
  }
}

const filteredJobs = computed(() => {
  const query = searchQuery.value.toLowerCase()
  return jobs.value.filter(job => {
    const matchesSearch = job.title.toLowerCase().includes(query) || 
                         job.company.toLowerCase().includes(query) ||
                         (job.keywords && job.keywords.toLowerCase().includes(query))
    
    const matchesTag = activeTag.value === 'Všechny pozice' || 
                      (job.keywords && job.keywords.toLowerCase().includes(activeTag.value.toLowerCase()))
    
    return matchesSearch && matchesTag
  })
})

onMounted(fetchJobs)
</script>

<template>
  <div class="max-w-5xl mx-auto px-4 py-12">
    <!-- Header with Search and Categories -->
    <div class="mb-12 space-y-10">
      <div class="text-center md:text-left">
        <h1 class="text-5xl font-black text-[#002B5C] mb-3 tracking-tighter">Kariéra v AI</h1>
        <p class="text-gray-500 text-xl font-medium">Najděte svou příští výzvu v nejlepších českých AI firmách.</p>
      </div>

      <div class="flex flex-col md:flex-row md:items-center justify-between gap-8 border-b border-gray-100 pb-2">
        <!-- Categories (Tags) -->
        <nav class="flex overflow-x-auto gap-8 no-scrollbar scroll-smooth">
          <button 
            v-for="tag in availableTags" 
            :key="tag"
            @click="activeTag = tag"
            :class="[
              'text-sm transition-all whitespace-nowrap pb-4 relative font-bold',
              activeTag === tag 
                ? 'text-[#002B5C]' 
                : 'text-gray-400 hover:text-[#002B5C]'
            ]"
          >
            {{ tag }}
            <div v-if="activeTag === tag" class="absolute bottom-0 left-0 right-0 h-1 bg-[#002B5C] rounded-full"></div>
          </button>
        </nav>

        <!-- Search Bar -->
        <div class="relative w-full md:w-80 mb-4 md:mb-0">
          <div class="absolute inset-y-0 left-4 flex items-center pointer-events-none">
            <Search class="h-4 w-4 text-gray-400" />
          </div>
          <input 
            v-model="searchQuery"
            type="text" 
            class="block w-full pl-11 pr-4 py-3 bg-white border border-gray-200 rounded-full text-sm placeholder-gray-400 focus:outline-none focus:ring-4 focus:ring-blue-50 focus:border-[#002B5C] transition-all shadow-sm"
            placeholder="Pozice, technologie nebo firma..."
          >
        </div>
      </div>
    </div>

    <!-- Content Area -->
    <div v-if="loading" class="flex flex-col items-center justify-center py-24 space-y-4">
      <Loader2 class="h-12 w-12 text-[#002B5C] animate-spin" />
      <p class="text-gray-400 font-bold uppercase tracking-widest text-xs">Aktualizujeme nabídky</p>
    </div>

    <div v-else>
      <div v-if="filteredJobs.length > 0" class="animate-in fade-in slide-in-from-bottom-4 duration-700">
        <JobCard 
          v-for="job in filteredJobs" 
          :key="job.id" 
          :job="job" 
        />
      </div>

      <div v-else class="text-center py-24 bg-gray-50/50 rounded-3xl border-2 border-dashed border-gray-100">
        <div class="mb-4 inline-flex items-center justify-center w-16 h-16 bg-white rounded-full shadow-sm">
          <Search class="text-gray-300" :size="24" />
        </div>
        <p class="text-[#002B5C] font-black text-xl mb-2">Žádné pozice nenalezeny</p>
        <p class="text-gray-500 max-w-xs mx-auto">Zkuste upravit vyhledávání nebo zvolit jinou kategorii technologií.</p>
        <button @click="searchQuery = ''; activeTag = 'Všechny pozice'" class="mt-6 text-sm font-bold text-[#002B5C] hover:underline px-6 py-2 bg-white rounded-full shadow-sm border border-gray-100">
          Zobrazit vše
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.no-scrollbar::-webkit-scrollbar {
  display: none;
}
.no-scrollbar {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
</style>