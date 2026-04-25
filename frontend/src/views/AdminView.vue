<script setup lang="ts">
import { ref, onMounted, computed, onUnmounted } from 'vue'
import axios from 'axios'
import { 
  Plus, Play, Cpu, Globe, Search, 
  RefreshCw, Clock, Briefcase, MapPin, 
  Key, X, ExternalLink, Trash2, Edit3, Filter, CheckCircle2, AlertCircle, AlertTriangle, Terminal
} from 'lucide-vue-next'

interface Source {
  id: number; name: string; url: string; last_crawled_at: string | null; 
  last_scrape_count: number | null; last_scrape_found: number | null;
}
interface Job {
  id: number; title: string; company: string; location: string; 
  summary: string; keywords: string; link: string | null; 
  created_at: string; last_analyzed_at: string | null;
}

const sources = ref<Source[]>([])
const jobs = ref<Job[]>([])
const selectedIds = ref<number[]>([])
const searchQuery = ref('')
const loading = ref(false)
const hasAiKey = ref(false)
const maskedKey = ref('')
const showKeyModal = ref(false)
const newAiKey = ref('')
const keyError = ref('')
const scrapingIds = ref<Set<number>>(new Set())
const analyzingIds = ref<Set<number>>(new Set())
const showLogs = ref(false)
const debugLogs = ref<string[]>([])
let logInterval: any = null

const showConfirmAnalysis = ref(false)
const lastAnalysisResult = ref<{ count: number, deleted: number } | null>(null)
const showEditModal = ref(false)
const editingJob = ref<Partial<Job>>({})
const onlyNeedsAi = ref(false)

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
    maskedKey.value = keyRes.data.masked_key
  } catch (e) { console.error("Chyba při načítání dat", e) }
}

const fetchLogs = async () => {
  try {
    const res = await axios.get('/api/admin/debug/logs', adminAuth)
    debugLogs.value = res.data.logs
  } catch (e) { console.error("Chyba při načítání logů", e) }
}

const toggleLogs = () => {
  showLogs.value = !showLogs.value
  if (showLogs.value) {
    fetchLogs()
    logInterval = setInterval(fetchLogs, 3000)
  } else {
    clearInterval(logInterval)
  }
}

const saveAiKey = async () => {
  if (!newAiKey.value) return
  keyError.value = ''; loading.value = true
  try {
    await axios.post(`/api/admin/settings/gemini-key?key=${newAiKey.value}`, {}, adminAuth)
    newAiKey.value = ''; showKeyModal.value = false; await fetchData()
  } catch (e: any) {
    keyError.value = e.response?.data?.detail || 'Klíč se nepodařilo uložit.'
  } finally { loading.value = false }
}

const runBulkAiAnalysis = async () => {
  loading.value = true; showConfirmAnalysis.value = false; lastAnalysisResult.value = null
  try {
    const res = await axios.post('/api/admin/run-ai-analysis', {}, adminAuth)
    lastAnalysisResult.value = res.data; await fetchData()
  } finally { loading.value = false }
}

const analyzeSingleJob = async (id: number) => {
  analyzingIds.value.add(id)
  try { await axios.post(`/api/admin/analyze-job/${id}`, {}, adminAuth); await fetchData() }
  finally { analyzingIds.value.delete(id) }
}

const scrapeSingle = async (id: number) => {
  scrapingIds.value.add(id)
  try { await axios.post(`/api/admin/scrape/${id}`, {}, adminAuth); await fetchData() } 
  finally { scrapingIds.value.delete(id) }
}

const deleteJob = async (id: number) => {
  if (!confirm('Opravdu chcete tuto pozici smazat?')) return
  await axios.delete(`/api/admin/jobs/${id}`, adminAuth); fetchData()
}

const filteredJobs = computed(() => {
  const q = searchQuery.value.toLowerCase()
  return jobs.value.filter(j => {
    const matchesSearch = j.title.toLowerCase().includes(q) || j.company.toLowerCase().includes(q)
    const needsAi = !j.last_analyzed_at || j.summary.includes('Čeká na AI') || j.summary.includes('Chyba AI')
    return matchesSearch && (!onlyNeedsAi.value || needsAi)
  })
})

const formatDate = (d: string | null) => d ? new Date(d).toLocaleString('cs-CZ', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) : '---'

onMounted(fetchData)
onUnmounted(() => clearInterval(logInterval))
</script>

