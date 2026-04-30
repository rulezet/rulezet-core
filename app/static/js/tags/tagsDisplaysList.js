import SingleTagDisplay from './singleTagDisplay.js';

/**
 * TagsDisplaysList
 * Fetches tags for a given rule or bundle and displays them inline.
 * Delegates rendering to SingleTagDisplay.
 */
const TagsDisplaysList = {
    components: { 'single-tag-display': SingleTagDisplay },
    props: {
        objectId: { type: [Number, String], required: true },
        objectType: { type: String, required: true, validator: v => ['bundle', 'rule'].includes(v) },
        maxVisible: { type: Number, default: 5 },
        sectionTitle: { type: String, default: '' },
        userId: { type: Number, default: null },
        showNamespace: { type: Boolean, default: true },
    },
    delimiters: ['[[', ']]'],
    setup(props) {
        const tags = Vue.ref([]);
        const loading = Vue.ref(false);

        async function fetchTags() {
            loading.value = true;
            try {
                let url = `/${props.objectType}/get_tags/${props.objectId}`;
                if (props.userId !== null && !isNaN(props.userId)) url += `?user_id=${props.userId}`;
                const res = await fetch(url);
                if (res.ok) {
                    const data = await res.json();
                    tags.value = data.tags || [];
                }
            } catch (e) {
                console.error('Error fetching tags:', e);
            } finally {
                loading.value = false;
            }
        }

        Vue.onMounted(fetchTags);
        Vue.watch(() => props.objectId, fetchTags);

        return { tags, loading };
    },
    data() {
        return { isShowingAll: false };
    },
    computed: {
        visibleTags() {
            return this.isShowingAll ? this.tags : this.tags.slice(0, this.maxVisible);
        }
    },
    template: `
        <div class="tag-display-container">
            <div v-if="sectionTitle" class="d-flex align-items-center mb-2 mt-1">
                <div class="bg-primary rounded-pill me-2" style="width:3px; height:14px;"></div>
                <span class="text-uppercase fw-bold text-muted" style="font-size:0.65rem; letter-spacing:0.05rem;">
                    [[ sectionTitle ]]
                </span>
            </div>

            <div v-if="loading" class="d-flex gap-1 py-1">
                <div class="spinner-grow spinner-grow-sm text-primary opacity-25" role="status"></div>
                <div class="spinner-grow spinner-grow-sm text-primary opacity-25" role="status" style="animation-delay:0.1s"></div>
            </div>

            <div v-else class="d-flex flex-wrap gap-2 align-items-center">
                <single-tag-display
                    v-for="tag in visibleTags" :key="tag.id"
                    :tag="tag"
                    :show-namespace="showNamespace"
                ></single-tag-display>

                <button v-if="tags.length > maxVisible"
                        @click.stop="isShowingAll = !isShowingAll"
                        class="btn btn-sm border rounded-pill text-primary fw-bold shadow-sm"
                        style="font-size:0.7rem; padding:2px 10px; height:26px; background: var(--card-bg-color)">
                    [[ isShowingAll ? 'Collapse' : '+' + (tags.length - maxVisible) ]]
                </button>
            </div>
        </div>
    `
};

export default TagsDisplaysList;