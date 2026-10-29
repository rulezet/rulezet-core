/**
 * formatSelect.js — the Format filter of the rules list: the chosen format shown like the format
 * badge of the rows (logo + colour, formatChip.js), and a menu of every format with its logo.
 *
 *   <format-select v-model="ruleType" :formats="rulesFormats" @change="onFilterChange" />
 *
 * Props:
 *   modelValue  the chosen format ('' = all formats)
 *   formats     [{ id, name }] (/rule/get_rules_formats)
 * Emits: update:modelValue, change
 */
import { formatLook } from '/static/js/rule/formatChip.js'

export default {
    name: 'FormatSelect',
    delimiters: ['[[', ']]'],
    props: {
        modelValue: { type: String, default: '' },
        formats: { type: Array, default: () => [] },
    },
    emits: ['update:modelValue', 'change'],
    methods: {
        look(name) { return formatLook(name) },
        pick(name) {
            this.$emit('update:modelValue', name)
            this.$emit('change', name)
        },
    },
    template: `
<div class="dropdown fsel">
    <button type="button" class="fsel-trigger" data-bs-toggle="dropdown" aria-expanded="false"
            data-bs-popper-config='{"strategy":"fixed"}'
            :class="{ 'fsel-trigger--set': modelValue }" :style="modelValue ? { '--fmt': look(modelValue).color } : null"
            aria-label="Format">
        <template v-if="modelValue">
            <span class="fmt-chip__logo" v-if="look(modelValue).logo"><img :src="look(modelValue).logo" alt=""></span>
            <span class="fsel-label">[[ look(modelValue).title ]]</span>
        </template>
        <span v-else class="fsel-placeholder"><i class="fa-solid fa-file-code"></i>Format</span>
        <i class="fa-solid fa-chevron-down fsel-caret"></i>
    </button>
    <ul class="dropdown-menu fsel-menu shadow-lg border-0">
        <li>
            <button type="button" class="fsel-item" :class="{ 'fsel-item--on': !modelValue }" @click="pick('')">
                <span class="fsel-item__logo fsel-item__logo--all"><i class="fa-solid fa-layer-group"></i></span>
                <span class="fsel-item__name">All formats</span>
                <i v-if="!modelValue" class="fa-solid fa-check fsel-check"></i>
            </button>
        </li>
        <li v-for="f in formats" :key="f.id || f.name">
            <button type="button" class="fsel-item" :class="{ 'fsel-item--on': modelValue === f.name }"
                    :style="{ '--fmt': look(f.name).color }" @click="pick(f.name)">
                <span class="fsel-item__logo">
                    <img v-if="look(f.name).logo" :src="look(f.name).logo" alt="" loading="lazy">
                    <i v-else class="fa-solid fa-file-code"></i>
                </span>
                <span class="fsel-item__name">[[ look(f.name).title ]]</span>
                <i v-if="modelValue === f.name" class="fa-solid fa-check fsel-check"></i>
            </button>
        </li>
    </ul>
</div>`,
}
