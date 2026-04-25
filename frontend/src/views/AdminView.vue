<script setup lang="ts">
import { ref, onMounted, computed, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { 
  Plus, Play, Cpu, Search, 
  RefreshCw, Clock, Briefcase, MapPin, 
  Key, X, ExternalLink, Trash2, Filter, CheckCircle2, AlertCircle, AlertTriangle, Terminal, ChevronRight, LogOut, ShieldCheck, User, Lock
} from 'lucide-vue-next'

const router = useRouter()

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
const selectedJobIds = ref<number[]>([])
const searchQuery = ref('')
const loading = ref(false)
const hasAiKey = ref(false)
const maskedKey = ref('')
const currentModel = ref('')
const isEditingAi = ref(false)
const isEditingCreds = ref(false)
const isAddingSource = ref(false)
const newAiKey = ref('')
const availableModels = ref<any[]>([])
const selectedModel = ref('gemini-1.5-flash')
const keyError = ref('')
const scrapingIds = ref<Set<number>>(new Set())
const analyzingIds = ref<Set<number>>(new Set())
const deletingSourceId = ref<number | null>(null)
const deletingJobId = ref<number | null>(null)
const showBulkDeleteConfirm = ref(false)
const showLogs = ref(false)
const debugLogs = ref<string[]>([])
let logInterval: any = null

const newSource = ref({ name: '', url: '' })
const newCreds = ref({ username: '', password: '' })

const showConfirmAnalysis = ref(false)
const lastAnalysisResult = ref<{ count: number, deleted: number } | null>(null)
const onlyNeedsAi = ref(false)

const getAdminAuth = () => {
  const username = sessionStorage.getItem('admin_user')
  const password = sessionStorage.getItem('admin_pass')
  if (!username || !password) return null
  return { auth: { username, password } }
}

const logout = () => {
  sessionStorage.removeItem('admin_user')
  sessionStorage.removeItem('admin_pass')
  router.push('/login')
}

const fetchData = async () => {
  const adminAuth = getAdminAuth()
  if (!adminAuth) return router.push('/login')
  
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
  } catch (e: any) { 
    if (e.response?.status === 401) logout()
    console.error("Chyba při načítání dat", e) 
  }
}

const fetchLogs = async () => {
  const adminAuth = getAdminAuth()
  if (!adminAuth) return
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
  const adminAuth = getAdminAuth()
  if (!newSource.value.name || !newSource.value.url || !adminAuth) return
  loading.value = true
  try {
    await axios.post('/api/admin/sources', newSource.value, adminAuth)
    newSource.value = { name: '', url: '' }
    isAddingSource.value = false
    await fetchData()
  } finally { loading.value = false }
}

const confirmDeleteSource = async (id: number) => {
  const adminAuth = getAdminAuth()
  if (!adminAuth) return
  loading.value = true
  try {
    await axios.delete(`/api/admin/sources/${id}`, adminAuth)
    deletingSourceId.value = null
    await fetchData()
  } finally { loading.value = false }
}

const confirmDeleteJob = async (id: number) => {
  const adminAuth = getAdminAuth()
  if (!adminAuth) return
  loading.value = true
  try {
    await axios.delete(`/api/admin/jobs/${id}`, adminAuth)
    deletingJobId.value = null
    await fetchData()
  } finally { loading.value = false }
}

const bulkDeleteJobs = async () => {
  const adminAuth = getAdminAuth()
  if (!adminAuth || !selectedJobIds.value.length) return
  loading.value = true
  try {
    await axios.post('/api/admin/jobs/bulk-delete', { ids: selectedJobIds.value }, adminAuth)
    selectedJobIds.value = []
    showBulkDeleteConfirm.value = false
    await fetchData()
  } finally { loading.value = false }
}

