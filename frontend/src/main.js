import { createApp } from 'vue'
import { createPinia } from 'pinia'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import axios from 'axios'
// 按需引入:ElMessage / ElMessageBox 为显式 import,需手动引入其样式
// (resolver 只会为模板组件与 auto-import 的 API 注入样式)
import 'element-plus/es/components/message/style/css'
import 'element-plus/es/components/message-box/style/css'

import App from './App.vue'
import router from './router'
import { getBackendBaseUrl } from './utils/runtime'
import './styles/index.scss'

axios.defaults.baseURL = getBackendBaseUrl()

const app = createApp(App)

// 图标全局注册:模板中 :icon="'VideoPlay'" 等字符串形式依赖全局解析
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.use(createPinia())
app.use(router)

app.mount('#app')
