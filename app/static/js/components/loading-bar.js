export default {
    name: 'LoadingBar',
    props: {
        active: { type: Boolean, default: false }
    },
    template: `
        <transition name="fade">
            <div v-if="active" class="progress-bar-container">
                <div class="progress-bar-value"></div>
            </div>
        </transition>
    `,
}
