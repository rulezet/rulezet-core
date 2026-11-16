/**
 * TagSuggest — Rulezy proposes taxonomy / galaxy tags (6th AI integration).
 * Same component on rules and bundles.
 *
 *   1. POST /<kind>/suggest_tags     — instant matches from the tag trie
 *   2. POST /<kind>/ai_suggest_tags  — (AI users) the model keeps the relevant
 *      ones with a reason; they come first, the other matches stay below.
 * Nothing is added by itself: a click (or "Add all") adds to v-model.
 *
 * Props:
 *   modelValue  Array of tag objects (same as TagInput's v-model)
 *   kind        'rule' (default) — reads title / description / to_string /
 *               format from the enclosing <form>, works before saving
 *               'bundle' — the server reads the saved bundle (targetId)
 *   targetId    rule id (optional) / bundle id (required for bundles)
 *   csrf        CSRF token
 * Rulezy shows when the instance's mascot is on (mascot.js), icons otherwise.
 */
import { getTextColor, mapIcon } from '/static/js/tags/utils/galaxie.js';
import { MASCOT_ENABLED } from '/static/js/components/mascot.js';

const RULEZY = '/static/images/rulezy/';
// Rulezy pose / fallback icon per state
const MOODS = {
    idle:     { img: 'lookup.png',      icon: 'fa-tags' },
    scanning: { img: 'db.png',          icon: 'fa-magnifying-glass' },
    thinking: { img: 'reflexion.png',   icon: 'fa-brain' },
    found:    { img: 'analyseRule.png', icon: 'fa-wand-magic-sparkles' },
    empty:    { img: 'armcross.png',    icon: 'fa-circle-question' },
    error:    { img: 'armcross.png',    icon: 'fa-triangle-exclamation' },
};
const CONF = {
    high:   { label: 'Strong match', icon: 'fa-circle-check' },
    medium: { label: 'Likely',       icon: 'fa-circle-half-stroke' },
    low:    { label: 'Maybe',        icon: 'fa-circle-dot' },
};
const PREVIEW = 10;

