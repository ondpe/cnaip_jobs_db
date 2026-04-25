<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import axios from 'axios'
import { 
  Plus, Play, Cpu, Globe, Search, 
  CheckSquare, Square, RefreshCw, Clock, 
  Briefcase, MapPin, AlertCircle, Key, X
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
const hasAiKey = ref(false)
const showKeyModal = ref(false)
const newAiKey = ref('')
const scrapingIds = ref<Set<number>>(new Set())
const analyzingIds = ref<Set<number>>(new Set())

// Auth pro API
const adminAuth = { auth: { username: 'admin', password: 'admin123' } }

const fetchData = async () => {
  try {
    const [srcRes, jobRes, keyRes] = await Promise.all([
      axios.get('/api/sources'),
      axios.get('/api/jobs'),
      axios.get('/api/admin/settings/gemini-key', adminAuth)
    ])
    sources.value = srcRes.data
    jobs.value = jobRes.data
    hasAiKey.value = keyRes.data.has_key
  } catch (e) {
    console.error("Chyba při načítání dat", e)
  }
}

const saveAiKey = async () => {
  if (!newAiKey.value) return
  await axios.post(`/api/admin/settings/gemini-key?key=${newAiKey.value}`, {}, adminAuth)
  newAiKey.value = ''
  showKeyModal.value = false
  fetchData()
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

const analyzeSingleJob = async (id: number) => {
  analyzingIds.value.add(id)
  try {
    await axios.post(`/api/admin/analyze-job/${id}`, {}, adminAuth)
    await fetchData()
  } finally {
    analyzingIds.value.delete(id)
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

const runBulkAiAnalysis = async () => {
  loading.value = true
  try {
    const res = await axios.post('/api/admin/run-ai-analysis', {}, adminAuth)
    alert(`Hromadná AI analýza dokončena pro ${res.data.count} pozic.`)
    await fetchData()
  } finally {
    loading.value = false
  }
}

const formatDate = (d: string | null) => d ? new Date(d).toLocaleString('cs-CZ', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) : '---'

onMounted(fetchData)
</script>

<template>
  <div class="space-y-6">
    <!-- Top Header / Stats -->
    <div class="bg-white p-4 rounded-xl shadow-sm border border-gray-200 flex flex-wrap items-center justify-between gap-4">
      <div class="flex items-center gap-6">
        <div class="flex items-center gap-2">
          <div :class="`w-2 h-2 rounded-full ${hasAiKey ? 'bg-green-500' : 'bg-red-500'}`"></div>
          <span class="text-sm font-medium text-gray-700">AI: {{ hasAiKey ? 'Připraveno' : 'Chybí klíč' }}</span>
        </div>
        <button @click="showKeyModal = true" class="text-xs flex items-center gap-1 text-blue-600 hover:underline">
          <Key :size="14" /> Nastavit AI klíč
        </button>
      </div>
      <div class="flex gap-3">
        <button 
          @click="runBulkAiAnalysis" 
          :disabled="loading" 
          class="bg-purple-600 text-white px-4 py-2 rounded-lg text-sm font-bold flex items-center gap-2 hover:bg-purple-700 disabled:opacity-50 transition-all shadow-sm"
        >
          <Cpu :size="18" :class="{ 'animate-pulse': loading }" />
          Spustit hromadnou AI analýzu
        </button>
      </div>
    </div>

    <div class="grid grid-cols-12 gap-8 items-start">
      <!-- LEFT: Sources (Sticky) -->
      <div class="col-span-12 lg:col-span-4 sticky top-6">
        <div class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div class="p-4 border-b border-gray-100 bg-gray-50/50 flex justify-between items-center">
            <h2 class="font-bold text-gray-800">Zdroje ({{ sources.length }})</h2>
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
              Aktualizovat ({{ selectedIds.length }})
            </button>
          </div>

          <div class="divide-y divide-gray-100">
            <div v-for="source in sources" :key="source.id" class="p-4 hover:bg-gray-50 transition-colors group">
              <div class="flex items-start gap-3">
                <input type="checkbox" v-model="selectedIds" :value="source.id" class="mt-1 rounded border-gray-300 text-blue-600 focus:ring-blue-500">
                <div class="flex-1 min-w-0">
                  <div class="flex justify-between items-start">
                    <h3 class="font-semibold text-gray-900 truncate">{{ source.name }}</h3>
                    <button @click="scrapeSingle(source.id)" :disabled="scrapingIds.has(source.id)" class="opacity-0 group-hover:opacity-100 p-1 text-blue-600 hover:bg-blue-50 rounded transition-all">
                      <RefreshCw :size="16" :class="{ 'animate-spin': scrapingIds.has(source.id) }" />
                    </button>
                  </div>
                  <div class="space-y-1">
                    <div class="flex items-center gap-1 text-[10px] text-gray-500">
                      <Clock :size="12" /> {{ formatDate(source.last_crawled_at) }}
                    </div>
                    <div v-if="source.last_scrape_found !== null" class="text-[10px]">
                      <span class="text-green-600 font-bold">+{{ source.last_scrape_count }} nové</span>
                      <span class="mx-1 text-gray-300">/</span>
                      <span class="text-gray-500">{{ source.last_scrape_found }} celkem</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- RIGHT: Jobs (Full height) -->
      <div class="col-span-12 lg:col-span-8 space-y-4">
        <div class="flex items-center gap-4 bg-white p-2 rounded-xl shadow-sm border border-gray-200">
          <div class="relative flex-1">
            <Search class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" :size="18" />
            <input v-model="searchQuery" type="text" placeholder="Hledat v pozicích..." class="w-full pl-10 pr-4 py-2 bg-transparent border-none focus:ring-0 text-sm">
          </div>
          <div class="px-4 py-1 border-l border-gray-100 text-sm font-medium text-gray-500">{{ filteredJobs.length }} pozic</div>
        </div>

        <div class="space-y-3 pb-20">
          <div v-for="job in filteredJobs" :key="job.id" class="bg-white p-5 rounded-xl border border-gray-200 shadow-sm hover:border-blue-200 transition-all group">
            <div class="flex justify-between items-start mb-3">
              <div>
                <h3 class="font-bold text-lg text-gray-900">{{ job.title }}</h3>
                <div class="flex flex-wrap gap-3 mt-1 text-sm text-gray-500">
                  <span class="flex items-center gap-1"><Briefcase :size="14" /> {{ job.company }}</span>
                  <span class="flex items-center gap-1"><MapPin :size="14" /> {{ job.location || 'Remote' }}</span>
                </div>
              </div>
              <div class="flex flex-col items-end gap-2 shrink-0">
                <span class="text-[11px] font-medium text-gray-400">Přidáno: {{ formatDate(job.created_at) }}</span>
                <div class="flex gap-2">
                   <button 
                    @click="analyzeSingleJob(job.id)"
                    :disabled="analyzingIds.has(job.id)"
                    class="opacity-0 group-hover:opacity-100 p-1.5 bg-purple-50 text-purple-600 rounded-lg hover:bg-purple-100 transition-all title='Analyzovat pomocí AI'"
                  >
                    <Cpu :size="16" :class="{ 'animate-pulse': analyzingIds.has(job.id) }" />
                  </button>
                  <div v-if="job.last_analyzed_at" class="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-green-50 text-green-700 text-[10px] font-bold border border-green-100">
                    <Cpu :size="12" /> AI OK
                  </div>
                  <div v-else class="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-amber-50 text-amber-700 text-[10px] font-bold border border-amber-100">
                    <AlertCircle :size="12" /> Čeká
                  </div>
                </div>
              </div>
            </div>
            
            <div class="bg-gray-50 rounded-lg p-3 text-sm text-gray-700 italic border-l-4 border-gray-200">
              {{ job.summary || 'Tato pozice zatím nebyla analyzována.' }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- AI Key Modal -->
    <div v-if="showKeyModal" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-2xl shadow-xl max-w-md w-full overflow-hidden">
        <div class="p-6 border-b border-gray-100 flex justify-between items-center bg-gray-50">
          <h3 class="font-bold text-gray-900 flex items-center gap-2">
            <Key :size="20" class="text-blue-600" /> Nastavení AI klíče
          </h3>
          <button @click="showKeyModal = false" class="text-gray-400 hover:text-gray-600">
            <X :size="20" />
          </button>
        </div>
        <div class="p-6 space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Google Gemini API Key</label>
            <input 
              v-model="newAiKey" 
              type="password" 
              placeholder="Vložte svůj klíč..." 
              class="w-full border-gray-300 rounded-lg shadow-sm focus:ring-blue-500 focus:border-blue-500 border p-2"
            >
            <p class="mt-2 text-xs text-gray-500">Klíč získáte zdarma v <a href="https://aistudio.google.com/" target="_blank" class="text-blue-600 hover:underline">Google AI Studio</a>.</p>
          </div>
          <button @click="saveAiKey" class="w-full bg-blue-600 text-white font-bold py-2.5 rounded-xl hover:bg-blue-700 transition-colors shadow-lg shadow-blue-200">
            Uložit klíč
          </button>
        </div>
      </div>
    </div>
  </div>
</template>