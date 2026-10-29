/**
 * Rulezet's own section of the YARA editor's "Credits & licences" page (options.credits of
 * rulezet-editor): what Rulezet adds around the editor. Markdown, rendered safely by the editor.
 */
export const RULEZET_EDITOR_CREDITS = `# Rulezet

The YARA editor runs inside [Rulezet](https://rulezet.org) (CIRCL, AGPL-3.0).

## Tests on samples

| Project | Used for | Licence |
|---|---|---|
| [rulezet-tester](https://github.com/rulezet/rulezet-tester) | runs the rules on sample sets (Test panel, test when creating) | AGPL-3.0 |
| [yara-python](https://github.com/VirusTotal/yara-python) / libyara | the engine the tests and the server checks use | Apache-2.0 / BSD-3-Clause |
| [bubblewrap](https://github.com/containers/bubblewrap) | the sandbox every test runs in (no network, read-only) | LGPL-2.0-or-later |
| [MalwareBazaar](https://bazaar.abuse.ch/) (abuse.ch) | real samples, fetched on the isolated lab machine only, when it is set up | data under CC0 |

## External checks

Advice under the editor and in the Create step, next to Rulezet's own validation.

| Project | Used for | Licence |
|---|---|---|
| [YARA-X](https://github.com/VirusTotal/yara-x) (VirusTotal) | diagnostics of the new YARA engine, formatter | BSD-3-Clause |
| [CCCS YARA](https://github.com/CybercentreCanada/CCCS-Yara) (Canadian Centre for Cyber Security) | metadata checked against the CCCS YARA specification, generated id / fingerprint | MIT |
| [yaraQA](https://github.com/Neo23x0/yaraQA) (Florian Roth) | logic and performance advice on strings and conditions | GPL-3.0 |
| [plyara](https://github.com/plyara/plyara) | parses the rules for CCCS and yaraQA | Apache-2.0 |
| [MITRE ATT&CK](https://attack.mitre.org/) | ATT&CK data read by the CCCS checks | ATT&CK terms of use |
`;
