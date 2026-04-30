import { getTextColor, mapIcon } from '../utils/galaxie.js';

/**
 * TagBadge
 * Renders a tag as a split pill: [icon] [label]
 *
 * The label respects the user-controlled `showNamespace` prop:
 *   showNamespace = true  → 'tlp:green'   /   'atrm:AZT705 - Azure Backup Delete'
 *   showNamespace = false → 'green'       /   'AZT705 - Azure Backup Delete'
 *
 * For galaxy tags, the namespace shown is the type ('atrm', 'threat-actor'…)
 * — the noisy 'misp-galaxy:' prefix is dropped because it is always the same.
 */
const TagBadge = {
    props: {
        tag: { type: Object, required: true },
        size: { type: String, default: 'md' },
        showNamespace: { type: Boolean, default: true },
    },
    setup(props) {
        const { computed } = Vue;

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

        const label = computed(() => {
            const ns = namespaceOf(props.tag.name);
            const val = valueOf(props.tag.name);
            if (props.showNamespace && ns) return `${ns}:${val}`;
            return val;
        });

        return { getTextColor, mapIcon, label };
    },
    template: `
        <span class="tag-split shadow-sm on-hover-zoom" :class="'tag-' + size">
            <span class="tag-left" v-html="mapIcon(tag.icon)"></span>
            <span class="tag-right" :style="{ backgroundColor: tag.color || '#6c757d' }" :title="tag.name">
                <span :style="{ color: getTextColor(tag.color || '#6c757d') }">{{ label }}</span>
            </span>
        </span>
    `
};

export default TagBadge;