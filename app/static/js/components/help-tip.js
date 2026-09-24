/**
 * help-tip.js — small "?" icon that explains something on hover / click.
 *
 * The bubble is teleported to <body> with position:fixed so it's never
 * clipped by overflow:hidden parents (same approach as the tag tooltips).
 * Works on touch devices (tap toggles, tap elsewhere closes).
 *
 * Props:
 *   text   String  required — plain text (line breaks kept)
 *   title  String  optional bold first line
 *   width  Number  bubble max width in px (default 300)
 *
 * Usage:
 *   <help-tip title="Releases" text="A release freezes the bundle…"></help-tip>
 */

const { ref, onBeforeUnmount } = Vue

export default {
    name: 'HelpTip',
    props: {
        text:  { type: String, required: true },
        title: { type: String, default: '' },
        width: { type: Number, default: 300 },
    },
    template: `
    <span class="ht-wrap" ref="anchor"
          @mouseenter="show" @mouseleave="hideSoon" @click.stop.prevent="toggle"
          @keydown.enter.prevent="toggle" @keydown.esc="hide"
          tabindex="0" role="button" :aria-label="(title ? title + ': ' : '') + text">
        <i class="fa-solid fa-circle-question ht-icon"></i>
        <teleport to="body">
            <div v-if="open" class="ht-bubble" :style="style" @mouseenter="cancelHide" @mouseleave="hideSoon" role="tooltip">
                <strong v-if="title">{{ title }}</strong>
                <span>{{ text }}</span>
            </div>
        </teleport>
    </span>
    `,
    setup(props) {
        const open = ref(false)
        const anchor = ref(null)
        const style = ref({})
        let timer = null

        function place() {
            const r = anchor.value?.getBoundingClientRect()
            if (!r) return
            const w = Math.min(props.width, window.innerWidth - 24)
            let left = r.left + r.width / 2 - w / 2
            left = Math.max(12, Math.min(left, window.innerWidth - w - 12))
            const below = r.bottom + 8
            const fitsBelow = below + 140 < window.innerHeight
            style.value = fitsBelow
                ? { left: left + 'px', top: below + 'px', maxWidth: w + 'px' }
                : { left: left + 'px', bottom: (window.innerHeight - r.top + 8) + 'px', maxWidth: w + 'px' }
        }
        function show() { cancelHide(); place(); open.value = true }
        function hide() { open.value = false }
        function hideSoon() { cancelHide(); timer = setTimeout(hide, 150) }
        function cancelHide() { clearTimeout(timer) }
        function toggle() { open.value ? hide() : show() }
        const onDoc = () => hide()
        document.addEventListener('click', onDoc)
        window.addEventListener('scroll', onDoc, true)
        onBeforeUnmount(() => {
            document.removeEventListener('click', onDoc)
            window.removeEventListener('scroll', onDoc, true)
            clearTimeout(timer)
        })
        return { open, anchor, style, show, hide, hideSoon, cancelHide, toggle }
    },
}
