const InputEditorByFormat = {
    name: 'InputEditorByFormat',
    delimiters: ['[[', ']]'],
    props: {
        format:     { type: String, required: true },
        modelValue: { type: Object, default: () => ({ type: 'string', value: '' }) },
    },
    emits: ['update:modelValue'],
    data() {
        return {
            activeType: this.modelValue?.type || this._defaultType(),
            localValue: this.modelValue?.value || '',
            // http request builder
            httpMethod:  'GET',
            httpUrl:     '/',
            httpHeaders: [{ key: '', value: '' }],
            httpBody:    '',
            // host json builder (NSE)
            hostIp:    '192.168.1.1',
            hostPorts: '80,443',
            hostBanners: '',
        };
    },
    computed: {
        inputTypes() {
            const map = {
                yara:     ['string', 'hex', 'file_b64'],
                sigma:    ['json'],
                suricata: ['text_payload', 'http_request', 'hex_payload'],
                zeek:     ['zeek_log_json'],
                wazuh:    ['syslog_line', 'json_event'],
                nse:      ['host_json'],
                crs:      ['http_request'],
                atr:      ['text'],
                nova:     ['text'],
            };
            return map[this.format?.toLowerCase()] || ['text'];
        },
        typeLabel() {
            const labels = {
                string:       'Raw String',
                hex:          'Hex Bytes',
                file_b64:     'File (base64)',
                json:         'Log Event (JSON)',
                text_payload: 'Raw Payload',
                http_request: 'HTTP Request',
                hex_payload:  'Hex Payload',
                syslog_line:  'Syslog Line',
                json_event:   'JSON Event',
                host_json:    'Host Description',
                zeek_log_json:'Zeek Log (JSON)',
                text:         'Text',
            };
            return labels[this.activeType] || this.activeType;
        },
        placeholderText() {
            const p = {
                string:       'Paste text to scan against the rule…',
                hex:          '4d5a 9000 0300 0000…',
                file_b64:     'Base64-encoded file content…',
                json:         '{\n  "CommandLine": "powershell.exe -enc …",\n  "Image": "C:\\\\Windows\\\\System32\\\\powershell.exe"\n}',
                text_payload: 'HTTP/1.1 GET / …',
                hex_payload:  '45 00 00 28 ab cd ef 00…',
                syslog_line:  'Jan  1 00:00:00 hostname sshd[1234]: Failed password for root',
                json_event:   '{"event": {"action": "network-connection"}, "process": {"name": "evil.exe"}}',
                zeek_log_json:'{"_path":"conn","id.orig_h":"1.2.3.4","id.resp_p":443}',
                text:         'Paste content to test against the rule…',
            };
            return p[this.activeType] || '';
        },
    },
    watch: {
        format(newFmt) {
            this.activeType = this._defaultType();
            this.emitValue();
        },
        modelValue(val) {
            if (val && val.type !== this.activeType) this.activeType = val.type;
            if (val && val.value !== this.localValue) this.localValue = val.value;
        },
    },
    methods: {
        _defaultType() {
            const map = {
                yara: 'string', sigma: 'json', suricata: 'text_payload',
                zeek: 'zeek_log_json', wazuh: 'syslog_line', nse: 'host_json',
                crs: 'http_request', atr: 'text', nova: 'text',
            };
            return map[this.format?.toLowerCase()] || 'text';
        },
        selectType(t) {
            this.activeType = t;
            this.emitValue();
        },
        emitValue() {
            let value = this.localValue;
            if (this.activeType === 'http_request') value = this._buildHttpJson();
            if (this.activeType === 'host_json')    value = this._buildHostJson();
            this.$emit('update:modelValue', { type: this.activeType, value });
        },
        _buildHttpJson() {
            const headers = {};
            this.httpHeaders.forEach(h => { if (h.key) headers[h.key] = h.value; });
            return JSON.stringify({
                method: this.httpMethod,
                url:    this.httpUrl,
                headers,
                body:   this.httpBody,
            });
        },
        _buildHostJson() {
            const ports = this.hostPorts.split(',').map(p => parseInt(p.trim())).filter(p => !isNaN(p));
            return JSON.stringify({
                ip:      this.hostIp,
                ports,
                banners: this.hostBanners ? { raw: this.hostBanners } : {},
            });
        },
        addHeader() { this.httpHeaders.push({ key: '', value: '' }); },
        removeHeader(i) { this.httpHeaders.splice(i, 1); },
        onFileChange(e) {
            const file = e.target.files[0];
            if (!file) return;
            const reader = new FileReader();
            reader.onload = ev => {
                this.localValue = ev.target.result.split(',')[1] || '';
                this.emitValue();
            };
            reader.readAsDataURL(file);
        },
    },
    template: `
<div>
  <!-- Mode tabs -->
  <div class="rtr-mode-tabs" v-if="inputTypes.length > 1">
    <button v-for="t in inputTypes" :key="t"
            class="rtr-mode-tab" :class="{ active: activeType === t }"
            @click="selectType(t)" type="button">
      [[ t.replace(/_/g,' ') ]]
    </button>
  </div>

  <!-- string / text / syslog_line / text_payload / hex / hex_payload / zeek_log_json -->
  <div v-if="['string','text','syslog_line','text_payload','hex','hex_payload','zeek_log_json'].includes(activeType)">
    <textarea class="rtr-textarea"
              v-model="localValue"
              @input="emitValue"
              :placeholder="placeholderText"
              rows="6"></textarea>
  </div>

  <!-- json / json_event -->
  <div v-else-if="['json','json_event'].includes(activeType)">
    <textarea class="rtr-textarea"
              v-model="localValue"
              @input="emitValue"
              :placeholder="placeholderText"
              rows="8"
              spellcheck="false"></textarea>
  </div>

  <!-- file_b64 -->
  <div v-else-if="activeType === 'file_b64'" class="mt-1">
    <input type="file" class="form-control form-control-sm" @change="onFileChange">
    <div v-if="localValue" class="mt-2" style="font-size:.72rem;color:var(--subtle-text-color);">
      <i class="fa-solid fa-check text-success me-1"></i>
      File loaded ([[ Math.round(localValue.length * 0.75 / 1024) ]] KB)
    </div>
  </div>

  <!-- http_request -->
  <div v-else-if="activeType === 'http_request'" class="d-flex flex-column gap-2">
    <div class="d-flex gap-2">
      <select class="form-select form-select-sm" style="width:100px;flex-shrink:0;" v-model="httpMethod" @change="emitValue">
        <option v-for="m in ['GET','POST','PUT','PATCH','DELETE','OPTIONS','HEAD']" :key="m">[[ m ]]</option>
      </select>
      <input type="text" class="form-control form-control-sm" v-model="httpUrl" @input="emitValue"
             placeholder="/path?param=value">
    </div>
    <div>
      <div class="d-flex align-items-center gap-2 mb-1" style="font-size:.72rem;color:var(--subtle-text-color);font-weight:600;">
        HEADERS
        <button type="button" class="btn btn-outline-secondary btn-sm py-0 px-2" @click="addHeader" style="font-size:.68rem;">+ Add</button>
      </div>
      <div v-for="(h, i) in httpHeaders" :key="i" class="d-flex gap-2 mb-1">
        <input type="text" class="form-control form-control-sm" v-model="h.key" @input="emitValue" placeholder="Header-Name">
        <input type="text" class="form-control form-control-sm" v-model="h.value" @input="emitValue" placeholder="value">
        <button type="button" class="btn btn-outline-danger btn-sm py-0 px-2" @click="removeHeader(i)">×</button>
      </div>
    </div>
    <textarea class="rtr-textarea" v-model="httpBody" @input="emitValue"
              placeholder="Request body…" rows="3"></textarea>
  </div>

  <!-- host_json (NSE) -->
  <div v-else-if="activeType === 'host_json'" class="d-flex flex-column gap-2">
    <input type="text" class="form-control form-control-sm" v-model="hostIp" @input="emitValue" placeholder="IP address">
    <input type="text" class="form-control form-control-sm" v-model="hostPorts" @input="emitValue"
           placeholder="Open ports (comma-separated): 80,443,8080">
    <textarea class="rtr-textarea" v-model="hostBanners" @input="emitValue"
              placeholder='Service banners (optional): {"http": "Apache/2.4"}' rows="3"></textarea>
  </div>

  <!-- fallback -->
  <div v-else>
    <textarea class="rtr-textarea" v-model="localValue" @input="emitValue"
              :placeholder="placeholderText" rows="6"></textarea>
  </div>
</div>
`,
};

export default InputEditorByFormat;
