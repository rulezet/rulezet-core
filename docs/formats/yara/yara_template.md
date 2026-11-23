# Writing a YARA rule for Rulezet

How Rulezet reads a YARA rule, and how to write each part so every field is filled.
The machine-readable version (every key, its aliases, type and example) is
[`yara_template.json`](yara_template.json), which also holds a full example rule.

## General syntax

- A meta entry is `key = "value"`. Write values **in double quotes**: integers and
  `true`/`false` are valid YARA, but only end up in the extra metadata, never in
  title / author / version / license / uuid.
- Author, description, license, version, id and source come from the **first `meta:` block**
  of the file. Keep one rule per file.
- A key can be repeated (`reference` twice): every value is kept for references and
  extra metadata. For the main fields, the last value wins.
- A list is one string: `"a, b, c"`. Tags also accept spaces, `;` and `|`.
- Keys inside `//` or `/* */` comments are ignored.

## Header

| Part | Rulezet field | How to write it |
|---|---|---|
| `rule Name` | **title** | `[A-Za-z_][A-Za-z0-9_]*`. The rule name is the title, there is no `title` key. |
| `rule Name : t1 t2` | **tags** (imported) | Identifiers separated by spaces. Lower-cased on Rulezet. |
| `global rule` | — | Avoid it: Rulezet flags it as a risk (its condition is ANDed into every rule of the namespace). |
| other rule names in `condition:` | **dependencies** | Resolved from rules already on the instance. Validation fails if one is missing. |

## Meta keys

### Main fields

| Key (aliases) | Rulezet field | Format | If missing |
|---|---|---|---|
| `description` | description + **vulnerabilities** | Free text. CVE / GHSA / GCVE ids written here are linked to the rule. For YARA this is the only place Rulezet reads them from. | `Rule <name> (No description metadata provided).` |
| `author` | author | `"Jane Doe (@janedoe)"`, several authors: `"Alice, Bob"` | repo owner or `Unknown` |
| `license` | license | SPDX id (`DRL-1.1`, `MIT`, `CC-BY-4.0`…) | repo license or `unknown` |
| `version` | version | `"1.0"`, **quoted** | `1.0` |
| `id` (`uuid`) | original_uuid | UUID v4, generated once and **never changed**. Rulezet uses it to recognise the rule on re-import, GitHub update or connector sync. | `Unknown` |
| `source` | source | Project or repo URL. On a GitHub import, the repo URL is used instead. | repo URL or `Unknown` |

### References, tags, markings, ATT&CK

| Key (aliases) | Rulezet field | Format |
|---|---|---|
| `reference` (`references`, `ref`, `refs`, `url`, `urls`, `link`, `links`, `report`, `reports`, `blog`, `source_url`, `more_info`, `see_also`) | references | One URL per entry; repeat the key for several. Up to 50 are kept. |
| `tags` (`tag`) | tags (imported) + platform badges | `"loader, windows, ransomware"`. `namespace:value` makes one tag: `"exploit: cve-2024-1234"` → `exploit:cve-2024-1234`. |
| `tlp` (`sharing`) | TLP tag, replaces the default `tlp:clear` | `"TLP:AMBER"`, `"tlp:amber"` or `"AMBER"`: CLEAR, WHITE, GREEN, AMBER, AMBER+STRICT, RED |
| `pap` | PAP tag, replaces the default `PAP:CLEAR` | `"PAP:GREEN"` or `"GREEN"` |
| `mitre_attack` (`attack`, `attack_id`, `mitre_attack_id`, `technique_id`, `attck`) | ATT&CK techniques | `"T1059.001, T1105"`. A `attack.mitre.org/techniques/…` reference URL is also mapped. |

### Displayed metadata

Every other key is kept as **extra metadata** and shown on the rule page. These keys get a label and
a style:

| Key (aliases) | Shown as | Format |
|---|---|---|
| `date` (`creation_date`) | Date | `YYYY-MM-DD` |
| `modified` (`last_modified`, `updated_date`) | Modified | `YYYY-MM-DD` |
| `hash` (`sha256`, `md5`, `sha1`) | hash, type detected | hex, one per entry, repeatable |
| `malware_family` (`malware`, `family`) | red badge | `"Mirai, Gafgyt"` |
| `threat_actor` (`actor`) | purple badge | actor name(s) |
| `malware_type` (`category`, `type`) | orange / blue badge | Loader, Ransomware, RAT, Webshell… |
| `os` (`platform`) | teal badge + platform | Windows, Linux, macOS, Android… |
| `filetype` | blue badge | PE, ELF, Mach-O, PDF… |
| `severity` (`level`, `threat_level`, `priority`) | colour scale | informational, low, medium, high, critical |
| `score` (`risk_score`) | meter | integer 0–100 |
| `confidence` (`reliability`) | colour scale | low, medium, high |
| `status` (`maturity`) | colour scale | experimental, test, stable, deprecated |
| `falsepositives` | False positives | free text |

Limits: 40 keys, 20 values per key, 300 characters per value.

## Documentation score

The rule's documentation checklist looks for `description`, `date` and `reference`
(or `reference_url`). Fill all three.

## Minimal good rule

```yara
rule MAL_Example_Loader_Nov26 : loader windows
{
    meta:
        description = "Detects the Example loader dropped by exploitation of CVE-2024-1234"
        author = "Jane Doe"
        date = "2026-11-23"
        version = "1.0"
        license = "DRL-1.1"
        id = "5d1c9a6e-3b2f-4c8e-9a1d-7f4e2b6c8a10"
        reference = "https://example.org/blog/example-loader-analysis"
        tlp = "TLP:CLEAR"
        mitre_attack = "T1105"

    strings:
        $s1 = "ExampleLoader/1.0" ascii wide

    condition:
        uint16(0) == 0x5A4D and $s1
}
```

The full rule with every key is in `example_rule` of `yara_template.json`.
