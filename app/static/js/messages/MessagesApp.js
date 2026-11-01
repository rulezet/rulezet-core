/**
 * MessagesApp.js — the Messages page (/messages/): conversations on the left, the open conversation in the
 * middle, its details (about, pinned, members, settings) on the right. Server side: app/features/messages/.
 * New messages arrive by polling (every 3 s for the open conversation, 12 s for the list).
 */
import { create_message } from '/static/js/toaster.js'
import MessageText, { plainMessage, REF_ICONS } from '/static/js/components/chat/message-text.js'
import MessageComposer from '/static/js/components/chat/message-composer.js'
import PeoplePicker from '/static/js/components/chat/people-picker.js'

const { ref, reactive, computed, watch, nextTick, onMounted, onUnmounted } = Vue

const csrf = () => document.getElementById('csrf_token')?.value || ''
async function api(url, method = 'GET', body) {
    try {
        const res = await fetch(url, {
            method, headers: { 'X-CSRFToken': csrf(), 'Content-Type': 'application/json' },
            body: body === undefined ? undefined : JSON.stringify(body),
        })
        const data = await res.json().catch(() => null)
        if (!res.ok) { create_message((data && data.message) || (res.status === 404 ? 'Not found.' : 'Something went wrong.'), 'danger-subtle'); return null }
        return data || {}
    } catch { create_message('Network error.', 'danger-subtle'); return null }
}

const asDate = iso => new Date(iso)
const sameDay = (a, b) => a.toDateString() === b.toDateString()
function dayLabel(iso) {
    const d = asDate(iso), now = new Date(), y = new Date(now); y.setDate(now.getDate() - 1)
    if (sameDay(d, now)) return 'Today'
    if (sameDay(d, y)) return 'Yesterday'
    return d.toLocaleDateString(undefined, { weekday: 'long', day: 'numeric', month: 'long', year: d.getFullYear() === now.getFullYear() ? undefined : 'numeric' })
}
const timeLabel = iso => asDate(iso).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
function listTime(iso) {
    if (!iso) return ''
    const d = asDate(iso), now = new Date()
    if (sameDay(d, now)) return timeLabel(iso)
    if ((now - d) < 6 * 864e5) return d.toLocaleDateString(undefined, { weekday: 'short' })
    return d.toLocaleDateString(undefined, { day: 'numeric', month: 'short' })
}