<template>
  <div class="space-y-6">
    <!-- Top Stats / Actions -->
    <div class="bg-white p-5 rounded-2xl shadow-sm border border-gray-100">
      <div class="flex flex-wrap items-center justify-between gap-6">
        <div class="flex items-center gap-8">
          <div class="flex items-center gap-3">
            <div :class="`w-3 h-3 rounded-full ${hasAiKey ? 'bg-green-500 shadow-lg shadow-green-200' : 'bg-red-500 shadow-lg shadow-red-200'}`"></div>
            <span class="text-sm font-bold text-[#002B5C] uppercase tracking-wider">AI Služba: {{ hasAiKey ? 'Aktivní' : 'Chybí klíč' }}</span>
            <button @click="showKeyModal = true" class="p-1.5 hover:bg-gray-50 rounded-lg transition-colors flex items-center gap-2">
              <span v-if="maskedKey" class="text-[10px] text-gray-400 font-mono">{{ maskedKey }}</span>
              <Key :size="16" class="text-gray-400" />
            </button>
          </div>
          
          <button @click="toggleLogs" :class="['flex items-center gap-2 px-3 py-1 rounded-lg text-[10px] font-black uppercase tracking-widest transition-all', showLogs ? 'bg-gray-900 text-white' : 'bg-gray-100 text-gray-400 hover:bg-gray-200']">
            <Terminal :size="14" /> {{ showLogs ? 'Zavřít Logy' : 'Zobrazit Logy' }}
          </button>
        </div>

        <div class="flex flex-col items-end gap-2">
          <div v-if="!showConfirmAnalysis" class="flex flex-col items-end gap-2">
            <button @click="showConfirmAnalysis = true" :disabled="loading" class="bg-[#002B5C] text-white px-6 py-2.5 rounded-xl text-sm font-black flex items-center gap-2 hover:bg-blue-900 transition-all shadow-md shadow-blue-100 disabled:opacity-50">
              <Cpu :size="18" :class="{ 'animate-pulse': loading }" /> Hromadná AI analýza
            </button>
          </div>
          <div v-else class="flex items-center gap-3 animate-in fade-in slide-in-from-right-4">
            <span class="text-xs font-bold text-amber-600 flex items-center gap-1.5"><AlertTriangle :size="14" /> Analyzovat vše neupravené?</span>
            <button @click="runBulkAiAnalysis" class="bg-green-600 text-white px-4 py-1.5 rounded-lg text-xs font-black hover:bg-green-700 transition-all">ANO</button>
            <button @click="showConfirmAnalysis = false" class="bg-gray-100 text-gray-500 px-4 py-1.5 rounded-lg text-xs font-black hover:bg-gray-200 transition-all">ZRUŠIT</button>
          </div>
          <div v-if="lastAnalysisResult" class="text-[10px] font-bold uppercase tracking-widest animate-in fade-in">
            <span class="text-green-600 bg-green-50 px-2 py-1 rounded">Ok: {{ lastAnalysisResult.count }}</span>
            <span class="text-red-600 bg-red-50 px-2 py-1 rounded ml-2">Smazáno: {{ lastAnalysisResult.deleted }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Debug Log Console -->
    <div v-if="showLogs" class="bg-gray-900 text-green-400 p-4 rounded-2xl font-mono text-xs overflow-y-auto max-h-60 shadow-2xl border border-gray-800 animate-in slide-in-from-top-4 duration-300">
      <div class="flex justify-between items-center mb-3 text-gray-500 font-bold border-b border-gray-800 pb-2">
        <span>BACKEND DEBUG CONSOLE</span>
        <span class="animate-pulse">● LIVE</span>
      </div>
      <div v-if="debugLogs.length === 0" class="text-gray-600">Zatím žádné záznamy. Spusťte scraping nebo analýzu...</div>
      <div v-for="(log, idx) in debugLogs" :key="idx" class="mb-1">
        <span class="text-gray-600">>>></span> {{ log }}
      </div>
    </div>

    <div class="grid grid-cols-12 gap-8 items-start">
      <!-- Sources Column -->
      <div class="col-span-12 lg:col-span-4 lg:sticky lg:top-24">
        <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
          <div class="p-5 border-b border-gray-100 bg-gray-50/50 flex justify-between items-center">
            <h2 class="font-black text-[#002B5C] uppercase tracking-widest text-xs">Zdroje</h2>
            <span class="text-[10px] font-bold px-2 py-0.5 bg-gray-200 rounded text-gray-600">{{ sources.length }}</span>
          </div>
          <div class="divide-y divide-gray-50 max-h-[600px] overflow-y-auto">
            <div v-for="source in sources" :key="source.id" class="p-5 hover:bg-gray-50/50 transition-colors group">
              <div class="flex justify-between items-start">
                <div class="flex-1 min-w-0">
                  <h3 class="font-bold text-[#002B5C] truncate">{{ source.name }}</h3>
                  <div class="text-[10px] text-gray-400 mt-1 flex items-center gap-2">
                    <Clock :size="10" /> {{ formatDate(source.last_crawled_at) }}
                    <span v-if="source.last_scrape_count" class="text-green-500">+{{ source.last_scrape_count }}</span>
                  </div>
                </div>
                <button @click="scrapeSingle(source.id)" :disabled="scrapingIds.has(source.id)" class="p-2 hover:bg-blue-50 rounded-lg text-blue-600 transition-all">
                  <RefreshCw :size="16" :class="{ 'animate-spin': scrapingIds.has(source.id) }" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Jobs Column -->
      <div class="col-span-12 lg:col-span-8 space-y-4">
        <div class="flex items-center gap-4 bg-white p-3 rounded-2xl shadow-sm border border-gray-100">
          <Search class="ml-3 text-gray-300" :size="20" />
          <input v-model="searchQuery" type="text" placeholder="Hledat..." class="flex-1 border-none focus:ring-0 text-md">
          <button @click="onlyNeedsAi = !onlyNeedsAi" :class="['px-4 py-1.5 rounded-full text-xs font-bold transition-all border', onlyNeedsAi ? 'bg-amber-50 border-amber-200 text-amber-700' : 'bg-gray-50 border-gray-100 text-gray-500']">
            <Filter :size="14" class="inline mr-1" /> Jen neanalyzované
          </button>
        </div>

        <div class="space-y-4 pb-20">
          <div v-for="job in filteredJobs" :key="job.id" class="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm hover:border-blue-100 transition-all group">
            <div class="flex justify-between items-start mb-4">
              <div class="flex-1 min-w-0 pr-4">
                <h3 class="font-black text-xl text-[#002B5C] truncate">{{ job.title }}</h3>
                <div class="flex items-center gap-4 text-sm font-medium text-gray-500 mt-1">
                  <span class="flex items-center gap-1.5"><Briefcase :size="14" /> {{ job.company }}</span>
                  <span class="flex items-center gap-1.5"><MapPin :size="14" /> {{ job.location || 'Dle webu' }}</span>
                </div>
              </div>
              <div class="flex flex-col items-end gap-2 shrink-0">
                <div class="flex gap-1">
                  <button @click="analyzeSingleJob(job.id)" :disabled="analyzingIds.has(job.id)" class="px-3 py-1 bg-purple-50 hover:bg-purple-100 text-purple-700 text-[10px] font-black uppercase rounded-lg transition-all">
                    <Cpu :size="12" :class="['inline mr-1', { 'animate-pulse': analyzingIds.has(job.id) }]" /> Analyzovat
                  </button>
                  <button @click="deleteJob(job.id)" class="p-1.5 hover:bg-red-50 rounded-lg text-gray-300 hover:text-red-500 transition-all"><Trash2 :size="16" /></button>
                </div>
                <div class="flex items-center gap-1">
                  <span v-if="job.last_analyzed_at" class="text-green-500 text-[10px] font-bold"><CheckCircle2 :size="14" class="inline" /> OK</span>
                  <span v-else class="text-amber-400 text-[10px] font-bold"><AlertCircle :size="14" class="inline" /> AI?</span>
                </div>
              </div>
            </div>
            <div v-if="job.keywords" class="flex flex-wrap gap-1.5 mb-4">
              <span v-for="kw in job.keywords.split(',')" :key="kw" class="px-2 py-0.5 rounded bg-gray-50 text-gray-400 text-[9px] font-bold uppercase border border-gray-100">{{ kw.trim() }}</span>
            </div>
            <div :class="['rounded-xl p-4 text-sm border-l-4', job.summary?.includes('Chyba AI') ? 'bg-red-50 text-red-700 border-red-200' : job.summary ? 'bg-blue-50/50 text-[#002B5C] border-blue-200' : 'bg-gray-50 text-gray-400 border-gray-200 italic']">
              {{ job.summary || 'Tato pozice zatím nebyla zpracována AI modelem.' }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal: AI Key -->
    <div v-if="showKeyModal" class="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-6 animate-in fade-in">
      <div class="bg-white rounded-3xl shadow-2xl max-w-md w-full p-8 border border-gray-100">
        <div class="flex justify-between items-center mb-6">
          <h3 class="font-black text-2xl text-[#002B5C]">Nastavení AI</h3>
          <button @click="showKeyModal = false" class="p-2 hover:bg-gray-100 rounded-full"><X :size="24" /></button>
        </div>
        <div class="space-y-4">
          <div v-if="maskedKey && !newAiKey" class="px-4 py-3 bg-gray-50 rounded-2xl border border-gray-100 flex items-center justify-between">
            <span class="text-sm font-mono text-gray-400">{{ maskedKey }}</span>
            <span class="text-[9px] font-black text-green-600 bg-green-100 px-2 py-0.5 rounded uppercase">Uloženo</span>
          </div>
          <input v-model="newAiKey" type="password" placeholder="Nový API klíč..." class="w-full border-2 border-gray-100 rounded-2xl p-4 focus:border-blue-200 outline-none" :disabled="loading">
          <div v-if="keyError" class="p-3 bg-red-50 text-red-600 text-xs rounded-xl flex items-start gap-2"><AlertCircle :size="16" class="shrink-0" /> {{ keyError }}</div>
        </div>
        <button @click="saveAiKey" :disabled="loading || !newAiKey" class="w-full mt-6 bg-[#002B5C] text-white font-black py-4 rounded-2xl shadow-lg hover:bg-blue-900 transition-all disabled:opacity-50 flex items-center justify-center gap-2">
          <RefreshCw v-if="loading" :size="20" class="animate-spin" /> {{ loading ? 'OVĚŘUJI...' : 'ULOŽIT A OVĚŘIT' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: #E5E7EB; border-radius: 10px; }
</style>