import SingleTagDisplay from './singleTagDisplay.js';

/**
 * TagDisplay
 * Collapsible section showing a list of tags.
 * Delegates rendering to SingleTagDisplay for visual consistency.
 *
 * group-by-source (off by default, every existing caller unchanged) splits
 * the list in two: Rulezet's standardized tags (MISP taxonomies & galaxies)
 * first, then the free-form ones — Manual tags and "Imported" tags (the
 * rule author's own tags extracted from the rule, GitHub #70).
 */
const STANDARD_SOURCES = ['Taxonomy', 'Galaxy'];

const TagChipList = {
    components: { 'single-tag': SingleTagDisplay },
    props: {
        tags: { type: Array, required: true },
        maxVisible: { type: Number, default: 10 },
        showNamespace: { type: Boolean, default: true },
        emptyText: { type: String, default: 'No tags assigned.' },
    },
    delimiters: ['[[', ']]'],
    data() {
        return { isShowingAll: false };
    },
    computed: {
        visibleTags() {
            return this.isShowingAll ? this.tags : this.tags.slice(0, this.maxVisible);
        }
    },
    template: `
        <div class="d-flex flex-wrap gap-2">
            <single-tag v-for="tag in visibleTags" :key="tag.id"
                        :tag="tag" :show-namespace="showNamespace"></single-tag>

            <button v-if="tags.length > maxVisible"
                    @click.stop="isShowingAll = !isShowingAll"
                    class="btn btn-sm btn-outline-primary rounded-pill px-3 fw-bold shadow-sm"
                    style="font-size:0.75rem;">
                [[ isShowingAll ? 'Show less' : '+ ' + (tags.length - maxVisible) + ' more' ]]
            </button>

            <div v-if="tags.length === 0" class="text-muted small fst-italic py-1">
                <i class="fas fa-tags me-1 opacity-50"></i> [[ emptyText ]]
            </div>
        </div>
    `
};

const TagDisplay = {
    components: { 'single-tag': SingleTagDisplay, 'tag-chip-list': TagChipList },
    props: {
        tags: { type: Array, required: true },
        loading: { type: Boolean, default: false },
        maxVisible: { type: Number, default: 10 },
        sectionTitle: { type: String, default: 'Included Tags' },
        showNamespace: { type: Boolean, default: true },
        groupBySource: { type: Boolean, default: false },
    },
    delimiters: ['[[', ']]'],
    data() {
        return { isCollapsed: false };
    },
    computed: {
        standardTags() {
            return this.tags.filter(t => STANDARD_SOURCES.includes(t.source));
        },
        freeTags() {
            return this.tags.filter(t => !STANDARD_SOURCES.includes(t.source));
        },
        importedCount() {
            return this.freeTags.filter(t => t.source === 'Imported').length;
        },
    },
    template: `
        <div class="mt-4">
            <div @click="isCollapsed = !isCollapsed" style="cursor:pointer" class="user-select-none">
                <div class="d-flex justify-content-between align-items-center">
                    <div class="d-flex align-items-center gap-2">
                        <div style="width:3px; height:14px; background:#0d6efd; border-radius:2px; flex-shrink:0;"></div>
                        <span class="fw-bold d-flex align-items-center" style="font-size:.75rem; text-transform:uppercase; letter-spacing:.07em; color:var(--subtle-text-color);">
                            <i class="fa-solid fa-tags me-1"></i>[[ sectionTitle ]]
                            <i class="fas fa-chevron-down ms-2 small opacity-50"
                               :style="{ transform: isCollapsed ? 'rotate(0deg)' : 'rotate(180deg)', transition: '0.3s' }"></i>
                        </span>
                    </div>
                    <span v-if="!isCollapsed" class="badge rounded-pill px-3" style="background:var(--light-bg-color); color:var(--subtle-text-color); border:1px solid var(--border-color); font-size:.75rem;">
                        [[ tags.length ]] tags
                    </span>
                </div>
                <div v-if="isCollapsed" class="text-muted small mt-1" style="padding-left:1.5rem">
                    <i class="fas fa-info-circle me-1"></i>
                    <strong>[[ tags.length ]] tags</strong> hidden — click to expand.
                </div>
            </div>

            <div v-show="!isCollapsed" class="mt-3">
                <div v-if="loading" class="d-flex align-items-center gap-2 p-3 rounded-3 shadow-sm border" style="background: var(--light-bg-color)">
                    <div class="spinner-border spinner-border-sm text-primary"></div>
                    <small class="text-muted">Loading tags…</small>
                </div>

                <!-- Single list (default) -->
                <div v-else-if="!groupBySource" class="p-3 rounded-3 shadow-sm border" style="background: var(--light-bg-color)">
                    <tag-chip-list :tags="tags" :max-visible="maxVisible" :show-namespace="showNamespace"></tag-chip-list>
                </div>

                <!-- Two sections: standardized tags, then manual + imported -->
                <div v-else class="rounded-3 shadow-sm border" style="background: var(--light-bg-color)">
                    <div class="p-3">
                        <div class="d-flex align-items-center justify-content-between mb-2">
                            <span class="fw-semibold" style="font-size:.72rem; text-transform:uppercase; letter-spacing:.06em; color:var(--subtle-text-color);">
                                <i class="fa-solid fa-sitemap me-1"></i>Taxonomies &amp; Galaxies
                            </span>
                            <span style="font-size:.7rem; color:var(--subtle-text-color);">[[ standardTags.length ]]</span>
                        </div>
                        <tag-chip-list :tags="standardTags" :max-visible="maxVisible" :show-namespace="showNamespace"
                                       empty-text="No taxonomy or galaxy tags."></tag-chip-list>
                    </div>
                    <div class="p-3 border-top">
                        <div class="d-flex align-items-center justify-content-between mb-2">
                            <span class="fw-semibold" style="font-size:.72rem; text-transform:uppercase; letter-spacing:.06em; color:var(--subtle-text-color);">
                                <i class="fa-solid fa-tag me-1"></i>Manual &amp; Imported Tags
                            </span>
                            <span style="font-size:.7rem; color:var(--subtle-text-color);"
                                  :title="importedCount + ' imported from the rule author\\'s own tags'">
                                [[ freeTags.length ]]<template v-if="importedCount"> · <i class="fa-solid fa-user-tag"></i> [[ importedCount ]] imported</template>
                            </span>
                        </div>
                        <tag-chip-list :tags="freeTags" :max-visible="maxVisible" :show-namespace="showNamespace"
                                       empty-text="No manual or imported tags."></tag-chip-list>
                    </div>
                </div>
            </div>
        </div>
    `
};

export default TagDisplay;
