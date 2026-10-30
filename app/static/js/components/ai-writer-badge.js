/**
 * ai-writer-badge.js — the "which AI" badge (logo, name, model) from a model / author string,
 * e.g. "claude-opus-5-5", "qwen2.5:3b", "llama3.1:8b", "gpt-4o". Same list as the server
 * (setting rule.ai_writers, fetched once for the whole page). An unknown model still shows, generic.
 *
 * Props: text (the model or author string), label (optional prefix shown before the badge)
 * CSS:   css/components/ai-writer-badge.css
 */
const { ref, computed } = Vue;

let writersPromise = null;
const writers = ref([]);
function loadWriters() {
    if (!writersPromise) {
        writersPromise = fetch('/api/config/settings/rule.ai_writers')
            .then(r => (r.ok ? r.json() : null))
            .then(d => { writers.value = (d && d.value) || []; })
            .catch(() => {});
    }
    return writersPromise;
}

export default {
    name: 'AiWriterBadge',
    delimiters: ['[[', ']]'],
    props: { text: { type: String, default: '' }, label: { type: String, default: '' } },
    setup(props) {
        loadWriters();
        const match = computed(() => {
            const t = (props.text || '').replace(/_/g, ' ');
            if (!t) return null;
            for (const w of writers.value) {
                try {
                    if (!new RegExp(w.pattern, 'i').test(t)) continue;
                    return { ...w, model: props.text };
                } catch { /* bad pattern in the setting: skip it */ }
            }
            return { key: 'ai', label: 'AI', vendor: null, logo: null, color: '#6f42c1', model: props.text };
        });
        return { match };
    },
    template: `
    <span v-if="match" class="ai-writer-badge" :style="{ '--ai-color': match.color }"
          :data-rz-pop-title="match.label + (match.vendor ? ' — ' + match.vendor : '')" :data-rz-pop-text="'Model: ' + match.model">
        <img v-if="match.logo" :src="match.logo" alt="" class="ai-writer-badge__logo">
        <span v-else class="ai-writer-badge__initial">[[ match.label.charAt(0) ]]</span>
        <span class="ai-writer-badge__name">[[ match.label ]]</span>
        <span v-if="match.model && match.model.toLowerCase() !== match.label.toLowerCase()" class="ai-writer-badge__model">[[ match.model ]]</span>
    </span>`,
};
