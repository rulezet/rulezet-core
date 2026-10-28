/**
 * rulePicker.js — choose rules in Rulezet's full rule list (filters, search, pagination), in a
 * full-screen modal, from anywhere: pickRules() opens it and resolves with the chosen rules.
 *
 *   const picked = await pickRules({ selected: [{ id, title }], max: 20, csrfToken, exclude: [ruleId] })
 *   // picked: [{ id, title, format, author }] — or null when the modal was closed with Cancel
 *
 * The rules already chosen show checked (RuleList :pre-selected); every checkbox updates the
 * choice live; "Done" (or closing the modal) hands it back. Used by the YARA editor's Fields
 * panel ("Linked rules" → Browse), same browser as the manual form's RelatedRuleInput.
 * Mounted on demand as its own small Vue app, removed when closed.
 */
import RuleList from '/static/js/rule/ruleList.js';
import { create_message } from '/static/js/toaster.js';

let counter = 0;

export function pickRules({ selected = [], max = 20, csrfToken = '', exclude = [], title = 'Choose the linked rules' } = {}) {
    const { createApp, ref, nextTick } = Vue;
    const id = `rule-picker-${++counter}`;
    const host = document.createElement('div');
    document.body.appendChild(host);

    return new Promise((resolve) => {
        let result = null;
        const app = createApp({
            delimiters: ['[[', ']]'],
            components: { 'rule-list': RuleList },
            setup() {
                const chosen = ref(selected.map(r => ({ id: r.id, title: r.title, format: r.format || '', author: r.author || '' })));
                const excluded = new Set(exclude.map(Number));
                function onToggle(rule, isSelected) {
                    if (isSelected) {
                        if (excluded.has(Number(rule.id))) {
                            create_message('A rule cannot be linked to itself.', 'warning-subtle');
                            return;
                        }
                        if (chosen.value.length >= max) {
                            create_message(`At most ${max} linked rules.`, 'warning-subtle');
                            return;
                        }
                        if (!chosen.value.some(r => r.id === rule.id)) {
                            chosen.value = [...chosen.value, { id: rule.id, title: rule.title, format: rule.format, author: rule.author }];
                        }
                    } else {
                        chosen.value = chosen.value.filter(r => r.id !== rule.id);
                    }
                }
                function remove(r) { chosen.value = chosen.value.filter(x => x.id !== r.id); }
                function done() {
                    result = chosen.value;
                    bootstrap.Modal.getInstance(document.getElementById(id))?.hide();
                }
                return { id, title, max, csrfToken, chosen, preSelected: selected, onToggle, remove, done };
            },
            template: `
<div class="modal fade" :id="id" tabindex="-1" aria-hidden="true">
  <div class="modal-dialog modal-fullscreen">
    <div class="modal-content border-0 shadow-lg">
      <div class="modal-header border-0 pb-0 flex-wrap gap-2">
        <h6 class="modal-title fw-bold"><i class="fa-solid fa-diagram-project me-2 text-primary"></i>[[ title ]]</h6>
        <span class="rp-count">[[ chosen.length ]] / [[ max ]] chosen</span>
        <div class="ms-auto d-flex gap-2">
          <button type="button" class="btn btn-sm btn-outline-secondary rounded-pill px-3" data-bs-dismiss="modal">Cancel</button>
          <button type="button" class="btn btn-sm btn-primary rounded-pill px-3" @click="done"><i class="fa-solid fa-check me-1"></i>Done</button>
        </div>
      </div>
      <div v-if="chosen.length" class="rp-chosen px-3 pt-2">
        <span v-for="r in chosen" :key="r.id" class="rp-chip" :title="r.format ? r.format + ' · ' + (r.author || '?') : ''">
          [[ r.title ]] <button type="button" @click="remove(r)" aria-label="Remove">×</button>
        </span>
      </div>
      <div class="modal-body">
        <rule-list mode="select" default-view="table" fetch-url="/rule/data_table" :sync-url="false"
            :show-filters="true" :show-export="false" :show-create="false" :current-user-is-authenticated="true"
            :csrf-token="csrfToken" :initial-per-page="20" :pre-selected="preSelected" :show-confirm-button="false"
            @toggle-select="onToggle"></rule-list>
      </div>
    </div>
  </div>
</div>`,
        });
        app.mount(host);
        nextTick(() => {
            const el = document.getElementById(id);
            const modal = bootstrap.Modal.getOrCreateInstance(el);
            el.addEventListener('hidden.bs.modal', () => {
                resolve(result);                       // null: closed without "Done"
                app.unmount();
                host.remove();
            }, { once: true });
            modal.show();
        });
    });
}

/** The editor's pickValues for the "Linked rules" field: rules in and out as Fields-panel items. */
export function linkedRulesPicker(csrfToken, exclude = []) {
    return async (def, items) => {
        if (def.id !== 'related') return null;
        const picked = await pickRules({
            selected: items.map(i => ({ id: Number(i.value), title: i.label || String(i.value) })),
            max: def.max || 20, csrfToken, exclude,
        });
        return picked && picked.map(r => ({ value: r.id, label: r.title,
                                           detail: r.format ? `${r.format} · ${r.author || '?'}` : undefined }));
    };
}
