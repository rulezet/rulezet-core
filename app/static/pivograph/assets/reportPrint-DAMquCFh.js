import{b as z}from"./index-JwQxvkUN.js";import{reportModel as T,formatDate as v,lowerFirst as y,plural as d,capitalize as L,article as H,detailKey as A}from"./report-9ZQE3pry.js";const N="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700;12..96,800&family=JetBrains+Mono:wght@400;600&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400&display=swap",F=`
/* No page margin: the browser then prints no header or footer of its own
   (address, date, page title). The margins are the table's repeated head and
   foot rows below, and the body's side padding. */
@page { size: A4; margin: 0; }
:root {
  color-scheme: light;
  --ink: #18202e; --muted: #5d6679; --faint: #8a93a6; --rule: #e3e6ee; --wash: #f5f7fb; --accent: #3b63f3;
  --display: "Bricolage Grotesque", system-ui, "Segoe UI", sans-serif;
  --text: "Source Serif 4", Georgia, "Times New Roman", serif;
  --mono: "JetBrains Mono", ui-monospace, Menlo, Consolas, monospace;
}
* { box-sizing: border-box; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { margin: 0; padding: 0 17mm; font: 10pt/1.55 var(--text); color: var(--ink); }
a { color: inherit; text-decoration: none; }
.frame { width: 100%; border-collapse: collapse; }
.frame td { padding: 0; }
.running { height: 20mm; vertical-align: bottom; }
.running div { display: flex; justify-content: space-between; gap: 12pt; padding-bottom: 5pt; margin-bottom: 8mm; border-bottom: 0.6pt solid var(--rule); font: 7.5pt var(--mono); color: var(--faint); }
.bottom { height: 14mm; }

/* First page */
.cover h1 { font: 800 27pt/1.08 var(--display); letter-spacing: -0.02em; margin: 2mm 0 5mm; max-width: 150mm; }
.cover .lede { font-size: 11.5pt; line-height: 1.5; color: #333b4c; max-width: 150mm; margin: 0 0 6mm; }
.legend { display: flex; flex-wrap: wrap; gap: 3pt 14pt; margin: 0 0 5mm; font: 8.5pt var(--display); color: var(--muted); }
.legend span { display: inline-flex; align-items: center; gap: 5pt; }
.legend b { color: var(--ink); font-weight: 600; }
.dot { width: 8pt; height: 8pt; border-radius: 50%; flex: none; }
.figure { margin: 0 0 6mm; }
.figure img { display: block; width: 100%; max-height: 165mm; object-fit: contain; background: #f6f7f9; border: 0.6pt solid var(--rule); border-radius: 5pt; }
.figure figcaption { margin-top: 4pt; font: 8pt var(--mono); color: var(--faint); }
.overview { font-size: 10.5pt; max-width: 160mm; }

/* Sections */
h2 { font: 700 17pt/1.2 var(--display); letter-spacing: -0.01em; margin: 0 0 5mm; break-after: avoid; }
.section { break-before: page; }
.group-head { display: flex; align-items: baseline; gap: 8pt; margin: 7mm 0 3mm; padding-bottom: 3pt; border-bottom: 1.2pt solid var(--group); break-after: avoid; }
.group-head h3 { font: 700 12.5pt var(--display); margin: 0; color: var(--ink); }
.group-head .swatch { width: 9pt; height: 9pt; border-radius: 2pt; background: var(--group); align-self: center; }
.group-head .count { font: 8pt var(--mono); color: var(--faint); margin-left: auto; }

/* A node */
.node { position: relative; padding: 0 0 0 11pt; margin: 0 0 6mm; }
.node::before { content: ""; position: absolute; left: 0; top: 1pt; bottom: 1pt; width: 2.6pt; border-radius: 2pt; background: var(--node); }
.node-head { display: flex; align-items: center; gap: 9pt; margin-bottom: 3pt; break-after: avoid; }
.logo { width: 30pt; height: 30pt; object-fit: contain; flex: none; }
.node-head h4 { font: 700 12pt/1.2 var(--display); margin: 0; }
.chip { display: inline-block; margin-top: 1.5pt; padding: 0.5pt 6pt; border: 0.7pt solid var(--node); border-radius: 20pt; font: 500 7.5pt var(--display); color: var(--node); }
.node p { margin: 0 0 4pt; }
.facts { display: grid; grid-template-columns: 22mm 1fr; gap: 1.5pt 8pt; margin: 4pt 0; font-size: 9pt; }
.facts dt { font: 500 8pt/1.9 var(--display); color: var(--muted); }
.facts dd { margin: 0; min-width: 0; overflow-wrap: anywhere; }
.facts .url { font: 8pt/1.9 var(--mono); color: #2447c8; }
.repo-desc { font-style: italic; color: #333b4c; }
.stats { display: flex; flex-wrap: wrap; gap: 1pt 10pt; font: 7.8pt var(--mono); color: var(--muted); margin-top: 1pt; }
.stats b { color: var(--ink); font-weight: 600; }
.pills { display: flex; flex-wrap: wrap; gap: 3pt; margin: 5pt 0; }
.pill { display: inline-flex; align-items: center; gap: 3pt; padding: 1pt 6.5pt; border-radius: 20pt; font: 600 7.5pt/1.5 var(--display); white-space: nowrap; }
.pill svg { width: 7pt; height: 7pt; }
.label { font: 600 8pt var(--display); color: var(--muted); margin: 6pt 0 2pt; break-after: avoid; }
.details { width: 100%; border-collapse: collapse; font-size: 8.8pt; margin: 2pt 0 4pt; }
.details th, .details td { text-align: left; vertical-align: top; padding: 2.5pt 6pt 2.5pt 0; border-top: 0.5pt solid var(--rule); }
.details th { width: 28mm; font: 500 8pt var(--display); color: var(--muted); }
.details .details th { width: 22mm; }
.details .details tr:first-child > * { border-top: 0; }
.details ul { margin: 0; padding-left: 11pt; }
.relations { list-style: none; margin: 2pt 0 0; padding: 0; font-size: 9.2pt; }
.relations li { position: relative; padding-left: 12pt; margin: 1.5pt 0; }
.relations li::before { content: "→"; position: absolute; left: 0; color: var(--node, var(--faint)); font-family: var(--display); }
strong { font-family: var(--display); font-weight: 600; font-size: 0.95em; }

/* Relationships */
.rel-head svg { flex: none; align-self: center; }
.rel { margin: 0 0 4mm; break-inside: avoid-page; }
.rel > p:first-child { margin: 0 0 2pt; font-size: 10pt; }
.rel .desc { color: #333b4c; font-size: 9.4pt; margin: 0 0 2pt; }
.plain { margin: 0 0 4mm; }

/* Tags */
.tag-index { columns: 2; column-gap: 9mm; font-size: 9pt; }
.tag-index div { break-inside: avoid; margin: 0 0 4pt; }
.tag-index .pill { margin-right: 4pt; }
.colophon { margin-top: 10mm; padding-top: 4pt; border-top: 0.6pt solid var(--rule); font: 7.5pt var(--mono); color: var(--faint); }
`,e=t=>String(t??"").replace(/[&<>"]/g,o=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"})[o]),w=t=>/^(https?:|mailto:)/i.test(t??"")?t:null;function m(t,o=t,i="url"){const r=w(t),s=e(String(o).replace(/^https?:\/\/(www\.)?/,"").replace(/\/$/,""));return r?`<a class="${i}" href="${e(r)}">${s}</a>`:e(o)}function f(t,o=`#${t.tag}`){const i=t.icon?z(t.icon,t.fg)??"":"";return`<span class="pill" style="background:${e(t.color)};color:${e(t.fg)}">${i}${e(o)}</span>`}function c(t){return t.map(o=>typeof o=="string"?e(o):o.node!==void 0?`<strong>${e(o.name)}</strong>`:o.tag!==void 0?f(o):"").join("")}function $(t,o){return`<svg width="26" height="8" viewBox="0 0 26 8"><line x1="1" y1="4" x2="19" y2="4" stroke="${e(t)}" stroke-width="2" ${o?'stroke-dasharray="4 3"':""}/><path d="M18,0.5 L25,4 L18,7.5 Z" fill="${e(t)}"/></svg>`}function g(t,o=""){return String(t).trim().split(/\n\s*\n/).map(i=>`<p${o?` class="${o}"`:""}>${e(i)}</p>`).join("")}function h(t){if(typeof t=="boolean")return t?"yes":"no";if(Array.isArray(t))return t.every(i=>i===null||typeof i!="object")?t.map(h).join(", "):`<ul>${t.map(i=>`<li>${h(i)}</li>`).join("")}</ul>`;if(t&&typeof t=="object")return u(t);const o=String(t);return w(o)&&/^\S+$/.test(o)?m(o):e(o)}function u(t){return`<table class="details">${Object.entries(t).map(([o,i])=>`<tr><th>${e(A(o))}</th><td>${h(i)}</td></tr>`).join("")}</table>`}function G({slug:t,url:o,info:i,topics:r}){let s=m(o,t);if(!i)return s;i.description&&(s+=`<div class="repo-desc">${e(i.description)}</div>`);const a=[];return Number.isFinite(i.stars)&&a.push(`<span>★ <b>${i.stars}</b></span>`),Number.isFinite(i.forks)&&a.push(`<span><b>${i.forks}</b> ${d(i.forks,"fork")}</span>`),Number.isFinite(i.issues)&&a.push(`<span><b>${i.issues}</b> open ${d(i.issues,"issue")}</span>`),i.language&&a.push(`<span>${e(i.language)}</span>`),i.license&&a.push(`<span>${e(i.license)}</span>`),i.pushedAt&&a.push(`<span>updated ${e(v(i.pushedAt))}</span>`),i.archived&&a.push("<span><b>archived</b></span>"),a.length&&(s+=`<div class="stats">${a.join("")}</div>`),r.length&&(s+=`<div class="stats">Topics: ${r.map(e).join(", ")}</div>`),s}function M(t,o){const i=[];t.url&&i.push(["Website",m(t.url)]),t.github&&i.push(["Source code",G(t.github)]);for(const s of t.links)i.push([e(s.label||"Link"),m(s.url)]);const r=t.typeLabel&&!t.description?`<p>${e(t.name)} is ${H(t.typeLabel)} ${e(y(t.typeLabel))}.</p>`:"";return`<article class="node" style="--node:${e(t.color)}">
  <div class="node-head">${o?`<img class="logo" src="${e(o)}" alt="">`:""}<div><h4>${e(t.name)}</h4>${t.typeLabel?`<span class="chip">${e(t.typeLabel)}</span>`:""}</div></div>
  ${r}${t.description?g(t.description):""}
  ${i.length?`<dl class="facts">${i.map(([s,a])=>`<dt>${s}</dt><dd>${a}</dd>`).join("")}</dl>`:""}
  ${t.tags.length?`<div class="pills">${t.tags.map(s=>f(s)).join("")}</div>`:""}
  ${t.details?`<div class="label">Details</div>${u(t.details)}`:""}
  ${t.relations.length?`<div class="label">Relationships</div><ul class="relations">${t.relations.map(s=>`<li>${c(s)}</li>`).join("")}</ul>`:""}
</article>`}function R(t,{image:o,images:i=new Map,baseUrl:r,date:s=new Date}={}){const a=T(t),p=v(s),b=[...a.groups.filter(n=>n.key).map(n=>`<span><i class="dot" style="background:${e(n.color)}"></i><b>${n.nodes.length}</b> ${e(y(d(n.nodes.length,n.label)))}</span>`),...a.relations.filter(n=>n.key).map(n=>`<span>${$(n.color,n.dashed)}<b>${n.count}</b> × ${e(n.label)}</span>`)],k=`<section class="cover">
  <h1>${e(a.title)}</h1>
  ${a.description?g(a.description,"lede"):""}
  ${b.length?`<div class="legend">${b.join("")}</div>`:""}
  ${o?`<figure class="figure"><img src="${e(o)}" alt="Graph of ${e(a.title)}"><figcaption>The graph as drawn on ${e(p)}: ${a.counts.nodes} ${d(a.counts.nodes,"node")}, ${a.counts.edges} ${d(a.counts.edges,"relationship")}.</figcaption></figure>`:""}
  <div class="overview"><p>${c(a.overview)}</p></div>
</section>`,x=a.counts.nodes?`<section class="section"><h2>Nodes</h2>${a.groups.map(n=>`
  ${a.grouped?`<div class="group-head" style="--group:${e(n.color)}"><span class="swatch"></span><h3>${e(n.heading)}</h3><span class="count">${n.nodes.length}</span></div>`:""}
  ${n.nodes.map(l=>M(l,i.get(l.id)??l.image)).join("")}`).join("")}</section>`:"",j=a.counts.edges?`<section class="section"><h2>Relationships</h2>${a.relations.map(n=>`
  ${a.relationsGrouped?`<div class="group-head rel-head" style="--group:${e(n.color)}">${$(n.color,n.dashed)}<h3>${e(L(n.label))}</h3><span class="count">${n.count}</span></div>`:""}
  ${n.plain.length?`<ul class="relations plain" style="--node:${e(n.color)}">${n.plain.map(l=>`<li>${c(l)}</li>`).join("")}</ul>`:""}
  ${n.rich.map(l=>`<div class="rel"><ul class="relations" style="--node:${e(n.color)}"><li>${c(l.sentence)}</li></ul>${l.description?g(l.description,"desc"):""}${l.details?u(l.details):""}</div>`).join("")}`).join("")}</section>`:"",S=a.tags.length?`<section><h2 style="margin-top:10mm">Tags</h2><div class="tag-index">${a.tags.map(n=>`<div>${f(n)}${e(n.nodes.map(l=>l.name).join(", "))}</div>`).join("")}</div></section>`:"";return`<!doctype html><html lang="en"><head><meta charset="utf-8">
${r?`<base href="${e(r)}">`:""}
<title>${e(a.title)}</title>
<link rel="stylesheet" href="${N}">
<style>${F}</style></head><body>
<table class="frame">
<thead><tr><td class="running"><div><span>${e(a.title)}</span><span>Pivograph report · ${e(p)}</span></div></td></tr></thead>
<tfoot><tr><td class="bottom"></td></tr></tfoot>
<tbody><tr><td>
${k}${x}${j}${S}
<p class="colophon">Generated by Pivograph on ${e(p)} from the graph's data. The text follows the report protocol described in the Pivograph guide.</p>
</td></tr></tbody></table>
</body></html>`}function q(t){return new Promise((o,i)=>{const r=document.createElement("iframe");r.setAttribute("aria-hidden","true"),r.style.cssText="position:fixed; right:0; bottom:0; width:0; height:0; border:0; visibility:hidden",r.addEventListener("load",async()=>{var a;const s=r.contentWindow;await Promise.race([(a=s.document.fonts)==null?void 0:a.ready,new Promise(p=>setTimeout(p,3e3))]),s.addEventListener("afterprint",()=>setTimeout(()=>r.remove(),1e3),{once:!0});try{s.focus(),s.print(),o()}catch(p){r.remove(),i(p)}setTimeout(()=>r.isConnected&&r.remove(),300*1e3)},{once:!0}),r.srcdoc=t,document.body.append(r)})}export{q as printHtml,R as reportHtml};
