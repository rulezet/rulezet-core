// Admin Media manager (templates/admin/media.html, backend features/admin/media).
// "Site images": static/images and static/image — replace (same name), rename,
// delete, add, with where each image is used. "Uploads": every stored file by
// category, with what it belongs to — delete also clears that reference.
import { create_message } from '/static/js/toaster.js';
import FileTree from '/static/js/components/file-tree.js';

const { createApp, ref, computed, onMounted } = Vue;

const csrf = () => document.getElementById('csrf_token')?.value || '';

async function postJson(url, body) {
    const res = await fetch(url, {
        method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf() }, body: JSON.stringify(body),
    });
    return res.json();
}

async function postFile(url, fields, file) {
    const body = new FormData();
    Object.entries(fields).forEach(([k, v]) => body.append(k, v));
    body.append('file', file);
    const res = await fetch(url, { method: 'POST', headers: { 'X-CSRFToken': csrf() }, body });
    return res.json();
}

// Flat files [{ rel, … }] → FileTree nodes (folders first), each file node
// carrying its file (`file`) and an optional badge.
function buildTree(files, prefix, badgeOf, labelOf = (n) => n) {
    const root = { children: new Map(), files: [] };
    for (const f of files) {
        const parts = f.rel.split('/');
        let dir = root;
        for (const part of parts.slice(0, -1)) {
            if (!dir.children.has(part)) dir.children.set(part, { children: new Map(), files: [] });
            dir = dir.children.get(part);
        }
        dir.files.push(f);
    }
    const toNodes = (dir, base) => [
        ...[...dir.children.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([name, sub]) => {
            const path = base ? `${base}/${name}` : name;
            return { name: labelOf(name, path), type: 'dir', path: `${prefix}${path}`, rel: path, children: toNodes(sub, path), defaultOpen: true };
        }),
        ...dir.files.map((f) => ({
            name: f.name, type: 'file', path: `${prefix}${f.rel}`, ext: f.ext.replace('.', ''),
            badge: badgeOf(f), file: f,
        })),
    ];
    return toNodes(root, '');
}

