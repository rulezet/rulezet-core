/**
 * people-picker.js — choose people from the directory (not only by typing a name): everyone is listed with their
 * organisations, filtered by name and by organisation ("My organisation" = any of yours), with "select all".
 * Data: GET /messages/api/people (verified accounts only).
 *
 *   import PeoplePicker from '/static/js/components/chat/people-picker.js'
 *   <people-picker v-model="selected" :channel="uuid"></people-picker>       several people (chips on top)
 *   <people-picker single @pick="user => …"></people-picker>                 one person
 *
 * Keyboard: type to search · ↓/↑ move in the list · Space or Enter selects · Ctrl+A selects all shown ·
 * Home / End · Esc goes back to the search box · Tab moves on as usual.
 */
const { ref, reactive, computed, watch, onMounted, nextTick } = Vue

export default {
    name: 'PeoplePicker',
    delimiters: ['[[', ']]'],
    props: {
        modelValue: { type: Array, default: () => [] },     // [{ id, name, avatar, … }]
        single: { type: Boolean, default: false },
        channel: { type: String, default: null },             // members of this channel are shown as "already in"
        autofocus: { type: Boolean, default: true },
    },
    emits: ['update:modelValue', 'pick'],
    setup(props, { emit }) {
        const q = ref('')
        const org = ref('')
        const data = reactive({ users: [], total: 0, page: 1, pages: 1, orgs: [], my_orgs: [] })
        const loading = ref(false)
        const cursor = ref(0)
        const searchEl = ref(null), listEl = ref(null)
        const selectedIds = computed(() => new Set(props.modelValue.map(u => u.id)))
        let timer = null, seq = 0

        async function load(page = 1, append = false) {
            const my = ++seq
            loading.value = true
            const params = new URLSearchParams({ page })
            if (q.value.trim()) params.set('q', q.value.trim())
            if (org.value) params.set('org', org.value)
            if (props.channel) params.set('channel', props.channel)
            try {
                const res = await (await fetch('/messages/api/people?' + params)).json()
                if (my !== seq) return
                Object.assign(data, res, { users: append ? [...data.users, ...res.users] : res.users })
                if (!append) cursor.value = 0
            } catch { } finally { if (my === seq) loading.value = false }
        }
        watch(q, () => { clearTimeout(timer); timer = setTimeout(() => load(1), 220) })
        watch(org, () => load(1))

        const choosable = u => !u.in_channel
        function toggle(u) {
            if (!u || !choosable(u)) return
            if (props.single) { emit('pick', u); return }
            emit('update:modelValue', selectedIds.value.has(u.id)
                ? props.modelValue.filter(x => x.id !== u.id) : [...props.modelValue, u])
        }
        const remove = u => emit('update:modelValue', props.modelValue.filter(x => x.id !== u.id))
        const shownChoosable = computed(() => data.users.filter(choosable))
        const allShownSelected = computed(() => shownChoosable.value.length > 0 && shownChoosable.value.every(u => selectedIds.value.has(u.id)))
        function toggleShown() {
            if (allShownSelected.value) {
                const shown = new Set(shownChoosable.value.map(u => u.id))
                emit('update:modelValue', props.modelValue.filter(u => !shown.has(u.id)))
            } else {
                emit('update:modelValue', [...props.modelValue, ...shownChoosable.value.filter(u => !selectedIds.value.has(u.id))])
            }
        }
        // every match, not only this page (up to 500)
        async function selectAllMatching() {
            const params = new URLSearchParams({ ids_only: 1, page: 1 })
            if (q.value.trim()) params.set('q', q.value.trim())
            if (org.value) params.set('org', org.value)
            const res = await (await fetch('/messages/api/people?' + params)).json().catch(() => ({ ids: [] }))
            const have = selectedIds.value
            const known = new Map(data.users.map(u => [u.id, u]))
            const inChannel = new Set(data.users.filter(u => u.in_channel).map(u => u.id))
            const extra = (res.ids || []).filter(id => !have.has(id) && !inChannel.has(id))
                .map(id => known.get(id) || { id, name: `User #${id}`, initial: '#', avatar: null })
            emit('update:modelValue', [...props.modelValue, ...extra])
        }
        const clearAll = () => emit('update:modelValue', [])

        // ── keyboard ──
        function rowEl(i) { return listEl.value && listEl.value.querySelectorAll('.pp-row')[i] }
        function focusRow(i) {
            if (!data.users.length) return
            cursor.value = Math.max(0, Math.min(i, data.users.length - 1))
            nextTick(() => { const el = rowEl(cursor.value); el && el.focus({ preventScroll: false }) })
            if (cursor.value >= data.users.length - 3 && data.page < data.pages && !loading.value) load(data.page + 1, true)
        }
        function onSearchKey(e) {
            if (e.key === 'ArrowDown') { e.preventDefault(); focusRow(0) }
            else if (e.key === 'Enter') { e.preventDefault(); if (data.users[0]) toggle(data.users[0]) }
        }
        function onRowKey(e, i) {
            const u = data.users[i]
            if (e.key === 'ArrowDown') { e.preventDefault(); focusRow(i + 1) }
            else if (e.key === 'ArrowUp') { e.preventDefault(); i === 0 ? searchEl.value.focus() : focusRow(i - 1) }
            else if (e.key === 'Home') { e.preventDefault(); focusRow(0) }
            else if (e.key === 'End') { e.preventDefault(); focusRow(data.users.length - 1) }
            else if (e.key === ' ' || e.key === 'Enter') { e.preventDefault(); toggle(u) }
            else if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); searchEl.value.focus() }
            else if ((e.ctrlKey || e.metaKey) && e.key === 'a' && !props.single) { e.preventDefault(); toggleShown() }
            else if (e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) { searchEl.value.focus() }   // typing goes to the search
        }
        function onChipKey(e, u) { if (e.key === 'Backspace' || e.key === 'Delete') { e.preventDefault(); remove(u); searchEl.value.focus() } }
        function onListScroll() {
            const el = listEl.value
            if (el && el.scrollTop + el.clientHeight > el.scrollHeight - 60 && data.page < data.pages && !loading.value) load(data.page + 1, true)
        }

        onMounted(() => { load(1); if (props.autofocus) nextTick(() => searchEl.value && searchEl.value.focus()) })

        return { q, org, data, loading, cursor, searchEl, listEl, selectedIds, allShownSelected,
                 toggle, remove, toggleShown, selectAllMatching, clearAll, onSearchKey, onRowKey, onChipKey, onListScroll, choosable }
    },
    template: `
    <div class="pp" :class="{ 'pp--single': single }">
        <div class="pp-filters">
            <div class="pp-search">
                <i class="fa-solid fa-magnifying-glass"></i>
                <input ref="searchEl" v-model="q" type="search" placeholder="Search by name or username" aria-label="Search people"
                       @keydown="onSearchKey">
            </div>
            <select v-model="org" class="form-select form-select-sm pp-org" aria-label="Organisation">
                <option value="">Everyone</option>
                <option v-if="data.my_orgs.length" value="mine">My organisation[[ data.my_orgs.length > 1 ? 's' : '' ]]</option>
                <optgroup v-if="data.orgs.length" label="Organisation">
                    <option v-for="o in data.orgs" :key="o.id" :value="String(o.id)">[[ o.name ]][[ o.mine ? ' (yours)' : '' ]]</option>
                </optgroup>
            </select>
        </div>

        <div v-if="!single" class="pp-bar">
            <span class="pp-count">[[ data.total ]] [[ data.total === 1 ? 'person' : 'people' ]]</span>
            <button type="button" class="pp-link" @click="toggleShown" :disabled="!data.users.length">[[ allShownSelected ? 'Unselect shown' : 'Select shown' ]]</button>
            <button v-if="data.total > data.users.length" type="button" class="pp-link" @click="selectAllMatching">Select all [[ Math.min(data.total, 500) ]]</button>
            <span class="ms-auto pp-count"><b>[[ modelValue.length ]]</b> selected</span>
            <button v-if="modelValue.length" type="button" class="pp-link pp-link--muted" @click="clearAll">Clear</button>
        </div>

        <div v-if="!single && modelValue.length" class="pp-chips" aria-label="Selected people">
            <span v-for="u in modelValue" :key="u.id" class="pp-chip" tabindex="0" @keydown="onChipKey($event, u)" :title="'Remove ' + (u.username || u.name) + ' (Delete)'">
                <span class="chat-avatar chat-avatar--xs"><img v-if="u.avatar" :src="u.avatar" alt=""><template v-else>[[ u.initial ]]</template></span>
                [[ u.username || u.name ]]
                <button type="button" tabindex="-1" @click="remove(u)" aria-label="Remove"><i class="fa-solid fa-xmark"></i></button>
            </span>
        </div>

        <div class="pp-list" ref="listEl" role="listbox" :aria-multiselectable="!single" @scroll.passive="onListScroll">
            <div v-if="!data.users.length && !loading" class="pp-empty">Nobody matches.</div>
            <div v-for="(u, i) in data.users" :key="u.id" class="pp-row" role="option" tabindex="0"
                 :aria-selected="selectedIds.has(u.id)" :aria-disabled="!choosable(u)"
                 :class="{ 'is-selected': selectedIds.has(u.id), 'is-disabled': !choosable(u), 'is-cursor': i === cursor }"
                 @click="toggle(u)" @keydown="onRowKey($event, i)" @focus="cursor = i">
                <span v-if="!single" class="pp-check"><i :class="selectedIds.has(u.id) || u.in_channel ? 'fa-solid fa-square-check' : 'fa-regular fa-square'"></i></span>
                <span class="chat-avatar"><img v-if="u.avatar" :src="u.avatar" alt=""><template v-else>[[ u.initial ]]</template></span>
                <span class="pp-name">
                    <b>[[ u.username ]]</b>
                    <span class="pp-orgs">
                        <span v-for="o in u.orgs" :key="o.id" class="pp-org-badge" :style="{ '--c': o.color }"><i :class="'fa-solid ' + o.icon"></i>[[ o.text ]]</span>
                        <span v-if="u.is_admin" class="chat-tag chat-tag--admin">Admin</span>
                    </span>
                </span>
                <span v-if="u.in_channel" class="pp-state">Already in</span>
                <span v-else-if="single" class="pp-state"><i class="fa-solid fa-arrow-right"></i></span>
            </div>
            <div v-if="loading" class="pp-empty"><i class="fa-solid fa-circle-notch fa-spin"></i></div>
        </div>
        <div class="pp-keys"><kbd>↑</kbd><kbd>↓</kbd> move · <kbd>Space</kbd>/<kbd>Enter</kbd> [[ single ? 'choose' : 'select' ]]<template v-if="!single"> · <kbd>Ctrl</kbd>+<kbd>A</kbd> all shown</template> · <kbd>Esc</kbd> back to search</div>
    </div>`,
}
