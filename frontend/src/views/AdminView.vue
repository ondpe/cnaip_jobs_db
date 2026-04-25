<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import axios from 'axios'
import { 
  Plus, Play, Cpu, Globe, Search, 
  CheckSquare, Square, RefreshCw, Clock, 
  Briefcase, MapPin, AlertCircle, Key, X, ExternalLink
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
  link: string | null
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

const isAllSelected = computed(() => sources.value.length > 0 && selectedIds.value.length === sources.value.length)
const toggleSelectAll = () => selectedIds.value = isAllSelected.value ? [] : sources.value.map(s => s.id)

const scrapeSingle = async (id: number) => {
  scrapingIds.value.add(id)
  try { await axios.post(`/api/admin/scrape/${id}`, {}, adminAuth); await fetchData() } 
  finally { scrapingIds.value.delete(id) }
}

const analyzeSingleJob = async (id: number) => {
  analyzingIds.value.add(id)
  try { await axios.post(`/api/admin/analyze-job/${id}`, {}, adminAuth); await fetchData() }
  finally { analyzingIds.value.delete(id) }
}

const scrapeSelected = async () => {
  loading.value = true
  try { for (const id of selectedIds.value) await scrapeSingle(id) }
  finally { loading.value = false }
}

const runBulkAiAnalysis = async () => {
  loading.value = true
  try {
    const res = await axios.post('/api/admin/run-ai-analysis', {}, adminAuth)
    alert(`AI analýza dokončena pro ${res.data.count} pozic.`)
    await fetchData()
  } finally { loading.value = false }
}

const formatDate = (d: string | null) => d ? new Date(d).toLocaleString('cs-CZ', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) : '---'

onMounted(fetchData)
</script>

<template>
  <div class="space-y-6">
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
      <button @click="runBulkAiAnalysis" :disabled="loading" class="bg-purple-600 text-white px-4 py-2 rounded-lg text-sm font-bold flex items-center gap-2 hover:bg-purple-700 disabled:opacity-50">
        <Cpu :size="18" :class="{ 'animate-pulse': loading }" /> Hromadná AI analýza
      </button>
    </div>

    <div class="grid grid-cols-12 gap-8 items-start">
      <div class="col-span-12 lg:col-span-4 sticky top-6">
        <div class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div class="p-4 border-b border-gray-100 bg-gray-50/50"><h2 class="font-bold text-gray-800">Zdroje</h2></div>
          <div class="p-3 border-b border-gray-100 flex items-center justify-between">
            <label class="flex items-center gap-2 text-sm"><input type="checkbox" :checked="isAllSelected" @change="toggleSelectAll"> Vybrat vše</label>
            <button v-if="selectedIds.length" @click="scrapeSelected" class="text-xs bg-blue-600 text-white px-3 py-1.5 rounded-md"><RefreshCw :size="14" :class="{ 'animate-spin': loading }" /> Aktualizovat</button>
          </div>
          <div class="divide-y divide-gray-100">
            <div v-for="source in sources" :key="source.id" class="p-4 hover:bg-gray-50 group">
              <div class="flex items-start gap-3">
                <input type="checkbox" v-model="selectedIds" :value="source.id">
                <div class="flex-1 min-w-0">
                  <div class="flex justify-between items-start">
                    <h3 class="font-semibold text-gray-900 truncate">{{ source.name }}</h3>
                    <button @click="scrapeSingle(source.id)" :disabled="scrapingIds.has(source.id)" class="opacity-0 group-hover:opacity-100 p-1 text-blue-600"><RefreshCw :size="16" :class="{ 'animate-spin': scrapingIds.has(source.id) }" /></button>
                  </div>
                  <div class="text-[10px] text-gray-500 mt-1"><Clock :size="12" class="inline" /> {{ formatDate(source.last_crawled_at) }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="col-span-12 lg:col-span-8 space-y-4">
        <div class="flex items-center gap-4 bg-white p-2 rounded-xl shadow-sm border border-gray-200">
          <Search class="ml-3 text-gray-400" :size="18" />
          <input v-model="searchQuery" type="text" placeholder="Hledat..." class="flex-1 border-none focus:ring-0 text-sm">
          <div class="px-4 text-sm font-medium text-gray-500">{{ filteredJobs.length }} pozic</div>
        </div>

        <div class="space-y-3 pb-20">
          <div v-for="job in filteredJobs" :key="job.id" class="bg-white p-5 rounded-xl border border-gray-200 shadow-sm hover:border-blue-200 group">
            <div class="flex justify-between items-start mb-3">
              <div>
                <div class="flex items-center gap-2">
                  <h3 class="font-bold text-lg text-gray-900">{{ job.title }}</h3>
                  <a v-if="job.link" :href="job.link" target="_blank" class="text-blue-500 hover:text-blue-700" title="Otevřít inzerát">
                    <ExternalLink :size="16" />
                  </a>
                </div>
                <div class="flex gap-3 mt-1 text-sm text-gray-500">
                  <span class="flex items-center gap-1"><Briefcase :size="14" /> {{ job.company }}</span>
                  <span class="flex items-center gap-1"><MapPin :size="14" /> {{ job.location || 'Remote' }}</span>
                </div>
              </div>
              <div class="flex flex-col items-end gap-2">
                <span class="text-[11px] text-gray-400">{{ formatDate(job.created_at) }}</span>
                <div class="flex gap-2">
                  <button @click="analyzeSingleJob(job.id)" :disabled="analyzingIds.has(job.id)" class="opacity-0 group-hover:opacity-100 p-1.5 bg-purple-50 text-purple-600 rounded-lg"><Cpu :size="16" :class="{ 'animate-pulse': analyzingIds.has(job.id) }" /></button>
                  <div v-if="job.last_analyzed_at" class="px-2 py-0.5 rounded bg-green-50 text-green-700 text-[10px] font-bold border">AI OK</div>
                  <div v-else class="px-2 py-0.5 rounded bg-amber-50 text-amber-700 text-[10px] font-bold border">Čeká</div>
                </div>
              </div>
            </div>
            <div class="bg-gray-50 rounded-lg p-3 text-sm text-gray-700 italic border-l-4">{{ job.summary || 'Tato pozice zatím nebyla analyzována.' }}</div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="showKeyModal" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-2xl shadow-xl max-w-md w-full p-6">
        <div class="flex justify-between items-center mb-4"><h3 class="font-bold text-gray-900">Nastavení AI klíče</h3><button @click="showKeyModal = false"><X :size="20" /></button></div>
        <input v-model="newAiKey" type="password" placeholder="Google Gemini API Key..." class="w-full border rounded-lg p-2 mb-4">
        <button @click="saveAiKey" class="w-full bg-blue-600 text-white font-bold py-2 rounded-xl">Uložit klíč</button>
      </div>
    </div>
  </div>
</template>