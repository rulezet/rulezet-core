/**
 * ollamaServerCard.js — which Ollama server every AI agent talks to (Models &
 * Security page). Empty fields fall back to config.py's OLLAMA_URL /
 * OLLAMA_MODEL. A non-local URL needs the explicit "Allow remote server"
 * opt-in, since rule/user content is then sent to that host.
 *
 * Props:
 *   csrfToken  String (required)
 *
 * Emits:
 *   saved  — after a successful save, so the page can refresh model lists.
 */

import { create_message } from '/static/js/toaster.js'

const { ref, computed, onMounted } = Vue

const PRIVATE_V4 = /^(127\.|10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)/

function isLocalUrl(url) {
    let host = ''
    try { host = new URL(url).hostname.toLowerCase() } catch (e) { return false }
    return host === 'localhost' || host.endsWith('.local') || PRIVATE_V4.test(host)
}

export default {
    name: 'OllamaServerCard',
    delimiters: ['[[', ']]'],

    props: {
        csrfToken: { type: String, required: true },
    },

    emits: ['saved'],

    template: `
        <div class="card border-0 shadow-sm rounded-4 mb-4">
            <div class="card-body p-4">
                <div class="d-flex align-items-center justify-content-between flex-wrap gap-2 mb-1">
                    <div class="d-flex align-items-center gap-2">
                        <div style="width:3px;height:14px;background:#0d6efd;border-radius:2px;flex-shrink:0;"></div>
                        <span class="fw-bold" style="font-size:.75rem;text-transform:uppercase;letter-spacing:.07em;color:var(--subtle-text-color);">
                            <i class="fa-solid fa-server me-1"></i>Ollama server
                        </span>
                    </div>
                    <span v-if="effective.url" class="badge rounded-pill"
                          :class="effective.is_local ? 'bg-success-subtle text-success-emphasis' : 'bg-warning-subtle text-warning-emphasis'">
                        <i class="fa-solid me-1" :class="effective.is_local ? 'fa-house' : 'fa-globe'"></i>
                        [[ effective.is_local ? 'Local' : 'Remote' ]] · [[ effective.url ]]
                    </span>
                </div>
                <small class="text-muted d-block mb-3">
                    The server every AI feature talks to. Leave a field empty to use the value from <code>config.py</code> / <code>.env</code>
                    ([[ fallback.url || 'http://localhost:11434' ]], [[ fallback.default_model || '—' ]]).
                </small>

                <div v-if="loading" class="text-center py-3 text-muted"><i class="fa-solid fa-spinner fa-spin"></i></div>
                <template v-else>
                    <div class="row g-3">
                        <div class="col-md-7">
                            <label class="form-label small fw-semibold mb-1">Server URL</label>
                            <input type="text" class="form-control form-control-sm font-monospace" v-model.trim="url"
                                   :placeholder="fallback.url || 'http://localhost:11434'">
                        </div>
                        <div class="col-md-5">
                            <label class="form-label small fw-semibold mb-1">Default model</label>
                            <input type="text" class="form-control form-control-sm font-monospace" v-model.trim="defaultModel"
                                   list="ollama-server-models" :placeholder="fallback.default_model || 'qwen2.5:1.5b'">
                            <datalist id="ollama-server-models">
                                <option v-for="m in testedModels" :key="m" :value="m"></option>
                            </datalist>
                            <div class="form-text" style="font-size:.72rem;">Used by every agent that has no model of its own.</div>
                        </div>
                    </div>

                    <div v-if="isRemote" class="rounded-3 border p-3 mt-3" style="background:var(--light-bg-color);">
                        <div class="form-check mb-1">
                            <input class="form-check-input" type="checkbox" id="ollama-remote-allowed" v-model="remoteAllowed">
                            <label class="form-check-label small fw-semibold" for="ollama-remote-allowed">Allow remote server</label>
                        </div>
                        <div class="small text-muted">
                            <i class="fa-solid fa-triangle-exclamation text-warning me-1"></i>
                            [[ remoteHost ]] is not on this machine or a private network. Rule content and user
                            messages will be sent to it<span v-if="url.startsWith('http://')">, unencrypted over plain HTTP</span>.
                            Only enable this for a server you trust.
                        </div>
                    </div>

                    <div v-if="testResult" class="alert py-2 px-3 mt-3 mb-0" style="font-size:.82rem;"
                         :class="testResult.success ? 'alert-success' : 'alert-danger'">
                        <template v-if="testResult.success">
                            <i class="fa-solid fa-circle-check me-1"></i>Reachable — [[ testResult.models.length ]] model(s):
                            <span class="font-monospace">[[ testResult.models.join(', ') || '—' ]]</span>
                            <div v-if="defaultModel && !testResult.models.includes(defaultModel)" class="mt-1">
                                <i class="fa-solid fa-triangle-exclamation me-1"></i>
                                "[[ defaultModel ]]" isn't installed on this server.
                            </div>
                        </template>
                        <template v-else>
                            <i class="fa-solid fa-circle-xmark me-1"></i>[[ testResult.error ]]
                        </template>
                    </div>

                    <div class="d-flex justify-content-end gap-2 mt-3">
                        <button class="btn btn-sm btn-outline-secondary rounded-pill px-3" :disabled="testing || (isRemote && !remoteAllowed)" @click="testConnection">
                            <i class="fa-solid me-1" :class="testing ? 'fa-spinner fa-spin' : 'fa-plug'"></i>Test connection
                        </button>
                        <button class="btn btn-sm btn-primary rounded-pill px-3" :disabled="saving || (isRemote && !remoteAllowed)" @click="save">
                            <i class="fa-solid me-1" :class="saving ? 'fa-spinner fa-spin' : 'fa-floppy-disk'"></i>Save
                        </button>
                    </div>
                </template>
            </div>
        </div>
    `,

    setup(props, { emit }) {
        const loading       = ref(true)
        const saving        = ref(false)
        const testing       = ref(false)
        const url           = ref('')
        const defaultModel  = ref('')
        const remoteAllowed = ref(false)
        const effective     = ref({})
        const fallback      = ref({})
        const testResult    = ref(null)

        const testedModels = computed(() => testResult.value?.success ? testResult.value.models : [])
        const isRemote     = computed(() => !!url.value && !isLocalUrl(url.value))
        const remoteHost   = computed(() => {
            try { return new URL(url.value).hostname } catch (e) { return url.value }
        })

        function apply(data) {
            url.value           = data.ollama_url || ''
            defaultModel.value  = data.ollama_default_model || ''
            remoteAllowed.value = !!data.ollama_remote_allowed
            effective.value     = data.effective || {}
            fallback.value      = data.config_fallback || {}
        }

        async function load() {
            loading.value = true
            try {
                const res = await fetch('/ai/admin/ollama_settings')
                apply(await res.json())
            } catch (e) {
                create_message('Could not load Ollama settings: ' + e, 'danger-subtle')
            } finally {
                loading.value = false
            }
        }

        function payload() {
            return JSON.stringify({
                ollama_url:            url.value,
                ollama_default_model:  defaultModel.value,
                ollama_remote_allowed: isRemote.value && remoteAllowed.value,
            })
        }

        async function testConnection() {
            testing.value = true
            testResult.value = null
            try {
                const res = await fetch('/ai/admin/ollama_settings/test', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': props.csrfToken },
                    body: payload(),
                })
                const data = await res.json()
                testResult.value = data.success ? data : { success: false, error: data.error || 'Test failed' }
            } catch (e) {
                testResult.value = { success: false, error: 'Network error: ' + e }
            } finally {
                testing.value = false
            }
        }

        async function save() {
            saving.value = true
            try {
                const res = await fetch('/ai/admin/ollama_settings', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': props.csrfToken },
                    body: payload(),
                })
                const data = await res.json()
                if (data.success) {
                    apply(data)
                    create_message('Ollama server saved.', 'success-subtle')
                    emit('saved')
                } else {
                    create_message(data.error || 'Save failed', 'danger-subtle')
                }
            } catch (e) {
                create_message('Network error: ' + e, 'danger-subtle')
            } finally {
                saving.value = false
            }
        }

        onMounted(load)

        return {
            loading, saving, testing, url, defaultModel, remoteAllowed, effective, fallback,
            testResult, testedModels, isRemote, remoteHost, testConnection, save,
        }
    },
}
