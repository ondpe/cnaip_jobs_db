<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import axios from 'axios'
import { Search, Loader2, Filter, Building2, Tag } from 'lucide-vue-next'
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
const selectedTag = ref('Všechny tagy')
const selectedCompany = ref('Všechny firmy')

// Dynamicky extrahované tagy
const availableTags = computed(() => {
  const tags = new Set<string>(['Všechny tagy'])
  jobs.value.forEach(job => {
    if (job.keywords) {
      job.keywords.split(',').forEach(k => {
        const trimmed = k.trim().replace(/[\[\]\{\}]/g, '')
        if (trimmed) tags.add(trimmed)
      })
    }
  })
  return Array.from(tags).sort()
})

// Dynamicky extrahované firmy
const availableCompanies = computed(() => {
  const companies = new Set<string>(['Všechny firmy'])
  jobs.value.forEach(job => {
    if (job.company) companies.add(job.company)
  })
  return Array.from(companies).sort()
})

const fetchJobs = async () => {
  loading.value = true
  try {
    const response = await axios.get('/api/jobs')
    // Zobrazujeme pouze pozice, které mají odkaz (validní inzeráty)
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
    
    const matchesTag = selectedTag.value === 'Všechny tagy' || 
                      (job.keywords && job.keywords.toLowerCase().includes(selectedTag.value.toLowerCase()))
    
    const matchesCompany = selectedCompany.value === 'Všechny firmy' || 
                          job.company === selectedCompany.value
    
    return matchesSearch && matchesTag && matchesCompany
  })
})

const resetFilters = () => {
  searchQuery.value = ''
  selectedTag.value = 'Všechny tagy'
  selectedCompany.value = 'Všechny firmy'
}

onMounted(fetchJobs)
</script>

<template>
  <div class="max-w-5xl mx-auto px-4 py-12">
    <!-- Header with Search and Dropdown Filters -->
    <div class="mb-12 space-y-8">
      <div class="text-center md:text-left">
        <h1 class="text-5xl font-black text-[#002B5C] mb-3 tracking-tighter">Kariéra v AI</h1>
        <p class="text-gray-500 text-xl font-medium">Najděte svou příští výzvu v nejlepších českých AI firmách.</p>
      </div>

      <div class="bg-white p-2 rounded-3xl border border-gray-100 shadow-xl shadow-blue-900/5">
        <div class="grid grid-cols-1 md:grid-cols-12 gap-2">
          <!-- Search Bar -->
          <div class="md:col-span-5 relative">
            <div class="absolute inset-y-0 left-4 flex items-center pointer-events-none text-gray-400">
              <Search class="h-4 w-4" />
            </div>
            <input 
              v-model="searchQuery"
              type="text" 
              class="block w-full pl-11 pr-4 py-4 bg-gray-50 border-none rounded-2xl text-sm placeholder-gray-400 focus:ring-2 focus:ring-[#002B5C]/10 transition-all"
              placeholder="Pozice nebo technologie..."
            >
          </div>

          <!-- Company Filter -->
          <div class="md:col-span-3 relative">
            <div class="absolute inset-y-0 left-4 flex items-center pointer-events-none text-gray-400">
              <Building2 class="h-4 w-4" />
            </div>
            <select 
              v-model="selectedCompany"
              class="block w-full pl-11 pr-4 py-4 bg-gray-50 border-none rounded-2xl text-sm focus:ring-2 focus:ring-[#002B5C]/10 appearance-none transition-all cursor-pointer"
            >
              <option v-for="company in availableCompanies" :key="company" :value="company">{{ company }}</option>
            </select>
          </div>

          <!-- Tag Filter -->
          <div class="md:col-span-3 relative">
            <div class="absolute inset-y-0 left-4 flex items-center pointer-events-none text-gray-400">
              <Tag class="h-4 w-4" />
            </div>
            <select 
              v-model="selectedTag"
              class="block w-full pl-11 pr-4 py-4 bg-gray-50 border-none rounded-2xl text-sm focus:ring-2 focus:ring-[#002B5C]/10 appearance-none transition-all cursor-pointer"
            >
              <option v-for="tag in availableTags" :key="tag" :value="tag">{{ tag }}</option>
            </select>
          </div>

          <!-- Reset/Count info -->
          <div class="md:col-span-1 flex items-center justify-center">
             <button @click="resetFilters" class="p-4 text-gray-400 hover:text-[#002B5C] transition-colors" title="Resetovat filtry">
               <Filter class="h-5 w-5" />
             </button>
          </div>
        </div>
      </div>
      
      <div v-if="!loading" class="flex justify-between items-center px-4">
        <p class="text-xs font-black uppercase tracking-widest text-gray-400">
          Nalezeno: <span class="text-[#002B5C]">{{ filteredJobs.length }} pozic</span>
        </p>
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
        <p class="text-gray-500 max-w-xs mx-auto">Zkuste upravit vyhledávání nebo zvolit jiný filtr.</p>
        <button @click="resetFilters" class="mt-6 text-sm font-bold text-[#002B5C] hover:underline px-6 py-2 bg-white rounded-full shadow-sm border border-gray-100">
          Zrušit filtry
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Odstranění defaultního modrého zvýraznění na mobilu */
select {
  -webkit-tap-highlight-color: transparent;
}
</style>