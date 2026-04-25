<script setup lang="ts">
import { ref, onMounted, computed, onUnmounted, watch } from 'vue'
import axios from 'axios'
import { 
  Plus, Play, Cpu, Globe, Search, 
  RefreshCw, Clock, Briefcase, MapPin, 
  Key, X, ExternalLink, Trash2, Edit3, Filter, CheckCircle2, AlertCircle, AlertTriangle, Terminal, ChevronRight
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
const selectedSourceIds = ref<number[]>([])
const searchQuery = ref('')
const loading = ref(false)
const hasAiKey = ref(false)
const maskedKey = ref('')
const currentModel = ref('')
const showKeyModal = ref(false)
const newAiKey = ref('')
const availableModels = ref<any[]>([])
const selectedModel = ref('gemini-1.5-flash')
const keyError = ref('')
const scrapingIds = ref<Set<number>>(new Set())
const analyzingIds = ref<Set<number>>(new Set())
const deletingSourceId = ref<number | null>(null)
const showLogs = ref(false)
const debugLogs = ref<string[]>([])
let logInterval: any = null

const showSourceModal = ref(false)
const newSource = ref({ name: '', url: '' })

const showConfirmAnalysis = ref(false)
const lastAnalysisResult = ref<{ count: number, deleted: number } | null>(null)
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
    currentModel.value = keyRes.data.model_name
    if (!selectedModel.value || selectedModel.value === 'gemini-1.5-flash') {
      selectedModel.value = keyRes.data.model_name
    }
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

const addSource = async () => {
  if (!newSource.value.name || !newSource.value.url) return
  loading.value = true
  try {
    await axios.post('/api/admin/sources', newSource.value, adminAuth)
    newSource.value = { name: '', url: '' }
    showSourceModal.value = false
    await fetchData()
  } finally { loading.value = false }
}

const confirmDeleteSource = async (id: number) => {
  loading.value = true
  try {
    await axios.delete(`/api/admin/sources/${id}`, adminAuth)
    deletingSourceId.value = null
    await fetchData()
  } finally { loading.value = false }
}

const fetchAvailableModels = async () => {
  if (!newAiKey.value) return
  keyError.value = ''; loading.value = true
  try {
    const res = await axios.get(`/api/admin/settings/list-models?key=${newAiKey.value}`, adminAuth)
    availableModels.value = res.data
    if (availableModels.value.length > 0) {
      // Zkusíme předvybrat flash verzi, pokud existuje
      const flash = availableModels.value.find(m => m.name.includes('flash'))
      if (flash) selectedModel.value = flash.name
      else selectedModel.value = availableModels.value[0].name
    }
  } catch (e: any) {
    keyError.value = e.response?.data?.detail || 'Nepodařilo se načíst seznam modelů. Zkontrolujte klíč.'
  } finally { loading.value = false }
}

const saveAiSettings = async () => {
  if (!newAiKey.value || !selectedModel.value) return
  keyError.value = ''; loading.value = true
  try {
    await axios.post(`/api/admin/settings/gemini-key?key=${newAiKey.value}&model_name=${selectedModel.value}`, {}, adminAuth)
    newAiKey.value = ''; availableModels.value = []; showKeyModal.value = false; await fetchData()
  } catch (e: any) {
    keyError.value = e.response?.data?.detail || 'Nastavení se nepodařilo uložit.'
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

const scrapeBulk = async () => {
  loading.value = true
  try {
    for (const id of selectedSourceIds.value) {
      await scrapeSingle(id)
    }
    selectedSourceIds.value = []
  } finally { loading.value = false }
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

const isAllSourcesSelected = computed(() => sources.value.length > 0 && selectedSourceIds.value.length === sources.value.length)
const toggleSelectAllSources = () => {
  selectedSourceIds.value = isAllSourcesSelected.value ? [] : sources.value.map(s => s.id)
}

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
            <div class="flex flex-col">
              <span class="text-[10px] font-black text-gray-400 uppercase tracking-widest">AI Služba</span>
              <span class="text-sm font-bold text-[#002B5C]">{{ hasAiKey ? currentModel : 'Chybí klíč' }}</span>
            </div>
            <button @click="showKeyModal = true" class="p-1.5 hover:bg-gray-50 rounded-lg transition-colors flex items-center gap-2">
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
            <button @click="showSourceModal = true" class="p-1.5 bg-[#002B5C] text-white rounded-lg hover:bg-blue-900 transition-colors">
              <Plus :size="16" />
            </button>
          </div>
          
          <div v-if="sources.length" class="px-5 py-3 bg-gray-50 border-b border-gray-100 flex items-center justify-between">
            <label class="flex items-center gap-2 text-[10px] font-black text-gray-400 uppercase tracking-widest cursor-pointer">
              <input type="checkbox" :checked="isAllSourcesSelected" @change="toggleSelectAllSources" class="rounded text-blue-600"> Vybrat vše
            </label>
            <button v-if="selectedSourceIds.length" @click="scrapeBulk" class="text-[10px] font-black bg-blue-600 text-white px-3 py-1.5 rounded-lg hover:bg-blue-700 transition-all flex items-center gap-2">
              <Play :size="12" /> SPUSTIT ({{ selectedSourceIds.length }})
            </button>
          </div>

          <div class="divide-y divide-gray-50 max-h-[500px] overflow-y-auto custom-scrollbar">
            <div v-for="source in sources" :key="source.id" class="p-5 hover:bg-gray-50/50 transition-colors group">
              <div class="flex items-start gap-4">
                <input type="checkbox" v-model="selectedSourceIds" :value="source.id" class="mt-1 rounded text-blue-600">
                <div class="flex-1 min-w-0">
                  <div class="flex justify-between items-start">
                    <h3 class="font-bold text-[#002B5C] truncate">{{ source.name }}</h3>
                    <div class="flex gap-1 opacity-0 group-hover:opacity-100 transition-all">
                      <button @click="scrapeSingle(source.id)" :disabled="scrapingIds.has(source.id)" class="p-1 text-blue-600 hover:bg-blue-50 rounded">
                        <RefreshCw :size="14" :class="{ 'animate-spin': scrapingIds.has(source.id) }" />
                      </button>
                      <button @click="deletingSourceId = source.id" class="p-1 text-red-400 hover:bg-red-50 rounded">
                        <Trash2 :size="14" />
                      </button>
                    </div>
                  </div>
                  <div class="text-[10px] text-gray-400 mt-1 flex flex-wrap gap-2">
                    <span class="flex items-center gap-1"><Clock :size="10" /> {{ formatDate(source.last_crawled_at) }}</span>
                    <span v-if="source.last_scrape_count" class="text-green-500 font-bold">+{{ source.last_scrape_count }}</span>
                    <span class="truncate max-w-[150px] italic">{{ source.url }}</span>
                  </div>

                  <div v-if="deletingSourceId === source.id" class="mt-3 p-3 bg-red-50 rounded-xl border border-red-100 animate-in fade-in slide-in-from-top-2">
                    <p class="text-[10px] font-bold text-red-600 mb-2 uppercase tracking-widest">Smazat zdroj i pozice?</p>
                    <div class="flex gap-2">
                      <button @click="confirmDeleteSource(source.id)" :disabled="loading" class="bg-red-600 text-white px-3 py-1 rounded text-[10px] font-black hover:bg-red-700 disabled:opacity-50">SMAZAT</button>
                      <button @click="deletingSourceId = null" class="bg-white border border-gray-200 text-gray-500 px-3 py-1 rounded text-[10px] font-black hover:bg-gray-50">ZRUŠIT</button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div v-if="!sources.length" class="p-10 text-center text-gray-400 text-sm">Zatím žádné zdroje.</div>
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
                <div class="flex items-center gap-2 mb-1">
                  <h3 class="font-black text-xl text-[#002B5C] truncate">{{ job.title }}</h3>
                  <a v-if="job.link" :href="job.link" target="_blank" class="text-gray-300 hover:text-blue-600 transition-colors"><ExternalLink :size="16" /></a>
                </div>
                <div class="flex items-center gap-4 text-sm font-medium text-gray-500">
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

    <!-- Modal: Add Source -->
    <div v-if="showSourceModal" class="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-6 animate-in fade-in">
      <div class="bg-white rounded-3xl shadow-2xl max-w-md w-full p-8 border border-gray-100">
        <div class="flex justify-between items-center mb-6">
          <h3 class="font-black text-2xl text-[#002B5C]">Přidat zdroj</h3>
          <button @click="showSourceModal = false" class="p-2 hover:bg-gray-100 rounded-full"><X :size="24" /></button>
        </div>
        <div class="space-y-4">
          <div>
            <label class="block text-[10px] font-black text-gray-400 uppercase tracking-widest mb-2">Název firmy</label>
            <input v-model="newSource.name" type="text" placeholder="Např. Google" class="w-full border-2 border-gray-100 rounded-2xl p-4 focus:border-blue-200 outline-none">
          </div>
          <div>
            <label class="block text-[10px] font-black text-gray-400 uppercase tracking-widest mb-2">URL kariérních stránek</label>
            <input v-model="newSource.url" type="url" placeholder="https://..." class="w-full border-2 border-gray-100 rounded-2xl p-4 focus:border-blue-200 outline-none">
          </div>
        </div>
        <button @click="addSource" :disabled="loading || !newSource.name || !newSource.url" class="w-full mt-6 bg-[#002B5C] text-white font-black py-4 rounded-2xl shadow-lg hover:bg-blue-900 transition-all disabled:opacity-50 flex items-center justify-center gap-2">
          ULOŽIT ZDROJ
        </button>
      </div>
    </div>

    <!-- Modal: AI Settings -->
    <div v-if="showKeyModal" class="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-6 animate-in fade-in">
      <div class="bg-white rounded-3xl shadow-2xl max-w-md w-full p-8 border border-gray-100">
        <div class="flex justify-between items-center mb-6">
          <h3 class="font-black text-2xl text-[#002B5C]">Nastavení AI</h3>
          <button @click="showKeyModal = false" class="p-2 hover:bg-gray-100 rounded-full"><X :size="24" /></button>
        </div>
        
        <div class="space-y-6">
          <!-- Step 1: API Key -->
          <div>
            <label class="block text-[10px] font-black text-gray-400 uppercase tracking-widest mb-2">Google AI API Klíč</label>
            <div class="relative">
              <input v-model="newAiKey" type="password" placeholder="Vložte API klíč..." class="w-full border-2 border-gray-100 rounded-2xl p-4 pr-12 focus:border-blue-200 outline-none" :disabled="loading">
              <button @click="fetchAvailableModels" :disabled="loading || !newAiKey" class="absolute right-2 top-2 p-2 bg-blue-50 text-blue-600 rounded-xl hover:bg-blue-100 transition-all disabled:opacity-50">
                <ChevronRight :size="20" />
              </button>
            </div>
            <p v-if="maskedKey" class="mt-2 text-[10px] text-gray-400 font-mono">Aktuální: {{ maskedKey }}</p>
          </div>

          <!-- Step 2: Model Selection (Visible only after fetching) -->
          <div v-if="availableModels.length > 0" class="animate-in slide-in-from-top-4">
            <label class="block text-[10px] font-black text-gray-400 uppercase tracking-widest mb-2">Vyberte model</label>
            <select v-model="selectedModel" class="w-full border-2 border-gray-100 rounded-2xl p-4 bg-white outline-none focus:border-blue-200">
              <option v-for="m in availableModels" :key="m.name" :value="m.name">{{ m.display_name }} ({{ m.name }})</option>
            </select>
            <div class="mt-4 p-4 bg-blue-50 rounded-2xl border border-blue-100 flex items-start gap-3">
              <AlertCircle :size="18" class="text-blue-600 shrink-0" />
              <p class="text-[10px] text-blue-800 font-medium leading-relaxed">
                Doporučujeme modely s příponou <span class="font-bold">flash</span> pro nejrychlejší a nejlevnější analýzu.
              </p>
            </div>
          </div>

          <div v-if="keyError" class="p-4 bg-red-50 text-red-600 text-xs rounded-2xl flex items-start gap-3 border border-red-100">
            <AlertCircle :size="18" class="shrink-0" /> {{ keyError }}
          </div>

          <button v-if="availableModels.length > 0" @click="saveAiSettings" :disabled="loading || !selectedModel" class="w-full bg-[#002B5C] text-white font-black py-4 rounded-2xl shadow-lg hover:bg-blue-900 transition-all disabled:opacity-50 flex items-center justify-center gap-2">
            <RefreshCw v-if="loading" :size="20" class="animate-spin" /> {{ loading ? 'UKLÁDÁM...' : 'DOKONČIT NASTAVENÍ' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: #E5E7EB; border-radius: 10px; }
</style>