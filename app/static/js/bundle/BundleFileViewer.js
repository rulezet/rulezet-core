/**
 * BundleFileViewer.js — full-screen overlay to read one bundle file.
 *
 * Opens in front of the page (teleported to <body>) instead of expanding
 * below the tree, so on a big bundle the user sees the file right away
 * wherever they clicked it.
 *
 * Props:
 *   file     Object|null  { name, path, folder, content, isRule, format, rule_id } — null = closed
 *   hasPrev  Boolean      enable "previous file" (← key)
 *   hasNext  Boolean      enable "next file" (→ key)
 *   origin   String       where it was opened from: 'structure' | 'files' | ''
 *
 * Emits: close, prev, next,
 *        locate('structure' | 'list') — "show it in the bundle": in the
 *        structure tree, or (when opened from the tree) in the Rules list /
 *        Files & Documents panel
 *
 * Rules are highlighted with their rule format; custom files by extension.
 * Markdown files render (sanitised) by default, with a toggle to the source.
 */

import CodeViewer from '/static/js/components/code-viewer.js'
import { create_message } from '/static/js/toaster.js'
import {
    isMarkdown, languageForFile, docIcon, RULE_ICON, downloadText, formatBytes, renderSafeMarkdown,
} from '/static/js/bundle/bundleFileTypes.js'

const { ref, computed, watch, onMounted, onBeforeUnmount } = Vue

