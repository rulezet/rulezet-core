import SingleTagDisplay from './singleTagDisplay.js';

/**
 * TagDisplay
 * Collapsible section showing a list of tags.
 * Delegates rendering to SingleTagDisplay for visual consistency.
 */
const TagDisplay = {
    components: { 'single-tag': SingleTagDisplay },
    props: {
        tags: { type: Array, required: true },
        loading: { type: Boolean, default: false },
        maxVisible: { type: Number, default: 10 },
        sectionTitle: { type: String, default: 'Included Tags' },
        showNamespace: { type: Boolean, default: true },
    },
    delimiters: ['[[', ']]'],
    data() {
        return { isCollapsed: false, isShowingAll: false };
    },
    computed: {
        visibleTags() {
            return this.isShowingAll ? this.tags : this.tags.slice(0, this.maxVisible);
        }
    },
    template: `
        <div class="mt-4">
            <div @click="isCollapsed = !isCollapsed" style="cursor:pointer" class="user-select-none">
                <div class="d-flex justify-content-between align-items-center">
                    <h6 class="fw-bold mb-0 d-flex align-items-center" style="color: var(--text-color)">
                        <span class="text-primary me-2">|</span>[[ sectionTitle ]]
                        <i class="fas fa-chevron-down ms-2 small opacity-50"
                           :style="{ transform: isCollapsed ? 'rotate(0deg)' : 'rotate(180deg)', transition: '0.3s' }"></i>
                    </h6>
                    <span v-if="!isCollapsed" class="badge bg-light text-primary border rounded-pill px-3 shadow-sm">
                        [[ tags.length ]] tags
                    </span>
                </div>
                <div v-if="isCollapsed" class="text-muted small mt-1" style="padding-left:1.5rem">
                    <i class="fas fa-info-circle me-1"></i>
                    <strong>[[ tags.length ]] tags</strong> hidden — click to expand.
                </div>
            </div>

            <div v-show="!isCollapsed" class="mt-3">
                <div class="d-flex flex-wrap gap-2 p-3 rounded-3 shadow-sm border" style="background: var(--light-bg-color)">
                    <single-tag
                        v-for="tag in visibleTags" :key="tag.id"
                        :tag="tag"
                        :show-namespace="showNamespace"
                    ></single-tag>

                    <button v-if="tags.length > maxVisible"
                            @click.stop="isShowingAll = !isShowingAll"
                            class="btn btn-sm btn-outline-primary rounded-pill px-3 fw-bold shadow-sm"
                            style="font-size:0.75rem;">
                        [[ isShowingAll ? 'Show less' : '+ ' + (tags.length - maxVisible) + ' more' ]]
                    </button>

                    <div v-if="tags.length === 0 && !loading" class="text-muted small fst-italic py-1">
                        <i class="fas fa-tags me-1 opacity-50"></i> No tags assigned.
                    </div>

                    <div v-if="loading" class="d-flex align-items-center gap-2 py-1">
                        <div class="spinner-border spinner-border-sm text-primary"></div>
                        <small class="text-muted">Loading tags…</small>
                    </div>
                </div>
            </div>
        </div>
    `
};

export default TagDisplay;