import { create_message } from '/static/js/toaster.js';

const TestHistoryPanel = {
    name: 'TestHistoryPanel',
    delimiters: ['[[', ']]'],
    props: {
        ruleUuid:        { type: String, required: true },
        ruleId:          { type: Number, default: null },
        currentUserId:   { type: Number, default: null },
        isAdmin:         { type: Boolean, default: false },
        isAuthenticated: { type: Boolean, default: false },
        csrfToken:       { type: String, default: '' },
    },
    data() {
        return {
            tests:        [],
            loading:      true,
            page:         1,
            totalPages:   1,
            total:        0,
            filter:       'all',
            togglingUuid: null,
        };
    },
    mounted() { this.load(); },
    watch: { filter() { this.page = 1; this.load(); } },
    computed: {
        filters() {
            const f = [{ key: 'all', label: 'All' }];
            if (this.isAuthenticated) f.push({ key: 'mine', label: 'Mine' });
            f.push({ key: 'public', label: 'Public' });
            return f;
        },
    },
    methods: {
        async load() {
            this.loading = true;
            try {
                const params = new URLSearchParams({ page: this.page, per_page: 10 });
                const resp = await fetch(`/api/rule_tester/public/rule/${this.ruleUuid}/tests?${params}`);
                const data = await resp.json();
                let items  = data.tests || [];

                if (this.filter === 'mine')   items = items.filter(t => t.user_id === this.currentUserId);
                if (this.filter === 'public') items = items.filter(t => t.is_public);

                this.tests      = items;
                this.totalPages = data.pages || 1;
                this.total      = data.total  || 0;
            } catch (e) {
                console.error('TestHistoryPanel load error', e);
            } finally {
                this.loading = false;
            }
        },
        async toggleVisibility(e, test) {
            e.preventDefault();
            e.stopPropagation();
            if (!this.isAuthenticated) return;
            this.togglingUuid = test.uuid;
            try {
                const resp = await fetch(`/api/rule_tester/private/test/${test.uuid}/visibility`, {
                    method: 'PUT',
                    headers: { 'X-CSRFToken': this.csrfToken },
                });
                const data = await resp.json();
                test.is_public = data.is_public;
                create_message(data.is_public ? 'Test is now public.' : 'Test is now private.', 'success');
            } catch (e) {
                create_message('Failed to update visibility.', 'danger');
            } finally {
                this.togglingUuid = null;
            }
        },
        isOwner(test)  { return this.currentUserId && test.user_id === this.currentUserId; },
        canToggle(test){ return this.isOwner(test) || this.isAdmin; },
        stripeClass(t) {
            if (t.status === 'running' || t.status === 'pending') return 'th-stripe--running';
            if (t.matched_count > 0) return 'th-stripe--matched';
            if (t.status === 'done') return 'th-stripe--no-match';
            return 'th-stripe--default';
        },
        statusStyle(t) {
            if (t.status === 'running' || t.status === 'pending')
                return 'background:#0d6efd;color:#fff;';
            if (t.matched_count > 0)
                return 'background:#198754;color:#fff;';
            if (t.status === 'done')
                return 'background:var(--border-color);color:var(--subtle-text-color);';
            return 'background:#6c757d;color:#fff;';
        },
        statusLabel(t) {
            if (t.status === 'pending') return 'Queued';
            if (t.status === 'running') return 'Running';
            if (t.matched_count > 0)   return 'Matched';
            if (t.status === 'done')   return 'No match';
            return t.status;
        },
        statusIcon(t) {
            if (t.status === 'running') return 'fa-circle-notch fa-spin';
            if (t.status === 'pending') return 'fa-clock';
            if (t.matched_count > 0)   return 'fa-check';
            if (t.status === 'done')   return 'fa-xmark';
            return 'fa-circle';
        },
        matchRate(t) {
            if (!t.total_rules || t.matched_count == null) return null;
            return Math.round((t.matched_count / t.total_rules) * 100);
        },
        formatDate(dt) {
            if (!dt) return '';
            const d    = new Date(dt);
            const now  = new Date();
            const diff = Math.floor((now - d) / 1000);
            if (diff < 60)    return 'just now';
            if (diff < 3600)  return Math.floor(diff / 60) + 'm ago';
            if (diff < 86400) return Math.floor(diff / 3600) + 'h ago';
            if (diff < 604800) return Math.floor(diff / 86400) + 'd ago';
            return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
        },
        scoreBarStyle(t) {
            const pct   = this.matchRate(t) || 0;
            const color = pct > 10 ? '#198754' : '#dc3545';
            return 'width:' + pct + '%;background:' + color + ';';
        },
        prevPage() { if (this.page > 1)               { this.page--; this.load(); } },
        nextPage() { if (this.page < this.totalPages)  { this.page++; this.load(); } },
    },

    template: `
<div>
  <!-- Filter tabs -->
  <div class="d-flex align-items-center gap-2 mb-4 flex-wrap">
    <button v-for="f in filters" :key="f.key"
            class="btn btn-sm rounded-pill"
            :class="filter === f.key ? 'btn-primary' : 'btn-outline-secondary'"
            @click="filter = f.key" type="button">
      [[ f.label ]]
    </button>
    <span class="ms-auto" style="font-size:.72rem;color:var(--subtle-text-color);">
      [[ total ]] test(s)
    </span>
  </div>

  <!-- Loading -->
  <div v-if="loading" class="text-center py-5">
    <div class="spinner-border text-primary" role="status"></div>
  </div>

  <!-- Empty -->
  <div v-else-if="!tests.length" class="text-center py-5" style="color:var(--subtle-text-color);">
    <i class="fa-solid fa-flask-vial fa-2x mb-3 d-block opacity-25"></i>
    <p class="mb-2">No tests yet for this rule.</p>
    <a v-if="isAuthenticated" :href="ruleId ? ('/rule/detail_rule/' + ruleId + '/test') : '#'"
       class="btn btn-sm btn-primary rounded-pill">
      <i class="fa-solid fa-flask-vial me-1"></i>Be the first to test this rule
    </a>
  </div>

  <!-- Cards list -->
  <div v-else class="d-flex flex-column gap-3">
    <a v-for="t in tests" :key="t.uuid"
       :href="'/rule_tester/test/' + t.uuid"
       class="th-card">

      <!-- Stripe -->
      <div class="th-card__stripe" :class="stripeClass(t)"></div>

      <div class="th-card__body">

        <!-- Header: user + status -->
        <div class="th-card__header">
          <div class="th-card__meta">
            <!-- Avatar -->
            <div v-if="t.user && (t.is_public || isOwner(t) || isAdmin)"
                 style="width:32px;height:32px;border-radius:50%;overflow:hidden;flex-shrink:0;background:var(--light-bg-color);display:flex;align-items:center;justify-content:center;">
              <img v-if="t.user.avatar" :src="t.user.avatar" :alt="t.user.username"
                   style="width:100%;height:100%;object-fit:cover;">
              <span v-else style="font-size:.75rem;font-weight:700;color:var(--subtle-text-color);">
                [[ (t.user.username||'?')[0].toUpperCase() ]]
              </span>
            </div>
            <div v-else style="width:32px;height:32px;border-radius:50%;background:var(--light-bg-color);display:flex;align-items:center;justify-content:center;flex-shrink:0;">
              <i class="fa-solid fa-user-secret" style="font-size:.75rem;color:var(--subtle-text-color);"></i>
            </div>
            <div>
              <span class="fw-semibold" style="font-size:.875rem;">
                [[ t.user && (t.is_public || isOwner(t) || isAdmin) ? t.user.username : 'Anonymous' ]]
              </span>
              <span style="font-size:.8rem;color:var(--subtle-text-color);margin-left:4px;">ran a test</span>
            </div>
          </div>

          <!-- Status badge -->
          <span class="th-status-badge" :style="statusStyle(t)">
            <i class="fa-solid me-1" :class="statusIcon(t)"></i>[[ statusLabel(t) ]]
          </span>
        </div>

        <!-- Label / description -->
        <div v-if="t.label || t.input_label" class="th-card__message">
          [[ t.label || t.input_label ]]
        </div>

        <!-- Footer chips -->
        <div class="th-card__footer">

          <!-- Format -->
          <span class="th-badge" style="background:#111;color:#fff;font-weight:700;letter-spacing:.06em;">
            [[ (t.format||'').toUpperCase() ]]
          </span>

          <!-- Type -->
          <span class="th-badge">
            <i class="fa-solid me-1" :class="t.test_type==='bulk' ? 'fa-layer-group' : 'fa-crosshairs'"></i>
            [[ t.test_type ]]
          </span>

          <!-- Input type -->
          <span class="th-badge" style="color:#0d6efd;border-color:rgba(13,110,253,.3);background:rgba(13,110,253,.06);">
            [[ t.input_type ]]
          </span>

          <!-- Match rate (bulk) -->
          <span v-if="t.test_type==='bulk' && matchRate(t)!==null" class="th-score">
            <span style="color:var(--subtle-text-color);font-size:.68rem;">match rate</span>
            <span class="th-score__bar">
              <span class="th-score__fill" :style="scoreBarStyle(t)"></span>
            </span>
            <span>[[ matchRate(t) ]]%</span>
          </span>

          <!-- Matched count (bulk) -->
          <span v-if="t.test_type==='bulk' && t.matched_count!=null" class="th-badge"
                :style="t.matched_count>0 ? 'color:#198754;border-color:rgba(25,135,84,.3);background:rgba(25,135,84,.06);' : ''">
            <i class="fa-solid fa-check me-1"></i>[[ t.matched_count ]] matched
          </span>

          <!-- Date -->
          <span class="th-card__time">
            <i class="fa-regular fa-clock me-1"></i>[[ formatDate(t.created_at) ]]
          </span>

          <!-- Visibility toggle -->
          <span v-if="canToggle(t)" @click="toggleVisibility($event, t)"
                class="th-badge ms-auto"
                style="cursor:pointer;"
                :title="t.is_public ? 'Make private' : 'Make public'">
            <i class="fa-solid" :class="t.is_public ? 'fa-globe' : 'fa-lock'"></i>
          </span>
          <span v-else class="ms-auto th-card__time">
            <i class="fa-solid" :class="t.is_public ? 'fa-globe' : 'fa-lock'"></i>
          </span>
        </div>
      </div>
    </a>
  </div>

  <!-- Pagination -->
  <nav v-if="totalPages > 1" class="mt-4">
    <ul class="pagination justify-content-center">
      <li class="page-item" :class="{ disabled: page === 1 }">
        <a class="page-link" href="#" @click.prevent="prevPage">Previous</a>
      </li>
      <li class="page-item disabled">
        <span class="page-link">[[ page ]] / [[ totalPages ]]</span>
      </li>
      <li class="page-item" :class="{ disabled: page === totalPages }">
        <a class="page-link" href="#" @click.prevent="nextPage">Next</a>
      </li>
    </ul>
  </nav>
</div>
`,
};

export default TestHistoryPanel;