createApp({
    delimiters: ['[[', ']]'],
    components: { 'file-tree': FileTree },
    setup() {
        const LIBRARY_ROOTS = window.MEDIA_LIBRARY_ROOTS || {};
        const params = new URLSearchParams(location.search);
        const tab = ref(params.get('tab') === 'uploads' ? 'uploads' : 'library');
        const root = ref(Object.keys(LIBRARY_ROOTS)[0] || 'images');
        const folder = ref(null);              // null = every folder
        const q = ref('');
        const loading = ref(false);
        const library = ref({ folders: [], files: [] });
        const uploads = ref([]);
        const category = ref('avatars');
        const orphansOnly = ref(false);
        const current = ref(null);             // { kind, file }
        const renameTo = ref('');
        const uploadFolder = ref(null);        // a sub-folder of the category (workspace, vendor…)
        const treeRef = ref(null);

        const match = (f) => {
            const term = q.value.trim().toLowerCase();
            return !term || f.rel.toLowerCase().includes(term) || (f.owner?.label || '').toLowerCase().includes(term);
        };
        const libraryFiles = computed(() => library.value.files.filter(f => (folder.value === null || f.folder === folder.value) && match(f)));
        const currentCategory = computed(() => uploads.value.find(c => c.key === category.value));
        const uploadFiles = computed(() => (currentCategory.value?.files || []).filter(f => match(f)
            && (!orphansOnly.value || !f.owner)
            && (!uploadFolder.value || f.rel.startsWith(uploadFolder.value + '/'))));

        // The tree on the left: what is really on disk.
        const libraryTree = computed(() => [{
            name: `${root.value}/`, type: 'dir', path: 'lib:', rel: '', defaultOpen: true,
            children: buildTree(library.value.files, 'lib:', (f) => (f.ref_count ? `×${f.ref_count}` : '')),
        }]);
        const uploadsTree = computed(() => uploads.value.map((c) => ({
            name: c.label, type: 'dir', path: `up:${c.key}`, rel: '', category: c.key, defaultOpen: c.key === category.value,
            badge: String(c.files.length),
            children: buildTree(c.files, `up:${c.key}/`, (f) => (f.owner ? '' : 'unused'), (name, path) => {
                // a workspace folder is named by its uuid: show the workspace's name
                const owner = c.files.find((f) => f.rel.startsWith(path + '/') && f.owner)?.owner?.label;
                const ws = owner && owner.match(/in workspace "(.*)"$/);
                return ws ? `${ws[1]} (${name.slice(0, 8)})` : name;
            }).map((n) => ({ ...n, category: c.key })),
        })));

        function onTreeSelect(node) {
            if (tab.value === 'library') {
                if (node.type === 'dir') { folder.value = node.rel === '' ? null : node.rel; return; }
                open('library', node.file);
                return;
            }
            const key = node.path.slice(3).split('/')[0];
            if (key !== category.value) { category.value = key; uploadFolder.value = null; }
            if (node.type === 'dir') { uploadFolder.value = node.path.includes('/') ? node.path.slice(3 + key.length + 1) : null; return; }
            open('uploads', node.file);
        }
        // Folders offered when adding an image (the library's root always included).
        const folderOptions = computed(() => [...new Set(['', ...library.value.folders])]);
        const countIn = (f) => library.value.files.filter(x => x.folder === f).length;

        async function loadLibrary() {
            loading.value = true;
            try {
                const data = await (await fetch(`/admin/media/library.json?root=${encodeURIComponent(root.value)}`)).json();
                if (data.success) library.value = data;
                else create_message(data.message || 'Could not load the images', 'danger-subtle');
            } finally { loading.value = false; }
        }
        async function loadUploads() {
            loading.value = true;
            try {
                const data = await (await fetch('/admin/media/uploads.json')).json();
                if (data.success) uploads.value = data.categories;
            } finally { loading.value = false; }
        }
        const reload = () => (tab.value === 'library' ? loadLibrary() : loadUploads());

        function setTab(t) {
            tab.value = t; q.value = ''; current.value = null;
            const url = new URL(location); url.searchParams.set('tab', t); history.replaceState(null, '', url);
            reload();
        }
        function setRoot(r) { root.value = r; folder.value = null; loadLibrary(); }

        function open(kind, file) {
            current.value = { kind, file };
            renameTo.value = file.name;
            const path = kind === 'library' ? `lib:${file.rel}` : `up:${category.value}/${file.rel}`;
            treeRef.value?.reveal?.(path);
        }
        const pathOf = (c) => c.kind === 'library' ? `/static/${root.value}/${c.file.rel}` : `${category.value}/${c.file.rel}`;
        function copyPath() {
            const url = current.value.file.url.split('?')[0];
            navigator.clipboard?.writeText(url).then(() => create_message('URL copied', 'success-subtle'));
        }

        function hintFor(kind, file) {
            if (kind === 'library') {
                const n = file.ref_count;
                return n ? `Used in ${n} place${n > 1 ? 's' : ''} — those references will break (blog covers are cleared).` : 'Nothing references it.';
            }
            return file.owner ? `Also removes it from: ${file.owner.label}.` : 'Nothing references it.';
        }
        const deleteHint = computed(() => (current.value ? hintFor(current.value.kind, current.value.file) : ''));

        // Delete one file — from its card, its row in the tree, or the drawer.
        async function deleteFile(kind, file, cat = category.value, confirmed = false) {
            if (!confirmed && !confirm(`Delete ${file.name}?\n\n${hintFor(kind, file)}`)) return;
            const data = kind === 'library'
                ? await postJson('/admin/media/library/delete', { root: root.value, rel: file.rel })
                : await postJson('/admin/media/upload/delete', { category: cat, rel: file.rel });
            if (!data.success) return create_message(data.message || 'Error', 'danger-subtle');
            create_message(`${file.name} deleted`, 'success-subtle');
            if (current.value?.file.rel === file.rel) current.value = null;
            reload();
        }

        // Card trash button: a first click arms it ("Again?"), a second one within 3 s deletes.
        const armed = ref(null);
        let armTimer = null;
        function clickDelete(kind, file) {
            const key = `${kind}:${file.rel}`;
            clearTimeout(armTimer);
            if (armed.value === key) {
                armed.value = null;
                deleteFile(kind, file, category.value, true);
                return;
            }
            armed.value = key;
            armTimer = setTimeout(() => { armed.value = null; }, 3000);
        }

        // Double-click a card's name to rename it in place (site images only).
        const editingRel = ref(null);
        const editName = ref('');
        function startInlineRename(file) { editingRel.value = file.rel; editName.value = file.name; }
        async function saveInlineRename(file) {
            const name = editName.value.trim();
            editingRel.value = null;
            if (name && name !== file.name) await renameFile(file, name);
        }

        const TREE_ACTIONS = [{ key: 'delete', label: 'Delete', icon: 'fa-solid fa-trash' }];   // FileTree takes the full icon class
        function onTreeAction({ action, node }) {
            if (action !== 'delete' || !node.file) return;
            if (tab.value === 'library') return deleteFile('library', node.file);
            deleteFile('uploads', node.file, node.path.slice(3).split('/')[0]);
        }

        async function replaceCurrent(event) {
            const file = event.target.files[0];
            event.target.value = '';
            if (!file) return;
            const c = current.value;
            const data = c.kind === 'library'
                ? await postFile('/admin/media/library/replace', { root: root.value, rel: c.file.rel }, file)
                : await postFile('/admin/media/upload/replace', { category: category.value, rel: c.file.rel }, file);
            create_message(data.message || (data.success ? 'Replaced' : 'Error'), data.success ? 'success-subtle' : 'danger-subtle');
            if (data.success) { current.value = null; reload(); }
        }

        async function renameFile(file, name) {
            const data = await postJson('/admin/media/library/rename', { root: root.value, rel: file.rel, name });
            if (!data.success) return create_message(data.message || 'Error', 'danger-subtle');
            const extra = data.code_refs.length ? ` — update ${data.code_refs.length} reference${data.code_refs.length > 1 ? 's' : ''} in the code` : '';
            create_message(`Renamed to ${data.rel}${extra}`, data.code_refs.length ? 'warning-subtle' : 'success-subtle');
            current.value = null;
            loadLibrary();
        }
        const renameCurrent = () => renameFile(current.value.file, renameTo.value.trim());

        const deleteCurrent = () => deleteFile(current.value.kind, current.value.file);

        // Add an image: choose its folder (an existing one, or a new one), then the file.
        const adding = ref(false);                 // false | true | 'busy'
        const addFolder = ref('');
        const addNewFolder = ref('');
        const addFile = ref(null);
        function openAdd() {
            adding.value = true;
            addFolder.value = folder.value ?? '';
            addNewFolder.value = '';
            addFile.value = null;
        }
        async function uploadToLibrary() {
            if (!addFile.value) return;
            const isNew = addFolder.value === '__new__';
            const target = isNew ? addNewFolder.value.trim().replace(/^\/+|\/+$/g, '') : addFolder.value;
            if (isNew && !target) return create_message('Name the new folder.', 'warning-subtle');
            adding.value = 'busy';
            const data = await postFile('/admin/media/library/upload',
                { root: root.value, folder: target, new_folder: isNew ? '1' : '0' }, addFile.value);
            create_message(data.message || (data.success ? 'Added' : 'Error'), data.success ? 'success-subtle' : 'danger-subtle');
            if (!data.success) { adding.value = true; return; }
            adding.value = false;
            await loadLibrary();
            folder.value = target;                 // show where it went
        }

        function size(n) {
            if (n < 1024) return `${n} B`;
            if (n < 1048576) return `${(n / 1024).toFixed(0)} KB`;
            return `${(n / 1048576).toFixed(1)} MB`;
        }
        function fileIcon(f) {
            if (f.ext === '.pdf') return 'fa-file-pdf';
            if (['.docx', '.odt'].includes(f.ext)) return 'fa-file-word';
            if (['.xlsx', '.ods', '.csv'].includes(f.ext)) return 'fa-file-excel';
            if (['.pptx', '.odp'].includes(f.ext)) return 'fa-file-powerpoint';
            if (['.zip', '.tar', '.gz'].includes(f.ext)) return 'fa-file-zipper';
            return 'fa-file';
        }

        // Escape closes the drawer.
        window.addEventListener('keydown', (e) => { if (e.key === 'Escape') current.value = null; });
        onMounted(reload);

        return {
            LIBRARY_ROOTS, tab, root, folder, q, loading, library, uploads, category, orphansOnly, current, renameTo,
            uploadFolder, treeRef, libraryTree, uploadsTree, onTreeSelect, TREE_ACTIONS, onTreeAction, deleteFile,
            armed, clickDelete, editingRel, editName, startInlineRename, saveInlineRename,
            adding, addFolder, addNewFolder, addFile, openAdd,
            libraryFiles, currentCategory, uploadFiles, folderOptions, countIn, deleteHint,
            setTab, setRoot, open, pathOf, copyPath, replaceCurrent, renameCurrent, deleteCurrent, uploadToLibrary, size, fileIcon,
        };
    },
}).mount('#main-container');
