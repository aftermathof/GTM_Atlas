import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import Home from './pages/Home.vue'
import Learn from './pages/Learn.vue'
import Interviews from './pages/Interviews.vue'
import Career from './pages/Career.vue'
import Utility from './pages/Utility.vue'
import Glossary from './pages/Glossary.vue'
import './style.css'

const router = createRouter({ history: createWebHistory(), scrollBehavior: (to, from, savedPosition) => {
  if (savedPosition) return savedPosition
  if (to.path === from.path) return false
  return { top: 0 }
}, routes: [
  { path: '/', component: Home },
  { path: '/glossary', component: Glossary },
  { path: '/learn/:slug?', component: Learn },
  { path: '/library', redirect: '/learn' },
  { path: '/jobs', redirect: '/learn?kind=jd' },
  { path: '/interviews/:pathMatch(.*)*', component: Interviews },
  { path: '/career/:pathMatch(.*)*', component: Career },
  { path: '/career/history', redirect: '/history' },
  { path: '/:page(history|settings|login|search)', component: Utility },
  { path: '/:pathMatch(.*)*', redirect: '/' }
] })
createApp(App).use(router).mount('#app')
