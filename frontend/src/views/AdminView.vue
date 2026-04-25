<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import axios from 'axios'
import { 
  Plus, Play, Cpu, Globe, Search, 
  RefreshCw, Clock, Briefcase, MapPin, 
  Key, X, ExternalLink, Trash2, Edit3, Filter, CheckCircle2, AlertCircle, AlertTriangle
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

// Analysis State
const showConfirmAnalysis = ref(false)
const lastAnalysisResult = ref<{ count: number, deleted: number } | null>(null)

// Edit Modal
const showEditModal = ref(false)
const editingJob = ref<Partial<Job>>({})

// Filter
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
  } catch (e) {
    console.error("Chyba při načítání dat", e)
  }
}

const deleteJob = async (id: number) => {
  if (!confirm('Opravdu chcete tuto pozici smazat?')) return
  await axios.delete(`/api/admin/jobs/${id}`, adminAuth)
  fetchData()
}

const openEdit = (job: Job) => {
  editingJob.value = { ...job }
  showEditModal.value = true
}

const saveEdit = async () => {
  if (!editingJob.value.id) return
  await axios.patch(`/api/admin/jobs/${editingJob.value.id}`, editingJob.value, adminAuth)
  showEditModal.value = false
  fetchData()
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
  return jobs.value.filter(j => {
    const matchesSearch = j.title.toLowerCase().includes(q) || 
                         j.company.toLowerCase().includes(q) ||
                         (j.keywords && j.keywords.toLowerCase().includes(q))
    
    const needsAi = !j.last_analyzed_at || !j.summary
    const matchesFilter = !onlyNeedsAi.value || needsAi
    
    return matchesSearch && matchesFilter
  })
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
  showConfirmAnalysis.value = false
  lastAnalysisResult.value = null
  try {
    const res = await axios.post('/api/admin/run-ai-analysis', {}, adminAuth)
    lastAnalysisResult.value = res.data
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
    <!-- Top Stats / Actions -->
    <div class="bg-white p-5 rounded-2xl shadow-sm border border-gray-100">
      <div class="flex flex-wrap items-center justify-between gap-6">
        <div class="flex items-center gap-8">
          <div class="flex items-center gap-3">
            <div :class="`w-3 h-3 rounded-full ${hasAiKey ? 'bg-green-500 shadow-lg shadow-green-200' : 'bg-red-500 shadow-lg shadow-red-200'}`"></div>
            <span class="text-sm font-bold text-[#002B5C] uppercase tracking-wider">AI Služba: {{ hasAiKey ? 'Aktivní' : 'Chybí klíč' }}</span>
            <button @click="showKeyModal = true" class="p-1.5 hover:bg-gray-50 rounded-lg transition-colors">
              <Key :size="16" class="text-gray-400" />
            </button>
          </div>
          
          <div class="h-6 w-px bg-gray-100"></div>

          <button 
            @click="onlyNeedsAi = !onlyNeedsAi" 
            :class="['flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-bold transition-all border', 
              onlyNeedsAi ? 'bg-amber-50 border-amber-200 text-amber-700' : 'bg-gray-50 border-gray-100 text-gray-500 hover:border-gray-300']"
          >
            <Filter :size="14" /> {{ onlyNeedsAi ? 'Filtruji neanalyzované' : 'Všechny pozice' }}
          </button>
        </div>

        <div class="flex flex-col items-end gap-2">
          <div v-if="!showConfirmAnalysis" class="flex flex-col items-end gap-2">
            <button 
              @click="showConfirmAnalysis = true" 
              :disabled="loading" 
              class="bg-[#002B5C] text-white px-6 py-2.5 rounded-xl text-sm font-black flex items-center gap-2 hover:bg-blue-900 transition-all shadow-md shadow-blue-100 disabled:opacity-50"
            >
              <Cpu :size="18" :class="{ 'animate-pulse': loading }" /> Hromadná AI analýza
            </button>
          </div>
          
          <div v-else class="flex items-center gap-3 animate-in fade-in slide-in-from-right-4">
            <span class="text-xs font-bold text-amber-600 flex items-center gap-1.5">
              <AlertTriangle :size="14" /> Opravdu analyzovat vše?
            </span>
            <button @click="runBulkAiAnalysis" class="bg-green-600 text-white px-4 py-1.5 rounded-lg text-xs font-black hover:bg-green-700 transition-all">ANO, SPUSTIT</button>
            <button @click="showConfirmAnalysis = false" class="bg-gray-100 text-gray-500 px-4 py-1.5 rounded-lg text-xs font-black hover:bg-gray-200 transition-all">ZRUŠIT</button>
          </div>

          <!-- Analysis Results -->
          <div v-if="lastAnalysisResult" class="text-[10px] font-bold uppercase tracking-widest animate-in fade-in duration-500">
            <span class="text-green-600 bg-green-50 px-2 py-1 rounded">Analyzováno: {{ lastAnalysisResult.count }}</span>
            <span class="text-red-600 bg-red-50 px-2 py-1 rounded ml-2">Smazáno (odpad): {{ lastAnalysisResult.deleted }}</span>
            <button @click="lastAnalysisResult = null" class="ml-2 text-gray-300 hover:text-gray-500"><X :size="10" /></button>
          </div>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-12 gap-8 items-start">
      <!-- Sources Column -->
      <div class="col-span-12 lg:col-span-4 lg:sticky lg:top-24">
        <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
          <div class="p-5 border-b border-gray-100 bg-gray-50/50 flex justify-between items-center">
            <h2 class="font-black text-[#002B5C] uppercase tracking-widest text-xs">Zdroje dat</h2>
            <span class="text-[10px] font-bold px-2 py-0.5 bg-gray-200 rounded text-gray-600">{{ sources.length }}</span>
          </div>
          <div class="p-4 border-b border-gray-50 flex items-center justify-between">
            <label class="flex items-center gap-3 text-xs font-bold text-gray-400 cursor-pointer">
              <input type="checkbox" :checked="isAllSelected" @change="toggleSelectAll" class="rounded text-blue-600 focus:ring-blue-100"> 
              VYBRAT VŠE
            </label>
            <button v-if="selectedIds.length" @click="scrapeSelected" class="text-[10px] font-black bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 flex items-center gap-1.5 transition-all">
              <RefreshCw :size="12" :class="{ 'animate-spin': loading }" /> AKTUALIZOVAT ({{ selectedIds.length }})
            </button>
          </div>
          <div class="divide-y divide-gray-50 max-h-[600px] overflow-y-auto custom-scrollbar">
            <div v-for="source in sources" :key="source.id" class="p-5 hover:bg-gray-50/50 transition-colors group">
              <div class="flex items-start gap-4">
                <input type="checkbox" v-model="selectedIds" :value="source.id" class="mt-1 rounded text-blue-600 focus:ring-blue-100">
                <div class="flex-1 min-w-0">
                  <div class="flex justify-between items-start mb-1">
                    <h3 class="font-bold text-[#002B5C] truncate pr-2">{{ source.name }}</h3>
                    <button @click="scrapeSingle(source.id)" :disabled="scrapingIds.has(source.id)" class="opacity-0 group-hover:opacity-100 p-1.5 hover:bg-blue-50 rounded-lg text-blue-600 transition-all">
                      <RefreshCw :size="16" :class="{ 'animate-spin': scrapingIds.has(source.id) }" />
                    </button>
                  </div>
                  <div class="flex items-center gap-3 text-[10px] text-gray-400 font-medium">
                    <span class="flex items-center gap-1"><Clock :size="10" /> {{ formatDate(source.last_crawled_at) }}</span>
                    <span v-if="source.last_scrape_count !== null" class="text-green-600">+{{ source.last_scrape_count }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Jobs Column -->
      <div class="col-span-12 lg:col-span-8 space-y-4">
        <div class="flex items-center gap-4 bg-white p-3 rounded-2xl shadow-sm border border-gray-100 mb-6">
          <Search class="ml-3 text-gray-300" :size="20" />
          <input v-model="searchQuery" type="text" placeholder="Hledat v inzerátech..." class="flex-1 border-none focus:ring-0 text-md placeholder-gray-300">
          <div class="px-5 py-1.5 bg-gray-50 rounded-full text-[10px] font-black text-gray-400 uppercase tracking-widest">{{ filteredJobs.length }} nalezeno</div>
        </div>

        <div class="space-y-4 pb-20">
          <div v-for="job in filteredJobs" :key="job.id" class="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm hover:border-blue-100 transition-all group">
            <div class="flex justify-between items-start mb-4">
              <div class="flex-1 min-w-0 pr-4">
                <div class="flex items-center gap-2 mb-1">
                  <h3 class="font-black text-xl text-[#002B5C] tracking-tight truncate">{{ job.title }}</h3>
                  <a v-if="job.link" :href="job.link" target="_blank" class="text-gray-300 hover:text-blue-600" title="Náhled inzerátu">
                    <ExternalLink :size="16" />
                  </a>
                  <span v-else class="px-2 py-0.5 bg-red-50 text-red-500 text-[9px] font-black uppercase rounded tracking-widest">CHYBÍ LINK</span>
                </div>
                <div class="flex items-center gap-4 text-sm font-medium text-gray-500">
                  <span class="flex items-center gap-1.5"><Briefcase :size="14" /> {{ job.company }}</span>
                  <span class="flex items-center gap-1.5"><MapPin :size="14" /> {{ job.location || 'Remote' }}</span>
                </div>
              </div>
              
              <div class="flex flex-col items-end gap-3 shrink-0">
                <div class="flex gap-2">
                  <button @click="openEdit(job)" class="p-2 hover:bg-gray-100 rounded-xl text-gray-400 hover:text-blue-600 transition-all" title="Upravit">
                    <Edit3 :size="18" />
                  </button>
                  <button @click="deleteJob(job.id)" class="p-2 hover:bg-gray-100 rounded-xl text-gray-400 hover:text-red-500 transition-all" title="Smazat">
                    <Trash2 :size="18" />
                  </button>
                </div>
                <div class="flex items-center gap-2">
                  <button @click="analyzeSingleJob(job.id)" :disabled="analyzingIds.has(job.id)" class="px-3 py-1 bg-purple-50 hover:bg-purple-100 text-purple-700 text-[10px] font-black uppercase rounded-lg transition-all flex items-center gap-1.5">
                    <Cpu :size="12" :class="{ 'animate-pulse': analyzingIds.has(job.id) }" /> ANALYZOVAT
                  </button>
                  <span v-if="job.last_analyzed_at" class="text-green-500" title="Analyzováno"><CheckCircle2 :size="16" /></span>
                  <span v-else class="text-amber-400" title="Čeká na AI"><AlertCircle :size="16" /></span>
                </div>
              </div>
            </div>

            <!-- Tags in Admin -->
            <div v-if="job.keywords" class="flex flex-wrap gap-1.5 mb-4">
              <span v-for="kw in job.keywords.split(',')" :key="kw" class="px-2 py-0.5 rounded bg-gray-50 text-gray-400 text-[9px] font-bold uppercase border border-gray-100">
                {{ kw.trim() }}
              </span>
            </div>
            
            <div :class="['rounded-xl p-4 text-sm leading-relaxed border-l-4', job.summary ? 'bg-blue-50/50 text-[#002B5C] border-blue-200' : 'bg-gray-50 text-gray-400 border-gray-200 italic']">
              {{ job.summary || 'Tato pozice zatím nebyla zpracována AI modelem.' }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal: AI Key -->
    <div v-if="showKeyModal" class="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-6 animate-in fade-in duration-200">
      <div class="bg-white rounded-3xl shadow-2xl max-w-md w-full p-8 border border-gray-100">
        <div class="flex justify-between items-center mb-6">
          <h3 class="font-black text-2xl text-[#002B5C] tracking-tight">Nastavení AI</h3>
          <button @click="showKeyModal = false" class="p-2 hover:bg-gray-100 rounded-full transition-colors"><X :size="24" /></button>
        </div>
        <p class="text-gray-500 mb-6 text-sm">Vložte Google Gemini API klíč pro automatickou extrakci dovedností a shrnutí inzerátů.</p>
        <input v-model="newAiKey" type="password" placeholder="AI Key..." class="w-full border-2 border-gray-100 rounded-2xl p-4 mb-6 focus:border-blue-200 focus:outline-none transition-all">
        <button @click="saveAiKey" class="w-full bg-[#002B5C] text-white font-black py-4 rounded-2xl shadow-lg shadow-blue-100 hover:bg-blue-900 transition-all">ULOŽIT KLÍČ</button>
      </div>
    </div>

    <!-- Modal: Edit Job -->
    <div v-if="showEditModal" class="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-6 animate-in fade-in duration-200">
      <div class="bg-white rounded-3xl shadow-2xl max-w-2xl w-full p-8 border border-gray-100 overflow-y-auto max-h-[90vh]">
        <div class="flex justify-between items-center mb-8">
          <h3 class="font-black text-2xl text-[#002B5C] tracking-tight">Upravit pozici</h3>
          <button @click="showEditModal = false" class="p-2 hover:bg-gray-100 rounded-full transition-colors"><X :size="24" /></button>
        </div>
        
        <div class="space-y-5">
          <div>
            <label class="block text-[10px] font-black text-gray-400 uppercase tracking-widest mb-2">Název pozice</label>
            <input v-model="editingJob.title" type="text" class="w-full border-2 border-gray-50 bg-gray-50/50 rounded-xl p-3 focus:border-blue-100 focus:bg-white outline-none font-bold text-[#002B5C]">
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-[10px] font-black text-gray-400 uppercase tracking-widest mb-2">Firma</label>
              <input v-model="editingJob.company" type="text" class="w-full border-2 border-gray-50 bg-gray-50/50 rounded-xl p-3 focus:border-blue-100 focus:bg-white outline-none">
            </div>
            <div>
              <label class="block text-[10px] font-black text-gray-400 uppercase tracking-widest mb-2">Lokalita</label>
              <input v-model="editingJob.location" type="text" class="w-full border-2 border-gray-50 bg-gray-50/50 rounded-xl p-3 focus:border-blue-100 focus:bg-white outline-none">
            </div>
          </div>
          <div>
            <label class="block text-[10px] font-black text-gray-400 uppercase tracking-widest mb-2">Klíčová slova (čárka)</label>
            <input v-model="editingJob.keywords" type="text" class="w-full border-2 border-gray-50 bg-gray-50/50 rounded-xl p-3 focus:border-blue-100 focus:bg-white outline-none">
          </div>
          <div>
            <label class="block text-[10px] font-black text-gray-400 uppercase tracking-widest mb-2">AI Shrnutí</label>
            <textarea v-model="editingJob.summary" rows="3" class="w-full border-2 border-gray-50 bg-gray-50/50 rounded-xl p-3 focus:border-blue-100 focus:bg-white outline-none"></textarea>
          </div>
          <div>
            <label class="block text-[10px] font-black text-gray-400 uppercase tracking-widest mb-2">Odkaz na inzerát</label>
            <input v-model="editingJob.link" type="text" class="w-full border-2 border-gray-50 bg-gray-50/50 rounded-xl p-3 focus:border-blue-100 focus:bg-white outline-none text-blue-600">
          </div>
        </div>

        <div class="mt-10 flex gap-4">
          <button @click="showEditModal = false" class="flex-1 bg-gray-100 text-gray-500 font-black py-4 rounded-2xl hover:bg-gray-200 transition-all">ZRUŠIT</button>
          <button @click="saveEdit" class="flex-1 bg-[#002B5C] text-white font-black py-4 rounded-2xl shadow-lg shadow-blue-100 hover:bg-blue-900 transition-all">ULOŽIT ZMĚNY</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: #E5E7EB; border-radius: 10px; }
</style>