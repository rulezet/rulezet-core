import { getTextColor, mapIcon } from './utils/galaxie.js';

/**
 * SingleTagDisplay
 * Renders one tag as a split pill with a hover tooltip.
 * Uses the same getTextColor + mapIcon as the rest of the tag system.
 */
const SingleTagDisplay = {
    props: {
        tag: { type: Object, required: true },
        showNamespace: { type: Boolean, default: true },
    },
    delimiters: ['[[', ']]'],
    setup(props) {
        function namespaceOf(name) {
            if (!name || !name.includes(':')) return '';
            if (name.startsWith('misp-galaxy:') && name.includes('=')) {
                return name.split(':')[1].split('=')[0];
            }
            return name.split(':')[0];
        }

        function valueOf(name) {
            if (!name) return '';
            const m = name.match(/="(.+)"$/);
            if (m) return m[1];
            if (name.includes(':')) return name.split(':').slice(1).join(':');
            return name;
        }

        function label(tag) {
            const ns = namespaceOf(tag.name);
            const val = valueOf(tag.name);
            if (props.showNamespace && ns) return `${ns}:${val}`;
            return val;
        }

        return { getTextColor, mapIcon, label };
    },
    template: `
        <div class="tag-wrapper d-inline-block">
            <span class="tag-split shadow-sm on-hover-zoom">
                <span class="tag-left" v-html="mapIcon(tag.icon)"></span>
                <span class="tag-right" :style="{ backgroundColor: tag.color || '#6c757d' }" :title="tag.name">
                    <span :style="{ color: getTextColor(tag.color || '#6c757d') }" class="fw-bold">
                        [[ label(tag) ]]
                    </span>
                </span>
            </span>
            <div class="tag-tooltip animate__animated animate__fadeIn">
                <div class="hover-bridge"></div>
                <div class="tooltip-header" :style="{ borderLeft: '4px solid ' + (tag.color || '#6c757d') }">
                    <span v-html="mapIcon(tag.icon)" class="me-2 text-white"></span>
                    <strong class="text-white">[[ tag.name ]]</strong>
                </div>
                <div class="tooltip-body">
                    <div class="description-container">
                        <div class="description-scroll text-white-50">
                            [[ tag.description || 'No description available.' ]]
                        </div>
                    </div>
                    <div class="d-flex justify-content-between mt-2 pt-2 border-top border-white border-opacity-10" style="font-size:0.7rem;">
                        <span class="text-white-50">
                            <i :class="tag.visibility === 'public' ? 'fas fa-eye me-1' : 'fas fa-eye-slash me-1'"></i>
                            [[ tag.visibility || 'private' ]]
                        </span>
                        <span v-if="tag.created_at" class="text-white-50">
                            <i class="far fa-calendar-alt me-1"></i>[[ tag.created_at ]]
                        </span>
                    </div>
                </div>
                <div class="tooltip-arrow"></div>
            </div>
        </div>
    `
};

export default SingleTagDisplay;