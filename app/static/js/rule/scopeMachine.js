/**
 * scopeMachine.js — "My machine" for a scope declaration: what the browser can tell about the
 * computer it runs on (operating system, architecture, OS version), as scope criteria.
 * Only after the user said yes (askAndDetect shows the question); nothing leaves the browser
 * until the user saves the declaration. Used by the Scope tab and the review dialog's scope form.
 *
 *   const entries = await askAndDetect()   // [] if refused / nothing found, else [{key, value}]
 */

function osFrom(text) {
    const t = (text || '').toLowerCase();
    if (t.includes('android')) return 'android';
    if (/iphone|ipad|ios/.test(t)) return 'ios';
    if (t.includes('win')) return 'windows';
    if (t.includes('mac')) return 'macos';
    if (t.includes('freebsd')) return 'freebsd';
    if (t.includes('linux') || t.includes('x11') || t.includes('cros')) return 'linux';
    return null;
}

function archFrom(arch, bitness, ua) {
    const a = (arch || '').toLowerCase();
    if (a === 'arm') return bitness === '32' ? 'arm32' : 'aarch64';
    if (a === 'x86') return bitness === '32' ? 'i386' : 'x86_64';
    const u = (ua || '').toLowerCase();
    if (/aarch64|arm64/.test(u)) return 'aarch64';
    if (/x86_64|x64|win64|amd64|wow64/.test(u)) return 'x86_64';
    if (/i[3-6]86/.test(u)) return 'i386';
    return null;
}

function windowsVersion(platformVersion) {
    // userAgentData: platformVersion major >= 13 → Windows 11, 1-10 → Windows 10
    const major = parseInt(String(platformVersion || '').split('.')[0], 10);
    if (Number.isNaN(major)) return null;
    return major >= 13 ? '11' : major > 0 ? '10' : null;
}

export async function detectMachine() {
    const ua = navigator.userAgent || '';
    const out = [];
    let os = null, arch = null, version = null;
    const uad = navigator.userAgentData;
    if (uad && uad.getHighEntropyValues) {
        try {
            const v = await uad.getHighEntropyValues(['architecture', 'bitness', 'platformVersion']);
            os = osFrom(uad.platform);
            arch = archFrom(v.architecture, v.bitness, ua);
            version = os === 'windows' ? windowsVersion(v.platformVersion) : (v.platformVersion || null);
        } catch { /* the browser refused: fall back on the user agent */ }
    }
    os = os || osFrom(ua);
    arch = arch || archFrom(null, null, ua);
    if (!version) {
        const m = ua.match(/Mac OS X ([\d_]+)/) || ua.match(/Android ([\d.]+)/) || ua.match(/OS ([\d_]+) like Mac/);
        if (m) version = m[1].replace(/_/g, '.');
    }
    if (os) out.push({ key: 'os', value: os });
    if (arch) out.push({ key: 'os::arch', value: arch });
    if (version) out.push({ key: 'os::version', value: version });
    return out;
}

export async function askAndDetect() {
    const ok = window.confirm('Fill the scope with this computer? Your browser tells its operating system, '
        + 'architecture and version — nothing is sent until you save the declaration.');
    if (!ok) return [];
    return detectMachine();
}

/** Merge detected criteria into a form's entries: replace the same key, keep the others. */
export function mergeEntries(entries, detected) {
    const keys = new Set(detected.map(d => d.key));
    return [...entries.filter(e => !keys.has(e.key) && (e.value || '').trim()), ...detected];
}
