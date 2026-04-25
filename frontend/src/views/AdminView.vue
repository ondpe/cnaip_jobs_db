<script setup lang="ts">
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { Plus, Play, Cpu, Trash2, Globe } from 'lucide-vue-next'

const sources = ref([])
const newSourceName = ref('')
const newSourceUrl = ref('')
const loading = ref(false)

// Pro demo/lokální vývoj - v reálu by se použil login form
const adminUser = 'admin'
const adminPass = 'admin123'
const authHeader = { auth: { username: adminUser, password: adminPass } }

const fetchSources = async () => {
  const res = await axios.get('/api/sources')
  sources.value = res.data
}

const addSource = async () => {
  if (!newSourceName.value || !newSourceUrl.value) return
  await axios.post(`/api/admin/sources?name=${newSourceName.value}&url=${newSourceUrl.value}`, {}, authHeader)
  newSourceName.value = ''
  newSourceUrl.value = ''
  fetchSources()
}

const scrapeSource = async (id: number) => {
  loading.value = true
  try {
    await axios.post(`/api/admin/scrape/${id}`, {}, authHeader)
    alert('Scrapování dokončeno')
    fetchSources()
  } finally {
    loading.value = false
  }
}

const runAi = async () => {
  loading.value = true
  try {
    const res = await axios.post('/api/admin/run-ai-analysis', {}, authHeader)
    alert(`Analýza dokončena pro ${res.data.count} pozic`)
  } finally {
    loading.value = false
  }
}

onMounted(fetchSources)
</script>

<template>
  <div class="space-y-8">
    <div class="flex justify-between items-center">
      <h1 class="text-2xl font-bold text-gray-900">Správa systému</h1>
      <button @click="runAi" :disabled="loading" class="flex items-center gap-2 bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700 disabled:opacity-50">
        <Cpu :size="20" /> Spustit AI analýzu
      </button>
    </div>

    <!-- Add Source -->
    <div class="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
      <h2 class="text-lg font-semibold mb-4">Přidat nový zdroj</h2>
      <div class="flex gap-4">
        <input v-model="newSourceName" placeholder="Název (např. StartupJobs)" class="flex-1 border rounded-lg px-4 py-2" />
        <input v-model="newSourceUrl" placeholder="URL" class="flex-1 border rounded-lg px-4 py-2" />
        <button @click="addSource" class="bg-blue-600 text-white px-6 py-2 rounded-lg flex items-center gap-2">
          <Plus :size="20" /> Přidat
        </button>
      </div>
    </div>

    <!-- Sources List -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
      <table class="w-full text-left">
        <thead class="bg-gray-50 border-b border-gray-100">
          <tr>
            <th class="px-6 py-4 font-semibold text-gray-600">Zdroj</th>
            <th class="px-6 py-4 font-semibold text-gray-600">Poslední kontrola</th>
            <th class="px-6 py-4 font-semibold text-gray-600 text-right">Akce</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          <tr v-for="source in sources" :key="source.id" class="hover:bg-gray-50">
            <td class="px-6 py-4">
              <div class="font-medium">{{ source.name }}</div>
              <div class="text-xs text-gray-400 truncate max-w-xs">{{ source.url }}</div>
            </td>
            <td class="px-6 py-4 text-sm text-gray-500">
              {{ source.last_crawled_at ? new Date(source.last_crawled_at).toLocaleString('cs-CZ') : 'Nikdy' }}
            </td>
            <td class="px-6 py-4 text-right">
              <button @click="scrapeSource(source.id)" :disabled="loading" class="text-blue-600 hover:text-blue-800 p-2">
                <Play :size="20" />
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>