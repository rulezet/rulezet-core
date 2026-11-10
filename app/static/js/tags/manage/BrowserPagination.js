/**
 * BrowserPagination — pagination of the tag browser tabs: the shared PaginationComponent
 * (rule/paginationComponent.js) behind the props / event its callers already use.
 *   <browser-pagination :current="page" :total="pages" @change="go" />
 */
import PaginationComponent from '/static/js/rule/paginationComponent.js';

const BrowserPagination = {
    components: { 'pagination-component': PaginationComponent },
    props: {
        current: { type: Number, required: true },
        total: { type: Number, required: true },
    },
    emits: ['change'],
    template: `<pagination-component v-if="total > 1" :current-page="current" :total-pages="total" @change-page="p => $emit('change', p)"></pagination-component>`,
};

export default BrowserPagination;
