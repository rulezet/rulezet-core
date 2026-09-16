/**
 * RuleHoverPreview — wraps any chip/row content and shows a rich rule
 * preview card on hover: title, format/license, description, author,
 * vote counts, and a compact read-only code snippet. Same
 * fetch-cache/position/show-hide-timer/teleport-to-body pattern as
 * UserChip.js (app/static/js/components/UserChip.js) — kept deliberately
 * close to that implementation rather than inventing new hover-tooltip
 * mechanics.
 *
 * Usage (Vue template):
 *   <rule-hover-preview :rule-id="entry.id">
 *     <span class="badge ...">...</span>
 *   </rule-hover-preview>
 *
 * Props:
 *   ruleId  (Number)  — required; fetched via /rule/get_current_rule
 */
import CodeViewer from '/static/js/components/code-viewer.js';

const { defineComponent, ref, computed } = Vue;

const _cache = {};

function fetchRulePreview(ruleId) {
    if (_cache[ruleId]) return Promise.resolve(_cache[ruleId]);
    return fetch(`/rule/get_current_rule?rule_id=${ruleId}`)
        .then(r => r.ok ? r.json() : null)
        .then(data => { const rule = data && data.rule; if (rule) _cache[ruleId] = rule; return rule; });
}

const RuleHoverPreview = defineComponent({
    name: 'RuleHoverPreview',
    delimiters: ['[[', ']]'],
    components: { 'code-viewer': CodeViewer },
    props: {
        ruleId: { type: Number, required: true },
    },
    setup(props) {
        const previewData    = ref(null);
        const tooltipVisible = ref(false);
        const tooltipStyle   = ref({});
        const chipRef        = ref(null);
        let showTimer = null;
        let hideTimer = null;

        const snippet = computed(() => {
            const content = previewData.value && previewData.value.to_string;
            if (!content) return '';
            const lines = content.split('\n');
            return lines.length > 12 ? lines.slice(0, 12).join('\n') + '\n…' : content;
        });

        function positionTooltip() {
            if (!chipRef.value) return;
            const rect = chipRef.value.getBoundingClientRect();
            const scrollY = window.scrollY;
            const scrollX = window.scrollX;
            const height = 340; // rough popover height for the flip/clamp math below
            let top = rect.bottom + scrollY + 6;
            let left = rect.left + scrollX;
            if (rect.bottom + height > window.innerHeight) {
                top = rect.top + scrollY - height - 6;
            }
            if (left + 360 > window.innerWidth) {
                left = window.innerWidth - 368;
            }
            if (left < 8) left = 8;
            tooltipStyle.value = { top: top + 'px', left: left + 'px' };
        }

        function onMouseEnter() {
            clearTimeout(hideTimer);
            showTimer = setTimeout(async () => {
                positionTooltip();
                if (!previewData.value) {
                    previewData.value = await fetchRulePreview(props.ruleId);
                }
                tooltipVisible.value = true;
                positionTooltip();
            }, 200);
        }

        function onMouseLeave() {
            clearTimeout(showTimer);
            hideTimer = setTimeout(() => { tooltipVisible.value = false; }, 150);
        }

        function onTooltipEnter() { clearTimeout(hideTimer); }
        function onTooltipLeave() {
            hideTimer = setTimeout(() => { tooltipVisible.value = false; }, 150);
        }

        return {
            previewData, tooltipVisible, tooltipStyle, chipRef, snippet,
            onMouseEnter, onMouseLeave, onTooltipEnter, onTooltipLeave,
        };
    },
    template: `
<span ref="chipRef" style="display:inline-flex;align-items:center;" @mouseenter="onMouseEnter" @mouseleave="onMouseLeave">
  <slot></slot>

  <teleport to="body">
    <div v-if="tooltipVisible"
         class="rule-hover-preview-card"
         :style="[tooltipStyle, {position:'absolute', zIndex:9999}]"
         @mouseenter="onTooltipEnter" @mouseleave="onTooltipLeave">

      <div v-if="!previewData" class="rule-hover-preview-card__skeleton">
        <div class="spinner-border spinner-border-sm text-primary"></div>
      </div>

      <template v-else>
        <div class="d-flex align-items-start justify-content-between gap-2 mb-2">
          <div style="min-width:0;">
            <div class="fw-bold text-truncate" style="font-size:.88rem;color:var(--text-color);">[[ previewData.title ]]</div>
            <div class="d-flex align-items-center gap-1 mt-1">
              <span class="badge rounded-pill bg-secondary-subtle text-secondary-emphasis" style="font-size:.65rem;">[[ previewData.format ]]</span>
              <span v-if="previewData.license" class="badge rounded-pill bg-light text-muted border" style="font-size:.65rem;">[[ previewData.license ]]</span>
            </div>
          </div>
          <div class="d-flex align-items-center gap-2 flex-shrink-0" style="font-size:.72rem;color:var(--subtle-text-color);">
            <span><i class="fa-solid fa-thumbs-up me-1 opacity-50"></i>[[ previewData.vote_up ]]</span>
            <span><i class="fa-solid fa-thumbs-down me-1 opacity-50"></i>[[ previewData.vote_down ]]</span>
          </div>
        </div>

        <p v-if="previewData.description" class="mb-2 text-muted"
           style="font-size:.78rem;line-height:1.4;max-height:52px;overflow:hidden;">
          [[ previewData.description ]]
        </p>

        <div class="mb-2" style="font-size:.72rem;color:var(--subtle-text-color);">
          <span v-if="previewData.author"><i class="fa-solid fa-user me-1 opacity-50"></i>[[ previewData.author ]]</span>
          <span v-if="previewData.creation_date" class="ms-2"><i class="fa-regular fa-calendar me-1 opacity-50"></i>[[ previewData.creation_date ]]</span>
        </div>

        <div v-if="snippet" class="mb-2" style="border-radius:8px;overflow:hidden;">
          <code-viewer :code="snippet" :language="previewData.format" max-height="140px" :show-lines="false" :foldable="false"></code-viewer>
        </div>

        <a :href="'/rule/detail_rule/' + ruleId" class="btn btn-sm btn-outline-primary w-100" style="font-size:.75rem;padding:3px 0;" @click.stop>
          <i class="fa-solid fa-arrow-up-right-from-square me-1"></i>View rule
        </a>
      </template>
    </div>
  </teleport>
</span>
`,
});

export default RuleHoverPreview;
