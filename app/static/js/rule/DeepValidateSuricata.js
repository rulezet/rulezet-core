/**
 * DeepValidateSuricata.js — on-demand real-engine check for Suricata rule
 * content (issue #61 suggestion #1). See
 * docs/design/suricata_language_server_integration.md. Shared by the
 * create-rule form (both Manual and Parse tabs) and the edit-rule form —
 * shown only when format === 'suricata' and this instance has opted in
 * (window.__deep_validation_available, set once per page load).
 *
 * Props:
 *   format   String — current format select value
 *   content  String — current rule content (v-model'd editor value)
 *
 * Never runs automatically — only on explicit button click, since a real
 * Suricata engine run is ~0.5-5s per call.
 */
const { ref, computed } = Vue

export default {
    name: 'DeepValidateSuricata',
    delimiters: ['[[', ']]'],
    props: {
        format:  { type: String, default: '' },
        content: { type: String, default: '' },
    },
    setup(props) {
        const validating = ref(false)
        const result      = ref(null)

        const visible = computed(() =>
            window.__deep_validation_available && (props.format || '').toLowerCase() === 'suricata'
        )

        async function run() {
            if (!props.content || !props.content.trim()) return
            validating.value = true
            result.value = null
            try {
                const res = await fetch('/rule/deep_validate_content', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': document.getElementById('csrf_token')?.value
                            || document.querySelector('input[name="csrf_token"]')?.value || '',
                    },
                    body: JSON.stringify({ content: props.content, format: props.format }),
                })
                const data = await res.json()
                result.value = data.success ? data : { error: data.message || 'Request failed.' }
            } catch (e) {
                result.value = { error: String(e) }
            } finally {
                validating.value = false
            }
        }

        return { validating, result, visible, run }
    },
    template: `
    <div v-if="visible" class="d-flex flex-column gap-2 mt-2">
        <div>
            <button type="button" class="btn btn-sm btn-outline-primary rounded-pill px-3"
                    :disabled="validating || !content.trim()" @click="run">
                <i class="fa-solid" :class="validating ? 'fa-spinner fa-spin' : 'fa-microscope'"></i>
                [[ validating ? 'Running…' : 'Deep validate with Suricata engine' ]]
            </button>
        </div>
        <div v-if="result">
            <div v-if="result.error" class="text-danger small">
                <i class="fa-solid fa-circle-exclamation me-1"></i>[[ result.error ]]
            </div>
            <div v-else-if="result.ok && result.diagnostics.length === 0" class="text-success small">
                <i class="fa-solid fa-circle-check me-1"></i>Passed — the real Suricata engine accepted this rule.
            </div>
            <div v-else>
                <div v-for="(diag, idx) in result.diagnostics" :key="idx"
                     class="small mb-2 p-2 rounded-3"
                     :style="diag.severity === 1 ? 'background:rgba(220,53,69,.08);' : 'background:rgba(255,193,7,.1);'">
                    <span class="badge" :class="diag.severity === 1 ? 'bg-danger' : 'bg-warning text-dark'" style="font-size:.65rem;">
                        [[ diag.severity === 1 ? 'ERROR' : 'WARNING' ]]
                    </span>
                    <span class="ms-1">Line [[ diag.range.start.line + 1 ]]:</span>
                    [[ diag.message ]]
                </div>
            </div>
        </div>
    </div>
    `,
}
