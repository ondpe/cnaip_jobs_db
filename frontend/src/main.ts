import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import './style.css'
import App from './App.vue'
import JobBoard from './components/JobBoard.vue'
import AdminView from './views/AdminView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: JobBoard },
    { path: '/admin', component: AdminView }
  ]
})

const app = createApp(App)
app.use(router)
app.mount('#app')