const bulkAnalyzeJobs = async () => {
  const adminAuth = getAdminAuth()
  if (!adminAuth || !selectedJobIds.value.length) return
  loading.value = true
  try {
    const res = await axios.post('/api/admin/jobs/bulk-analyze', { ids: selectedJobIds.value }, adminAuth)
    selectedJobIds.value = []
    lastAnalysisResult.value = res.data
    await fetchData()
  } finally { loading.value = false }
}

const fetchAvailableModels = async () => {
  const adminAuth = getAdminAuth()
  if (!newAiKey.value || !adminAuth) return
  keyError.value = ''; loading.value = true
  try {
    const res = await axios.get(`/api/admin/settings/list-models?key=${newAiKey.value}`, adminAuth)
    availableModels.value = res.data
    if (availableModels.value.length > 0) {
      const flash = availableModels.value.find(m => m.name.includes('flash'))
      if (flash) selectedModel.value = flash.name
      else selectedModel.value = availableModels.value[0].name
    }
  } catch (e: any) {
    keyError.value = e.response?.data?.detail || 'Nepodařilo se načíst modely.'
  } finally { loading.value = false }
}

const saveAiSettings = async () => {
  const adminAuth = getAdminAuth()
  if (!newAiKey.value || !selectedModel.value || !adminAuth) return
  keyError.value = ''; loading.value = true
  try {
    await axios.post(`/api/admin/settings/gemini-key?key=${newAiKey.value}&model_name=${selectedModel.value}`, {}, adminAuth)
    newAiKey.value = ''; availableModels.value = []; isEditingAi.value = false; await fetchData()
  } catch (e: any) {
    keyError.value = e.response?.data?.detail || 'Nastavení se nepodařilo uložit.'
  } finally { loading.value = false }
}

const saveCredentials = async () => {
  const adminAuth = getAdminAuth()
  if (!newCreds.value.username || !newCreds.value.password || !adminAuth) return
  loading.value = true
  try {
    await axios.post('/api/admin/settings/credentials', newCreds.value, adminAuth)
    alert('Údaje byly změněny. Budete odhlášeni.')
    logout()
  } catch (e: any) {
    alert('Chyba při ukládání údajů.')
  } finally { loading.value = false }
}

const runBulkAiAnalysis = async () => {
  const adminAuth = getAdminAuth()
  if (!adminAuth) return
  loading.value = true; showConfirmAnalysis.value = false; lastAnalysisResult.value = null
  try {
    const res = await axios.post('/api/admin/run-ai-analysis', {}, adminAuth)
    lastAnalysisResult.value = res.data; await fetchData()
  } finally { loading.value = false }
}

const analyzeSingleJob = async (id: number) => {
  const adminAuth = getAdminAuth()
  if (!adminAuth) return
  analyzingIds.value.add(id)
  try { await axios.post(`/api/admin/analyze-job/${id}`, {}, adminAuth); await fetchData() }
  finally { analyzingIds.value.delete(id) }
}

