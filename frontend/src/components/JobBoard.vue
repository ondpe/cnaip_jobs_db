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
const activeCategory = ref('Všechny pozice')
const categories = ['Všechny pozice', 'Vývoj', 'Data Science', 'AI Research', 'Management']

const fetchJobs = async () => {
  loading.value = true
  try {
    const response = await axios.get('/api/jobs')
    // Zobrazujeme pouze pozice, které mají odkaz
    jobs.value = response.data.filter((j: Job) => j.link)
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
    (job.keywords && job.keywords.toLowerCase().includes(query))
  )
})

onMounted(fetchJobs)
</script>

<template>
  <div class="max-w-5xl mx-auto px-4 py-12">
    <!-- Header with Search and Categories -->
    <div class="mb-12 space-y-8 text-center md:text-left">
      <div>
        <h1 class="text-4xl font-extrabold text-[#002B5C] mb-2 tracking-tight">Kariéra v AI</h1>
        <p class="text-gray-500 text-lg">Najděte svou příští výzvu v nejlepších českých AI firmách.</p>
      </div>

      <div class="flex flex-col md:flex-row md:items-center justify-between gap-6">
        <!-- Categories -->
        <nav class="flex overflow-x-auto pb-2 md:pb-0 gap-6 no-scrollbar">
          <button 
            v-for="cat in categories" 
            :key="cat"
            @click="activeCategory = cat"
            :class="[
              'text-sm transition-all whitespace-nowrap pb-1',
              activeCategory === cat 
                ? 'font-bold text-[#002B5C] border-b-2 border-[#002B5C]' 
                : 'text-gray-500 hover:text-gray-700'
            ]"
          >
            {{ cat }}
          </button>
        </nav>

        <!-- Search Bar -->
        <div class="relative w-full md:w-80">
          <div class="absolute inset-y-0 left-4 flex items-center pointer-events-none">
            <Search class="h-4 w-4 text-gray-400" />
          </div>
          <input 
            v-model="searchQuery"
            type="text" 
            class="block w-full pl-11 pr-4 py-2.5 bg-white border border-gray-200 rounded-full text-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-[#002B5C] transition-all shadow-sm"
            placeholder="Pozice, firma nebo technologie..."
          >
        </div>
      </div>
    </div>

    <!-- Content Area -->
    <div v-if="loading" class="flex flex-col items-center justify-center py-20 space-y-4">
      <Loader2 class="h-10 w-10 text-[#002B5C] animate-spin" />
      <p class="text-gray-500 font-medium">Načítáme aktuální nabídky...</p>
    </div>

    <div v-else>
      <div v-if="filteredJobs.length > 0" class="animate-in fade-in slide-in-from-bottom-4 duration-500">
        <JobCard 
          v-for="job in filteredJobs" 
          :key="job.id" 
          :job="job" 
        />
      </div>

      <div v-else class="text-center py-20 bg-gray-50 rounded-2xl border border-dashed border-gray-200">
        <p class="text-[#002B5C] font-semibold text-lg mb-1">Žádné pozice nenalezeny</p>
        <p class="text-gray-500">Zkuste upravit vyhledávání nebo zvolit jinou kategorii.</p>
        <button @click="searchQuery = ''; activeCategory = 'Všechny pozice'" class="mt-4 text-sm font-bold text-[#002B5C] hover:underline">
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