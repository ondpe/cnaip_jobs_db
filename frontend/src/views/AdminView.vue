<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import axios from 'axios'
import { 
  Plus, Play, Cpu, Globe, Search, 
  CheckSquare, Square, RefreshCw, Clock, 
  Briefcase, MapPin, AlertCircle 
} from 'lucide-vue-next'

interface Source {
  id: number
  name: string
  url: string
  last_crawled_at: string | null
  last_scrape_count: number | null
  last_scrape_found: number | null
}

interface Job {
  id: number
  title: string
  company: string
  location: string
  summary: string
  keywords: string
  created_at: string
  last_analyzed_at: string | null
}

const sources = ref<Source[]>([])
const jobs = ref<Job[]>([])
const selectedIds = ref<number[]>([])
const searchQuery = ref('')
const loading = ref(false)
const scrapingIds = ref<Set<number>>(new Set())

// Auth pro API
const adminAuth = { auth: { username: 'admin', password: 'admin123' } }

const fetchData = async () => {
  try {
    const [srcRes, jobRes] = await Promise.all([
      axios.get('/api/sources'),
      axios.get('/api/jobs')
    ])
    sources.value = srcRes.data
    jobs.value = jobRes.data
  } catch (e) {
    console.error("Chyba při načítání dat", e)
  }
}

const filteredJobs = computed(() => {
  const q = searchQuery.value.toLowerCase()
  return jobs.value.filter(j => 
    j.title.toLowerCase().includes(q) || 
    j.company.toLowerCase().includes(q)
  )
})

const isAllSelected = computed(() => 
  sources.value.length > 0 && selectedIds.value.length === sources.value.length
)

const toggleSelectAll = () => {
  if (isAllSelected.value) {
    selectedIds.value = []
  } else {
    selectedIds.value = sources.value.map(s => s.id)
  }
}

const scrapeSingle = async (id: number) => {
  scrapingIds.value.add(id)
  try {
    await axios.post(`/api/admin/scrape/${id}`, {}, adminAuth)
    await fetchData()
  } finally {
    scrapingIds.value.delete(id)
  }
}

const scrapeSelected = async () => {
  loading.value = true
  try {
    for (const id of selectedIds.value) {
      await scrapeSingle(id)
    }
  } finally {
    loading.value = false
  }
}

const runAiAnalysis = async () => {
  loading.value = true
  try {
    const res = await axios.post('/api/admin/run-ai-analysis', {}, adminAuth)
    alert(`AI analýza dokončena pro ${res.data.count} pozic.`)
    await fetchData()
  } finally {
    loading.value = false
  }
}

const formatDate = (d: string | null) => d ? new Date(d).toLocaleString('cs-CZ', { day: '2.digit', month: '2.digit', hour: '2.digit', minute: '2.digit' }) : '---'

onMounted(fetchData)
</script>