export default {
    name: 'BundleFileViewer',
    components: { CodeViewer },

    props: {
        file:    { type: Object,  default: null },
        hasPrev: { type: Boolean, default: false },
        hasNext: { type: Boolean, default: false },
        origin:  { type: String,  default: '' },
    },

    emits: ['close', 'prev', 'next', 'locate'],

    template: `
    <teleport to="body">
        <transition name="bfv-fade">
            <div v-if="file" class="bfv-backdrop" @mousedown.self="$emit('close')">
                <div class="bfv-dialog" role="dialog" aria-modal="true" :aria-label="file.name">

                    <div class="bfv-header" :class="file.isRule ? 'bfv-header--rule' : 'bfv-header--doc'">
                        <div class="bfv-icon" :style="{ color: icon.color, background: icon.color + '1a' }">
                            <i :class="icon.icon"></i>
                        </div>
                        <div class="bfv-title-wrap">
                            <div class="bfv-title" :title="file.name">{{ file.name }}</div>
                            <div class="bfv-meta">
                                <span class="bfv-kind" :class="file.isRule ? 'bfv-kind--rule' : 'bfv-kind--doc'">
                                    {{ file.isRule ? (file.format || 'Rule') : icon.label }}
                                </span>
                                <span v-if="file.folder" class="bfv-path" :title="file.folder">
                                    <i class="fa-solid fa-folder me-1"></i>{{ file.folder }}
                                </span>
                                <span class="bfv-size">{{ size }}</span>
                            </div>
                        </div>

                        <div class="bfv-actions">
                            <div v-if="markdown" class="bfv-toggle" role="group">
                                <button type="button" :class="{ active: mdView === 'rendered' }" @click="mdView = 'rendered'">
                                    <i class="fa-solid fa-eye me-1"></i>Preview
                                </button>
                                <button type="button" :class="{ active: mdView === 'source' }" @click="mdView = 'source'">
                                    <i class="fa-solid fa-code me-1"></i>Source
                                </button>
                            </div>
                            <a v-if="file.isRule && file.rule_id" class="bfv-btn" :href="'/rule/detail_rule/' + file.rule_id"
                               target="_blank" rel="noopener" title="Open rule page">
                                <i class="fa-solid fa-arrow-up-right-from-square"></i>
                            </a>
                            <button v-if="origin !== 'structure'" type="button" class="bfv-locate"
                                    title="Show where it is in the bundle structure" @click="$emit('locate', 'structure')">
                                <i class="fa-solid fa-folder-tree"></i><span>Show in structure</span>
                            </button>
                            <button v-else type="button" class="bfv-locate" @click="$emit('locate', 'list')"
                                    :title="file.isRule ? 'Show this rule in the Rules tab' : 'Show this file in Files & Documents'">
                                <i :class="file.isRule ? 'fa-solid fa-shield-halved' : 'fa-solid fa-file-lines'"></i>
                                <span>{{ file.isRule ? 'Show in Rules' : 'Show in Files' }}</span>
                            </button>
                            <button type="button" class="bfv-btn" title="Download file" @click="download">
                                <i class="fa-solid fa-download"></i>
                            </button>
                            <button type="button" class="bfv-btn" :disabled="!hasPrev" title="Previous file (←)" @click="$emit('prev')">
                                <i class="fa-solid fa-chevron-left"></i>
                            </button>
                            <button type="button" class="bfv-btn" :disabled="!hasNext" title="Next file (→)" @click="$emit('next')">
                                <i class="fa-solid fa-chevron-right"></i>
                            </button>
                            <button type="button" class="bfv-btn bfv-btn--close" title="Close (Esc)" @click="$emit('close')">
                                <i class="fa-solid fa-xmark"></i>
                            </button>
                        </div>
                    </div>

                    <div v-if="!file.isRule" class="bfv-warn" role="note">
                        <i class="fa-solid fa-triangle-exclamation"></i>
                        <span>User-submitted file, not reviewed by Rulezet. Don't run commands or open links from it without checking them first.</span>
                    </div>

                    <div class="bfv-body">
                        <div v-if="file.loading" class="bfv-empty">
                            <i class="fas fa-spinner fa-spin me-1"></i> Loading…
                        </div>
                        <div v-else-if="markdown && mdView === 'rendered'" class="bfv-markdown">
                            <div v-if="!file.content" class="bfv-empty">
                                <i class="fa-regular fa-file"></i> This file is empty.
                            </div>
                            <div v-else class="bfv-md" v-html="rendered"></div>
                        </div>
                        <code-viewer v-else
                            :key="file.id"
                            :code="file.content || ''"
                            :language="language"
                            max-height="calc(88vh - 150px)">
                        </code-viewer>
                    </div>
                </div>
            </div>
        </transition>
    </teleport>
    `,

    setup(props, { emit }) {
        const mdView   = ref('rendered')
        const rendered = ref('')

        const markdown = computed(() => props.file && !props.file.isRule && isMarkdown(props.file.name))
        const language = computed(() => {
            if (!props.file) return 'text'
            return props.file.isRule ? (props.file.format || 'auto') : languageForFile(props.file.name)
        })
        const icon = computed(() => props.file?.isRule ? RULE_ICON : docIcon(props.file?.name))
        const size = computed(() => props.file?.loading ? '…' : formatBytes(props.file?.content))

        watch(() => props.file, async (f) => {
            document.body.classList.toggle('bfv-open', !!f)
            rendered.value = ''
            if (f && !f.isRule && isMarkdown(f.name)) {
                try { rendered.value = await renderSafeMarkdown(f.content || '') }
                catch { rendered.value = '<p><em>Could not render markdown.</em></p>' }
            }
        }, { immediate: true })

        function download() {
            if (!props.file || props.file.loading) return
            downloadText(props.file.name, props.file.content)
            create_message(`Downloaded ${props.file.name}`, 'success-subtle')
        }

        function onKey(e) {
            if (!props.file) return
            // Don't hijack arrows while the user types in CodeViewer's search box
            if (e.target && ['INPUT', 'TEXTAREA'].includes(e.target.tagName)) {
                if (e.key === 'Escape') emit('close')
                return
            }
            if (e.key === 'Escape') emit('close')
            else if (e.key === 'ArrowLeft' && props.hasPrev) emit('prev')
            else if (e.key === 'ArrowRight' && props.hasNext) emit('next')
        }

        onMounted(() => document.addEventListener('keydown', onKey))
        onBeforeUnmount(() => {
            document.removeEventListener('keydown', onKey)
            document.body.classList.remove('bfv-open')
        })

        return { mdView, rendered, markdown, language, icon, size, download }
    },
}