const TagSuggest = {
    props: {
        modelValue: { type: Array, default: () => [] },
        kind: { type: String, default: 'rule' },
        targetId: { type: [Number, String], default: null },
        csrf: { type: String, default: '' },
    },
    emits: ['update:modelValue'],
    delimiters: ['[[', ']]'],
    setup(props, { emit }) {
        const root = Vue.ref(null);
        const loading = Vue.ref(false);
        const aiLoading = Vue.ref(false);
        const candidates = Vue.ref([]);
        const aiPicks = Vue.ref(null);
        const aiError = Vue.ref('');
        const aiModel = Vue.ref('');
        const error = Vue.ref('');
        const aiAvailable = Vue.ref(false);
        const showAll = Vue.ref(false);
        const done = Vue.ref(false);
        const elapsed = Vue.ref(0);
        const noun = Vue.computed(() => props.kind === 'bundle' ? 'bundle' : 'rule');

        const field = (form, name) => (form?.querySelector(`[name="${name}"]`)?.value || '');
        const readBody = () => {
            const exclude_ids = props.modelValue.map(t => t.id);
            if (props.kind === 'bundle') return { bundle_id: props.targetId, exclude_ids };
            const form = root.value?.closest('form') || document;
            return {
                title: field(form, 'title'), description: field(form, 'description'),
                content: field(form, 'to_string'), format: field(form, 'format'),
                rule_id: props.targetId, exclude_ids,
            };
        };
        const post = async (url, body) => {
            const r = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': props.csrf },
                body: JSON.stringify(body),
            });
            const data = await r.json().catch(() => ({}));
            if (!r.ok || !data.ok) throw new Error(data.error || `Error ${r.status}`);
            return data;
        };

        const suggest = async () => {
            const body = readBody();
            error.value = ''; aiError.value = ''; aiPicks.value = null; aiModel.value = ''; showAll.value = false;
            loading.value = true;
            const t0 = performance.now();
            try {
                const data = await post(`/${props.kind}/suggest_tags`, body);
                elapsed.value = Math.max(1, Math.round(performance.now() - t0));
                candidates.value = data.candidates;
                aiAvailable.value = data.ai_available;
                done.value = true;
                if (data.ai_available && data.candidates.length) askAi(body);
            } catch (e) {
                error.value = e.message;
            } finally {
                loading.value = false;
            }
        };
        const askAi = async (body) => {
            aiLoading.value = true;
            try {
                const data = await post(`/${props.kind}/ai_suggest_tags`, body);
                aiPicks.value = data.suggestions;
                aiModel.value = data.simulated ? 'simulated' : (data.model || '');
            } catch (e) {
                aiError.value = e.message;
            } finally {
                aiLoading.value = false;
            }
        };

        const selectedIds = Vue.computed(() => new Set(props.modelValue.map(t => t.id)));
        const aiIds = Vue.computed(() => new Set((aiPicks.value || []).map(t => t.id)));
        const others = Vue.computed(() => candidates.value.filter(c => !aiIds.value.has(c.id)));
        const shownOthers = Vue.computed(() => showAll.value ? others.value : others.value.slice(0, PREVIEW));

        // One emit for the whole batch — emitting per tag would read the same
        // stale modelValue each time and keep only the last one.
        const addMany = (list) => {
            const ids = new Set(props.modelValue.map(t => t.id));
            const fresh = list.filter(t => !ids.has(t.id)).map(({ score, matched, confidence, reason, ...clean }) => clean);
            if (fresh.length) emit('update:modelValue', [...props.modelValue, ...fresh]);
        };
        const add = (tag) => addMany([tag]);
        const addAllAi = () => addMany(aiPicks.value || []);
        const addAllOthers = () => addMany(others.value);
        const remaining = (list) => (list || []).filter(t => !selectedIds.value.has(t.id)).length;
        const bg = (tag) => tag.color || '#6c757d';
        const fg = (tag) => getTextColor(bg(tag));

        const mood = Vue.computed(() => {
            if (error.value || aiError.value) return 'error';
            if (loading.value) return 'scanning';
            if (aiLoading.value) return 'thinking';
            if (!done.value) return 'idle';
            if (!candidates.value.length || (aiPicks.value && !aiPicks.value.length)) return 'empty';
            return 'found';
        });
        const moodImg = Vue.computed(() => RULEZY + MOODS[mood.value].img);
        const moodIcon = Vue.computed(() => MOODS[mood.value].icon);
        const speech = Vue.computed(() => {
            const n = noun.value;
            switch (mood.value) {
                case 'scanning': return `Looking through the taxonomies and galaxies for your ${n}…`;
                case 'thinking': return `${candidates.value.length} tags match words of your ${n}. Let me keep the ones that really fit…`;
                case 'error':    return error.value || `I couldn't finish: ${aiError.value} The plain matches below still work.`;
                case 'empty':    return candidates.value.length
                    ? `Nothing really fits this ${n} — the matches below only share a word with it.`
                    : (n === 'bundle' ? 'No tag matches yet — add some rules to the bundle, then ask me again.'
                                      : 'No tag matches yet — write a title or some content first, then ask me again.');
                case 'found':    return aiPicks.value
                    ? `I'd tag this ${n} with ${aiPicks.value.length === 1 ? 'this one' : 'these ' + aiPicks.value.length}. Click to add, nothing is added by itself.`
                    : `${candidates.value.length} tag${candidates.value.length > 1 ? 's' : ''} match words of your ${n}. Click to add.`;
                default:         return `I can suggest MISP taxonomy and galaxy tags from what your ${n} contains.`;
            }
        });

        return { root, loading, aiLoading, candidates, aiPicks, aiError, aiModel, error, aiAvailable, showAll, done,
                 elapsed, others, shownOthers, selectedIds, suggest, add, addAllAi, addAllOthers, remaining, bg, fg,
                 mapIcon, mascot: MASCOT_ENABLED, mood, moodImg, moodIcon, speech, CONF, PREVIEW };
    },
    template: `
    <div ref="root" class="ts-card" :class="'ts-card--' + mood">
        <span class="premium-accent-line"></span>

        <!-- Header: Rulezy (or icon) + what she says + action -->
        <div class="ts-header">
            <div class="ts-avatar" :class="{'ts-avatar--busy': loading || aiLoading}">
                <img v-if="mascot" :src="moodImg" alt="Rulezy">
                <span v-else class="ts-avatar__icon"><i class="fa-solid" :class="moodIcon"></i></span>
            </div>
            <div class="ts-header__text">
                <div class="ts-title">
                    Tag suggestions
                    <span class="ts-badge"><i class="fa-solid fa-wand-magic-sparkles me-1"></i>AI</span>
                    <span v-if="aiModel" class="ts-badge ts-badge--model" :class="{'ts-badge--sim': aiModel === 'simulated'}"
                          :title="aiModel === 'simulated' ? 'Simulation mode — no model was called' : 'Model'">
                        <i class="fa-solid me-1" :class="aiModel === 'simulated' ? 'fa-flask' : 'fa-microchip'"></i>[[ aiModel ]]
                    </span>
                </div>
                <div class="ts-speech" :class="{'ts-speech--bubble': mascot}">[[ speech ]]</div>
            </div>
            <button type="button" class="btn btn-primary btn-sm rounded-pill px-3 ts-go" :disabled="loading || aiLoading" @click="suggest">
                <i class="fa-solid me-1" :class="loading || aiLoading ? 'fa-spinner fa-spin' : (done ? 'fa-rotate' : 'fa-wand-magic-sparkles')"></i>
                [[ done ? 'Suggest again' : 'Suggest tags' ]]
            </button>
        </div>

        <div v-if="done" class="ts-body">
            <!-- AI picks -->
            <section v-if="aiAvailable" class="ts-section">
                <div class="ts-section__head">
                    <span class="ts-section__icon ts-section__icon--ai"><i class="fa-solid fa-robot"></i></span>
                    <span class="ts-section__title">[[ mascot ? "Rulezy's picks" : 'AI picks' ]]</span>
                    <span v-if="aiPicks" class="ts-count">[[ aiPicks.length ]]</span>
                    <button v-if="remaining(aiPicks)" type="button" class="btn btn-sm btn-primary rounded-pill ts-addall" @click="addAllAi">
                        <i class="fa-solid fa-plus me-1"></i>Add all ([[ remaining(aiPicks) ]])
                    </button>
                    <span v-else-if="aiPicks && aiPicks.length" class="ts-all-added"><i class="fa-solid fa-check me-1"></i>All added</span>
                </div>

                <div v-if="aiLoading" class="ts-picks">
                    <div v-for="i in 3" :key="'sk'+i" class="ts-pick ts-pick--skeleton"><span></span><span></span></div>
                </div>
                <div v-else-if="aiError" class="ts-note ts-note--error"><i class="fa-solid fa-triangle-exclamation me-1"></i>[[ aiError ]]</div>
                <div v-else-if="aiPicks && !aiPicks.length" class="ts-note"><i class="fa-solid fa-circle-info me-1"></i>No tag really fits according to the AI.</div>
                <div v-else class="ts-picks">
                    <button v-for="t in aiPicks" :key="'ai'+t.id" type="button" class="ts-pick"
                            :class="['ts-pick--' + t.confidence, {'ts-pick--added': selectedIds.has(t.id)}]"
                            :disabled="selectedIds.has(t.id)" @click="add(t)">
                        <span class="ts-pick__top">
                            <span class="tag-split shadow-sm">
                                <span class="tag-left" v-html="mapIcon(t.icon)"></span>
                                <span class="tag-right" :style="{ backgroundColor: bg(t) }">
                                    <span class="fw-bold" :style="{ color: fg(t) }">[[ t.name ]]</span>
                                </span>
                            </span>
                            <span class="ts-conf" :class="'ts-conf--' + t.confidence">
                                <i class="fa-solid me-1" :class="CONF[t.confidence].icon"></i>[[ CONF[t.confidence].label ]]
                            </span>
                            <span v-if="t.generic" class="ts-generic" title="Generic tag: comes from what rules of this format detect"><i class="fa-solid fa-shapes me-1"></i>Generic</span>
                            <span class="ts-pick__action">
                                <i class="fa-solid" :class="selectedIds.has(t.id) ? 'fa-check' : 'fa-plus'"></i>
                            </span>
                        </span>
                        <span class="ts-pick__reason">[[ t.reason ]]</span>
                    </button>
                </div>
            </section>

            <!-- Other matches -->
            <section class="ts-section">
                <div class="ts-section__head">
                    <span class="ts-section__icon"><i class="fa-solid fa-magnifying-glass"></i></span>
                    <span class="ts-section__title">[[ aiAvailable ? 'Also matched' : 'Matches' ]]</span>
                    <span class="ts-count">[[ others.length ]]</span>
                    <span class="ts-meta d-none d-md-inline">words of the [[ kind === 'bundle' ? 'bundle' : 'rule' ]] found in taxonomies &amp; galaxies · [[ elapsed ]] ms</span>
                    <button v-if="remaining(others)" type="button" class="btn btn-sm btn-outline-primary rounded-pill ts-addall" @click="addAllOthers">
                        <i class="fa-solid fa-plus me-1"></i>Add all ([[ remaining(others) ]])
                    </button>
                </div>
                <div v-if="!others.length" class="ts-note"><i class="fa-solid fa-circle-info me-1"></i>No other match.</div>
                <div v-else class="ts-chips">
                    <span v-for="t in shownOthers" :key="t.id" class="tag-split shadow-sm ts-chip"
                          :class="{'ts-chip--added': selectedIds.has(t.id)}" role="button" tabindex="0"
                          :title="(t.generic ? 'Generic tag for this format: ' : 'Matched: ') + t.matched.join(', ')" @click="add(t)" @keydown.enter.prevent="add(t)">
                        <span class="tag-left" v-html="mapIcon(t.icon)"></span>
                        <span class="tag-right" :style="{ backgroundColor: bg(t) }">
                            <span class="fw-bold me-2" :style="{ color: fg(t) }">[[ t.name ]]</span>
                            <i class="fas" :class="selectedIds.has(t.id) ? 'fa-check-circle' : 'fa-plus-circle'" :style="{ color: fg(t) }"></i>
                        </span>
                    </span>
                    <button v-if="others.length > PREVIEW" type="button" class="btn btn-link btn-sm p-0 ts-more" @click="showAll = !showAll">
                        [[ showAll ? 'Show less' : '+' + (others.length - PREVIEW) + ' more' ]]
                    </button>
                </div>
            </section>
        </div>
    </div>`,
};

export default TagSuggest;
