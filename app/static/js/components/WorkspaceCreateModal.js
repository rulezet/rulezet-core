/**
 * WorkspaceCreateModal — the "New Workspace" window (name, description, icon,
 * color) of the Workspaces page, reusable anywhere: Workspaces page and the
 * "Add to a workspace" picker (WorkspacePicker).
 *
 * Props: csrfToken
 * Exposes: open()
 * Emits: created(workspace)   (workspace = Workspace.to_json())
 * Backend: POST /workspace/create
 */
import IconPicker from '/static/js/tags/utils/iconPicker.js'
import { create_message } from '/static/js/toaster.js'
const { ref, onMounted, onBeforeUnmount } = Vue

let seq = 0
const blank = () => ({ name: '', description: '', icon: 'fa-folder', color: '#0d6efd' })

const WorkspaceCreateModal = {
    name: 'WorkspaceCreateModal',
    delimiters: ['[[', ']]'],
    components: { 'icon-picker': IconPicker },
    props: {
        csrfToken: { type: String, default: '' },
    },
    emits: ['created'],
    setup(props, { emit, expose }) {
        const modalId = `ws-create-modal-${++seq}`
        const form = ref(blank())
        const saving = ref(false)
        let modal = null

        onMounted(() => { modal = new bootstrap.Modal(document.getElementById(modalId)) })
        onBeforeUnmount(() => { modal?.dispose() })

        function open() {
            form.value = blank()
            modal?.show()
        }

        async function save() {
            const name = form.value.name.trim()
            if (!name || saving.value) return
            saving.value = true
            try {
                const csrf = document.getElementById('csrf_token')?.value || props.csrfToken
                const res = await fetch('/workspace/create', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
                    body: JSON.stringify({ ...form.value, name }),
                })
                const data = await res.json().catch(() => ({}))
                if (!res.ok || !data.success || !data.workspace) {
                    create_message(data.message || `Failed to create workspace (HTTP ${res.status})`, 'danger')
                    return
                }
                modal?.hide()
                create_message(`Workspace "${name}" created`, 'success')
                emit('created', data.workspace)
            } catch {
                create_message('Failed to create workspace', 'danger')
            } finally {
                saving.value = false
            }
        }

        expose({ open })
        return { modalId, form, saving, save }
    },
    template: `
    <teleport to="body">
    <div class="modal fade ws-create-modal" :id="modalId" tabindex="-1" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content border-0 shadow-lg rounded-4" style="background:var(--card-bg-color);">
            <div class="modal-header border-0 pb-0 pt-4 px-4">
                <div class="d-flex align-items-center gap-3">
                    <div class="rounded-circle d-flex align-items-center justify-content-center shadow-sm"
                         :style="{ backgroundColor: form.color, width: '52px', height: '52px', color: 'white', transition: 'all 0.3s ease' }">
                        <i :class="['fa-solid', form.icon || 'fa-folder']" style="font-size:1.4rem;"></i>
                    </div>
                    <div>
                        <h5 class="modal-title fw-bold mb-0">New Workspace</h5>
                        <p class="text-muted small mb-0">Organise your rules by category or project</p>
                    </div>
                </div>
                <button type="button" class="btn-close shadow-none" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body p-4">
                <div class="row g-3">
                    <div class="col-12">
                        <label class="form-label fw-bold small text-muted text-uppercase mb-1">Name <span class="text-danger">*</span></label>
                        <div class="input-group shadow-sm rounded-3">
                            <span class="input-group-text border-0 bg-light">
                                <i class="fa-solid fa-signature text-muted"></i>
                            </span>
                            <input type="text" class="form-control border-0 bg-light"
                                   v-model="form.name" placeholder="e.g. Ransomware Detection"
                                   maxlength="100" style="height:45px;" @keydown.enter.prevent="save">
                        </div>
                    </div>
                    <div class="col-12">
                        <label class="form-label fw-bold small text-muted text-uppercase mb-1">Description</label>
                        <textarea class="form-control border-0 bg-light rounded-3 p-3 shadow-sm"
                                  v-model="form.description" rows="2"
                                  placeholder="Optional description…"></textarea>
                    </div>
                    <div class="col-md-7">
                        <icon-picker v-model="form.icon"></icon-picker>
                    </div>
                    <div class="col-md-5">
                        <label class="form-label fw-bold small text-muted text-uppercase mb-1">Color</label>
                        <div class="d-flex align-items-center bg-light rounded-3 p-1 shadow-sm">
                            <input type="color" class="form-control form-control-color border-0 bg-transparent"
                                   v-model="form.color" style="width:45px;height:35px;">
                            <input type="text" class="form-control border-0 bg-transparent py-0 small text-muted font-monospace"
                                   v-model="form.color">
                        </div>
                    </div>
                </div>
            </div>
            <div class="modal-footer border-0 p-4 pt-0">
                <button type="button" class="btn btn-link text-decoration-none fw-bold text-muted px-4"
                        data-bs-dismiss="modal">Cancel</button>
                <button type="button" class="btn btn-primary rounded-pill px-5 fw-bold shadow"
                        @click="save" :disabled="!form.name.trim() || saving">
                    <i class="fa-solid me-2" :class="saving ? 'fa-spinner fa-spin' : 'fa-circle-check'"></i>Create
                </button>
            </div>
        </div>
    </div>
    </div>
    </teleport>`,
}
export default WorkspaceCreateModal