<template>
  <div class="grid grid-cols-12 gap-8">
    
    <!-- LEFT: Sources -->
    <div class="col-span-12 lg:col-span-4 space-y-4">
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div class="p-4 border-b border-gray-100 bg-gray-50/50 flex justify-between items-center">
          <h2 class="font-bold text-gray-800">Zdroje ({{ sources.length }})</h2>
          <div class="flex gap-2">
            <button @click="runAiAnalysis" :disabled="loading" class="p-2 text-purple-600 hover:bg-purple-50 rounded-lg title='AI Analýza'">
              <Cpu :size="20" :class="{ 'animate-pulse': loading }" />
            </button>
          </div>
        </div>

        <div class="p-3 border-b border-gray-100 flex items-center justify-between bg-white">
          <label class="flex items-center gap-2 cursor-pointer text-sm text-gray-600">
            <input type="checkbox" :checked="isAllSelected" @change="toggleSelectAll" class="rounded border-gray-300 text-blue-600 focus:ring-blue-500">
            Vybrat vše
          </label>
          <button 
            v-if="selectedIds.length > 0" 
            @click="scrapeSelected"
            :disabled="loading"
            class="text-xs bg-blue-600 text-white px-3 py-1.5 rounded-md hover:bg-blue-700 flex items-center gap-1 transition-all"
          >
            <RefreshCw :size="14" :class="{ 'animate-spin': loading }" />
            Aktualizovat vybrané ({{ selectedIds.length }})
          </button>
        </div>

        <div class="divide-y divide-gray-100 max-h-[calc(100vh-300px)] overflow-y-auto">
          <div v-for="source in sources" :key="source.id" class="p-4 hover:bg-gray-50 transition-colors group">
            <div class="flex items-start gap-3">
              <input 
                type="checkbox" 
                v-model="selectedIds" 
                :value="source.id"
                class="mt-1 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              >
              <div class="flex-1 min-w-0">
                <div class="flex justify-between items-start">
                  <h3 class="font-semibold text-gray-900 truncate">{{ source.name }}</h3>
                  <button 
                    @click="scrapeSingle(source.id)" 
                    :disabled="scrapingIds.has(source.id)"
                    class="opacity-0 group-hover:opacity-100 p-1 text-blue-600 hover:bg-blue-50 rounded transition-all"
                  >
                    <RefreshCw :size="16" :class="{ 'animate-spin': scrapingIds.has(source.id) }" />
                  </button>
                </div>
                <p class="text-xs text-gray-400 truncate mb-2">{{ source.url }}</p>
                
                <div class="space-y-1">
                  <div class="flex items-center gap-1 text-[10px] text-gray-500">
                    <Clock :size="12" />
                    <span>Kontrola: {{ formatDate(source.last_crawled_at) }}</span>
                  </div>
                  <div v-if="source.last_scrape_found !== null" class="text-[10px]">
                    <span class="text-gray-600">Nalezeno: <b>{{ source.last_scrape_found }}</b></span>
                    <span class="mx-1 text-gray-300">|</span>
                    <span class="text-green-600">Nové: <b>{{ source.last_scrape_count }}</b></span>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div v-if="sources.length === 0" class="p-8 text-center text-gray-400 text-sm">
            Zatím žádné zdroje.
          </div>
        </div>
      </div>
    </div>

    <!-- RIGHT: Jobs -->
    <div class="col-span-12 lg:col-span-8 space-y-4">
      <div class="flex items-center gap-4 bg-white p-2 rounded-xl shadow-sm border border-gray-200">
        <div class="relative flex-1">
          <Search class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" :size="18" />
          <input 
            v-model="searchQuery"
            type="text" 
            placeholder="Hledat v pozicích..." 
            class="w-full pl-10 pr-4 py-2 bg-transparent border-none focus:ring-0 text-sm"
          >
        </div>
        <div class="px-4 py-1 border-l border-gray-100 text-sm font-medium text-gray-500">
          {{ filteredJobs.length }} pozic
        </div>
      </div>

      <div class="space-y-3">
        <div v-for="job in filteredJobs" :key="job.id" class="bg-white p-5 rounded-xl border border-gray-200 shadow-sm hover:border-blue-200 transition-all">
          <div class="flex justify-between items-start mb-3">
            <div>
              <h3 class="font-bold text-lg text-gray-900">{{ job.title }}</h3>
              <div class="flex flex-wrap gap-3 mt-1 text-sm text-gray-500">
                <span class="flex items-center gap-1"><Briefcase :size="14" /> {{ job.company }}</span>
                <span class="flex items-center gap-1"><MapPin :size="14" /> {{ job.location || 'Remote' }}</span>
              </div>
            </div>
            <div class="text-right shrink-0">
              <div class="text-[11px] font-medium text-gray-400 mb-1">Přidáno: {{ formatDate(job.created_at) }}</div>
              <div v-if="job.last_analyzed_at" class="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-green-50 text-green-700 text-[10px] font-bold border border-green-100">
                <Cpu :size="12" /> AI OK: {{ formatDate(job.last_analyzed_at) }}
              </div>
              <div v-else class="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-amber-50 text-amber-700 text-[10px] font-bold border border-amber-100">
                <AlertCircle :size="12" /> Čeká na AI
              </div>
            </div>
          </div>
          
          <div class="bg-gray-50 rounded-lg p-3 text-sm text-gray-700 italic border-l-4 border-gray-200">
            {{ job.summary || 'Tato pozice zatím nebyla analyzována pomocí AI.' }}
          </div>

          <div v-if="job.keywords" class="mt-3 flex flex-wrap gap-1">
            <span v-for="kw in job.keywords.split(',')" :key="kw" class="px-2 py-0.5 bg-white border border-gray-200 text-gray-600 text-[10px] rounded-md shadow-sm">
              {{ kw.trim() }}
            </span>
          </div>
        </div>

        <div v-if="filteredJobs.length === 0" class="bg-white rounded-xl border-2 border-dashed border-gray-200 p-12 text-center text-gray-400">
          Nebyly nalezeny žádné pozice odpovídající hledání.
        </div>
      </div>
    </div>

  </div>
</template>