export default {
    name: 'MessagesApp',
    delimiters: ['[[', ']]'],
    components: { MessageText, MessageComposer, PeoplePicker },
    props: {
        currentUserId: { type: Number, required: true },
        isAdmin: { type: Boolean, default: false },
        openUuid: { type: String, default: null },
        start: { type: Object, default: null },
        reactions: { type: Array, default: () => ['👍', '❤️', '🎉', '😄', '🤔', '👀'] },
        maxLength: { type: Number, default: 8000 },
    },
    setup(props) {
        const dialog = ref(null)    // null | 'channel' | 'direct' | 'browse' | 'add' — declared first: watched below
        // ── conversations list ──
        const conversations = ref([])
        const listLoaded = ref(false)
        const filter = ref('')
        const filterBy = c => !filter.value || (c.name || '').toLowerCase().includes(filter.value.toLowerCase())
        const starred = computed(() => conversations.value.filter(c => c.is_starred && filterBy(c)))
        const channels = computed(() => conversations.value.filter(c => c.kind === 'channel' && !c.is_starred && filterBy(c)))
        const directs = computed(() => conversations.value.filter(c => c.kind === 'direct' && !c.is_starred && filterBy(c)))
        const unreadTotal = computed(() => conversations.value.reduce((s, c) => s + (c.is_muted ? 0 : c.unread), 0))
        const mobileList = ref(true)

        async function loadConversations() {
            const data = await fetch('/messages/api/conversations').then(r => r.ok ? r.json() : null).catch(() => null)
            if (!data) return
            conversations.value = data.conversations
            listLoaded.value = true
            if (current.value) {
                const mine = data.conversations.find(c => c.uuid === current.value.uuid)
                if (mine) mine.unread = 0
            }
            document.title = (unreadTotal.value ? `(${unreadTotal.value}) ` : '') + 'Messages — Rulezet'
        }

        // ── open conversation ──
        const current = ref(null)          // full channel json
        const msgs = ref([])
        const hasMore = ref(false)
        const loadingMsgs = ref(false)
        const firstUnreadId = ref(null)
        const scroller = ref(null)
        const highlight = ref(null)
        const replyTo = ref(null)
        const editing = ref(null)
        const panel = ref(localStorageGet('rz-msg-panel') || '')   // '' | 'about' | 'members' | 'pinned' | 'settings' | 'search'
        const composer = ref(null)

        function localStorageGet(k) { try { return localStorage.getItem(k) } catch { return null } }
        function localStorageSet(k, v) { try { v ? localStorage.setItem(k, v) : localStorage.removeItem(k) } catch { } }
        watch(panel, v => localStorageSet('rz-msg-panel', v))

        const atBottom = () => { const el = scroller.value; return !el || el.scrollHeight - el.scrollTop - el.clientHeight < 80 }
        const toBottom = () => nextTick(() => { const el = scroller.value; if (el) el.scrollTop = el.scrollHeight })

        async function openConversation(uuid, focusId = null) {
            if (!uuid) return
            const data = await api(`/messages/api/channels/${uuid}`)
            if (!data) return
            current.value = data.channel
            replyTo.value = null; editing.value = null; mobileList.value = false
            const listed = conversations.value.find(c => c.uuid === uuid)
            history.replaceState(null, '', `/messages/c/${uuid}` + (focusId ? `?m=${focusId}` : ''))
            loadingMsgs.value = true
            const page = await api(`/messages/api/channels/${uuid}/messages`)
            loadingMsgs.value = false
            if (!page || !current.value || current.value.uuid !== uuid) return
            msgs.value = page.messages; hasMore.value = page.has_more
            const unread = listed ? listed.unread : 0
            firstUnreadId.value = null
            if (unread) {
                const others = msgs.value.filter(m => m.kind === 'message' && !m.is_mine)
                const first = others[others.length - unread]
                firstUnreadId.value = first ? first.id : null
            }
            if (listed) listed.unread = 0
            await nextTick()
            if (focusId) jumpTo(focusId); else toBottom()
            markRead()
            composer.value && composer.value.focus && composer.value.focus()
        }

        function jumpTo(id) {
            highlight.value = id
            nextTick(() => {
                const el = document.getElementById('msg-' + id)
                if (el) el.scrollIntoView({ block: 'center' })
                setTimeout(() => { if (highlight.value === id) highlight.value = null }, 2500)
            })
        }

        async function loadOlder() {
            if (!current.value || !hasMore.value || loadingMsgs.value || !msgs.value.length) return
            loadingMsgs.value = true
            const el = scroller.value, h = el.scrollHeight
            const page = await api(`/messages/api/channels/${current.value.uuid}/messages?before=${msgs.value[0].id}`)
            loadingMsgs.value = false
            if (!page) return
            msgs.value = [...page.messages, ...msgs.value]; hasMore.value = page.has_more
            nextTick(() => { el.scrollTop = el.scrollHeight - h })
        }
        function onScroll() { if (scroller.value && scroller.value.scrollTop < 60) loadOlder() }

        let readTimer = null
        function markRead() {
            clearTimeout(readTimer)
            readTimer = setTimeout(() => {
                if (!current.value || !current.value.is_member || document.hidden) return
                const last = msgs.value[msgs.value.length - 1]
                if (last) api(`/messages/api/channels/${current.value.uuid}/read`, 'POST', { upto: last.id })
            }, 400)
        }

        // ── polling ──
        let pollTimer = null, listTimer = null, tick = 0, listTicks = 0
        async function poll() {
            tick++
            if (!current.value || document.hidden) return
            const uuid = current.value.uuid
            const last = msgs.value.length ? msgs.value[msgs.value.length - 1].id : 0
            const stay = atBottom()
            const page = await fetch(`/messages/api/channels/${uuid}/messages?after=${last}`).then(r => r.ok ? r.json() : null).catch(() => null)
            if (!page || !current.value || current.value.uuid !== uuid) return
            const fresh = page.messages.filter(m => !msgs.value.some(x => x.id === m.id))
            if (fresh.length) {
                msgs.value = [...msgs.value, ...fresh]
                if (stay) { toBottom(); markRead() }
                if (fresh.some(m => m.kind === 'system')) refreshChannel()
            }
            if (tick % 5 === 0) refreshRecent(uuid)       // edits, deletions and reactions of the last messages
        }
        async function refreshRecent(uuid) {
            const page = await fetch(`/messages/api/channels/${uuid}/messages?limit=50`).then(r => r.ok ? r.json() : null).catch(() => null)
            if (!page || !current.value || current.value.uuid !== uuid) return
            const byId = new Map(page.messages.map(m => [m.id, m]))
            msgs.value = msgs.value.map(m => byId.get(m.id) || m)
        }
        async function refreshChannel() {
            if (!current.value) return
            const data = await fetch(`/messages/api/channels/${current.value.uuid}`).then(r => r.ok ? r.json() : null).catch(() => null)
            if (data && current.value && data.channel.uuid === current.value.uuid) current.value = data.channel
        }

        // ── grouped display ──
        const rows = computed(() => {
            const out = []
            let prev = null
            for (const m of msgs.value) {
                const d = asDate(m.created_at)
                if (!prev || !sameDay(asDate(prev.created_at), d)) out.push({ type: 'day', key: 'd' + m.id, label: dayLabel(m.created_at) })
                if (m.id === firstUnreadId.value) out.push({ type: 'new', key: 'n' + m.id })
                const grouped = prev && m.kind === 'message' && prev.kind === 'message' && !m.reply_to
                    && prev.author && m.author && prev.author.id === m.author.id
                    && (d - asDate(prev.created_at)) < 5 * 60e3 && sameDay(asDate(prev.created_at), d) && m.id !== firstUnreadId.value
                out.push({ type: m.kind, key: 'm' + m.id, m, grouped })
                prev = m
            }
            return out
        })

        // ── sending, editing ──
        async function send(text, done) {
            if (!current.value) return done(false)
            if (editing.value) {
                const data = await api(`/messages/api/channels/${current.value.uuid}/messages/${editing.value.id}`, 'POST', { content: text })
                if (data) replaceMsg(data.message)
                editing.value = null
                return done(!!data)
            }
            const data = await api(`/messages/api/channels/${current.value.uuid}/messages`, 'POST',
                                   { content: text, reply_to_id: replyTo.value ? replyTo.value.id : null })
            if (!data) return done(false)
            if (!msgs.value.some(m => m.id === data.message.id)) msgs.value = [...msgs.value, data.message]
            replyTo.value = null; firstUnreadId.value = null
            if (!current.value.is_member) refreshChannel()
            toBottom()
            const listed = conversations.value.find(c => c.uuid === current.value.uuid)
            if (listed) { listed.last_message_at = data.message.created_at; listed.last = { author: 'You', author_id: props.currentUserId, text: plainMessage(text).slice(0, 140) } }
            else loadConversations()
            done(true)
        }
        function replaceMsg(m) { msgs.value = msgs.value.map(x => x.id === m.id ? m : x) }
        function cancelCompose() { replyTo.value = null; editing.value = null }
        function editLast() {
            const mine = [...msgs.value].reverse().find(m => m.is_mine && m.kind === 'message' && !m.is_deleted)
            if (mine) editing.value = mine
        }
        async function react(m, emoji) {
            const data = await api(`/messages/api/channels/${current.value.uuid}/messages/${m.id}/react`, 'POST', { emoji })
            if (data) replaceMsg(data.message)
            emojiFor.value = null
        }
        async function removeMsg(m) {
            if (!confirm('Delete this message?')) return
            const data = await api(`/messages/api/channels/${current.value.uuid}/messages/${m.id}`, 'DELETE')
            if (data) replaceMsg(data.message)
        }
        async function pin(m) {
            const data = await api(`/messages/api/channels/${current.value.uuid}/messages/${m.id}/pin`, 'POST')
            if (data) { replaceMsg(data.message); refreshChannel() }
        }
        function copyLink(m) {
            const url = `${location.origin}/messages/c/${current.value.uuid}?m=${m.id}`
            navigator.clipboard && navigator.clipboard.writeText(url).then(() => create_message('Link copied.', 'success-subtle'))
        }
        function quote(m) { replyTo.value = m; editing.value = null }
        const emojiFor = ref(null)
        const canModerate = computed(() => current.value && current.value.can_manage)
        const canPin = computed(() => current.value && (current.value.can_manage || current.value.kind === 'direct'))
        const reactorNames = g => (current.value?.members || []).filter(u => g.user_ids.includes(u.id)).map(u => u.name).join(', ') || `${g.count}`

        // ── channel actions ──
        async function join() {
            const data = await api(`/messages/api/channels/${current.value.uuid}/join`, 'POST')
            if (data) { current.value = data.channel; loadConversations(); loadPublic(); poll() }
        }
        async function leave() {
            if (!confirm(`Leave #${current.value.name}?` + (current.value.is_private ? ' It is private: you will need to be added again.' : ''))) return
            const data = await api(`/messages/api/channels/${current.value.uuid}/leave`, 'POST')
            if (data) { current.value = null; msgs.value = []; history.replaceState(null, '', '/messages/'); loadConversations() }
        }
        async function toggleMe(field) {
            const value = !current.value['is_' + field]
            const data = await api(`/messages/api/channels/${current.value.uuid}/me`, 'POST', { [field]: value })
            if (data) {
                current.value['is_' + field] = value
                const listed = conversations.value.find(c => c.uuid === current.value.uuid)
                if (listed) listed['is_' + field] = value
            }
        }
        const settings = reactive({ name: '', topic: '', is_private: false, members_can_invite: false })
        watch(() => current.value && current.value.uuid, () => {
            if (!current.value) return
            Object.assign(settings, { name: current.value.name || '', topic: current.value.topic || '', is_private: current.value.is_private, members_can_invite: current.value.members_can_invite })
        })
        async function saveSettings(extra = {}) {
            if (current.value.is_private && !settings.is_private && !extra.is_archived
                && !confirm(`Make #${current.value.name} public?\n\nAnyone with a Rulezet account will be able to find it, join it without an invitation and read every message — the ones already written too.`)) {
                settings.is_private = true
                return
            }
            const data = await api(`/messages/api/channels/${current.value.uuid}`, 'POST', { ...settings, ...extra })
            if (data) { current.value = data.channel; create_message('Saved.', 'success-subtle'); loadConversations(); poll() }
        }
        async function deleteChannel() {
            if (!confirm(`Delete #${current.value.name} and all its messages? This cannot be undone.`)) return
            const data = await api(`/messages/api/channels/${current.value.uuid}`, 'DELETE')
            if (data) { current.value = null; msgs.value = []; history.replaceState(null, '', '/messages/'); loadConversations() }
        }
        const toAdd = ref([])
        async function addPeople() {
            if (!toAdd.value.length) return
            const data = await api(`/messages/api/channels/${current.value.uuid}/members`, 'POST', { user_ids: toAdd.value.map(u => u.id) })
            if (data) { current.value = data.channel; toAdd.value = []; create_message(`${data.added} added.`, 'success-subtle'); poll() }
            return data
        }
        async function removeMember(u) {
            if (!confirm(`Remove ${u.name} from #${current.value.name}?`)) return
            const data = await api(`/messages/api/channels/${current.value.uuid}/members/${u.id}`, 'DELETE')
            if (data) { current.value = data.channel; poll() }
        }
        async function setRole(u, role) {
            if (role === 'owner' && !confirm(`Give #${current.value.name} to ${u.name}? You become a moderator.`)) return
            const data = await api(`/messages/api/channels/${current.value.uuid}/members/${u.id}/role`, 'POST', { role })
            if (data) { current.value = data.channel; poll() }
        }
        const memberIds = computed(() => (current.value?.members || []).map(u => u.id))

        // ── conversation menu (list and header): read, star, mute, delete for me, leave, delete the channel ──
        const findConv = uuid => conversations.value.find(c => c.uuid === uuid)
        async function convFlag(c, field) {
            const value = !c['is_' + field]
            if (!await api(`/messages/api/channels/${c.uuid}/me`, 'POST', { [field]: value })) return
            c['is_' + field] = value
            const listed = findConv(c.uuid); if (listed) listed['is_' + field] = value
            if (current.value && current.value.uuid === c.uuid) current.value['is_' + field] = value
        }
        async function convRead(c) {
            if (await api(`/messages/api/channels/${c.uuid}/read`, 'POST', {})) c.unread = 0
        }
        function closeIfOpen(uuid) {
            if (current.value && current.value.uuid === uuid) { current.value = null; msgs.value = []; history.replaceState(null, '', '/messages/'); mobileList.value = true }
        }
        async function convClear(c) {
            const who = c.kind === 'direct' ? c.name : '#' + c.name
            if (!confirm(`Delete the conversation with ${who} for you? Its messages disappear for you only — ${c.kind === 'direct' ? c.name + ' keeps them' : 'the others keep them'}. It comes back if someone writes again.`)) return
            if (!await api(`/messages/api/channels/${c.uuid}/clear`, 'POST')) return
            closeIfOpen(c.uuid)
            conversations.value = conversations.value.filter(x => x.uuid !== c.uuid)
            create_message('Conversation deleted for you.', 'success-subtle')
        }
        async function convLeave(c) {
            if (!confirm(`Leave #${c.name}?` + (c.is_private ? ' It is private: you will need to be added again.' : ''))) return
            if (!await api(`/messages/api/channels/${c.uuid}/leave`, 'POST')) return
            closeIfOpen(c.uuid); loadConversations()
        }
        async function convDelete(c) {
            if (!confirm(`Delete #${c.name} and all its messages for everyone? This cannot be undone.`)) return
            if (!await api(`/messages/api/channels/${c.uuid}`, 'DELETE')) return
            closeIfOpen(c.uuid); loadConversations()
            create_message('Channel deleted.', 'success-subtle')
        }
        const canDeleteChannel = c => c.kind === 'channel' && (c.my_role === 'owner' || props.isAdmin)

        // ── messages by email (Notifications → Preferences too) ──
        const EMAIL_MODES = [{ value: 'off', label: 'Never' }, { value: 'direct', label: 'Direct messages and mentions' },
                             { value: 'all', label: 'Everything, channels included' }]
        const emailMode = ref(null)
        async function loadEmailMode() {
            const p = await fetch('/notifications/preferences').then(r => r.ok ? r.json() : null).catch(() => null)
            if (p) emailMode.value = p.email_messages || 'off'
        }
        async function setEmailMode(v) {
            const data = await api('/notifications/preferences', 'POST', { email_messages: v })
            if (data) { emailMode.value = v; create_message(v === 'off' ? 'No email for messages.' : 'You\'ll get an email for unread messages.', 'success-subtle') }
        }

        // ── public channels to join (left list) ──
        const publicChannels = ref([])
        const joinable = computed(() => publicChannels.value.filter(c => !c.is_member && !conversations.value.some(x => x.uuid === c.uuid)).slice(0, 5))
        async function loadPublic() {
            const data = await fetch('/messages/api/browse').then(r => r.ok ? r.json() : null).catch(() => null)
            if (data) publicChannels.value = data.channels
        }
        async function quickJoin(c) {
            if (!await api(`/messages/api/channels/${c.uuid}/join`, 'POST')) return
            c.is_member = true
            await loadConversations()
            openConversation(c.uuid)
        }

        // ── invite link ──
        const inviteUrl = computed(() => current.value && current.value.invite_code ? `${location.origin}/messages/join/${current.value.invite_code}` : '')
        async function setInvite(on) {
            if (on && current.value.invite_code && !confirm('Renew the link? The current one stops working.')) return
            const data = await api(`/messages/api/channels/${current.value.uuid}/invite`, on ? 'POST' : 'DELETE')
            if (data) { current.value = data.channel; poll() }
        }
        function copyInvite() { navigator.clipboard && navigator.clipboard.writeText(inviteUrl.value).then(() => create_message('Invite link copied.', 'success-subtle')) }

        // ── keyboard: conversation list, browse list, dialogs ──
        function onConvKey(e, c) {
            const rowsEls = [...document.querySelectorAll('.chat-list .chat-conv')]
            const i = rowsEls.indexOf(e.currentTarget)
            if (e.key === 'Enter' || e.key === ' ') { if (e.target === e.currentTarget) { e.preventDefault(); openConversation(c.uuid) } }
            else if (e.key === 'ArrowDown') { e.preventDefault(); rowsEls[Math.min(i + 1, rowsEls.length - 1)]?.focus() }
            else if (e.key === 'ArrowUp') { e.preventDefault(); i === 0 ? document.getElementById('chat-filter')?.focus() : rowsEls[i - 1]?.focus() }
            else if (e.key === 'Home') { e.preventDefault(); rowsEls[0]?.focus() }
            else if (e.key === 'End') { e.preventDefault(); rowsEls[rowsEls.length - 1]?.focus() }
        }
        function onFilterKey(e) {
            const first = document.querySelector('.chat-list .chat-conv')
            if (e.key === 'ArrowDown' && first) { e.preventDefault(); first.focus() }
            if (e.key === 'Enter') { const c = [...starred.value, ...channels.value, ...directs.value][0]; if (c) { e.preventDefault(); openConversation(c.uuid) } }
        }
        const browseInput = ref(null)
        function focusBrowse(i) { const els = document.querySelectorAll('.chat-browse__row'); els[i] && els[i].focus() }
        function onBrowseKey(e) {
            const els = [...document.querySelectorAll('.chat-browse__row')], i = els.indexOf(e.currentTarget)
            if (e.key === 'ArrowDown') { e.preventDefault(); focusBrowse(Math.min(i + 1, els.length - 1)) }
            else if (e.key === 'ArrowUp') { e.preventDefault(); i === 0 ? browseInput.value?.focus() : focusBrowse(i - 1) }
        }
        const dialogEl = ref(null)
        let lastFocus = null
        watch(dialog, (v, old) => {
            if (v && !old) lastFocus = document.activeElement
            if (v) nextTick(() => {
                const el = dialogEl.value
                if (!el || el.contains(document.activeElement)) return
                const first = el.querySelector('input:not([type=hidden]):not([type=file]), select, textarea, button:not(.chat-icon-btn)')
                first && first.focus()
            })
            else if (lastFocus && lastFocus.focus) { lastFocus.focus(); lastFocus = null }
        })
        // Tab stays inside the open dialog
        function trapFocus(e) {
            if (e.key !== 'Tab' || !dialogEl.value) return
            const items = [...dialogEl.value.querySelectorAll('a[href], button:not([disabled]), input:not([type=hidden]):not([disabled]), select, textarea, [tabindex="0"]')]
                .filter(el => el.offsetParent !== null && !(el.type === 'file'))
            if (!items.length) return
            const first = items[0], last = items[items.length - 1]
            if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus() }
            else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus() }
        }

        // ── search in messages ──
        const searchQ = ref(''), searchResults = ref([]), searching = ref(false), searchScope = ref('here')
        let searchTimer = null
        watch([searchQ, searchScope], () => {
            clearTimeout(searchTimer)
            if (searchQ.value.trim().length < 2) { searchResults.value = []; return }
            searching.value = true
            searchTimer = setTimeout(async () => {
                const scope = searchScope.value === 'here' && current.value ? `&channel=${current.value.uuid}` : ''
                const data = await api(`/messages/api/search?q=${encodeURIComponent(searchQ.value.trim())}${scope}`)
                searchResults.value = data ? data.results : []
                searching.value = false
            }, 300)
        })
        async function openResult(r) {
            if (!current.value || current.value.uuid !== r.channel.uuid) return openConversation(r.channel.uuid, r.id)
            if (msgs.value.some(m => m.id === r.id)) return jumpTo(r.id)
            // older than what's loaded: load until it is there
            while (hasMore.value && !msgs.value.some(m => m.id === r.id)) await loadOlder()
            jumpTo(r.id)
        }

        // ── dialogs: new channel, new message, browse ──
        const form = reactive({ name: '', topic: '', is_private: false, members: [], ref: null, file: null, preview: null })
        function newChannel(refItem = null) {
            Object.assign(form, { name: refItem ? refItem.label.slice(0, 80) : '', topic: '', is_private: false, members: [], ref: refItem, file: null, preview: null })
            dialog.value = 'channel'
        }
        async function createChannel() {
            const data = await api('/messages/api/channels', 'POST', {
                name: form.name, topic: form.topic, is_private: form.is_private, member_ids: form.members.map(u => u.id),
                ref_type: form.ref ? form.ref.kind : null, ref_key: form.ref ? form.ref.key : null,
            })
            if (!data) return
            if (form.file) await sendAvatar(data.channel.uuid, form.file)
            dialog.value = null
            await loadConversations()
            openConversation(data.channel.uuid)
        }
        function pickAvatar(f) {
            if (!f) return
            if (f.size > 2 * 1024 * 1024) return create_message('The image is larger than 2 MB.', 'danger-subtle')
            form.file = f
            form.preview = URL.createObjectURL(f)
        }
        async function sendAvatar(uuid, file) {
            const fd = new FormData()
            fd.append('avatar', file)
            const res = await fetch(`/messages/api/channels/${uuid}/avatar`, { method: 'POST', headers: { 'X-CSRFToken': csrf() }, body: fd })
            const data = await res.json().catch(() => null)
            if (!res.ok) { create_message((data && data.message) || 'Upload failed.', 'danger-subtle'); return null }
            return data
        }
        async function uploadAvatar(file) {
            if (!file || !current.value) return
            const data = await sendAvatar(current.value.uuid, file)
            if (data) { current.value = data.channel; loadConversations(); poll() }
        }
        async function removeAvatar() {
            const data = await api(`/messages/api/channels/${current.value.uuid}/avatar`, 'DELETE')
            if (data) { current.value = data.channel; loadConversations(); poll() }
        }
        async function startDirect(u) {
            const data = await api(`/messages/api/direct/${u.id}`, 'POST')
            if (!data) return
            dialog.value = null
            await loadConversations()
            openConversation(data.channel.uuid)
        }
        const browseQ = ref(''), browseList = ref([]), browsing = ref(false)
        async function loadBrowse() {
            browsing.value = true
            const data = await api('/messages/api/browse?q=' + encodeURIComponent(browseQ.value))
            browseList.value = data ? data.channels : []
            browsing.value = false
        }
        let browseTimer = null
        watch(browseQ, () => { clearTimeout(browseTimer); browseTimer = setTimeout(loadBrowse, 250) })
        function openBrowse() { dialog.value = 'browse'; loadBrowse() }
        function openFromBrowse(c) { dialog.value = null; openConversation(c.uuid) }

        // ── helpers for the template ──
        const convIcon = c => c.kind === 'direct' ? null : (c.is_private ? 'fa-solid fa-lock' : 'fa-solid fa-hashtag')
        const roleLabel = { owner: 'Owner', moderator: 'Moderator', member: 'Member' }

        function onVisibility() { if (!document.hidden) { poll(); loadConversations(); markRead() } }
        function onGlobalKey(e) {
            if (e.key === 'k' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); const el = document.getElementById('chat-filter'); el && el.focus() }
            if (e.key === 'Escape' && dialog.value) dialog.value = null
        }

        onMounted(async () => {
            await loadConversations()
            loadPublic()
            const focusId = parseInt(new URLSearchParams(location.search).get('m')) || null
            if (props.openUuid && props.start && props.start.prefill) {
                // "Write to the author" from a rule, bundle…: the message starts with a link to it
                const r = props.start.prefill, token = `#[${r.label.replace(/[\[\]()]/g, ' ')}](${r.kind}:${r.key}) `
                try {
                    const key = 'rz-draft:' + props.openUuid, old = localStorage.getItem(key) || ''
                    if (!old.includes(`(${r.kind}:${r.key})`)) localStorage.setItem(key, token + old)
                } catch { }
                history.replaceState(null, '', `/messages/c/${props.openUuid}`)
            }
            if (props.openUuid) await openConversation(props.openUuid, focusId)
            else if (props.start && props.start.ref) newChannel(props.start.ref)
            pollTimer = setInterval(poll, 3000)
            listTimer = setInterval(() => { loadConversations(); if (++listTicks % 5 === 0) loadPublic() }, 12000)
            document.addEventListener('visibilitychange', onVisibility)
            document.addEventListener('keydown', onGlobalKey)
        })
        onUnmounted(() => {
            clearInterval(pollTimer); clearInterval(listTimer)
            document.removeEventListener('visibilitychange', onVisibility)
            document.removeEventListener('keydown', onGlobalKey)
        })

        return {
            REF_ICONS, conversations, listLoaded, filter, starred, channels, directs, unreadTotal, mobileList,
            current, msgs, hasMore, loadingMsgs, rows, scroller, highlight, replyTo, editing, panel, composer, emojiFor,
            canModerate, canPin, memberIds, settings, toAdd, searchQ, searchResults, searching, searchScope,
            dialog, form, browseQ, browseList, browsing, roleLabel,
            openConversation, loadOlder, onScroll, send, cancelCompose, editLast, react, removeMsg, pin, copyLink, quote,
            join, leave, toggleMe, saveSettings, deleteChannel, addPeople, removeMember, setRole, openResult,
            EMAIL_MODES, emailMode, setEmailMode, loadEmailMode, joinable, quickJoin, inviteUrl, setInvite, copyInvite, onConvKey, onFilterKey, browseInput, focusBrowse, onBrowseKey, dialogEl, trapFocus, convFlag, convRead, convClear, convLeave, convDelete, canDeleteChannel, newChannel, createChannel, startDirect, pickAvatar, uploadAvatar, removeAvatar, openBrowse, openFromBrowse, convIcon, reactorNames,
            timeLabel, listTime, plainMessage,
        }
    },
    template: `
<div class="chat" :class="{ 'chat--panel': current && panel, 'chat--list': mobileList }">

  <!-- ═════ Conversations ═════ -->
  <aside class="chat-list">
    <div class="chat-list__head">
      <div class="chat-list__title">Messages <span v-if="unreadTotal" class="chat-badge">[[ unreadTotal ]]</span></div>
      <div class="dropdown">
        <button type="button" class="chat-new" data-bs-toggle="dropdown" title="New conversation, email settings" @click="emailMode === null && loadEmailMode()"><i class="fa-solid fa-pen-to-square"></i></button>
        <ul class="dropdown-menu dropdown-menu-end">
          <li><button type="button" class="dropdown-item" @click="newChannel()"><i class="fa-solid fa-hashtag me-2 text-primary"></i>New channel</button></li>
          <li><button type="button" class="dropdown-item" @click="dialog = 'direct'"><i class="fa-solid fa-user me-2 text-primary"></i>Message someone</button></li>
          <li><hr class="dropdown-divider"></li>
          <li><button type="button" class="dropdown-item" @click="openBrowse"><i class="fa-solid fa-compass me-2 text-primary"></i>Browse public channels</button></li>
          <li><hr class="dropdown-divider"></li>
          <li><h6 class="dropdown-header">Email me unread messages</h6></li>
          <li v-for="o in EMAIL_MODES" :key="o.value"><button type="button" class="dropdown-item" @click="setEmailMode(o.value)">
            <i class="me-2" :class="emailMode === o.value ? 'fa-solid fa-circle-check text-primary' : 'fa-regular fa-circle'"></i>[[ o.label ]]</button></li>
        </ul>
      </div>
    </div>
    <div class="chat-list__filter">
      <i class="fa-solid fa-magnifying-glass"></i>
      <input id="chat-filter" v-model="filter" placeholder="Find a conversation (Ctrl+K)" aria-label="Find a conversation" @keydown="onFilterKey">
    </div>

    <div class="chat-list__scroll">
      <div v-if="!listLoaded" class="chat-empty"><i class="fa-solid fa-circle-notch fa-spin"></i></div>
      <template v-else>
        <div v-if="!conversations.length" class="chat-welcome">
          <i class="fa-regular fa-comments"></i>
          <p>No conversation yet.</p>
          <div class="chat-welcome__actions">
            <button type="button" class="chat-link-btn" @click="newChannel()"><i class="fa-solid fa-hashtag"></i>New channel</button>
            <button type="button" class="chat-link-btn" @click="openBrowse"><i class="fa-solid fa-compass"></i>Browse</button>
          </div>
        </div>
        <template v-for="section in [{ key: 'star', title: 'Starred', icon: 'fa-solid fa-star', items: starred }, { key: 'chan', title: 'Channels', icon: 'fa-solid fa-hashtag', items: channels }, { key: 'dm', title: 'Direct messages', icon: 'fa-solid fa-user', items: directs }]" :key="section.key">
          <div v-if="section.items.length" class="chat-list__section">
            <div class="chat-list__label"><span><i :class="section.icon" class="me-1"></i>[[ section.title ]]</span>
              <button v-if="section.key === 'chan'" type="button" class="chat-mini" title="Browse public channels" @click="openBrowse"><i class="fa-solid fa-compass"></i></button>
              <button v-if="section.key === 'dm'" type="button" class="chat-mini" title="Message someone" @click="dialog = 'direct'"><i class="fa-solid fa-plus"></i></button>
            </div>
            <div v-for="c in section.items" :key="c.uuid" class="chat-conv" role="button" tabindex="0" :data-conv="c.uuid"
                    :class="['chat-conv--' + c.kind, { 'is-open': current && current.uuid === c.uuid, 'is-unread': c.unread && !c.is_muted, 'is-muted': c.is_muted }]"
                    @click="openConversation(c.uuid)" @keydown="onConvKey($event, c)">
              <span v-if="c.kind === 'direct'" class="chat-avatar">
                <img v-if="c.other && c.other.avatar" :src="c.other.avatar" alt=""><template v-else>[[ c.other ? c.other.initial : '?' ]]</template>
              </span>
              <span v-else class="chat-avatar chat-avatar--channel"><img v-if="c.avatar" :src="c.avatar" alt=""><i v-else :class="convIcon(c)"></i></span>
              <span class="chat-conv__body">
                <span class="chat-conv__top">
                  <span class="chat-conv__name"><span v-if="c.kind === 'channel'" class="chat-conv__hash">[[ c.is_private ? '' : '#' ]]<i v-if="c.is_private" class="fa-solid fa-lock"></i></span>[[ c.name ]]</span>
                  <i v-if="c.is_muted" class="fa-solid fa-bell-slash chat-conv__flag" title="Muted"></i>
                  <span class="chat-conv__time">[[ listTime(c.last_message_at) ]]</span>
                </span>
                <span class="chat-conv__bottom">
                  <span v-if="c.kind === 'channel' && !c.last" class="chat-conv__last"><i class="fa-solid fa-user-group me-1"></i>[[ c.member_count ]] · [[ c.is_private ? 'Private' : 'Public' ]] channel</span>
                  <span v-else class="chat-conv__last">
                    <template v-if="c.last"><b v-if="c.kind === 'channel' || c.last.author_id === currentUserId">[[ c.last.author_id === currentUserId ? 'You' : c.last.author ]]: </b>[[ c.last.text ]]</template>
                    <i v-else-if="c.ref" :class="c.ref.icon" class="me-1"></i><template v-if="!c.last && c.ref">[[ c.ref.label ]]</template>
                    <template v-if="!c.last && !c.ref">[[ c.topic || 'No message yet' ]]</template>
                  </span>
                  <span v-if="c.unread" class="chat-badge" :class="{ 'chat-badge--muted': c.is_muted }">[[ c.unread ]]</span>
                </span>
              </span>
              <div class="dropdown chat-conv__menu" @click.stop>
                  <button type="button" class="chat-mini" data-bs-toggle="dropdown" data-bs-popper-config='{"strategy":"fixed"}' title="More"><i class="fa-solid fa-ellipsis"></i></button>
                  <ul class="dropdown-menu dropdown-menu-end">
                    <li v-if="c.unread"><button type="button" class="dropdown-item" @click="convRead(c)"><i class="fa-solid fa-check-double me-2"></i>Mark as read</button></li>
                    <li><button type="button" class="dropdown-item" @click="convFlag(c, 'starred')"><i class="me-2" :class="c.is_starred ? 'fa-regular fa-star' : 'fa-solid fa-star'"></i>[[ c.is_starred ? 'Unstar' : 'Star' ]]</button></li>
                    <li><button type="button" class="dropdown-item" @click="convFlag(c, 'muted')"><i class="me-2" :class="c.is_muted ? 'fa-regular fa-bell' : 'fa-solid fa-bell-slash'"></i>[[ c.is_muted ? 'Unmute' : 'Mute' ]]</button></li>
                    <li><hr class="dropdown-divider"></li>
                    <li><button type="button" class="dropdown-item text-danger" @click="convClear(c)"><i class="fa-solid fa-eraser me-2"></i>Delete for me</button></li>
                    <li v-if="c.kind === 'channel'"><button type="button" class="dropdown-item text-danger" @click="convLeave(c)"><i class="fa-solid fa-right-from-bracket me-2"></i>Leave the channel</button></li>
                    <li v-if="canDeleteChannel(c)"><button type="button" class="dropdown-item text-danger" @click="convDelete(c)"><i class="fa-solid fa-trash me-2"></i>Delete the channel for everyone</button></li>
                  </ul>
                </div>
            </div>
          </div>
        </template>
        <div v-if="joinable.length" class="chat-list__section">
          <div class="chat-list__label"><span><i class="fa-solid fa-compass me-1"></i>Join a channel</span>
            <button type="button" class="chat-mini" title="All public channels" @click="openBrowse"><i class="fa-solid fa-arrow-right"></i></button></div>
          <div v-for="c in joinable" :key="c.uuid" class="chat-conv chat-conv--join" role="button" tabindex="0" :data-conv="c.uuid"
               @click="openConversation(c.uuid)" @keydown="onConvKey($event, c)">
            <span class="chat-avatar chat-avatar--channel"><img v-if="c.avatar" :src="c.avatar" alt=""><i v-else class="fa-solid fa-hashtag"></i></span>
            <span class="chat-conv__body">
              <span class="chat-conv__name">[[ c.name ]]</span>
              <span class="chat-conv__last"><i class="fa-solid fa-user-group me-1"></i>[[ c.member_count ]] · [[ c.topic || 'Public channel' ]]</span>
            </span>
            <button type="button" class="chat-join-btn" @click.stop="quickJoin(c)" title="Join">Join</button>
          </div>
        </div>
      </template>
    </div>
  </aside>

  <!-- ═════ Conversation ═════ -->
  <section class="chat-main">
    <div v-if="!current" class="chat-placeholder">
      <div class="chat-placeholder__icon"><i class="fa-regular fa-comments"></i></div>
      <h4>Talk with the community</h4>
      <p>Write privately to someone, or open a channel — public or private — to work on rules, bundles, a CVE or an ATT&amp;CK technique together.
         Type <code>@</code> to mention someone and <code>#</code> to link anything in Rulezet.</p>
      <div class="d-flex gap-2 flex-wrap justify-content-center">
        <button type="button" class="btn btn-primary rounded-pill px-4" @click="newChannel()"><i class="fa-solid fa-hashtag me-1"></i>New channel</button>
        <button type="button" class="btn btn-outline-primary rounded-pill px-4" @click="dialog = 'direct'"><i class="fa-solid fa-user me-1"></i>Message someone</button>
        <button type="button" class="btn btn-outline-secondary rounded-pill px-4" @click="openBrowse"><i class="fa-solid fa-compass me-1"></i>Browse</button>
      </div>
    </div>

    <template v-else>
      <header class="chat-head" :class="'chat-head--' + current.kind">
        <button type="button" class="chat-icon-btn chat-back" @click="mobileList = true" title="Conversations"><i class="fa-solid fa-arrow-left"></i></button>
        <span v-if="current.kind === 'direct'" class="chat-avatar">
          <img v-if="current.other && current.other.avatar" :src="current.other.avatar" alt=""><template v-else>[[ current.other ? current.other.initial : '?' ]]</template>
        </span>
        <span v-else class="chat-avatar chat-avatar--channel"><img v-if="current.avatar" :src="current.avatar" alt=""><i v-else :class="convIcon(current)"></i></span>
        <div class="chat-head__text">
          <div class="chat-head__name">
            <a v-if="current.kind === 'direct' && current.other && current.other.id" :href="'/account/detail_user/' + current.other.id">[[ current.name ]]</a>
            <template v-else>[[ current.name ]]</template>
            <span v-if="current.is_archived" class="chat-tag">Archived</span>
            <span v-if="current.kind === 'channel'" class="chat-tag chat-tag--kind" :title="current.is_private ? 'Only members see it' : 'Every signed-in user can read and join it'"><i :class="current.is_private ? 'fa-solid fa-lock' : 'fa-solid fa-globe'"></i> [[ current.is_private ? 'Private channel' : 'Public channel' ]]</span>
            <span v-else class="chat-tag chat-tag--dm"><i class="fa-solid fa-user-lock"></i> Direct message</span>
          </div>
          <div class="chat-head__sub">
            <a v-if="current.ref && current.ref.url" :href="current.ref.url" class="chat-chip" :class="'chat-chip--' + current.ref.kind"><i :class="current.ref.icon"></i>[[ current.ref.label ]]</a>
            <span v-else-if="current.ref" class="chat-chip"><i :class="current.ref.icon"></i>[[ current.ref.label ]]</span>
            <span v-if="current.topic" class="chat-head__topic" :title="current.topic">[[ current.topic ]]</span>
          </div>
        </div>
        <div class="chat-head__actions">
          <button v-if="current.kind === 'channel'" type="button" class="chat-people" @click="panel = panel === 'members' ? '' : 'members'" title="Members">
            <i class="fa-solid fa-user-group"></i>[[ current.member_count ]]
          </button>
          <button v-if="current.is_member" type="button" class="chat-icon-btn" :class="{ 'is-on': current.is_starred }" @click="toggleMe('starred')" :title="current.is_starred ? 'Unstar' : 'Star'">
            <i :class="current.is_starred ? 'fa-solid fa-star' : 'fa-regular fa-star'"></i></button>
          <button v-if="current.is_member" type="button" class="chat-icon-btn" :class="{ 'is-on': current.is_muted }" @click="toggleMe('muted')" :title="current.is_muted ? 'Unmute' : 'Mute — no notification, no count'">
            <i :class="current.is_muted ? 'fa-solid fa-bell-slash' : 'fa-regular fa-bell'"></i></button>
          <button type="button" class="chat-icon-btn" :class="{ 'is-on': panel === 'search' }" @click="panel = panel === 'search' ? '' : 'search'" title="Search messages"><i class="fa-solid fa-magnifying-glass"></i></button>
          <button type="button" class="chat-icon-btn" :class="{ 'is-on': panel && panel !== 'search' }" @click="panel = panel && panel !== 'search' ? '' : 'about'" title="Details"><i class="fa-solid fa-circle-info"></i></button>
          <template v-if="current.is_member"><div class="dropdown chat-conv__menu" @click.stop>
                  <button type="button" class="chat-icon-btn" data-bs-toggle="dropdown" data-bs-popper-config='{"strategy":"fixed"}' title="More"><i class="fa-solid fa-ellipsis"></i></button>
                  <ul class="dropdown-menu dropdown-menu-end">
                    <li v-if="current.unread"><button type="button" class="dropdown-item" @click="convRead(current)"><i class="fa-solid fa-check-double me-2"></i>Mark as read</button></li>
                    <li><button type="button" class="dropdown-item" @click="convFlag(current, 'starred')"><i class="me-2" :class="current.is_starred ? 'fa-regular fa-star' : 'fa-solid fa-star'"></i>[[ current.is_starred ? 'Unstar' : 'Star' ]]</button></li>
                    <li><button type="button" class="dropdown-item" @click="convFlag(current, 'muted')"><i class="me-2" :class="current.is_muted ? 'fa-regular fa-bell' : 'fa-solid fa-bell-slash'"></i>[[ current.is_muted ? 'Unmute' : 'Mute' ]]</button></li>
                    <li><hr class="dropdown-divider"></li>
                    <li><button type="button" class="dropdown-item text-danger" @click="convClear(current)"><i class="fa-solid fa-eraser me-2"></i>Delete for me</button></li>
                    <li v-if="current.kind === 'channel'"><button type="button" class="dropdown-item text-danger" @click="convLeave(current)"><i class="fa-solid fa-right-from-bracket me-2"></i>Leave the channel</button></li>
                    <li v-if="canDeleteChannel(current)"><button type="button" class="dropdown-item text-danger" @click="convDelete(current)"><i class="fa-solid fa-trash me-2"></i>Delete the channel for everyone</button></li>
                  </ul>
                </div></template>
        </div>
      </header>

      <div class="chat-pinned" v-if="current.pinned && current.pinned.length" @click="panel = 'pinned'">
        <i class="fa-solid fa-thumbtack"></i>
        <span><b>[[ current.pinned.length ]] pinned</b> · [[ plainMessage(current.pinned[0].content).slice(0, 90) ]]</span>
      </div>

      <div class="chat-scroll" ref="scroller" @scroll.passive="onScroll">
        <div v-if="hasMore" class="chat-more"><button type="button" class="btn btn-sm btn-light rounded-pill" @click="loadOlder" :disabled="loadingMsgs">
          <i :class="loadingMsgs ? 'fa-solid fa-circle-notch fa-spin' : 'fa-solid fa-clock-rotate-left'" class="me-1"></i>Older messages</button></div>
        <div v-else-if="!loadingMsgs" class="chat-start">
          <span class="chat-avatar chat-avatar--lg" :class="{ 'chat-avatar--channel': current.kind === 'channel' }">
            <template v-if="current.kind === 'direct'"><img v-if="current.other && current.other.avatar" :src="current.other.avatar" alt=""><template v-else>[[ current.other ? current.other.initial : '?' ]]</template></template>
            <img v-else-if="current.avatar" :src="current.avatar" alt=""><i v-else :class="convIcon(current)"></i>
          </span>
          <h5>[[ current.kind === 'direct' ? current.name : current.name ]]</h5>
          <p v-if="current.kind === 'direct'">This is the start of your private conversation with <b>[[ current.name ]]</b>. Only the two of you see it.</p>
          <p v-else>The beginning of <b>#[[ current.name ]]</b><template v-if="current.created_by"> — created by [[ current.created_by.name ]]</template>.
            <template v-if="current.ref"> About <i :class="current.ref.icon"></i> [[ current.ref.label ]].</template></p>
        </div>

        <template v-for="r in rows" :key="r.key">
          <div v-if="r.type === 'day'" class="chat-day"><span>[[ r.label ]]</span></div>
          <div v-else-if="r.type === 'new'" class="chat-newline"><span>New</span></div>
          <div v-else-if="r.type === 'system'" class="chat-system" :id="'msg-' + r.m.id"><i class="fa-solid fa-circle-info"></i>[[ r.m.content ]] · [[ timeLabel(r.m.created_at) ]]</div>
          <div v-else class="chat-msg" :id="'msg-' + r.m.id"
               :class="{ 'is-grouped': r.grouped, 'is-mine': r.m.is_mine, 'is-highlight': highlight === r.m.id, 'is-editing': editing && editing.id === r.m.id, 'is-pinned': r.m.is_pinned }">
            <div class="chat-msg__side">
              <a v-if="!r.grouped" :href="r.m.author && r.m.author.id ? '/account/detail_user/' + r.m.author.id : null" class="chat-avatar">
                <img v-if="r.m.author && r.m.author.avatar" :src="r.m.author.avatar" alt=""><template v-else>[[ r.m.author ? r.m.author.initial : '?' ]]</template>
              </a>
              <span v-else class="chat-msg__hover-time">[[ timeLabel(r.m.created_at) ]]</span>
            </div>
            <div class="chat-msg__main">
              <div v-if="!r.grouped" class="chat-msg__meta">
                <a :href="r.m.author && r.m.author.id ? '/account/detail_user/' + r.m.author.id : null" class="chat-msg__author">[[ r.m.author ? r.m.author.name : 'Deleted user' ]]</a>
                <span v-if="r.m.author && r.m.author.is_admin" class="chat-tag chat-tag--admin">Admin</span>
                <span class="chat-msg__time" :title="new Date(r.m.created_at).toLocaleString()">[[ timeLabel(r.m.created_at) ]]</span>
                <i v-if="r.m.is_pinned" class="fa-solid fa-thumbtack chat-msg__pin" title="Pinned"></i>
              </div>
              <button v-if="r.m.reply_to" type="button" class="chat-quote" @click="openResult({ id: r.m.reply_to.id, channel: current })">
                <i class="fa-solid fa-reply fa-flip-horizontal"></i><b>[[ r.m.reply_to.author ]]</b>
                <span>[[ r.m.reply_to.deleted ? 'Deleted message' : plainMessage(r.m.reply_to.content) ]]</span>
              </button>
              <div v-if="r.m.is_deleted" class="chat-msg__deleted"><i class="fa-solid fa-ban me-1"></i>Message deleted</div>
              <message-text v-else :text="r.m.content"></message-text>
              <span v-if="r.m.edited_at && !r.m.is_deleted" class="chat-msg__edited" :title="new Date(r.m.edited_at).toLocaleString()">(edited)</span>
              <div v-if="r.m.reactions.length" class="chat-reactions">
                <button v-for="g in r.m.reactions" :key="g.emoji" type="button" class="chat-reaction" :class="{ 'is-mine': g.mine }"
                        :title="reactorNames(g)" :disabled="!current.can_post" @click="react(r.m, g.emoji)">[[ g.emoji ]] <b>[[ g.count ]]</b></button>
                <button v-if="current.can_post" type="button" class="chat-reaction chat-reaction--add" title="Add a reaction" @click="emojiFor = emojiFor === r.m.id ? null : r.m.id"><i class="fa-regular fa-face-smile"></i></button>
              </div>
            </div>
            <div v-if="!r.m.is_deleted" class="chat-msg__tools">
              <template v-if="current.can_post">
                <button v-for="e in reactions.slice(0, 3)" :key="e" type="button" class="chat-tool" :title="'React ' + e" @click="react(r.m, e)">[[ e ]]</button>
                <button type="button" class="chat-tool" title="More reactions" @click="emojiFor = emojiFor === r.m.id ? null : r.m.id"><i class="fa-regular fa-face-smile"></i></button>
                <button type="button" class="chat-tool" title="Reply" @click="quote(r.m)"><i class="fa-solid fa-reply"></i></button>
              </template>
              <button v-if="r.m.is_mine" type="button" class="chat-tool" title="Edit" @click="editing = r.m; replyTo = null"><i class="fa-solid fa-pen"></i></button>
              <button v-if="canPin" type="button" class="chat-tool" :title="r.m.is_pinned ? 'Unpin' : 'Pin'" @click="pin(r.m)"><i class="fa-solid fa-thumbtack"></i></button>
              <button type="button" class="chat-tool" title="Copy link" @click="copyLink(r.m)"><i class="fa-solid fa-link"></i></button>
              <button v-if="r.m.is_mine || canModerate" type="button" class="chat-tool chat-tool--danger" title="Delete" @click="removeMsg(r.m)"><i class="fa-solid fa-trash"></i></button>
            </div>
            <div v-if="emojiFor === r.m.id" class="chat-emoji" role="menu" @click.stop @keydown.esc.stop="emojiFor = null" @vue:mounted="({ el }) => el.querySelector('button')?.focus()">
              <button v-for="e in reactions" :key="e" type="button" @click="react(r.m, e)">[[ e ]]</button>
            </div>
          </div>
        </template>
      </div>

      <div v-if="current.kind === 'channel' && !current.is_member && !current.is_private && !current.is_archived" class="chat-join">
        <span><i class="fa-solid fa-globe me-1 text-primary"></i>Public channel — you can read <b>#[[ current.name ]]</b>, and anyone can join it.</span>
        <button type="button" class="btn btn-primary rounded-pill px-4" @click="join"><i class="fa-solid fa-right-to-bracket me-1"></i>Join the channel</button>
      </div>
      <div v-else-if="current.is_archived" class="chat-join"><span><i class="fa-solid fa-box-archive me-1"></i>This channel is archived — read only.</span></div>
      <div v-if="current.kind === 'channel' && !current.is_private && current.is_member && !current.is_archived" class="chat-public-strip">
        <i class="fa-solid fa-globe"></i>Public channel — anyone signed in can join and read what you write here.
      </div>
      <message-composer v-if="!(current.kind === 'channel' && !current.is_member && !current.is_private) && !current.is_archived" ref="composer" :disabled="!current.can_post" :upload-url="'/messages/api/channels/' + current.uuid + '/images'" :reply-to="replyTo" :editing="editing" :max-length="maxLength"
                        :draft-key="current.uuid" :placeholder="current.kind === 'direct' ? 'Message ' + current.name : 'Message #' + current.name"
                        @send="send" @cancel="cancelCompose" @edit-last="editLast"></message-composer>
    </template>
  </section>

  <!-- ═════ Details ═════ -->
  <aside v-if="current && panel" class="chat-panel">
    <div class="chat-panel__head">
      <div class="chat-panel__tabs">
        <button v-for="t in (current.kind === 'channel' ? ['about', 'members', 'pinned', 'settings', 'search'] : ['about', 'pinned', 'search'])" :key="t"
                type="button" :class="{ 'is-on': panel === t }" @click="panel = t">
          [[ { about: 'About', members: 'Members', pinned: 'Pinned', settings: 'Settings', search: 'Search' }[t] ]]
        </button>
      </div>
      <button type="button" class="chat-icon-btn" @click="panel = ''" title="Close"><i class="fa-solid fa-xmark"></i></button>
    </div>
    <div class="chat-panel__body">

      <template v-if="panel === 'about'">
        <div v-if="current.kind === 'direct' && current.other" class="chat-about-user">
          <span class="chat-avatar chat-avatar--lg"><img v-if="current.other.avatar" :src="current.other.avatar" alt=""><template v-else>[[ current.other.initial ]]</template></span>
          <h5>[[ current.other.name ]]</h5>
          <a v-if="current.other.id" :href="'/account/detail_user/' + current.other.id" class="btn btn-sm btn-outline-primary rounded-pill px-3">View profile</a>
        </div>
        <template v-else>
          <div class="chat-field"><div class="chat-field__label">Topic</div><div>[[ current.topic || '—' ]]</div></div>
          <div v-if="current.ref" class="chat-field"><div class="chat-field__label">About</div>
            <a v-if="current.ref.url" :href="current.ref.url" class="chat-chip" :class="'chat-chip--' + current.ref.kind"><i :class="current.ref.icon"></i>[[ current.ref.label ]]</a>
            <span v-else class="chat-chip"><i :class="current.ref.icon"></i>[[ current.ref.label ]] (not available)</span></div>
          <div class="chat-field"><div class="chat-field__label">Visibility</div>
            <div><i :class="current.is_private ? 'fa-solid fa-lock' : 'fa-solid fa-globe'" class="me-1 text-primary"></i>[[ current.is_private ? 'Private — members only (and admins, to moderate)' : 'Public — anyone with a Rulezet account can join and read every message' ]]</div></div>
          <div class="chat-field"><div class="chat-field__label">Created</div>
            <div>[[ new Date(current.created_at).toLocaleDateString(undefined, { dateStyle: 'long' }) ]]<template v-if="current.created_by"> by [[ current.created_by.name ]]</template></div></div>
          <div class="chat-field"><div class="chat-field__label">Your role</div><div>[[ current.my_role ? roleLabel[current.my_role] : 'Not a member' ]]<template v-if="isAdmin && current.my_role !== 'owner'"> · Admin</template></div></div>
          <button v-if="current.is_member" type="button" class="btn btn-sm btn-outline-danger rounded-pill px-3 mt-2" @click="leave"><i class="fa-solid fa-right-from-bracket me-1"></i>Leave the channel</button>
        </template>
      </template>

      <template v-else-if="panel === 'members'">
        <div v-if="current.can_invite" class="d-flex gap-2 mb-3 flex-wrap">
          <button type="button" class="btn btn-sm btn-primary rounded-pill px-3" @click="toAdd = []; dialog = 'add'"><i class="fa-solid fa-user-plus me-1"></i>Add people</button>
          <button v-if="current.can_manage" type="button" class="btn btn-sm btn-outline-primary rounded-pill px-3" @click="panel = 'settings'"><i class="fa-solid fa-link me-1"></i>Invite link</button>
        </div>
        <div class="chat-field__label">[[ current.members.length ]] member[[ current.members.length === 1 ? '' : 's' ]]</div>
        <div v-for="u in current.members" :key="u.id" class="chat-member">
          <a :href="'/account/detail_user/' + u.id" class="chat-avatar"><img v-if="u.avatar" :src="u.avatar" alt=""><template v-else>[[ u.initial ]]</template></a>
          <div class="chat-member__name"><a :href="'/account/detail_user/' + u.id">[[ u.name ]]</a>
            <span v-if="u.role !== 'member'" class="chat-tag" :class="'chat-tag--' + u.role">[[ roleLabel[u.role] ]]</span></div>
          <div v-if="u.id !== currentUserId" class="dropdown">
            <button type="button" class="chat-icon-btn" data-bs-toggle="dropdown" title="Actions"><i class="fa-solid fa-ellipsis"></i></button>
            <ul class="dropdown-menu dropdown-menu-end">
              <li><button type="button" class="dropdown-item" @click="startDirect({ id: u.id })"><i class="fa-solid fa-envelope me-2"></i>Message</button></li>
              <template v-if="current.can_own">
                <li v-if="u.role !== 'moderator'"><button type="button" class="dropdown-item" @click="setRole(u, 'moderator')"><i class="fa-solid fa-user-shield me-2"></i>Make moderator</button></li>
                <li v-if="u.role === 'moderator'"><button type="button" class="dropdown-item" @click="setRole(u, 'member')"><i class="fa-solid fa-user me-2"></i>Make member</button></li>
                <li v-if="u.role !== 'owner'"><button type="button" class="dropdown-item" @click="setRole(u, 'owner')"><i class="fa-solid fa-crown me-2"></i>Make owner</button></li>
              </template>
              <li v-if="current.can_manage && u.role !== 'owner'"><button type="button" class="dropdown-item text-danger" @click="removeMember(u)"><i class="fa-solid fa-user-minus me-2"></i>Remove</button></li>
            </ul>
          </div>
        </div>
      </template>

      <template v-else-if="panel === 'pinned'">
        <div v-if="!current.pinned.length" class="chat-empty-small">No pinned message. [[ canPin ? 'Pin one from its menu.' : '' ]]</div>
        <button v-for="p in current.pinned" :key="p.id" type="button" class="chat-result" @click="openResult({ id: p.id, channel: current })">
          <div class="chat-result__meta"><b>[[ p.author ? p.author.name : '' ]]</b> · [[ new Date(p.created_at).toLocaleDateString() ]]</div>
          <div class="chat-result__text">[[ plainMessage(p.content).slice(0, 220) ]]</div>
        </button>
      </template>

      <template v-else-if="panel === 'settings'">
        <template v-if="current.can_manage">
          <label class="chat-field__label">Picture</label>
          <div class="chat-pic">
            <span class="chat-avatar chat-avatar--lg chat-avatar--channel"><img v-if="current.avatar" :src="current.avatar" alt=""><i v-else :class="convIcon(current)"></i></span>
            <div class="d-flex flex-column gap-1">
              <label class="btn btn-sm btn-outline-primary rounded-pill px-3 mb-0"><i class="fa-solid fa-image me-1"></i>[[ current.avatar ? 'Change' : 'Upload' ]]
                <input type="file" accept="image/png,image/jpeg,image/gif,image/webp" hidden @change="uploadAvatar($event.target.files[0]); $event.target.value = ''"></label>
              <button v-if="current.avatar" type="button" class="btn btn-sm btn-link text-danger p-0" @click="removeAvatar">Remove</button>
              <span class="small text-muted">PNG, JPEG, GIF or WebP · 2 MB</span>
            </div>
          </div>
          <label class="chat-field__label">Name</label>
          <input class="form-control form-control-sm mb-3" v-model="settings.name" maxlength="80">
          <label class="chat-field__label">Topic</label>
          <textarea class="form-control form-control-sm mb-3" v-model="settings.topic" maxlength="300" rows="3"></textarea>
          <div class="form-check form-switch mb-3">
            <input class="form-check-input" type="checkbox" id="chat-private" v-model="settings.is_private">
            <label class="form-check-label" for="chat-private">Private — only members see it</label>
          </div>
          <div v-if="!settings.is_private" class="chat-public-note mb-3" role="note">
            <i class="fa-solid fa-globe"></i><span><b>Public:</b> anyone with a Rulezet account can join it and read every message, the old ones too.</span>
          </div>
          <div class="form-check form-switch mb-3">
            <input class="form-check-input" type="checkbox" id="chat-mci" v-model="settings.members_can_invite">
            <label class="form-check-label" for="chat-mci">Every member can add people <span class="d-block small text-muted">Otherwise only the owner, moderators and admins</span></label>
          </div>
          <button type="button" class="btn btn-sm btn-primary rounded-pill px-4" @click="saveSettings()">Save</button>
          <p v-if="settings.is_private && !current.is_private" class="small text-muted mt-2 mb-0"><i class="fa-solid fa-circle-info me-1"></i>The current members stay; new people join only when added or with the invite link.</p>
          <hr>
          <label class="chat-field__label">Invite link</label>
          <p class="small text-muted mb-2">Whoever has it joins — even a private channel. Renew it to stop the old one.</p>
          <template v-if="current.invite_code">
            <div class="chat-invite"><input class="form-control form-control-sm" :value="inviteUrl" readonly @focus="$event.target.select()">
              <button type="button" class="btn btn-sm btn-primary" @click="copyInvite" title="Copy"><i class="fa-solid fa-copy"></i></button></div>
            <div class="d-flex gap-2 mt-2">
              <button type="button" class="btn btn-sm btn-outline-secondary rounded-pill px-3" @click="setInvite(true)"><i class="fa-solid fa-rotate me-1"></i>Renew</button>
              <button type="button" class="btn btn-sm btn-outline-danger rounded-pill px-3" @click="setInvite(false)">Turn off</button>
            </div>
          </template>
          <button v-else type="button" class="btn btn-sm btn-outline-primary rounded-pill px-3" @click="setInvite(true)"><i class="fa-solid fa-link me-1"></i>Make an invite link</button>
          <hr>
          <button type="button" class="btn btn-sm btn-outline-secondary rounded-pill px-3 mb-2 w-100" @click="saveSettings({ is_archived: !current.is_archived })">
            <i class="fa-solid fa-box-archive me-1"></i>[[ current.is_archived ? 'Reopen the channel' : 'Archive — read only' ]]</button>
          <button v-if="current.can_own" type="button" class="btn btn-sm btn-outline-danger rounded-pill px-3 w-100" @click="deleteChannel">
            <i class="fa-solid fa-trash me-1"></i>Delete the channel</button>
        </template>
        <div v-else class="chat-empty-small">Only the owner, the moderators and admins change the channel.</div>
      </template>

      <template v-else-if="panel === 'search'">
        <div class="chat-list__filter mb-2"><i class="fa-solid fa-magnifying-glass"></i><input v-model="searchQ" placeholder="Search messages" autofocus></div>
        <div class="chat-scope">
          <button type="button" :class="{ 'is-on': searchScope === 'here' }" @click="searchScope = 'here'">This conversation</button>
          <button type="button" :class="{ 'is-on': searchScope === 'all' }" @click="searchScope = 'all'">All my conversations</button>
        </div>
        <div v-if="searching" class="chat-empty-small"><i class="fa-solid fa-circle-notch fa-spin"></i></div>
        <div v-else-if="searchQ.trim().length >= 2 && !searchResults.length" class="chat-empty-small">Nothing found.</div>
        <button v-for="r in searchResults" :key="r.id" type="button" class="chat-result" @click="openResult(r)">
          <div class="chat-result__meta"><b>[[ r.author ? r.author.name : '' ]]</b><template v-if="searchScope === 'all'"> in [[ r.channel.kind === 'direct' ? r.channel.name : '#' + r.channel.name ]]</template> · [[ new Date(r.created_at).toLocaleDateString() ]]</div>
          <div class="chat-result__text">[[ plainMessage(r.content).slice(0, 220) ]]</div>
        </button>
      </template>
    </div>
  </aside>

  <!-- ═════ Dialogs ═════ -->
  <div v-if="dialog" class="chat-modal" @mousedown.self="dialog = null">
    <div class="chat-modal__card" :class="'chat-modal__card--' + dialog" role="dialog" aria-modal="true" ref="dialogEl" @keydown="trapFocus">
      <template v-if="dialog === 'channel'">
        <div class="chat-modal__head"><h5><i class="fa-solid fa-hashtag me-2 text-primary"></i>New channel</h5>
          <button type="button" class="chat-icon-btn" @click="dialog = null"><i class="fa-solid fa-xmark"></i></button></div>
        <div v-if="form.ref" class="chat-modal__ref"><span>About</span>
          <span class="chat-chip" :class="'chat-chip--' + form.ref.kind"><i :class="form.ref.icon"></i>[[ form.ref.label ]]</span>
          <button type="button" class="chat-icon-btn" title="Not about it" @click="form.ref = null"><i class="fa-solid fa-xmark"></i></button></div>
        <div class="chat-pic">
          <label class="chat-avatar chat-avatar--lg chat-avatar--channel chat-pic__pick" title="Add a picture (optional)">
            <img v-if="form.preview" :src="form.preview" alt=""><i v-else class="fa-solid fa-camera"></i>
            <input type="file" accept="image/png,image/jpeg,image/gif,image/webp" hidden @change="pickAvatar($event.target.files[0])"></label>
          <span class="small text-muted">Picture — optional</span>
        </div>
        <div class="chat-modal__cols">
        <div>
        <label class="chat-field__label" for="chat-new-name">Name</label>
        <input id="chat-new-name" class="form-control mb-3" v-model="form.name" maxlength="80" placeholder="e.g. yara-review" @keydown.enter.prevent="createChannel">
        <label class="chat-field__label" for="chat-new-topic">Topic <span class="fw-normal">(optional)</span></label>
        <input id="chat-new-topic" class="form-control mb-3" v-model="form.topic" maxlength="300" placeholder="What is it for?">
        <div class="chat-privacy" role="radiogroup" aria-label="Visibility">
          <button type="button" :class="{ 'is-on': !form.is_private }" @click="form.is_private = false">
            <i class="fa-solid fa-globe"></i><b>Public</b><span>Anyone signed in can find it, read it and join</span></button>
          <button type="button" :class="{ 'is-on': form.is_private }" @click="form.is_private = true">
            <i class="fa-solid fa-lock"></i><b>Private</b><span>The people you add, or who get the invite link</span></button>
        </div>
        <div v-if="!form.is_private" class="chat-public-note" role="note">
          <i class="fa-solid fa-triangle-exclamation"></i>
          <span><b>Anyone with a Rulezet account can join this channel</b> — no invitation needed — and read every message in it,
            the old ones too. It is listed under "Join a channel". Don't post anything private here.</span>
        </div>
        <div v-else class="chat-private-note" role="note">
          <i class="fa-solid fa-lock"></i><span>Hidden from everyone else: only members see it (and admins, to moderate).</span>
        </div>
        </div>
        <div>
          <label class="chat-field__label">People <span class="fw-normal">(optional — you can add more later)</span></label>
          <people-picker v-model="form.members" :autofocus="false"></people-picker>
        </div>
        </div>
        <div class="chat-modal__foot">
          <button type="button" class="btn btn-light rounded-pill px-3" @click="dialog = null">Cancel</button>
          <button type="button" class="btn btn-primary rounded-pill px-4" :disabled="!form.name.trim()" @click="createChannel">Create</button>
        </div>
      </template>

      <template v-else-if="dialog === 'direct'">
        <div class="chat-modal__head"><h5><i class="fa-solid fa-envelope me-2 text-primary"></i>Message someone</h5>
          <button type="button" class="chat-icon-btn" @click="dialog = null"><i class="fa-solid fa-xmark"></i></button></div>
        <p class="text-muted small">A private conversation: only the two of you see it.</p>
        <people-picker single @pick="startDirect"></people-picker>
      </template>

      <template v-else-if="dialog === 'add'">
        <div class="chat-modal__head"><h5><i class="fa-solid fa-user-plus me-2 text-primary"></i>Add people to #[[ current.name ]]</h5>
          <button type="button" class="chat-icon-btn" @click="dialog = null" aria-label="Close"><i class="fa-solid fa-xmark"></i></button></div>
        <people-picker v-model="toAdd" :channel="current.uuid"></people-picker>
        <div class="chat-modal__foot">
          <button type="button" class="btn btn-light rounded-pill px-3" @click="dialog = null">Cancel</button>
          <button type="button" class="btn btn-primary rounded-pill px-4" :disabled="!toAdd.length" @click="addPeople().then(() => dialog = null)">Add [[ toAdd.length || '' ]]</button>
        </div>
      </template>

      <template v-else-if="dialog === 'browse'">
        <div class="chat-modal__head"><h5><i class="fa-solid fa-compass me-2 text-primary"></i>Public channels</h5>
          <button type="button" class="chat-icon-btn" @click="dialog = null"><i class="fa-solid fa-xmark"></i></button></div>
        <div class="chat-list__filter mb-2"><i class="fa-solid fa-magnifying-glass"></i><input v-model="browseQ" placeholder="Search channels" ref="browseInput" @keydown.down.prevent="focusBrowse(0)" @keydown.enter.prevent="browseList[0] && openFromBrowse(browseList[0])"></div>
        <div class="chat-browse">
          <div v-if="browsing" class="chat-empty-small"><i class="fa-solid fa-circle-notch fa-spin"></i></div>
          <div v-else-if="!browseList.length" class="chat-empty-small">No public channel[[ browseQ ? ' matches' : ' yet' ]].
            <button type="button" class="btn btn-sm btn-link" @click="newChannel()">Create one</button></div>
          <button v-for="c in browseList" :key="c.uuid" type="button" class="chat-browse__row" @click="openFromBrowse(c)" @keydown="onBrowseKey">
            <span class="chat-avatar chat-avatar--channel"><img v-if="c.avatar" :src="c.avatar" alt=""><i v-else class="fa-solid fa-hashtag"></i></span>
            <span class="chat-browse__body"><b>[[ c.name ]]</b>
              <span>[[ c.topic || (c.ref ? c.ref.label : '') ]]</span></span>
            <span class="chat-browse__count"><i class="fa-solid fa-user-group me-1"></i>[[ c.member_count ]]</span>
            <span v-if="c.is_member" class="chat-tag">Joined</span>
          </button>
        </div>
      </template>
    </div>
  </div>
</div>`,
}
