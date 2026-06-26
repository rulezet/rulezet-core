const { ref, computed, watch } = Vue

const REASONS = [
    'Plagiarism',
    'Malicious content',
    'Incorrect or misleading',
    'Inappropriate content',
    'Spam',
    'Other',
]

const ReportModal = {
    name: 'ReportModal',
    delimiters: ['[[', ']]'],
    props: {
        objectType:  { type: String, required: true },   // 'rule' | 'bundle' | 'comment'
        objectId:    { type: Number, required: true },
        objectLabel: { type: String, default: '' },
        csrfToken:   { type: String, default: '' },
    },
    emits: ['submitted'],

    setup(props, { emit }) {
        const visible  = ref(false)
        const reason   = ref('')
        const message  = ref('')
        const loading  = ref(false)
        const done     = ref(false)
        const errorMsg = ref('')

        const labelMap = { rule: 'Rule', bundle: 'Bundle', comment: 'Comment' }
        const iconMap  = { rule: 'fa-shield-halved', bundle: 'fa-layer-group', comment: 'fa-comment' }

        const typeLabel = computed(() => labelMap[props.objectType] || props.objectType)
        const typeIcon  = computed(() => iconMap[props.objectType]  || 'fa-flag')

        function open() {
            reason.value   = ''
            message.value  = ''
            loading.value  = false
            done.value     = false
            errorMsg.value = ''
            visible.value  = true
            document.body.classList.add('report-modal-open')
        }

        function close() {
            visible.value = false
            document.body.classList.remove('report-modal-open')
        }

        watch(visible, v => {
            if (!v) document.body.classList.remove('report-modal-open')
        })

        async function submit() {
            if (!reason.value || loading.value) return
            loading.value  = true
            errorMsg.value = ''
            try {
                const res = await fetch('/report/submit', {
                    method:  'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken':  props.csrfToken,
                    },
                    body: JSON.stringify({
                        object_type: props.objectType,
                        object_id:   props.objectId,
                        reason:      reason.value,
                        message:     message.value.trim() || null,
                    }),
                })
                const data = await res.json()
                if (res.ok && data.success) {
                    done.value = true
                    emit('submitted', { objectType: props.objectType, objectId: props.objectId })
                    if (window.create_message) create_message(data.message, data.toast_class || 'success')
                    setTimeout(close, 2000)
                } else {
                    errorMsg.value = data.message || 'An error occurred.'
                    if (window.create_message) create_message(data.message, data.toast_class || 'danger')
                }
            } catch (e) {
                errorMsg.value = 'Network error. Please try again.'
            } finally {
                loading.value = false
            }
        }

        return {
            visible, reason, message, loading, done, errorMsg,
            REASONS, typeLabel, typeIcon,
            open, close, submit,
        }
    },

    template: `
<span>
    <slot name="trigger" :open="open">
        <button class="btn btn-sm btn-outline-danger report-modal-trigger" @click.prevent.stop="open" title="Report">
            <i class="fa-solid fa-flag me-1"></i>Report
        </button>
    </slot>

    <teleport to="body">
        <transition name="report-modal-fade">
            <div v-if="visible" class="report-modal-backdrop" @click.self="close">
                <div class="report-modal-dialog" role="dialog" aria-modal="true" :aria-label="'Report ' + typeLabel">

                    <!-- Header -->
                    <div class="report-modal-header">
                        <div class="report-modal-header__icon">
                            <i class="fa-solid fa-flag"></i>
                        </div>
                        <div class="report-modal-header__body">
                            <div class="report-modal-header__title">Report [[ typeLabel ]]</div>
                            <div v-if="objectLabel" class="report-modal-header__sub text-truncate">[[ objectLabel ]]</div>
                        </div>
                        <button class="report-modal-close" @click="close" aria-label="Close">
                            <i class="fa-solid fa-xmark"></i>
                        </button>
                    </div>

                    <!-- Success state -->
                    <div v-if="done" class="report-modal-success">
                        <i class="fa-solid fa-circle-check report-modal-success__icon"></i>
                        <div class="report-modal-success__title">Report submitted</div>
                        <div class="report-modal-success__sub">Our team will review it shortly. Thank you.</div>
                    </div>

                    <!-- Form -->
                    <div v-else class="report-modal-body">
                        <div class="report-modal-section-label">Why are you reporting this?</div>
                        <div class="report-modal-reasons">
                            <label
                                v-for="r in REASONS"
                                :key="r"
                                class="report-modal-reason"
                                :class="{ 'is-selected': reason === r }"
                            >
                                <input type="radio" :value="r" v-model="reason" class="visually-hidden">
                                [[ r ]]
                            </label>
                        </div>

                        <div class="report-modal-section-label mt-3">Additional details <span class="text-muted">(optional)</span></div>
                        <textarea
                            class="report-modal-textarea"
                            v-model="message"
                            placeholder="Describe the issue…"
                            maxlength="500"
                            rows="3"
                        ></textarea>
                        <div class="report-modal-char-count">[[ message.length ]]/500</div>

                        <div v-if="errorMsg" class="report-modal-error">
                            <i class="fa-solid fa-triangle-exclamation me-1"></i>[[ errorMsg ]]
                        </div>

                        <div class="report-modal-footer">
                            <button class="btn btn-sm btn-outline-secondary" @click="close">Cancel</button>
                            <button
                                class="btn btn-sm btn-danger"
                                @click="submit"
                                :disabled="!reason || loading"
                            >
                                <span v-if="loading" class="spinner-border spinner-border-sm me-1"></span>
                                <i v-else class="fa-solid fa-flag me-1"></i>
                                Submit report
                            </button>
                        </div>
                    </div>

                </div>
            </div>
        </transition>
    </teleport>
</span>
`,
}

export default ReportModal
