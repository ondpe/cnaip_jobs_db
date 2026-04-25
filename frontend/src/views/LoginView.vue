<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { Lock, User, LogIn, AlertCircle, Loader2 } from 'lucide-vue-next'

const router = useRouter()
const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

const handleLogin = async () => {
  loading.value = true
  error.value = ''
  
  try {
    // Ověříme údaje pokusem o načtení chráněného endpointu
    const auth = { username: username.value, password: password.value }
    await axios.get('/api/admin/settings/gemini-key', { auth })
    
    // Pokud OK, uložíme do session (zmizí po zavření prohlížeče)
    sessionStorage.setItem('admin_user', username.value)
    sessionStorage.setItem('admin_pass', password.value)
    
    router.push('/admin')
  } catch (err: any) {
    error.value = 'Neplatné jméno nebo heslo.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen bg-gray-50 flex items-center justify-center p-6">
    <div class="max-w-md w-full bg-white rounded-3xl shadow-xl shadow-blue-900/5 p-10 border border-gray-100">
      <div class="text-center mb-8">
        <div class="w-16 h-16 bg-[#002B5C] rounded-2xl flex items-center justify-center mx-auto mb-4">
          <Lock class="text-white" :size="32" />
        </div>
        <h1 class="text-2xl font-black text-[#002B5C] tracking-tighter uppercase">Admin Přihlášení</h1>
        <p class="text-[10px] font-bold text-gray-400 uppercase tracking-widest mt-2">Zadejte své údaje pro správu</p>
      </div>

      <form @submit.prevent="handleLogin" class="space-y-6">
        <div>
          <label class="block text-[10px] font-black text-gray-400 uppercase tracking-widest mb-2">Uživatelské jméno</label>
          <div class="relative">
            <User class="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" :size="18" />
            <input 
              v-model="username" 
              type="text" 
              required
              class="w-full pl-12 pr-4 py-4 bg-gray-50 border-none rounded-2xl text-sm focus:ring-2 focus:ring-[#002B5C]/10 transition-all outline-none"
              placeholder="Jméno"
            >
          </div>
        </div>

        <div>
          <label class="block text-[10px] font-black text-gray-400 uppercase tracking-widest mb-2">Heslo</label>
          <div class="relative">
            <Lock class="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" :size="18" />
            <input 
              v-model="password" 
              type="password" 
              required
              class="w-full pl-12 pr-4 py-4 bg-gray-50 border-none rounded-2xl text-sm focus:ring-2 focus:ring-[#002B5C]/10 transition-all outline-none"
              placeholder="Heslo"
            >
          </div>
        </div>

        <div v-if="error" class="p-4 bg-red-50 text-red-600 text-xs rounded-2xl flex items-start gap-3 border border-red-100 animate-in fade-in slide-in-from-top-2">
          <AlertCircle :size="18" class="shrink-0" /> {{ error }}
        </div>

        <button 
          type="submit" 
          :disabled="loading"
          class="w-full bg-[#002B5C] text-white font-black py-4 rounded-2xl shadow-lg hover:bg-blue-900 transition-all disabled:opacity-50 flex items-center justify-center gap-2"
        >
          <Loader2 v-if="loading" class="animate-spin" :size="20" />
          <LogIn v-else :size="20" />
          {{ loading ? 'OVĚŘUJI...' : 'PŘIHLÁSIT SE' }}
        </button>
      </form>
      
      <div class="mt-8 text-center">
        <router-link to="/" class="text-xs font-bold text-gray-400 hover:text-[#002B5C] transition-colors">
          Zpět na hlavní web
        </router-link>
      </div>
    </div>
  </div>
</template>