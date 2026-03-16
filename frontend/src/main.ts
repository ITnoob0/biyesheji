import axios from 'axios'
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

import App from './App.vue'
import router from './router'
import { clearSessionAuth, getSessionToken } from './utils/sessionAuth'

axios.interceptors.request.use(
  config => {
    const token = getSessionToken()

    if (token) {
      config.headers = config.headers ?? {}
      config.headers.Authorization = `Bearer ${token}`
    }

    return config
  },
  error => Promise.reject(error),
)

axios.interceptors.response.use(
  response => response,
  error => {
    if (error?.response?.status === 401) {
      clearSessionAuth()

      if (router.currentRoute.value.name !== 'login') {
        router.replace({ name: 'login' })
      }
    }

    return Promise.reject(error)
  },
)

const app = createApp(App)

for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.use(createPinia())
app.use(router)
app.use(ElementPlus)

app.mount('#app')
