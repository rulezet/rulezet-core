/**
 * request-builder.js — In-app HTTP request builder (mini Postman).
 *
 * Props:
 *   default-url    String  Pre-fill the URL input
 *   default-method String  Pre-fill the method (default: 'GET')
 *   default-body   String  Pre-fill the request body
 *
 * Events:
 *   response({ status, ok, time_ms, body, content_type })
 */

const { ref, computed } = Vue

const METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']

const METHOD_META = {
    GET:    { color: '#22c55e', bg: 'rgba(34,197,94,.12)' },
    POST:   { color: '#3b82f6', bg: 'rgba(59,130,246,.12)' },
    PUT:    { color: '#f59e0b', bg: 'rgba(245,158,11,.12)' },
    PATCH:  { color: '#a855f7', bg: 'rgba(168,85,247,.12)' },
    DELETE: { color: '#ef4444', bg: 'rgba(239,68,68,.12)' },
}

function get_csrf() {
    return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || ''
}

export default {
    name: 'RequestBuilder',

    props: {
        defaultUrl:    { type: String, default: '' },
        defaultMethod: { type: String, default: 'GET' },
        defaultBody:   { type: String, default: '' },
    },

    emits: ['response'],

    setup(props, { emit }) {
        const method       = ref(props.defaultMethod.toUpperCase())
        const url          = ref(props.defaultUrl)
        const body         = ref(props.defaultBody)
        const loading      = ref(false)
        const response     = ref(null)
        const error_msg    = ref('')
        const active_tab   = ref('headers')
        const method_open  = ref(false)

        const headers = ref([
            { key: 'Content-Type', value: 'application/json', enabled: true },
            { key: 'X-CSRFToken',  value: get_csrf(),          enabled: true },
            { key: '',             value: '',                   enabled: true },
        ])

        const show_body    = computed(() => ['POST', 'PUT', 'PATCH'].includes(method.value))
        const method_style = computed(() => METHOD_META[method.value] || METHOD_META.GET)
        const active_header_count = computed(() =>
            headers.value.filter(h => h.enabled && h.key.trim()).length
        )

        const response_json = computed(() => {
            if (!response.value?.body) return ''
            try { return JSON.stringify(JSON.parse(response.value.body), null, 2) }
            catch { return response.value.body }
        })

        const is_json = computed(() => {
            return (response.value?.content_type || '').includes('json')
        })

        function select_method(m) {
            method.value = m
            method_open.value = false
        }

        function add_header() {
            headers.value.push({ key: '', value: '', enabled: true })
        }

        function remove_header(i) {
            headers.value.splice(i, 1)
        }

        async function send() {
            const target = url.value.trim()
            if (!target) { error_msg.value = 'URL is required'; return }
            error_msg.value = ''
            loading.value   = true
            response.value  = null

            const active_headers = headers.value
                .filter(h => h.enabled && h.key.trim())
                .reduce((acc, h) => { acc[h.key.trim()] = h.value; return acc }, {})

            const opts = { method: method.value, headers: active_headers, credentials: 'same-origin' }
            if (show_body.value && body.value.trim()) opts.body = body.value

            const t0 = Date.now()
            try {
                const res  = await fetch(target, opts)
                const text = await res.text()
                response.value = {
                    status:       res.status,
                    ok:           res.ok,
                    time_ms:      Date.now() - t0,
                    body:         text,
                    content_type: res.headers.get('content-type') || '',
                }
                emit('response', response.value)
            } catch (err) {
                error_msg.value = String(err)
            }
            loading.value = false
        }

        function copy_response() {
            navigator.clipboard?.writeText(response_json.value || response.value?.body || '')
        }

        return {
            method, url, body, loading, response, error_msg,
            active_tab, method_open, headers,
            show_body, method_style, active_header_count,
            response_json, is_json,
            select_method, add_header, remove_header, send, copy_response,
            METHODS, METHOD_META,
        }
    },

    template: `
<div class="rb" @click.self="method_open = false">

    <!-- ── URL bar ─────────────────────────────────────────── -->
    <div class="rb-url-bar">

        <!-- Method dropdown -->
        <div class="rb-method-wrap" :class="{ 'rb-method-wrap--open': method_open }">
            <button
                class="rb-method-btn"
                :style="{ color: method_style.color }"
                @click.stop="method_open = !method_open">
                {{ method }}
                <i class="fas fa-chevron-down rb-method-chevron"></i>
            </button>
            <div v-if="method_open" class="rb-method-drop" @click.stop>
                <button
                    v-for="m in METHODS"
                    :key="m"
                    class="rb-method-opt"
                    :class="{ 'is-active': m === method }"
                    :style="{ color: METHOD_META[m].color }"
                    @click="select_method(m)">
                    {{ m }}
                </button>
            </div>
        </div>

        <div class="rb-url-divider"></div>

        <input
            v-model="url"
            class="rb-url-input"
            type="text"
            placeholder="https:// or /api/…"
            spellcheck="false"
            @keydown.enter="send">

        <button class="rb-send-btn" :disabled="loading" @click="send">
            <i v-if="loading" class="fas fa-spinner fa-spin"></i>
            <i v-else class="fas fa-arrow-right"></i>
            {{ loading ? 'Sending…' : 'Send' }}
        </button>
    </div>

    <!-- ── Error ────────────────────────────────────────────── -->
    <div v-if="error_msg" class="rb-error">
        <i class="fas fa-circle-xmark me-2"></i>{{ error_msg }}
    </div>

    <!-- ── Tab bar ──────────────────────────────────────────── -->
    <div class="rb-tab-bar">
        <button
            class="rb-tab"
            :class="{ 'rb-tab--active': active_tab === 'headers' }"
            @click="active_tab = 'headers'">
            Headers
            <span class="rb-tab-count">{{ active_header_count }}</span>
        </button>
        <button
            v-if="show_body"
            class="rb-tab"
            :class="{ 'rb-tab--active': active_tab === 'body' }"
            @click="active_tab = 'body'">
            Body
        </button>
    </div>

    <!-- ── Headers panel ────────────────────────────────────── -->
    <div v-show="active_tab === 'headers'" class="rb-panel">
        <div class="rb-headers-grid">
            <div v-for="(h, i) in headers" :key="i" class="rb-hrow">
                <label class="rb-hrow-check">
                    <input type="checkbox" v-model="h.enabled">
                </label>
                <input
                    v-model="h.key"
                    class="rb-hkey"
                    placeholder="Key"
                    type="text"
                    spellcheck="false">
                <input
                    v-model="h.value"
                    class="rb-hval"
                    placeholder="Value"
                    type="text"
                    spellcheck="false">
                <button class="rb-hdel" @click="remove_header(i)" title="Remove">
                    <i class="fas fa-xmark"></i>
                </button>
            </div>
        </div>
        <button class="rb-add-row" @click="add_header">
            <i class="fas fa-plus"></i> Add header
        </button>
    </div>

    <!-- ── Body panel ───────────────────────────────────────── -->
    <div v-if="show_body && active_tab === 'body'" class="rb-panel">
        <textarea
            v-model="body"
            class="rb-body-editor"
            placeholder='{"key": "value"}'
            spellcheck="false"
            rows="7">
        </textarea>
    </div>

    <!-- ── Response ─────────────────────────────────────────── -->
    <div v-if="response" class="rb-response">
        <div class="rb-res-bar">
            <span :class="['rb-status', response.ok ? 'rb-status--ok' : 'rb-status--err']">
                <span class="rb-status-dot"></span>
                {{ response.status }}
            </span>
            <span class="rb-res-time">{{ response.time_ms }}ms</span>
            <span class="rb-res-ct">{{ response.content_type }}</span>
            <button class="rb-res-copy" @click="copy_response" title="Copy response">
                <i class="fas fa-copy"></i>
            </button>
        </div>
        <pre class="rb-res-body" :class="{ 'rb-res-body--json': is_json }">{{ response_json || response.body }}</pre>
    </div>

</div>
    `,
}
