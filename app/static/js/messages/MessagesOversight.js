/**
 * MessagesOversight.js — /admin/messages (features/messages/oversight.py): conversations and their messages as
 * who / when / size — never the text, unless an admin reveals one (logged server side).
 */
import { create_message } from '/static/js/toaster.js'
import MessageText from '/static/js/components/chat/message-text.js'

const { ref, reactive, watch, onMounted } = Vue

const csrf = () => document.getElementById('csrf_token')?.value || ''
const when = iso => iso ? new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }) : '—'

export default {
    name: 'MessagesOversight',
    delimiters: ['[[', ']]'],
    components: { MessageText },
    setup() {
        const filters = reactive({ q: '', kind: '', page: 1 })
        const list = ref(null)
        const open = ref(null), msgs = ref([]), hasMore = ref(false), loading = ref(false)
        const revealed = reactive({})
        let timer = null

        async function load() {
            const params = new URLSearchParams({ page: filters.page, ...(filters.q ? { q: filters.q } : {}), ...(filters.kind ? { kind: filters.kind } : {}) })
            list.value = await fetch('/admin/messages/api/conversations?' + params).then(r => r.json()).catch(() => null)
        }
        watch(() => [filters.q, filters.kind], () => { clearTimeout(timer); timer = setTimeout(() => { filters.page = 1; load() }, 250) })
        async function openConv(c, more = false) {
            if (!more) { open.value = c; msgs.value = [] }
            loading.value = true
            const before = more && msgs.value.length ? `?before=${msgs.value[msgs.value.length - 1].id}` : ''
            const d = await fetch(`/admin/messages/api/conversations/${c.uuid}${before}`).then(r => r.json()).catch(() => null)
            loading.value = false
            if (d) { msgs.value = [...msgs.value, ...d.messages]; hasMore.value = d.has_more }
        }
        async function reveal(m) {
            if (!confirm('Reveal this message? It is written to the activity log with your name.')) return
            const res = await fetch(`/admin/messages/api/messages/${m.id}/reveal`, { method: 'POST', headers: { 'X-CSRFToken': csrf() } })
            const d = await res.json().catch(() => null)
            if (!res.ok || !d) return create_message('Could not reveal it.', 'danger-subtle')
            revealed[m.id] = d.content
        }
        onMounted(load)
        return { filters, list, open, msgs, hasMore, loading, revealed, load, openConv, reveal, when }
    },
    template: `
<div class="ovs">
  <div class="card border-0 shadow-sm rounded-3">
    <div class="card-body p-3">
      <div class="ovs-filters">
        <div class="chat-list__filter m-0 flex-fill"><i class="fa-solid fa-magnifying-glass"></i>
          <input v-model="filters.q" placeholder="Channel name, or a member's name / username / email" aria-label="Search"></div>
        <select v-model="filters.kind" class="form-select form-select-sm" style="width:auto;" aria-label="Kind">
          <option value="">Everything</option><option value="channel">Channels</option><option value="direct">Direct conversations</option>
        </select>
      </div>
      <div v-if="!list" class="chat-empty-small"><i class="fa-solid fa-circle-notch fa-spin"></i></div>
      <table v-else class="table table-sm align-middle mb-0 ovs-table">
        <thead><tr><th>Conversation</th><th>Members</th><th class="text-end">Messages</th><th>Last activity</th><th></th></tr></thead>
        <tbody>
          <tr v-for="c in list.conversations" :key="c.uuid" :class="{ 'table-active': open && open.uuid === c.uuid }">
            <td><i :class="c.kind === 'direct' ? 'fa-solid fa-user-lock' : (c.is_private ? 'fa-solid fa-lock' : 'fa-solid fa-hashtag')" class="me-1 text-primary"></i>
              <b>[[ c.kind === 'direct' ? 'Direct' : c.name ]]</b>
              <span v-if="c.is_archived" class="chat-tag ms-1">Archived</span></td>
            <td><span v-for="u in c.members" :key="u.id" class="ovs-member" :title="u.role">[[ u.name ]]</span>
              <span v-if="c.member_count > c.members.length" class="text-muted small">+[[ c.member_count - c.members.length ]]</span></td>
            <td class="text-end">[[ c.messages ]]</td>
            <td class="small text-muted">[[ when(c.last_message_at) ]]</td>
            <td class="text-end"><button type="button" class="btn btn-sm btn-outline-primary rounded-pill px-3" @click="openConv(c)">Activity</button></td>
          </tr>
          <tr v-if="!list.conversations.length"><td colspan="5" class="chat-empty-small">Nothing found.</td></tr>
        </tbody>
      </table>
      <div v-if="list && list.pages > 1" class="d-flex justify-content-end gap-2 mt-2">
        <button class="btn btn-sm btn-light" :disabled="filters.page <= 1" @click="filters.page--; load()">‹</button>
        <span class="small align-self-center">[[ filters.page ]] / [[ list.pages ]]</span>
        <button class="btn btn-sm btn-light" :disabled="filters.page >= list.pages" @click="filters.page++; load()">›</button>
      </div>
    </div>
  </div>

  <div v-if="open" class="card border-0 shadow-sm rounded-3 mt-4">
    <div class="card-body p-3">
      <div class="d-flex align-items-center justify-content-between mb-2">
        <h6 class="mb-0"><i class="fa-solid fa-list me-2 text-primary"></i>[[ open.kind === 'direct' ? 'Direct conversation' : '#' + open.name ]] — messages (newest first)</h6>
        <button type="button" class="btn-close" aria-label="Close" @click="open = null"></button>
      </div>
      <p class="small text-muted"><i class="fa-solid fa-eye-slash me-1"></i>The text is hidden. "Reveal" shows one message and logs it.</p>
      <table class="table table-sm align-middle mb-0">
        <thead><tr><th>When</th><th>Author</th><th>Size</th><th>Details</th><th></th></tr></thead>
        <tbody>
          <template v-for="m in msgs" :key="m.id">
            <tr>
              <td class="small">[[ when(m.created_at) ]]</td>
              <td><a v-if="m.author && m.author.id" :href="'/account/detail_user/' + m.author.id">[[ m.author.name ]]</a><span v-else>[[ m.author ? m.author.name : '—' ]]</span></td>
              <td class="small text-muted">[[ m.length ]] chars</td>
              <td class="small">
                <span v-if="m.image" class="chat-tag me-1">Image</span><span v-if="m.reply" class="chat-tag me-1">Reply</span>
                <span v-if="m.edited" class="chat-tag me-1">Edited</span><span v-if="m.deleted" class="chat-tag me-1">Deleted</span>
                <span v-if="m.pinned" class="chat-tag me-1">Pinned</span><span v-if="m.reactions" class="chat-tag me-1">[[ m.reactions ]] reactions</span>
                <span v-if="m.kind === 'feed'" class="chat-tag chat-tag--bot">Automation</span></td>
              <td class="text-end"><button v-if="revealed[m.id] === undefined" type="button" class="btn btn-sm btn-outline-danger rounded-pill px-3" @click="reveal(m)">
                <i class="fa-solid fa-eye me-1"></i>Reveal</button></td>
            </tr>
            <tr v-if="revealed[m.id] !== undefined" class="ovs-revealed"><td colspan="5"><message-text :text="revealed[m.id]" :previews="false"></message-text></td></tr>
          </template>
          <tr v-if="!msgs.length && !loading"><td colspan="5" class="chat-empty-small">No message.</td></tr>
        </tbody>
      </table>
      <div v-if="hasMore" class="text-center mt-2"><button class="btn btn-sm btn-light rounded-pill px-3" :disabled="loading" @click="openConv(open, true)">Older</button></div>
    </div>
  </div>
</div>`,
}
