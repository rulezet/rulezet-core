const TestResultDisplay = {
    name: 'TestResultDisplay',
    delimiters: ['[[', ']]'],
    props: {
        result:  { type: Object, required: true },  // { matched, score, details, quality_hints, execution_time_ms, error }
        testUuid:{ type: String, default: null },
    },
    data() {
        return { showDetails: false };
    },
    computed: {
        pct()       { return Math.round((this.result.score || 0) * 100); },
        scoreClass() {
            const s = this.result.score || 0;
            if (!this.result.matched) return 'none';
            if (s >= 0.7) return 'high';
            if (s >= 0.3) return 'partial';
            return 'low';
        },
        // SVG circle: r=22, circumference ≈ 138.2
        dashoffset() {
            const c = 138.2;
            return c - (c * (this.result.score || 0));
        },
        detailsJson() {
            return JSON.stringify(this.result.details || {}, null, 2);
        },
    },
    methods: {
        viewFull() {
            if (this.testUuid) window.location = `/rule_tester/test/${this.testUuid}`;
        },
    },
    template: `
<div class="rtr-result-block">
  <!-- header -->
  <div class="rtr-result-header">
    <!-- match badge -->
    <span v-if="result.error && !result.matched" class="rtr-match-badge rtr-match-badge--error">
      <i class="fa-solid fa-circle-xmark"></i> Error
    </span>
    <span v-else-if="result.matched" class="rtr-match-badge rtr-match-badge--matched">
      <i class="fa-solid fa-circle-check"></i> Matched
    </span>
    <span v-else class="rtr-match-badge rtr-match-badge--no-match">
      <i class="fa-regular fa-circle"></i> No Match
    </span>

    <!-- score ring -->
    <div class="rtr-score-ring" v-if="!result.error || result.matched">
      <svg viewBox="0 0 56 56">
        <circle class="rtr-score-ring__track" cx="28" cy="28" r="22"/>
        <circle class="rtr-score-ring__fill" :class="'rtr-score-ring__fill--' + scoreClass"
                cx="28" cy="28" r="22"
                stroke-dasharray="138.2"
                :stroke-dashoffset="dashoffset"/>
      </svg>
      <div class="rtr-score-ring__label">[[ pct ]]%</div>
    </div>

    <div style="flex:1;min-width:0;">
      <div style="font-size:.78rem;font-weight:600;color:var(--text-color);">
        Score: <strong>[[ pct ]]%</strong>
        <span v-if="scoreClass==='high'"   class="ms-1 badge bg-success">HIGH</span>
        <span v-if="scoreClass==='partial'" class="ms-1 badge bg-warning text-dark">PARTIAL</span>
        <span v-if="scoreClass==='low'"    class="ms-1 badge bg-danger">LOW</span>
      </div>
      <div style="font-size:.68rem;color:var(--subtle-text-color);">
        [[ result.execution_time_ms || 0 ]]ms
        <span v-if="result.details && result.details.mode" class="ms-1">
          · [[ result.details.mode.replace(/_/g,' ') ]]
        </span>
      </div>
    </div>

    <a v-if="testUuid" :href="'/rule_tester/test/' + testUuid"
       class="btn btn-outline-secondary btn-sm" style="font-size:.72rem;white-space:nowrap;">
      <i class="fa-solid fa-arrow-up-right-from-square me-1"></i> Full results
    </a>
  </div>

  <!-- error message -->
  <div v-if="result.error" class="rtr-hints">
    <div class="rtr-hint-item">
      <i class="fa-solid fa-circle-exclamation rtr-hint-icon" style="color:#dc3545;"></i>
      [[ result.error ]]
    </div>
  </div>

  <!-- quality hints -->
  <div v-if="result.quality_hints && result.quality_hints.length" class="rtr-hints">
    <div v-for="hint in result.quality_hints" :key="hint" class="rtr-hint-item">
      <i class="fa-solid fa-lightbulb rtr-hint-icon"></i>
      [[ hint ]]
    </div>
  </div>

  <!-- details accordion -->
  <div class="rtr-details">
    <div class="rtr-details-toggle" @click="showDetails = !showDetails">
      <i class="fa-solid" :class="showDetails ? 'fa-chevron-down' : 'fa-chevron-right'"></i>
      Raw details
    </div>
    <pre v-if="showDetails" class="rtr-details-body">[[ detailsJson ]]</pre>
  </div>
</div>
`,
};

export default TestResultDisplay;
