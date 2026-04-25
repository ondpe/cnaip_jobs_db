import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import './style.css'
import App from './App.vue'
import JobBoard from './components/JobBoard.vue'
import AdminView from './views/AdminView.vue'
import LoginView from './views/LoginView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: JobBoard },
    { path: '/login', component: LoginView },
    { 
      path: '/admin', 
      component: AdminView,
      beforeEnter: (to, from, next) => {
        const user = sessionStorage.getItem('admin_user')
        const pass = sessionStorage.getItem('admin_pass')
        if (!user || !pass) next('/login')
        else next()
      }
    }
  ]
})

const app = createApp(App)
app.use(router)
app.mount('#app')