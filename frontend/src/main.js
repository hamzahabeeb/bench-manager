import { createApp } from 'vue'
import router from './router/index.js'
import App from './App.vue'

// frappe-ui: FrappeUI is a named export (default re-exported under that name)
import { FrappeUI, setConfig, frappeRequest } from 'frappe-ui'
import 'frappe-ui/style.css'

// Point frappe-ui resource calls at our FastAPI backend
setConfig('resourceFetcher', frappeRequest)

const app = createApp(App)
app.use(router)
app.use(FrappeUI, { socketio: false }) // disable socketio — we don't have frappe socketio server
app.mount('#app')