const scrapeSingle = async (id: number) => {
  const adminAuth = getAdminAuth()
  if (!adminAuth) return
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

const isAllJobsSelected = computed(() => filteredJobs.value.length > 0 && selectedJobIds.value.length === filteredJobs.value.length)
const toggleSelectAllJobs = () => {
  selectedJobIds.value = isAllJobsSelected.value ? [] : filteredJobs.value.map(j => j.id)
}

const formatDate = (d: string | null) => d ? new Date(d).toLocaleString('cs-CZ', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) : '---'

onMounted(fetchData)
onUnmounted(() => clearInterval(logInterval))
</script>

<template>
  <div class="max-w-7xl mx-auto px-4 py-8 space-y-6">
    <!-- Admin Header -->
    <div class="flex items-center justify-between mb-8">
      <div class="flex items-center gap-4">
        <div class="w-10 h-10 bg-[#002B5C] rounded-lg flex items-center justify-center">
          <span class="text-white font-black text-sm">ADM</span>
        </div>
        <div>
          <h1 class="text-2xl font-black text-[#002B5C] tracking-tighter uppercase">Admin Rozhraní</h1>
          <p class="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Správa zdrojů a AI analýzy</p>
        </div>
      </div>
      <div class="flex items-center gap-6">
        <router-link to="/" class="text-xs font-black text-gray-400 hover:text-[#002B5C] uppercase tracking-widest transition-colors flex items-center gap-2">
          <ExternalLink :size="14" /> Zpět na web
        </router-link>
        <button @click="logout" class="text-xs font-black text-red-400 hover:text-red-600 uppercase tracking-widest transition-colors flex items-center gap-2">
          <LogOut :size="14" /> Odhlásit se
        </button>
      </div>
    </div>

    <!-- AI Stats & Inline Settings -->
    <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
      <div class="p-5 flex flex-wrap items-center justify-between gap-6">
        <div class="flex items-center gap-8">
          <div class="flex items-center gap-3">
            <div :class="`w-3 h-3 rounded-full ${hasAiKey ? 'bg-green-500 shadow-lg shadow-green-200' : 'bg-red-500 shadow-lg shadow-red-200'}`"></div>
            <div class="flex flex-col">
              <span class="text-[10px] font-black text-gray-400 uppercase tracking-widest">AI Služba</span>
              <span class="text-sm font-bold text-[#002B5C]">{{ hasAiKey ? currentModel : 'Chybí klíč' }}</span>
            </div>
            <div class="flex gap-1">
              <button @click="isEditingAi = !isEditingAi; isEditingCreds = false" :class="['p-1.5 rounded-lg transition-colors', isEditingAi ? 'bg-blue-50 text-blue-600' : 'hover:bg-gray-50 text-gray-400']" title="Nastavení AI">
                <Key :size="16" />
              </button>
              <button @click="isEditingCreds = !isEditingCreds; isEditingAi = false" :class="['p-1.5 rounded-lg transition-colors', isEditingCreds ? 'bg-blue-50 text-blue-600' : 'hover:bg-gray-50 text-gray-400']" title="Změna přístupových údajů">
                <ShieldCheck :size="16" />
              </button>
            </div>
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

      <!-- Inline AI Settings Form -->
      <div v-if="isEditingAi" class="px-5 pb-5 pt-0 animate-in slide-in-from-top-2">
        <div class="p-6 bg-blue-50/50 rounded-2xl border border-blue-100 space-y-4">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-[10px] font-black text-blue-900/40 uppercase tracking-widest mb-2">Nový Google AI API Klíč</label>
              <div class="relative">
                <input v-model="newAiKey" type="password" placeholder="Vložte API klíč..." class="w-full bg-white border border-blue-100 rounded-xl p-3 pr-12 text-sm outline-none focus:ring-2 focus:ring-blue-200">
                <button @click="fetchAvailableModels" :disabled="loading || !newAiKey" class="absolute right-2 top-2 p-1.5 text-blue-600 hover:bg-blue-50 rounded-lg disabled:opacity-30">
                  <ChevronRight :size="18" />
                </button>
              </div>
            </div>
            <div v-if="availableModels.length > 0">
              <label class="block text-[10px] font-black text-blue-900/40 uppercase tracking-widest mb-2">Vybrat Model</label>
              <select v-model="selectedModel" class="w-full bg-white border border-blue-100 rounded-xl p-3 text-sm outline-none focus:ring-2 focus:ring-blue-200">
                <option v-for="m in availableModels" :key="m.name" :value="m.name">{{ m.display_name }}</option>
              </select>
            </div>
          </div>
          <div class="flex justify-end gap-3 pt-2">
            <button @click="isEditingAi = false" class="text-xs font-black text-gray-400 hover:text-gray-600 uppercase tracking-widest">Zrušit</button>
            <button v-if="availableModels.length > 0" @click="saveAiSettings" :disabled="loading" class="bg-blue-600 text-white px-4 py-2 rounded-xl text-xs font-black hover:bg-blue-700 disabled:opacity-50">
              ULOŽIT NASTAVENÍ
            </button>
          </div>
        </div>
      </div>

      <!-- Credentials Settings Form -->
      <div v-if="isEditingCreds" class="px-5 pb-5 pt-0 animate-in slide-in-from-top-2">
        <div class="p-6 bg-gray-50/80 rounded-2xl border border-gray-200 space-y-4">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-[10px] font-black text-gray-400 uppercase tracking-widest mb-2">Nové přihlašovací jméno</label>
              <div class="relative">
                <User class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" :size="16" />
                <input v-model="newCreds.username" type="text" placeholder="Jméno..." class="w-full bg-white border border-gray-200 rounded-xl p-3 pl-10 text-sm outline-none focus:ring-2 focus:ring-blue-100">
              </div>
            </div>
            <div>
              <label class="block text-[10px] font-black text-gray-400 uppercase tracking-widest mb-2">Nové heslo</label>
              <div class="relative">
                <Lock class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" :size="16" />
                <input v-model="newCreds.password" type="password" placeholder="Heslo..." class="w-full bg-white border border-gray-200 rounded-xl p-3 pl-10 text-sm outline-none focus:ring-2 focus:ring-blue-100">
              </div>
            </div>
          </div>
          <div class="flex justify-end gap-3 pt-2">
            <button @click="isEditingCreds = false" class="text-xs font-black text-gray-400 hover:text-gray-600 uppercase tracking-widest">Zrušit</button>
            <button @click="saveCredentials" :disabled="loading || !newCreds.username || !newCreds.password" class="bg-gray-900 text-white px-4 py-2 rounded-xl text-xs font-black hover:bg-black disabled:opacity-50 uppercase tracking-widest">
              Změnit údaje
            </button>
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
      <div class="col-span-12 lg:col-span-4 lg:sticky lg:top-8">
        <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
          <div class="p-5 border-b border-gray-100 bg-gray-50/50 flex justify-between items-center">
            <h2 class="font-black text-[#002B5C] uppercase tracking-widest text-xs">Zdroje</h2>
            <button @click="isAddingSource = !isAddingSource" :class="['p-1.5 rounded-lg transition-colors', isAddingSource ? 'bg-blue-600 text-white' : 'bg-[#002B5C] text-white hover:bg-blue-900']">
              <Plus :size="16" />
            </button>
          </div>

          <!-- Inline Add Source Form -->
          <div v-if="isAddingSource" class="p-5 bg-blue-50/30 border-b border-blue-50 animate-in slide-in-from-top-2">
            <div class="space-y-4">
              <div>
                <label class="block text-[10px] font-black text-blue-900/40 uppercase tracking-widest mb-1.5">Název firmy</label>
                <input v-model="newSource.name" type="text" placeholder="Např. Google" class="w-full bg-white border border-blue-100 rounded-xl p-2.5 text-sm outline-none focus:ring-2 focus:ring-blue-100">
              </div>
              <div>
                <label class="block text-[10px] font-black text-blue-900/40 uppercase tracking-widest mb-1.5">URL kariérních stránek</label>
                <input v-model="newSource.url" type="url" placeholder="https://..." class="w-full bg-white border border-blue-100 rounded-xl p-2.5 text-sm outline-none focus:ring-2 focus:ring-blue-100">
              </div>
              <div class="flex gap-2 pt-2">
                <button @click="addSource" :disabled="loading || !newSource.name || !newSource.url" class="flex-1 bg-blue-600 text-white font-black py-2 rounded-xl text-xs hover:bg-blue-700 disabled:opacity-50">PŘIDAT</button>
                <button @click="isAddingSource = false" class="px-4 py-2 text-xs font-black text-gray-400 hover:text-gray-600 uppercase tracking-widest">Zrušit</button>
              </div>
            </div>
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

        <div v-if="filteredJobs.length" class="bg-white p-3 rounded-2xl border border-gray-100 flex flex-col shadow-sm">
          <div class="flex items-center justify-between w-full">
            <label class="flex items-center gap-2 text-[10px] font-black text-gray-400 uppercase tracking-widest cursor-pointer px-3">
              <input type="checkbox" :checked="isAllJobsSelected" @change="toggleSelectAllJobs" class="rounded text-blue-600"> Vybrat vše
            </label>
            <div v-if="selectedJobIds.length && !showBulkDeleteConfirm" class="flex gap-2 animate-in fade-in slide-in-from-right-2">
              <button @click="bulkAnalyzeJobs" class="text-[10px] font-black bg-purple-600 text-white px-3 py-1.5 rounded-lg hover:bg-purple-700 transition-all flex items-center gap-2">
                <Cpu :size="12" /> ANALYZOVAT ({{ selectedJobIds.length }})
              </button>
              <button @click="showBulkDeleteConfirm = true" class="text-[10px] font-black bg-red-600 text-white px-3 py-1.5 rounded-lg hover:bg-red-700 transition-all flex items-center gap-2">
                <Trash2 :size="12" /> SMAZAT ({{ selectedJobIds.length }})
              </button>
            </div>
            <div v-if="showBulkDeleteConfirm" class="flex items-center gap-3 px-3 py-1 animate-in fade-in slide-in-from-right-4">
              <span class="text-[10px] font-bold text-red-600 uppercase tracking-widest">Smazat {{ selectedJobIds.length }} pozic?</span>
              <button @click="bulkDeleteJobs" :disabled="loading" class="bg-red-600 text-white px-3 py-1 rounded text-[10px] font-black hover:bg-red-700 disabled:opacity-50">ANO, SMAZAT</button>
              <button @click="showBulkDeleteConfirm = false" class="bg-gray-100 text-gray-500 px-3 py-1 rounded text-[10px] font-black hover:bg-gray-200">ZRUŠIT</button>
            </div>
          </div>
        </div>

        <div class="space-y-4 pb-20">
          <div v-for="job in filteredJobs" :key="job.id" class="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm hover:border-blue-100 transition-all group relative overflow-hidden">
            <div class="flex items-start gap-4">
              <input type="checkbox" v-model="selectedJobIds" :value="job.id" class="mt-2 rounded text-blue-600">
              <div class="flex-1 min-w-0">
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
                      <button @click="deletingJobId = job.id" class="p-1.5 hover:bg-red-50 rounded-lg text-gray-300 hover:text-red-500 transition-all"><Trash2 :size="16" /></button>
                    </div>
                    <div class="flex items-center gap-1">
                      <span v-if="job.last_analyzed_at" class="text-green-500 text-[10px] font-bold"><CheckCircle2 :size="14" class="inline" /> OK</span>
                      <span v-else class="text-amber-400 text-[10px] font-bold"><AlertCircle :size="14" class="inline" /> AI?</span>
                    </div>
                  </div>
                </div>

                <div v-if="deletingJobId === job.id" class="mb-4 p-4 bg-red-50 rounded-xl border border-red-100 animate-in fade-in slide-in-from-top-2">
                  <p class="text-[10px] font-bold text-red-600 mb-2 uppercase tracking-widest">Smazat tuto pozici?</p>
                  <div class="flex gap-2">
                    <button @click="confirmDeleteJob(job.id)" :disabled="loading" class="bg-red-600 text-white px-3 py-1 rounded text-[10px] font-black hover:bg-red-700 disabled:opacity-50">SMAZAT</button>
                    <button @click="deletingJobId = null" class="bg-white border border-gray-200 text-gray-500 px-3 py-1 rounded text-[10px] font-black hover:bg-gray-50">ZRUŠIT</button>
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
      </div>
    </div>
  </div>
</template>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: #E5E7EB; border-radius: 10px; }
</style>