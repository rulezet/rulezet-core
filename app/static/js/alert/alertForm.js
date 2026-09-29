/**
 * alertForm.js — create / edit an alert, in three steps (what to watch,
 * on what, how to notify) with a live "what would this have caught in the
 * last 30 days" preview next to it.
 *
 * Props:
 *   initial          Object  alert fields (alert.to_json() shape, or the /alert/new prefill)
 *   criteriaDisplay  Object  { tags: [tag objects], unknown_tags: [names], attacks: [...], users: [...] }
 *   isEdit           Boolean
 *   alertUuid        String  (edit only)
 *   emailAvailable   Boolean email section shown only when true
 *   csrfToken        String
 */
import { create_message } from '/static/js/toaster.js'
import TagInput from '/static/js/tags/tagInput.js'
import AttackInput from '/static/js/attack/attackInput.js'
import VulnerabilityInput from '/static/js/vulnerability/vulnerabilityInput.js'
import AlertCriteriaChips from './alertCriteriaChips.js'

const EMAIL_MODES = [
    { key: 'off',     label: 'Off' },
    { key: 'instant', label: 'Instant' },
    { key: 'daily',   label: 'Daily digest' },
    { key: 'weekly',  label: 'Weekly digest' },
]

export default {
    name: 'AlertForm',
    delimiters: ['[[', ']]'],

    components: {
        'tag-input': TagInput,
        'attack-input': AttackInput,
        'vulnerability-input': VulnerabilityInput,
        'alert-criteria-chips': AlertCriteriaChips,
    },

    props: {
        initial:         { type: Object,  required: true },
        criteriaDisplay: { type: Object,  default: () => ({}) },
        isEdit:          { type: Boolean, default: false },
        alertUuid:       { type: String,  default: '' },
        emailAvailable:  { type: Boolean, default: false },
        csrfToken:       { type: String,  required: true },
    },

    template: `
<div class="row g-4">
  <div class="col-lg-8">

    <!-- Step 1 — what to watch -->
    <div class="al-step">
      <div class="al-step-head">
        <div class="al-step-num">1</div>
        <div>
          <div class="al-step-title">What should Rulezet watch for?</div>
          <div class="al-step-sub">Add as many criteria as you like — within one criterion, any value matches.</div>
        </div>
      </div>
      <div class="al-step-body">
        <div class="al-field">
          <div class="al-field-label"><i class="fa-solid fa-signature"></i>Alert name</div>
          <input type="text" class="form-control" v-model.trim="name" maxlength="120"
                 placeholder="e.g. NetScaler zero-days, Ransomware, My team's repos">
        </div>

        <div class="al-field">
          <div :class="{ 'al-disabled': cveAny }">
            <vulnerability-input v-model="cves" target-type="rule" label="Vulnerabilities (CVE, GHSA…)"></vulnerability-input>
          </div>
          <div class="form-check form-switch mt-2">
            <input class="form-check-input" type="checkbox" id="al-cve-any" v-model="cveAny">
            <label class="form-check-label small" for="al-cve-any">Any vulnerability — tell me about everything that carries a CVE, GHSA…</label>
          </div>
        </div>

        <div class="al-field">
          <div :class="{ 'al-disabled': tagAny }">
            <tag-input v-model="tags" label="Tags" placeholder="Search tags…"></tag-input>
          </div>
          <div class="form-check form-switch mt-2">
            <input class="form-check-input" type="checkbox" id="al-tag-any" v-model="tagAny">
            <label class="form-check-label small" for="al-tag-any">Any tag — every tagged rule (the default tlp:/pap: markings don't count)</label>
          </div>
          <div v-if="unknownTags.length && !tagAny" class="al-chips mt-2">
            <span v-for="t in unknownTags" :key="t" class="al-chip al-chip--tag" title="No tag with this exact name exists yet — it will still match once it does">
              <i class="fa-solid fa-tag"></i>[[ t ]]
              <button type="button" class="al-chip-remove" @click="unknownTags = unknownTags.filter(x => x !== t)">&times;</button>
            </span>
          </div>
        </div>

        <div class="al-field">
          <div :class="{ 'al-disabled': attackAny }">
            <attack-input v-model="attacks" label="ATT&CK techniques" :csrf-token="csrfToken"></attack-input>
            <div class="form-text" style="font-size:.74rem;">Watching a technique also covers its sub-techniques.</div>
          </div>
          <div class="form-check form-switch mt-2">
            <input class="form-check-input" type="checkbox" id="al-attack-any" v-model="attackAny">
            <label class="form-check-label small" for="al-attack-any">Any ATT&amp;CK technique — every rule mapped to MITRE ATT&amp;CK</label>
          </div>
        </div>

        <div class="al-field">
          <div class="al-field-label"><i class="fa-solid fa-magnifying-glass"></i>Keywords</div>
          <div class="al-chip-input" @click="$refs.keywordInput.focus()">
            <span v-for="k in keywords" :key="k" class="al-chip al-chip--keyword">
              [[ k ]]<button type="button" class="al-chip-remove" @click.stop="keywords = keywords.filter(x => x !== k)">&times;</button>
            </span>
            <input ref="keywordInput" v-model="keywordDraft" placeholder="netscaler, lockbit… (Enter to add)"
                   @keydown.enter.prevent="addKeyword" @keydown="onChipKey($event, 'keyword')" @blur="addKeyword">
          </div>
          <div class="form-text" style="font-size:.74rem;">Searched in titles, descriptions and rule content (3–60 characters).</div>
        </div>

        <div class="row g-3 mt-1">
          <div class="col-md-6">
            <div class="al-field-label"><i class="fa-solid fa-file-code"></i>Formats</div>
            <select class="form-select" @change="addFormat($event.target.value); $event.target.value = ''">
              <option value="">Any format — pick to restrict…</option>
              <option v-for="f in availableFormats" :key="f" :value="f">[[ f ]]</option>
            </select>
            <div class="al-chips mt-2" v-if="formats.length">
              <span v-for="f in formats" :key="f" class="al-chip al-chip--format">
                [[ f ]]<button type="button" class="al-chip-remove" @click="formats = formats.filter(x => x !== f)">&times;</button>
              </span>
            </div>
          </div>

          <div class="col-md-6">
            <div class="al-field-label"><i class="fa-solid fa-user"></i>Published by</div>
            <div class="position-relative">
              <input type="text" class="form-control" v-model="userQuery" placeholder="Search a user…"
                     @input="searchUsers" @blur="hideUserResults">
              <div v-if="userResults.length" class="al-user-results">
                <button type="button" v-for="u in userResults" :key="u.id" @mousedown.prevent="addUser(u)">
                  <img v-if="u.avatar" :src="u.avatar" alt=""><i v-else class="fa-solid fa-circle-user"></i>[[ u.username ]]
                </button>
              </div>
            </div>
            <div class="al-chips mt-2" v-if="users.length">
              <span v-for="u in users" :key="u.id" class="al-chip al-chip--user">
                <i class="fa-solid fa-user"></i>[[ u.username ]]<button type="button" class="al-chip-remove" @click="users = users.filter(x => x.id !== u.id)">&times;</button>
              </span>
            </div>
          </div>
        </div>

        <div class="al-field mt-3">
          <div class="al-field-label"><i class="fa-brands fa-github"></i>GitHub imports</div>
          <div class="al-chip-input" :class="{ 'al-disabled': githubAny }" @click="$refs.repoInput.focus()">
            <span v-for="r in githubRepos" :key="r" class="al-chip al-chip--github al-chip--mono">
              [[ r ]]<button type="button" class="al-chip-remove" @click.stop="githubRepos = githubRepos.filter(x => x !== r)">&times;</button>
            </span>
            <input ref="repoInput" v-model="repoDraft" :disabled="githubAny" placeholder="owner/repo or GitHub URL (Enter to add)"
                   @keydown.enter.prevent="addRepo" @keydown="onChipKey($event, 'repo')" @blur="addRepo">
          </div>
          <div class="form-check form-switch mt-2">
            <input class="form-check-input" type="checkbox" id="al-github-any" v-model="githubAny">
            <label class="form-check-label small" for="al-github-any">Any rule imported from GitHub, whatever the repository</label>
          </div>
        </div>

        <div class="rounded-3 border p-3 mt-4 d-flex align-items-center justify-content-between flex-wrap gap-2"
             style="background:var(--light-bg-color);">
          <div>
            <div class="fw-semibold small">How should the criteria combine?</div>
            <div class="small text-muted" style="font-size:.76rem;">
              [[ matchMode === 'all' ? 'Only content that satisfies every criterion above.' : 'Content that satisfies at least one criterion above.' ]]
            </div>
          </div>
          <div class="al-seg">
            <button type="button" :class="{ 'is-on': matchMode === 'any' }" @click="matchMode = 'any'">Any criterion</button>
            <button type="button" :class="{ 'is-on': matchMode === 'all' }" @click="matchMode = 'all'">All criteria</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Step 2 — on what -->
    <div class="al-step">
      <div class="al-step-head">
        <div class="al-step-num">2</div>
        <div>
          <div class="al-step-title">On what?</div>
          <div class="al-step-sub">Only public content is ever matched, and never your own.</div>
        </div>
      </div>
      <div class="al-step-body">
        <div class="al-field-label">Watch</div>
        <div class="al-options mb-3">
          <label class="al-option" :class="{ 'is-on': targets.includes('rule') }">
            <input type="checkbox" class="form-check-input" value="rule" v-model="targets">
            <div><div class="al-option-title"><i class="fa-solid fa-shield-halved me-1 text-primary"></i>Rules</div>
                 <div class="al-option-sub">YARA, Sigma, Suricata, Zeek…</div></div>
          </label>
          <label class="al-option" :class="{ 'is-on': targets.includes('bundle') }">
            <input type="checkbox" class="form-check-input" value="bundle" v-model="targets">
            <div><div class="al-option-title"><i class="fa-solid fa-layer-group me-1 text-primary"></i>Bundles</div>
                 <div class="al-option-sub">CVE, tag, keyword and user criteria apply</div></div>
          </label>
        </div>
        <div class="al-field-label">When they are</div>
        <div class="al-options">
          <label class="al-option" :class="{ 'is-on': events.includes('created') }">
            <input type="checkbox" class="form-check-input" value="created" v-model="events">
            <div><div class="al-option-title"><i class="fa-solid fa-circle-plus me-1 text-primary"></i>Published</div>
                 <div class="al-option-sub">New rules, imports, new public bundles</div></div>
          </label>
          <label class="al-option" :class="{ 'is-on': events.includes('updated') }">
            <input type="checkbox" class="form-check-input" value="updated" v-model="events">
            <div><div class="al-option-title"><i class="fa-solid fa-pen-to-square me-1 text-primary"></i>Updated</div>
                 <div class="al-option-sub">Edits, accepted proposals, GitHub updates</div></div>
          </label>
        </div>
      </div>
    </div>

    <!-- Step 3 — how to notify -->
    <div class="al-step">
      <div class="al-step-head">
        <div class="al-step-num">3</div>
        <div>
          <div class="al-step-title">How should we tell you?</div>
          <div class="al-step-sub">Matches are always grouped — never one message per rule.</div>
        </div>
      </div>
      <div class="al-step-body">
        <div class="d-flex align-items-center justify-content-between flex-wrap gap-2">
          <div>
            <div class="fw-semibold small"><i class="fa-solid fa-bell me-1 text-primary"></i>On Rulezet</div>
            <div class="small text-muted" style="font-size:.76rem;">In your notification bell</div>
          </div>
          <div class="form-check form-switch mb-0">
            <input class="form-check-input" type="checkbox" role="switch" v-model="notifyInApp">
          </div>
        </div>

        <template v-if="emailAvailable">
          <hr class="my-3">
          <div class="d-flex align-items-center justify-content-between flex-wrap gap-2">
            <div>
              <div class="fw-semibold small"><i class="fa-solid fa-envelope me-1 text-primary"></i>By email</div>
              <div class="small text-muted" style="font-size:.76rem;">
                [[ emailModeHint ]]
              </div>
            </div>
            <div class="al-seg">
              <button type="button" v-for="m in EMAIL_MODES" :key="m.key"
                      :class="{ 'is-on': emailMode === m.key }" @click="emailMode = m.key">[[ m.label ]]</button>
            </div>
          </div>
        </template>
        <div v-else class="small text-muted mt-3" style="font-size:.78rem;">
          <i class="fa-solid fa-circle-info me-1"></i>Email alerts are disabled on this instance — you'll be notified on Rulezet.
        </div>
      </div>
    </div>

    <div class="d-flex justify-content-end gap-2 mb-5">
      <a :href="isEdit ? '/alert/' + alertUuid : '/alert/'" class="btn btn-outline-secondary rounded-pill px-4">Cancel</a>
      <button type="button" class="btn btn-primary rounded-pill px-4 shadow-sm" :disabled="saving" @click="save">
        <i class="fa-solid me-1" :class="saving ? 'fa-spinner fa-spin' : 'fa-floppy-disk'"></i>
        [[ isEdit ? 'Save alert' : 'Create alert' ]]
      </button>
    </div>
  </div>

  <!-- Live preview -->
  <div class="col-lg-4">
    <div class="al-preview p-4">
      <div class="al-field-label mb-3"><i class="fa-solid fa-eye"></i>Live preview</div>

      <div class="al-summary mb-3">
        <template v-if="hasCriteria">
          Notify me [[ channelText ]] when [[ targetText ]] matching
          <alert-criteria-chips class="d-inline-flex my-1" :criteria="criteria" :match-mode="matchMode" :users="users"></alert-criteria-chips>
          [[ eventText ]].
        </template>
        <span v-else class="text-muted">Add a criterion to see what this alert would catch.</span>
      </div>

      <template v-if="hasCriteria">
        <div v-if="previewLoading" class="text-center py-3 text-muted"><i class="fa-solid fa-spinner fa-spin"></i></div>
        <template v-else-if="preview">
          <div class="d-flex align-items-end gap-2 mb-1">
            <div class="al-preview-count">[[ previewTotal ]]</div>
            <div class="small text-muted pb-1">match[[ previewTotal === 1 ? '' : 'es' ]] in the last [[ preview.days ]] days</div>
          </div>
          <div class="small text-muted mb-3" style="font-size:.76rem;">
            [[ preview.rules ]] rule[[ preview.rules === 1 ? '' : 's' ]] · [[ preview.bundles ]] bundle[[ preview.bundles === 1 ? '' : 's' ]]
            — [[ previewTotal ? 'this alert would have told you about them.' : 'quiet so far, it will speak up when something lands.' ]]
          </div>
          <div v-for="s in preview.sample" :key="s.type + s.id" class="al-preview-item">
            <i class="fa-solid" :class="s.type === 'bundle' ? 'fa-layer-group text-success' : 'fa-shield-halved text-primary'"></i>
            <a :href="s.link" target="_blank" :title="s.title">[[ s.title ]]</a>
            <span v-if="s.format" class="badge bg-light text-dark border ms-auto">[[ s.format ]]</span>
          </div>
        </template>
      </template>
    </div>
  </div>
</div>
    `,

    setup(props) {
        const { ref, computed, watch, onMounted } = Vue
        const init = props.initial || {}
        const c = init.criteria || {}
        const display = props.criteriaDisplay || {}

        const name = ref(init.name || '')
        const cves = ref([...(c.cves || [])])
        const tags = ref([...(display.tags || [])])
        const unknownTags = ref([...(display.unknown_tags || [])])
        const attacks = ref([...(display.attacks || [])])
        const keywords = ref([...(c.keywords || [])])
        const formats = ref([...(c.formats || [])])
        const users = ref([...(display.users || [])])
        const githubRepos = ref([...(c.github_repos || [])])
        const githubAny = ref(!!c.github_any)
        const cveAny = ref(!!c.cve_any)
        const tagAny = ref(!!c.tag_any)
        const attackAny = ref(!!c.attack_any)
        const matchMode = ref(init.match_mode || 'any')
        const targets = ref([...(init.targets || ['rule'])])
        const events = ref([...(init.events || ['created'])])
        const notifyInApp = ref(init.notify_in_app !== false)
        const emailMode = ref(init.email_mode || 'off')
        const saving = ref(false)

        const keywordDraft = ref('')
        const repoDraft = ref('')
        const availableFormats = ref([])
        const userQuery = ref('')
        const userResults = ref([])
        const preview = ref(null)
        const previewLoading = ref(false)

        // ── Criteria ────────────────────────────────────────────────────
        // An "any ..." switch supersedes its list — the list is kept in the
        // form (switching back restores it) but not sent.
        const criteria = computed(() => ({
            cves: cveAny.value ? [] : cves.value.map(v => String(v).toUpperCase()),
            tags: tagAny.value ? [] : [...new Set([...tags.value.map(t => (t.name || '').toLowerCase()),
                                                   ...unknownTags.value])].filter(Boolean),
            attacks: attackAny.value ? [] : attacks.value.map(t => t.technique_id || t.id),
            keywords: keywords.value,
            formats: formats.value,
            users: users.value.map(u => u.id),
            github_repos: githubAny.value ? [] : githubRepos.value,
            cve_any: cveAny.value,
            tag_any: tagAny.value,
            attack_any: attackAny.value,
            github_any: githubAny.value,
        }))
        const hasCriteria = computed(() => {
            const cr = criteria.value
            return cr.cve_any || cr.tag_any || cr.attack_any || cr.github_any
                || ['cves', 'tags', 'attacks', 'keywords', 'formats', 'users', 'github_repos'].some(k => cr[k].length)
        })

        function addKeyword() {
            const v = keywordDraft.value.trim().toLowerCase().replace(/,$/, '')
            keywordDraft.value = ''
            if (!v) return
            if (v.length < 3 || v.length > 60) { create_message('Keywords must be 3–60 characters.', 'warning-subtle'); return }
            if (!keywords.value.includes(v)) keywords.value = [...keywords.value, v]
        }
        function normalizeRepo(raw) {
            return raw.trim().toLowerCase().replace(/\/+$/, '').replace(/^(https?:\/\/)?(www\.)?github\.com\//, '').replace(/\.git$/, '')
        }
        function addRepo() {
            const v = normalizeRepo(repoDraft.value)
            repoDraft.value = ''
            if (!v) return
            if (!/^[a-z0-9_.-]+\/[a-z0-9_.-]+$/.test(v)) { create_message('Use owner/repo or a GitHub repository URL.', 'warning-subtle'); return }
            if (!githubRepos.value.includes(v)) githubRepos.value = [...githubRepos.value, v]
        }
        function onChipKey(event, kind) {
            // Comma also commits a chip; Backspace on an empty input removes the last one.
            const draft = kind === 'keyword' ? keywordDraft : repoDraft
            const list = kind === 'keyword' ? keywords : githubRepos
            if (event.key === ',') { event.preventDefault(); kind === 'keyword' ? addKeyword() : addRepo() }
            else if (event.key === 'Backspace' && !draft.value && list.value.length) list.value = list.value.slice(0, -1)
        }
        function addFormat(f) {
            if (f && !formats.value.includes(f)) formats.value = [...formats.value, f]
        }

        let userTimer = null
        function searchUsers() {
            clearTimeout(userTimer)
            const q = userQuery.value.trim()
            if (q.length < 2) { userResults.value = []; return }
            userTimer = setTimeout(async () => {
                try {
                    const data = await fetch(`/account/search_mentionable_users?q=${encodeURIComponent(q)}`).then(r => r.json())
                    userResults.value = (data.users || []).filter(u => !users.value.some(x => x.id === u.id))
                } catch { userResults.value = [] }
            }, 250)
        }
        function addUser(u) {
            users.value = [...users.value, u]
            userQuery.value = ''
            userResults.value = []
        }
        function hideUserResults() { setTimeout(() => { userResults.value = [] }, 150) }

        // ── Summary sentence ────────────────────────────────────────────
        const targetText = computed(() => targets.value.length > 1 ? 'a rule or bundle'
            : (targets.value[0] === 'bundle' ? 'a bundle' : 'a rule'))
        const eventText = computed(() => {
            const e = events.value
            if (e.includes('created') && e.includes('updated')) return 'is published or updated'
            return e.includes('updated') ? 'is updated' : 'is published'
        })
        const channelText = computed(() => {
            const email = props.emailAvailable && emailMode.value !== 'off'
            if (notifyInApp.value && email) return 'on Rulezet and by email'
            if (email) return 'by email'
            return 'on Rulezet'
        })
        const emailModeHint = computed(() => ({
            off: 'No emails for this alert.',
            instant: 'Grouped every few minutes, at most one email every 15 minutes.',
            daily: 'One digest a day with everything that matched.',
            weekly: 'One digest a week with everything that matched.',
        }[emailMode.value]))

        // ── Live preview (debounced) ────────────────────────────────────
        let previewTimer = null
        async function refreshPreview() {
            if (!hasCriteria.value || !targets.value.length) { preview.value = null; return }
            previewLoading.value = true
            try {
                const res = await fetch('/alert/preview', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': props.csrfToken },
                    body: JSON.stringify({ criteria: criteria.value, match_mode: matchMode.value, targets: targets.value }),
                })
                const data = await res.json()
                preview.value = data.success ? data.preview : null
            } catch { preview.value = null } finally { previewLoading.value = false }
        }
        watch([criteria, matchMode, targets], () => {
            clearTimeout(previewTimer)
            previewTimer = setTimeout(refreshPreview, 400)
        }, { deep: true })
        const previewTotal = computed(() => preview.value ? preview.value.rules + preview.value.bundles : 0)

        // ── Save ────────────────────────────────────────────────────────
        async function save() {
            saving.value = true
            try {
                const url = props.isEdit ? `/alert/${props.alertUuid}/update` : '/alert/create'
                const res = await fetch(url, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': props.csrfToken },
                    body: JSON.stringify({
                        name: name.value, criteria: criteria.value, match_mode: matchMode.value,
                        targets: targets.value, events: events.value,
                        notify_in_app: notifyInApp.value, email_mode: emailMode.value,
                    }),
                })
                const data = await res.json()
                if (data.success) {
                    window.location.href = `/alert/${data.alert.uuid}`
                } else {
                    create_message(data.message || 'Could not save the alert.', 'danger-subtle')
                }
            } catch (e) {
                create_message('Network error: ' + e, 'danger-subtle')
            } finally {
                saving.value = false
            }
        }

        onMounted(async () => {
            try {
                const data = await fetch('/rule/get_rules_formats').then(r => r.json())
                availableFormats.value = (data.formats || []).map(f => (f.name || '').toLowerCase()).filter(Boolean)
            } catch { /* the select just stays empty */ }
            refreshPreview()
        })

        return {
            EMAIL_MODES, name, cves, tags, unknownTags, attacks, keywords, formats, users, githubRepos, githubAny,
            cveAny, tagAny, attackAny,
            matchMode, targets, events, notifyInApp, emailMode, saving, keywordDraft, repoDraft,
            availableFormats, userQuery, userResults, preview, previewLoading, previewTotal,
            criteria, hasCriteria, targetText, eventText, channelText, emailModeHint,
            addKeyword, addRepo, onChipKey, addFormat, searchUsers, addUser, hideUserResults, save,
        }
    },
}
