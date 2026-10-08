/* pivotick-converters 76c0bf3a842bd506b5d48cff23b4d345e26d1df9 (MIT) — built by `python3 manage.py pivotick`, do not edit */
var c0=Object.defineProperty;var a0=(g,t,n)=>t in g?c0(g,t,{enumerable:!0,configurable:!0,writable:!0,value:n}):g[t]=n;var b=(g,t,n)=>a0(g,typeof t!="symbol"?t+"":t,n);var F=class{toPivotickOptions(t,n){let d=this.convert(t,n),i={};return this.getNodeTypeAccessor&&(i.nodeTypeAccessor=this.getNodeTypeAccessor()),this.getDefaultStyleMap&&(i.nodeStyleMap=this.getDefaultStyleMap()),{data:d,render:i}}};var x=class x{static registerImporter(t){x.register(x.importers,t)}static registerExporter(t){x.register(x.exporters,t)}static getImporter(t,n){return x.pick(x.importers,t,n)}static getExporter(t,n){return x.pick(x.exporters,t,n)}static importAuto(t){for(let n of x.importers.values()){let d=n.find(i=>i.detect(t));if(d)return d.convert(t)}throw new Error("No registered importer detected this input format")}static listImporters(){return[...x.importers.keys()]}static listExporters(){return[...x.exporters.keys()]}static listImporterVariants(t){return(x.importers.get(t)??[]).map(n=>n.variant)}static listExporterVariants(t){return(x.exporters.get(t)??[]).map(n=>n.variant)}static register(t,n){let d=t.get(n.format)??[];d.push(n),t.set(n.format,d)}static pick(t,n,d){let i=t.get(n);if(!i||i.length===0)throw new Error(`No converter registered for format "${n}"`);if(d){let e=i.find(o=>o.variant.id===d);if(!e)throw new Error(`No variant "${d}" registered for format "${n}"`);return e}return i.find(e=>e.variant.default)??i[0]}};b(x,"importers",new Map),b(x,"exporters",new Map);var V=x;function k(g,t,n){let d={...g},i={...t};for(let e of n??[])Object.entries(e.when).every(([r,a])=>d[r]===a)&&(e.data&&(d={...d,...e.data}),e.style&&(i={...i,...e.style}));return{data:d,style:i}}function B(g,t){let n=t?.hasIcon??!0,d=t?.fontSize??12,i=d*(6.5/12),e=d*(20/12),o=t?.iconSize??22,r=t?.maxWidth??260,a=t?.padding??20,l=t?.extraLines??0,p=t?.secondaryCharWidth??4.5,w=n?o+6:0,v=a+w+g.length*i+i,h=t?.secondaryText?a+w+t.secondaryText.length*p:0,s=Math.max(v,h),m=Math.min(r,s),c=Math.max(1,Math.ceil(v/r)),f=a+(c+l)*e;return Math.ceil(Math.min(m,f)/2)}function I(g,t,n){let d=n?.textColor??"#1892B1",i=n?.iconBackground??d,e=n?.borderColor??d,o=n?.background??"#FFFFFF",r=n?.fontSize??12,a=n?.iconSize??22,l=document.createElement("div");l.style.display="inline-flex",l.style.width="max-content",l.style.alignItems="center",l.style.justifyContent="center";let p=document.createElement("div");p.style.display="flex",p.style.flexDirection="column",p.style.alignItems="flex-start",p.style.justifyContent="flex-start",p.style.width="max-content",p.style.maxWidth=`${260}px`,p.style.height="auto",p.style.padding="8px 10px",p.style.boxSizing="border-box",p.style.background=o,p.style.border=`2px solid ${e}`,p.style.borderRadius="6px",p.style.fontFamily="system-ui, sans-serif",p.style.fontSize=`${r}px`,p.style.color=d;let w=document.createElement("div");if(w.style.display="flex",w.style.alignItems="flex-start",w.style.gap="6px",w.style.width="100%",g){let s=document.createElement("span");s.style.flex="0 0 auto",s.style.width=`${a}px`,s.style.height=`${a}px`,s.style.display="flex",s.style.alignItems="center",s.style.justifyContent="center",s.style.background=i,s.style.color="#FFFFFF",s.style.clipPath="polygon(25% 0%, 75% 0%, 100% 50%, 75% 100%, 25% 100%, 0% 50%)";let m=document.createElement("span"),c=Math.round(a*(14/22));m.style.width=`${c}px`,m.style.height=`${c}px`,m.innerHTML=g,s.append(m),w.append(s)}let v=document.createElement("div");v.style.display="flex",v.style.flexDirection="column",v.style.alignItems="flex-start",v.style.gap="4px",v.style.minWidth="0";let h=document.createElement("span");if(h.style.overflowWrap="anywhere",h.style.wordBreak="break-word",h.textContent=t,v.append(h),n?.badge){let s=document.createElement("span");s.textContent=n.badge,s.style.padding="0 4px",s.style.borderRadius="999px",s.style.fontSize="6px",s.style.lineHeight="1.6",s.style.fontWeight="600",s.style.textTransform="uppercase",s.style.letterSpacing="0.01em",s.style.color=d,s.style.background=`color-mix(in srgb, ${d} 16%, transparent)`,v.append(s)}return w.append(v),p.append(w),l.append(p),l}function h0(g){let t=g.replace("#",""),n=t.length===3?t.split("").map(r=>r+r).join(""):t.padEnd(6,"0").slice(0,6),d=parseInt(n.slice(0,2),16),i=parseInt(n.slice(2,4),16),e=parseInt(n.slice(4,6),16);return(.299*d+.587*i+.114*e)/255>.5?"#000000":"#FFFFFF"}function A(g,t){let n=t?.background??"#888888",d=t?.fontSize??11,i=t?.textColor??h0(n),e=document.createElement("div");e.style.display="inline-flex",e.style.width="max-content",e.style.alignItems="center",e.style.justifyContent="center";let o=document.createElement("div");return o.style.display="flex",o.style.alignItems="center",o.style.justifyContent="center",o.style.width="max-content",o.style.maxWidth=`${260}px`,o.style.padding="4px 10px",o.style.boxSizing="border-box",o.style.borderRadius="999px",o.style.background=n,o.style.color=i,o.style.fontFamily="system-ui, sans-serif",o.style.fontSize=`${d}px`,o.style.fontWeight="600",o.style.textAlign="center",o.style.overflowWrap="anywhere",o.style.wordBreak="break-word",o.style.border=`1px solid ${t?.borderColor??"rgba(128, 128, 128, 0.35)"}`,t?.backgroundImage&&(o.style.backgroundImage=t.backgroundImage),o.textContent=g,e.append(o),e}var p0={fitViewOnExpandCollapse:!1},g0=`
.pivotick[data-theme='light'],
.pivotick[data-theme='dark'] {
  --pvt-node-dash-stroke: transparent;
  --pvt-edge-stroke-dasharray: none;
}
.pvt-edge-group.pvt-edge-synthetic path {
  stroke-dasharray: none;
}
.pvt-node.pvt-node-has-children:not(.pvt-node-expanded).pvt-node-selected-highlight > .node {
  stroke: var(--pvt-node-selected-stroke);
}
.pvt-node.pvt-node-has-children:not(.pvt-node-expanded).pvt-node-highlighted > .node {
  stroke: var(--pvt-node-highlighted-stroke);
}
.pvt-shadow-edge {
  stroke-dasharray: none;
  animation: none;
}
`;var _={shape:"none",icon:"attribute",accentColor:"#97CC04",fontSize:10,iconSize:18},O={shape:"none",icon:"attribute",accentColor:"#97CC04",fontSize:14,iconSize:26};var N=[{key:"id"},{key:"uuid"},{key:"category"},{key:"object_relation"},{key:"to_ids"},{key:"comment"},{key:"timestamp",format:"date"},{key:"first_seen"},{key:"last_seen"},{key:"distribution",format:"distribution"},{key:"sharing_group_id",format:"sharing-group"}];var w0={0:"Your organisation only",1:"This community only",2:"Connected communities",3:"All communities",4:"Sharing group",5:"Inherit event"};function C(g){if(typeof g!="string"&&typeof g!="number")return g;let t=Number(g);return Number.isFinite(t)?new Date(t*1e3).toLocaleString():g}function M(g){return w0[String(g)]??g}function T(g,t){if(!(String(t.distribution)!=="4"||g===void 0||g===null||String(g)==="0"))return`Sharing group #${g}`}function G(g,t,n){switch(g){case"date":return C(t);case"distribution":return M(t);case"sharing-group":return T(t,n);default:return t}}var q={shape:"none",icon:"event",accentColor:"#1892B1",fontSize:20,iconSize:36};var j=[{key:"id"},{key:"uuid"},{key:"date"},{key:"published"},{key:"timestamp",format:"date"},{key:"publish_timestamp",format:"date"},{key:"first_publication",format:"date"},{key:"distribution",format:"distribution"},{key:"sharing_group_id",format:"sharing-group"},{key:"org",source:"Org",format:"org-name"},{key:"orgc",source:"Orgc",format:"org-name"}];function l0(g){return g?.name??g}function S(g,t,n){switch(g){case"date":return C(t);case"distribution":return M(t);case"sharing-group":return T(t,n);case"org-name":return l0(t);default:return t}}function v0(g){let t=0;for(let n=0;n<g.length;n++)t=(t<<5)-t+g.charCodeAt(n)&2147483647;return t%360}function Z(g){return m0(v0(g))}function m0(g){let t=(g%360+360)%360;return{hue:t,badgeBg:`hsla(${t}, 65%, 55%, 0.12)`,badgeText:`hsl(${t}, 65%, 28%)`,badgeBorder:`hsl(${t}, 55%, 65%)`,headerText:`hsl(${t}, 65%, 26%)`,sectionBg:`hsla(${t}, 55%, 55%, 0.08)`,sectionBorder:`hsl(${t}, 55%, 70%)`}}var R="linear-gradient(145deg, rgba(255,255,255,0.15) 0%, rgba(255,255,255,0.04) 40%, rgba(0,0,0,0.04) 100%)";var P={shape:"none",icon:"galaxy",accentColor:"#8B5CF6",fontSize:12,iconSize:22},$={shape:"none",icon:"galaxy",accentColor:"#8B5CF6",fontSize:12,iconSize:22};var Q=[{key:"namespace"},{key:"description"}],W=[{key:"description"},{key:"external_id"}];var D={event:`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   id="Layer_2"
   version="1.1"
   viewBox="3.4925 3.4875 25.0250 25.0250"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <defs
     id="defs2" />
  <!-- Generator: Adobe Illustrator 30.3.0, SVG Export Plug-In . SVG Version: 2.1.3 Build 182)  -->
  <rect
     x="11.24"
     y="21.54"
     width="4.37"
     height="2.43"
     fill="currentColor"
     id="rect1" />
  <path
     d="M20.95,10.07h-4.59v1.22c.22.16.38.41.38.7,0,.49-.39.88-.88.88s-.88-.39-.88-.88c0-.3.16-.54.38-.7v-1.22h-5.05l-1.39-2.77v18.71h14.17V6.9l-2.14,3.17ZM16.35,24.72h-5.87v-3.93h5.87v3.93ZM17.04,21.99h2.61v.75h-2.61v-.75ZM21.13,24.26h-4.09v-.75h4.09v.75Z"
     fill="currentColor"
     id="path1" />
  <path
     d="M15.35,9.07v-.42c-.22-.16-.38-.41-.38-.7,0-.49.39-.88.88-.88s.88.39.88.88c0,.3-.16.54-.38.7v.42h4.06l2.08-3.08h-13.12l1.54,3.08h4.44Z"
     fill="currentColor"
     id="path2" />
</svg>`,object:`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   id="Layer_2"
   version="1.1"
   viewBox="2.2400 2.2500 27.5000 27.5000"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <defs
     id="defs2" />
  <!-- Generator: Adobe Illustrator 30.3.0, SVG Export Plug-In . SVG Version: 2.1.3 Build 182)  -->
  <path
     d="M15.97,14.14l-8.57-4.57,8.57-4.57,8.57,4.57-8.57,4.57Z"
     fill="currentColor"
     id="path1" />
  <path
     d="M15.99,15.57l-8.8-4.69-.03,10.66,8.83,5.46,8.83-5.36v-10.99l-8.84,4.93ZM8.64,13.3l6.64,3.54v8.02l-6.66-4.12.02-7.44ZM23.38,20.83l-6.66,4.04v-8.04l6.66-3.71v7.71Z"
     fill="currentColor"
     id="path2" />
</svg>`,attribute:`<?xml version="1.0" encoding="UTF-8"?>
<svg id="Layer_1" xmlns="http://www.w3.org/2000/svg" version="1.1" viewBox="5.2750 5.2750 21.4500 21.4500">
  <!-- Generator: Adobe Illustrator 30.3.0, SVG Export Plug-In . SVG Version: 2.1.3 Build 182)  -->
  <g>
    <polygon points="13.85 24.58 8.82 24.58 8.82 7.42 13.85 7.42 13.85 8.87 10.27 8.87 10.27 23.13 13.85 23.13 13.85 24.58" fill="currentColor"/>
    <polygon points="23.18 24.58 18.15 24.58 18.15 23.13 21.73 23.13 21.73 8.87 18.15 8.87 18.15 7.42 23.18 7.42 23.18 24.58" fill="currentColor"/>
  </g>
  <g>
    <rect x="12.65" y="15.23" width="1.55" height="1.55" fill="currentColor"/>
    <rect x="15.23" y="15.23" width="1.55" height="1.55" fill="currentColor"/>
    <rect x="17.81" y="15.23" width="1.55" height="1.55" fill="currentColor"/>
  </g>
</svg>`,galaxy:`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   id="Layer_2"
   version="1.1"
   viewBox="2.0951 2.0889 27.8197 27.8197"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <defs
     id="defs1" />
  <!-- Generator: Adobe Illustrator 30.3.0, SVG Export Plug-In . SVG Version: 2.1.3 Build 182)  -->
  <path
     d="M23.78,24.32c-.08.08-.18.11-.28.11-.11,0-.21-.04-.29-.13-.15-.16-.15-.42.02-.57,2.42-2.29,3.56-5.85,2.92-9.06-.35-1.73-1.28-3.4-2.61-4.71-.24.17-.53.26-.84.26-.81,0-1.47-.66-1.47-1.47,0-.09,0-.18.03-.27.02-.12.06-.23.1-.32.03-.07.07-.14.11-.21.27-.42.73-.67,1.23-.67.81,0,1.47.66,1.47,1.47,0,.13-.02.26-.06.41-.02.06-.04.12-.06.17h0c1.48,1.43,2.5,3.27,2.89,5.18.7,3.48-.54,7.33-3.16,9.81h0ZM8.66,16.78c-.07-.21-.3-.33-.51-.26s-.33.3-.26.51c.84,2.59,3.49,5.28,6.79,5.28.08,0,.16,0,.24,0,4.33,0,6.3-2.99,6.3-5.76,0-1.44-.55-2.72-1.55-3.6-.99-.87-2.31-1.26-3.72-1.08-.22.03-.38.23-.35.45.03.22.23.38.45.35,1.18-.15,2.28.17,3.09.89.82.73,1.28,1.8,1.28,3,0,2.47-1.7,4.96-5.51,4.96-2.93.11-5.48-2.31-6.25-4.72h0ZM23.34,15.22c.07.21.3.33.51.26.21-.07.33-.3.26-.51-.86-2.66-3.62-5.41-7.04-5.27-4.33,0-6.3,2.99-6.3,5.76,0,1.44.55,2.72,1.55,3.6.83.73,1.9,1.12,3.06,1.12.22,0,.44-.01.66-.04.22-.03.38-.23.35-.45-.03-.22-.23-.38-.45-.35-1.18.14-2.28-.17-3.09-.89-.82-.73-1.28-1.8-1.28-3,0-2.47,1.7-4.96,5.51-4.96,2.93-.12,5.48,2.31,6.26,4.72h0ZM16,13.72c-1.26,0-2.28,1.02-2.28,2.28s1.02,2.28,2.28,2.28,2.28-1.02,2.28-2.28-1.02-2.28-2.28-2.28ZM6.88,12.99c-.05.1-.08.21-.1.32-.02.09-.03.18-.03.27,0,.7.5,1.31,1.18,1.44.09.02.19.03.3.03.59,0,1.12-.35,1.35-.89.02-.05.05-.11.06-.17.04-.15.06-.28.06-.41,0-.57-.32-1.06-.8-1.31.34-.83.84-1.62,1.47-2.29,2.24-2.37,6.1-3.31,9.38-2.3.21.07.44-.05.5-.26.07-.21-.05-.44-.26-.5-3.57-1.11-7.76-.08-10.21,2.51-.73.77-1.31,1.7-1.69,2.68-.53.05-1,.38-1.21.87h0ZM25.12,19c.02-.05.05-.11.06-.17.04-.15.06-.28.06-.41,0-.7-.5-1.31-1.18-1.44-.09-.02-.19-.03-.3-.03-.59,0-1.11.35-1.34.88-.05.1-.08.21-.1.32-.02.09-.03.18-.03.27,0,.57.32,1.06.8,1.31-.34.83-.84,1.62-1.47,2.29-2.24,2.37-6.1,3.31-9.38,2.3-.21-.06-.44.05-.5.26s.05.44.26.5c.96.3,1.96.44,2.97.44,2.73,0,5.45-1.06,7.24-2.95.73-.77,1.31-1.7,1.69-2.68.53-.05,1-.38,1.21-.88h0ZM9.3,21.76c-.3,0-.59.09-.83.26-1.34-1.31-2.27-2.98-2.62-4.71-.64-3.21.5-6.76,2.92-9.06.16-.15.17-.41.02-.57-.15-.16-.41-.17-.57-.02-2.61,2.48-3.85,6.33-3.15,9.8.38,1.91,1.41,3.75,2.89,5.18-.05.1-.08.2-.1.32-.02.09-.03.18-.03.27,0,.81.66,1.47,1.47,1.47.59,0,1.12-.35,1.36-.91.02-.05.04-.1.06-.15.04-.15.06-.28.06-.41,0-.82-.66-1.47-1.48-1.47h0Z"
     fill="currentColor"
     id="path1" />
</svg>`,sighting:`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   id="Layer_1"
   version="1.1"
   viewBox="5.2750 5.2750 21.4500 21.4500"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <defs
     id="defs4" />
  <!-- Generator: Adobe Illustrator 30.3.0, SVG Export Plug-In . SVG Version: 2.1.3 Build 182)  -->
  <g
     id="g2">
    <polygon
       points="12.46 24.58 7.43 24.58 7.43 7.42 12.46 7.42 12.46 8.87 8.88 8.87 8.88 23.13 12.46 23.13 12.46 24.58"
       fill="currentColor"
       id="polygon1" />
    <polygon
       points="24.57 24.58 19.54 24.58 19.54 23.13 23.12 23.13 23.12 8.87 19.54 8.87 19.54 7.42 24.57 7.42 24.57 24.58"
       fill="currentColor"
       id="polygon2" />
  </g>
  <g
     id="g4">
    <path
       d="M16,17.41c-.78,0-1.41-.63-1.41-1.41s.63-1.41,1.41-1.41,1.41.63,1.41,1.41-.63,1.41-1.41,1.41Z"
       fill="currentColor"
       id="path2" />
    <path
       d="M20.87,15.33s0,0,0,0c-.77-.92-2.67-2.86-4.87-2.86s-4.1,1.94-4.87,2.86c0,0,0,0,0,0-.32.39-.32.95,0,1.34,0,0,0,0,0,0,.77.92,2.67,2.86,4.87,2.86s4.1-1.94,4.87-2.86c0,0,0,0,0,0,.32-.39.32-.95,0-1.34ZM16,18.62c-1.43,0-2.6-1.17-2.6-2.6s1.17-2.6,2.6-2.6,2.6,1.17,2.6,2.6-1.17,2.6-2.6,2.6Z"
       fill="currentColor"
       id="path3" />
    <path
       d="M16,14.59c-.78,0-1.41.63-1.41,1.41s.63,1.41,1.41,1.41,1.41-.63,1.41-1.41-.63-1.41-1.41-1.41Z"
       fill="currentColor"
       id="path4" />
  </g>
</svg>`,tag:`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   id="Layer_1"
   version="1.1"
   viewBox="4.2822 4.2989 23.4050 23.4050"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <defs
     id="defs1" />
  <!-- Generator: Adobe Illustrator 30.3.0, SVG Export Plug-In . SVG Version: 2.1.3 Build 182)  -->
  <path
     d="M24.03,12.82l-2.56-5.86c-.1-.23-.34-.36-.59-.31l-6.29,1.18c-.16.03-.3.13-.37.27l-6.25,11.79c-.14.26-.04.58.22.72l8.84,4.69c.12.07.27.08.41.04.13-.04.25-.13.31-.26l6.25-11.79h0c.08-.14.08-.31.02-.46ZM16.6,21.22l-4.9-2.54.46-.89,4.9,2.54-.46.89ZM17.42,19.64l-4.9-2.54.46-.89,4.9,2.54-.46.89ZM18.22,18.1l-4.9-2.54.46-.89,4.9,2.54-.46.89ZM19.91,10.36c-.58,0-1.04-.47-1.04-1.04s.47-1.04,1.04-1.04,1.04.47,1.04,1.04-.47,1.04-1.04,1.04Z"
     fill="currentColor"
     id="path1" />
</svg>`,"objects/android-app":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-6.0000 0.0000 30.0000 24.0000"
   version="1.1"
   id="svg2"
   sodipodi:docname="android-app.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs2" />
  <path
     d="M -3,0 H 21 V 24 H -3 Z"
     fill="none"
     id="path1" />
  <path
     fill="currentColor"
     d="m 11.975,3.019 0.96,-1.732 A 0.19314049,0.19314049 0 0 0 12.597,1.1 l -0.97,1.75 a 6.54,6.54 0 0 0 -5.253,0 L 5.404,1.1 a 0.19401611,0.19401611 0 0 0 -0.34,0.187 l 0.96,1.732 A 5.55,5.55 0 0 0 2.932,7.895 H 15.069 A 5.55,5.55 0 0 0 11.975,3.019 M 6.2,5.674 A 0.507,0.507 0 1 1 6.707,5.168 0.507,0.507 0 0 1 6.2,5.674 m 5.602,0 A 0.507,0.507 0 1 1 12.309,5.168 0.507,0.507 0 0 1 11.802,5.674 M 2.93,17.171 A 1.467,1.467 0 0 0 4.4,18.64 h 0.973 v 3 a 1.3605,1.3605 0 1 0 2.721,0 v -3 h 1.814 v 3 a 1.36,1.36 0 1 0 2.72,0 v -3 h 0.974 A 1.467,1.467 0 0 0 15.07,17.172 V 8.375 H 2.93 Z M 1.063,8.141 a 1.36,1.36 0 0 0 -1.36,1.361 v 5.669 a 1.36,1.36 0 1 0 2.72,0 V 9.502 a 1.36,1.36 0 0 0 -1.36,-1.36 m 15.872,0 a 1.36,1.36 0 0 0 -1.36,1.361 v 5.669 a 1.36,1.36 0 1 0 2.72,0 v -5.67 a 1.36,1.36 0 0 0 -1.36,-1.36"
     id="path2" />
</svg>`,"objects/android-permission":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-9.0000 0.0000 30.0000 24.0000"
   version="1.1"
   id="svg2"
   sodipodi:docname="android-permission.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs2" />
  <path
     d="M -6,0 H 18 V 24 H -6 Z"
     fill="none"
     id="path1" />
  <path
     fill="currentColor"
     d="M 8.975,3.019 9.935,1.287 A 0.19314049,0.19314049 0 0 0 9.597,1.1 l -0.97,1.75 a 6.54,6.54 0 0 0 -5.253,0 L 2.404,1.1 a 0.19401611,0.19401611 0 0 0 -0.34,0.187 l 0.96,1.732 A 5.55,5.55 0 0 0 -0.068,7.895 H 12.069 A 5.55,5.55 0 0 0 8.975,3.019 M 3.2,5.674 A 0.507,0.507 0 1 1 3.707,5.168 0.507,0.507 0 0 1 3.2,5.674 m 5.602,0 A 0.507,0.507 0 1 1 9.309,5.168 0.507,0.507 0 0 1 8.802,5.674 M -0.07,17.171 A 1.467,1.467 0 0 0 1.4,18.64 h 0.973 v 3 a 1.3605,1.3605 0 1 0 2.721,0 v -3 h 1.814 v 3 a 1.36,1.36 0 1 0 2.72,0 v -3 h 0.974 A 1.467,1.467 0 0 0 12.07,17.172 V 8.375 H -0.07 Z m -1.867,-9.03 a 1.36,1.36 0 0 0 -1.36,1.361 v 5.669 a 1.36,1.36 0 1 0 2.72,0 V 9.502 a 1.36,1.36 0 0 0 -1.36,-1.36 m 15.872,0 a 1.36,1.36 0 0 0 -1.36,1.361 v 5.669 a 1.36,1.36 0 1 0 2.72,0 v -5.67 a 1.36,1.36 0 0 0 -1.36,-1.36"
     id="path2" />
</svg>`,"objects/annotation":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-7.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="annotation.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 2,20 A 1,1 0 0 1 1,19 V 16 H -3 A 2,2 0 0 1 -5,14 V 2 a 2,2 0 0 1 2,-2 h 16 a 2,2 0 0 1 2,2 v 12 a 2,2 0 0 1 -2,2 H 6.9 L 3.2,19.71 C 3,19.9 2.75,20 2.5,20 Z m 1,-6 v 3.08 L 6.08,14 H 13 V 2 H -3 V 14 Z M -1,5 H 11 V 7 H -1 Z m 0,4 h 9 v 2 h -9 z"
     id="path1" />
</svg>`,"objects/apk":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-9.0000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="apk.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m -1.5,17 h 10 Q 8.4,15.775 7.75,14.75 7.1,13.725 6.05,13.125 L 7,11.425 Q 7.05,11.325 7.025,11.2 7,11.075 6.875,11.025 6.775,10.975 6.662,11 6.549,11.025 6.5,11.125 l -0.975,1.75 q -0.5,-0.2 -1,-0.312 -0.5,-0.112 -1.025,-0.113 -0.525,-10e-4 -1.025,0.113 -0.5,0.114 -1,0.312 L 0.5,11.125 Q 0.45,11 0.338,11 0.226,11 0.1,11.05 l -0.1,0.375 0.95,1.7 q -1.05,0.6 -1.7,1.625 Q -1.4,15.775 -1.5,17 M 0.9,15.35 Q 0.75,15.2 0.75,15 q 0,-0.2 0.15,-0.35 0.15,-0.15 0.35,-0.15 0.2,0 0.35,0.15 0.15,0.15 0.15,0.35 0,0.2 -0.15,0.35 -0.15,0.15 -0.35,0.15 -0.2,0 -0.35,-0.15 m 4.5,0 Q 5.25,15.2 5.25,15 q 0,-0.2 0.15,-0.35 0.15,-0.15 0.35,-0.15 0.2,0 0.35,0.15 0.15,0.15 0.15,0.35 0,0.2 -0.15,0.35 -0.15,0.15 -0.35,0.15 -0.2,0 -0.35,-0.15 M -2.5,20 Q -3.325,20 -3.912,19.413 -4.499,18.826 -4.5,18 V 2 Q -4.5,1.175 -3.912,0.588 -3.324,0.001 -2.5,0 h 7.175 q 0.4,0 0.763,0.15 0.363,0.15 0.637,0.425 l 4.85,4.85 Q 11.2,5.7 11.35,6.063 11.5,6.426 11.5,6.825 V 18 q 0,0.825 -0.587,1.413 Q 10.326,20.001 9.5,20 Z M 4.5,6 Q 4.5,6.425 4.788,6.713 5.076,7.001 5.5,7 h 4 l -5,-5 z"
     id="path1" />
</svg>`,"objects/artifact":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-7.0000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="artifact.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 14.500006,14.5 c 0,0.38 -0.21,0.71 -0.53,0.88 l -7.9000003,4.44 c -0.16,0.12 -0.36,0.18 -0.57,0.18 -0.21,0 -0.41,-0.06 -0.57,-0.18 l -7.9,-4.44 a 0.99,0.99 0 0 1 -0.53,-0.88 v -9 c 0,-0.38 0.21,-0.71 0.53,-0.88 l 7.9,-4.44 c 0.16,-0.12 0.36,-0.18 0.57,-0.18 0.21,0 0.41,0.06 0.57,0.18 l 7.9000003,4.44 c 0.32,0.17 0.53,0.5 0.53,0.88 z M 5.5000057,2.15 l -1.89,1.07 5.8900003,3.39 1.96,-1.11 z m -5.96,3.35 5.96,3.35 1.9600003,-1.1 -5.8800003,-3.4 z m -1.04,8.41 6,3.38 v -6.71 l -6,-3.37 z m 14.0000003,0 v -6.7 l -6,3.37 v 6.71 z"
     id="path1" />
</svg>`,"objects/asn":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-9.7500 0.0000 17.5000 14.0000"
   version="1.1"
   id="svg2"
   sodipodi:docname="asn.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs2" />
  <g
     fill="none"
     stroke="currentColor"
     stroke-linecap="round"
     stroke-linejoin="round"
     id="g2"
     transform="translate(-8)">
    <path
       d="m 7,10.5 v 3 m -5,0 h 10 m -5,-3 a 5,5 0 1 0 0,-10 5,5 0 0 0 0,10 m -5,-5 h 10"
       id="path1" />
    <path
       d="M 7,10.5 C 10,7.08 10,3.74 7,0.5 4.06,3.62 4,6.94 7,10.5"
       id="path2" />
  </g>
</svg>`,"objects/attack-pattern":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-7.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="attack-pattern.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 5,0 A 10,10 0 0 0 -5,10 10,10 0 0 0 5,20 10,10 0 0 0 15,10 C 15,8.84 14.79,7.69 14.39,6.61 l -1.6,1.6 C 12.93,8.8 13,9.4 13,10 A 8,8 0 0 1 5,18 8,8 0 0 1 -3,10 8,8 0 0 1 5,2 C 5.6,2 6.2,2.07 6.79,2.21 L 8.4,0.6 C 7.31,0.21 6.16,0 5,0 M 12,0 8,4 V 5.5 L 5.45,8.05 C 5.3,8 5.15,8 5,8 a 2,2 0 0 0 -2,2 2,2 0 0 0 2,2 2,2 0 0 0 2,-2 C 7,9.85 7,9.7 6.95,9.55 L 9.5,7 H 11 L 15,3 H 12 Z M 5,4 a 6,6 0 0 0 -6,6 6,6 0 0 0 6,6 6,6 0 0 0 6,-6 H 9 A 4,4 0 0 1 5,14 4,4 0 0 1 1,10 4,4 0 0 1 5,6 Z"
     id="path1" />
</svg>`,"objects/av-signature":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-9.5000 0.0000 27.5000 22.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="av-signature.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 3.25,12 h 2 v 1 h -2 z m 10,-8 v 6 c 0,5.5 -3.8,10.7 -9,12 -5.2,-1.3 -9,-6.5 -9,-12 V 4 l 9,-4 z m -4,5 H 7.05 C 6.85,8.4 6.45,7.9 5.95,7.5 L 7.15,6.3 6.45,5.6 5.05,7 H 4.25 C 4.05,7 3.75,7 3.55,7.1 L 2.15,5.6 1.35,6.4 2.55,7.6 C 2.05,7.9 1.65,8.4 1.45,9 h -2.2 v 1 h 2 v 1 h -2 v 1 h 2 v 1 h -2 v 1 h 2.2 c 0.4,1.2 1.5,2 2.8,2 1.3,0 2.4,-0.8 2.8,-2 h 2.2 v -1 h -2 v -1 h 2 v -1 h -2 v -1 h 2 z m -6,2 h 2 v -1 h -2 z"
     id="path1" />
</svg>`,"objects/bank-account":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-2.0000 0.0000 30.0000 24.0000"
   version="1.1"
   id="svg2"
   sodipodi:docname="bank-account.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs2" />
  <path
     fill="currentColor"
     d="m 5,10 h 11 v 2 H 5 Z m 0,5 h 13 v 2 H 5 Z"
     id="path1" />
  <path
     fill="currentColor"
     d="M 25,0 H 1 a 2,2 0 0 0 -2,2 v 20 a 2,2 0 0 0 2,2 h 24 a 2,2 0 0 0 2,-2 V 2 A 2,2 0 0 0 25,0 m 0,2 V 4 H 1 V 2 Z M 1,22 V 6 h 24 v 16 z"
     id="path2" />
</svg>`,"objects/blog":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-6.7500 0.0000 22.5000 18.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="blog.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m -4.5,0 v 18 h 18 V 0 Z m 15,15 h -12 v -1 h 12 z m 0,-2 h -12 v -1 h 12 z m 0,-4 h -12 V 3 h 12 z"
     id="path1" />
</svg>`,"objects/btc-transaction":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-395.2923 0.0000 640.0000 512.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="btc-transaction.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 42.9118,242.638 c 27.73,-14.18 45.377,-39.39 41.28,-81.3 -5.358,-57.351 -52.458,-76.573 -114.85,-81.929 V 0 h -48.528 v 77.203 c -12.605,0 -25.525,0.315 -38.444,0.63 V 0 h -48.528 v 79.409 c -17.842,0.539 -38.622,0.276 -97.37,0 v 51.678 c 38.314,-0.678 58.417,-3.14 63.023,21.427 v 217.429 c -2.925,19.492 -18.524,16.685 -53.255,16.071 l -9.767,57.666 c 88.481,0 97.37,0.315 97.37,0.315 V 512 h 48.528 v -67.06 c 13.234,0.315 26.154,0.315 38.444,0.315 V 512 h 48.528 v -68.005 c 81.299,-4.412 135.647,-24.894 142.895,-101.467 5.671,-61.446 -23.32,-88.862 -69.326,-99.89 m -159.596,-108.085 c 27.415,0 113.126,-8.507 113.126,48.528 0,54.515 -85.71,48.212 -113.126,48.212 z m 0,251.776 V 279.821 c 32.772,0 133.127,-9.138 133.127,53.255 -10e-4,60.186 -100.355,53.253 -133.127,53.253"
     id="path1" />
</svg>`,"objects/btc-wallet":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-395.2923 0.0000 640.0000 512.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="btc-wallet.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 42.9118,242.638 c 27.73,-14.18 45.377,-39.39 41.28,-81.3 -5.358,-57.351 -52.458,-76.573 -114.85,-81.929 V 0 h -48.528 v 77.203 c -12.605,0 -25.525,0.315 -38.444,0.63 V 0 h -48.528 v 79.409 c -17.842,0.539 -38.622,0.276 -97.37,0 v 51.678 c 38.314,-0.678 58.417,-3.14 63.023,21.427 v 217.429 c -2.925,19.492 -18.524,16.685 -53.255,16.071 l -9.767,57.666 c 88.481,0 97.37,0.315 97.37,0.315 V 512 h 48.528 v -67.06 c 13.234,0.315 26.154,0.315 38.444,0.315 V 512 h 48.528 v -68.005 c 81.299,-4.412 135.647,-24.894 142.895,-101.467 5.671,-61.446 -23.32,-88.862 -69.326,-99.89 m -159.596,-108.085 c 27.415,0 113.126,-8.507 113.126,48.528 0,54.515 -85.71,48.212 -113.126,48.212 z m 0,251.776 V 279.821 c 32.772,0 133.127,-9.138 133.127,53.255 -10e-4,60.186 -100.355,53.253 -133.127,53.253"
     id="path1" />
</svg>`,"objects/c2-list":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-13.5000 0.0000 45.0000 36.0000"
   version="1.1"
   id="svg7"
   sodipodi:docname="c2-list.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs7" />
  <path
     fill="currentColor"
     d="m 1,17 h 14 v 2 H 1 Z"
     class="clr-i-outline--alerted clr-i-outline-path-1--alerted"
     id="path1" />
  <path
     fill="currentColor"
     d="m -3,25 h 2 v 2 h -2 z"
     class="clr-i-outline--alerted clr-i-outline-path-2--alerted"
     id="path2" />
  <path
     fill="currentColor"
     d="m 1,25 h 14 v 2 H 1 Z"
     class="clr-i-outline--alerted clr-i-outline-path-3--alerted"
     id="path3" />
  <path
     fill="currentColor"
     d="M 9.64,11 A 3.7,3.7 0 0 1 10,9.89 L 10.56,9 H 1 v 2 z"
     class="clr-i-outline--alerted clr-i-outline-path-4--alerted"
     id="path4" />
  <path
     fill="currentColor"
     d="M 24.68,15.4 H 23 V 21 H -5 V 15 H 11.58 A 3.67,3.67 0 0 1 10,13.56 3.6,3.6 0 0 1 9.74,13 H -5 V 7 H 11.71 L 12.86,5 H -5 a 2,2 0 0 0 -2,2 v 22 a 2,2 0 0 0 2,2 h 28 a 2,2 0 0 0 2,-2 V 15.38 Z M -5,29 v -6 h 28 v 6 z"
     class="clr-i-outline--alerted clr-i-outline-path-5--alerted"
     id="path5" />
  <path
     fill="currentColor"
     d="M 17.85,1.14 12.13,11 a 1.28,1.28 0 0 0 1.1,2 h 11.45 a 1.28,1.28 0 0 0 1.1,-2 L 20.06,1.14 a 1.28,1.28 0 0 0 -2.21,0"
     class="clr-i-outline--alerted clr-i-outline-path-6--alerted clr-i-alert"
     id="path6" />
  <path
     fill="none"
     d="M -9,0 H 27 V 36 H -9 Z"
     id="path7" />
</svg>`,"objects/chat-message":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-7.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="chat-message.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M -5,20 V 2 Q -5,1.175 -4.412,0.588 -3.824,0.001 -3,0 H 13 Q 13.825,0 14.413,0.588 15.001,1.176 15,2 v 12 q 0,0.825 -0.587,1.413 Q 13.826,16.001 13,16 H -1 Z m 4,-8 H 7 V 10 H -1 Z M -1,9 H 11 V 7 H -1 Z M -1,6 H 11 V 4 H -1 Z"
     id="path1" />
</svg>`,"objects/coin-address":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-7.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg2"
   sodipodi:docname="coin-address.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs2" />
  <path
     fill="currentColor"
     d="M 5,0 C -0.51,0 -5,4.49 -5,10 -5,15.51 -0.51,20 5,20 10.51,20 15,15.51 15,10 15,4.49 10.51,0 5,0 m 0,18 c -4.41,0 -8,-3.59 -8,-8 0,-4.41 3.59,-8 8,-8 4.41,0 8,3.59 8,8 0,4.41 -3.59,8 -8,8"
     id="path1" />
  <path
     fill="currentColor"
     d="M 1,10 5,16 9,10 5,4 Z"
     id="path2" />
</svg>`,"objects/command-line":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="0.0000 0.0000 24.6480 15.7900"
   version="1.1"
   id="svg1"
   sodipodi:docname="command-line.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 0,2.126 V 2.124 Z m 0.002,-0.002 5.77,5.773 -5.77,5.77 2.12,2.123 L 10.017,7.895 2.123,0 Z m 10.226,13.524 h 14.42 v -3 h -14.42 z m 4.335,-6.25 h 10.084 v -3 H 14.563 Z m -4.335,-9.25 v 3 h 14.42 v -3 z"
     id="path1" />
</svg>`,"objects/command":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="0.0000 0.0000 24.6480 15.7900"
   version="1.1"
   id="svg1"
   sodipodi:docname="command.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 0,2.126 V 2.124 Z m 0.002,-0.002 5.77,5.773 -5.77,5.77 2.12,2.123 L 10.017,7.895 2.123,0 Z m 10.226,13.524 h 14.42 v -3 h -14.42 z m 4.335,-6.25 h 10.084 v -3 H 14.563 Z m -4.335,-9.25 v 3 h 14.42 v -3 z"
     id="path1" />
</svg>`,"objects/cookie":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-7.5468 0.0000 25.0312 20.0250"
   version="1.1"
   id="svg1"
   sodipodi:docname="cookie.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 4.9688,20.025 q -2.075,0 -3.9,-0.788 -1.825,-0.788 -3.175,-2.137 -1.35,-1.349 -2.137,-3.175 -0.787,-1.826 -0.788,-3.9 0,-1.875 0.725,-3.675 0.725,-1.8 2.025,-3.213 1.3,-1.413 3.125,-2.275 1.825,-0.862 4,-0.862 0.525,0 1.075,0.05 0.55,0.05 1.125,0.175 -0.225,1.125 0.15,2.125 0.375,1 1.125,1.662 0.75,0.662 1.788,0.913 1.038,0.251 2.137,-0.125 -0.65,1.475 0.188,2.825 0.838,1.35 2.487,1.4 0.025,0.275 0.038,0.512 0.013,0.237 0.012,0.513 0,2.05 -0.788,3.862 -0.788,1.812 -2.137,3.175 -1.349,1.363 -3.175,2.15 -1.826,0.787 -3.9,0.788 m -1.5,-12 q 0.625,0 1.063,-0.437 Q 4.9698,7.151 4.9688,6.525 4.9678,5.899 4.5318,5.463 4.0958,5.027 3.4688,5.025 2.8418,5.023 2.4068,5.463 q -0.435,0.44 -0.438,1.062 -0.003,0.622 0.438,1.063 0.441,0.441 1.062,0.437 m -2,5 q 0.625,0 1.063,-0.437 0.438,-0.437 0.437,-1.063 -10e-4,-0.626 -0.437,-1.062 -0.436,-0.436 -1.063,-0.438 -0.627,-0.002 -1.062,0.438 -0.435,0.44 -0.438,1.062 -0.003,0.622 0.438,1.063 0.441,0.441 1.062,0.437 m 6.5,1 q 0.425,0 0.713,-0.288 0.288,-0.288 0.287,-0.712 -10e-4,-0.424 -0.288,-0.712 -0.287,-0.288 -0.712,-0.288 -0.425,0 -0.712,0.288 -0.287,0.288 -0.288,0.712 -10e-4,0.424 0.288,0.713 0.289,0.289 0.712,0.287"
     id="path1" />
</svg>`,"objects/course-of-action":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-14.2500 0.0000 27.5000 22.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="course-of-action.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m -2.5,16 -4,-4 1.41,-1.41 2.59,2.58 L 4.09,6.58 5.5,8 m -6,-8 -9,4 v 6 c 0,5.55 3.84,10.74 9,12 5.16,-1.26 9,-6.45 9,-12 V 4 Z"
     id="path1" />
</svg>`,"objects/cpe-asset":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="0.0000 0.0000 24.0000 16.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="cpe-asset.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 4,2 H 20 V 12 H 4 m 16,2 a 2,2 0 0 0 2,-2 V 2 A 2,2 0 0 0 20,0 H 4 C 2.89,0 2,0.89 2,2 v 10 a 2,2 0 0 0 2,2 H 0 v 2 h 24 v -2 z"
     id="path1" />
</svg>`,"objects/credential":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="0.0000 0.0000 20.0000 16.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="credential.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     fill-rule="evenodd"
     d="M 1.172,1.172 C 0,2.343 0,4.229 0,8 0,11.771 0,13.657 1.172,14.828 2.344,15.999 4.229,16 8,16 h 4 c 3.771,0 5.657,0 6.828,-1.172 C 19.999,13.656 20,11.771 20,8 20,4.229 20,2.343 18.828,1.172 17.656,0.001 15.771,0 12,0 H 8 C 4.229,0 2.343,0 1.172,1.172 M 10.75,6 A 0.75,0.75 0 0 0 9.25,6 V 6.701 L 8.643,6.351 A 0.75,0.75 0 0 0 7.893,7.649 L 8.5,7.999 7.893,8.35 a 0.75041655,0.75041655 0 1 0 0.75,1.3 L 9.25,9.299 V 10 a 0.75,0.75 0 0 0 1.5,0 V 9.3 l 0.607,0.35 a 0.75041655,0.75041655 0 0 0 0.75,-1.3 L 11.5,8 12.107,7.65 a 0.75041655,0.75041655 0 0 0 -0.75,-1.3 L 10.75,6.7 Z M 4.733,5.25 A 0.75,0.75 0 0 1 5.483,6 V 6.7 L 6.089,6.35 a 0.75041655,0.75041655 0 0 1 0.75,1.3 L 6.232,8 6.839,8.35 a 0.75041655,0.75041655 0 1 1 -0.75,1.3 L 5.483,9.3 V 10 a 0.75,0.75 0 0 1 -1.5,0 V 9.299 L 3.375,9.649 A 0.75,0.75 0 0 1 2.625,8.351 L 3.232,8 2.625,7.65 a 0.75041655,0.75041655 0 1 1 0.75,-1.3 L 3.983,6.701 V 6 A 0.75,0.75 0 0 1 4.733,5.25 M 16.018,6 a 0.75,0.75 0 0 0 -1.5,0 v 0.701 l -0.607,-0.35 a 0.75,0.75 0 0 0 -0.75,1.298 l 0.607,0.35 -0.608,0.351 a 0.75041655,0.75041655 0 0 0 0.75,1.3 L 14.518,9.299 V 10 a 0.75,0.75 0 0 0 1.5,0 V 9.3 l 0.607,0.35 a 0.75041655,0.75041655 0 0 0 0.75,-1.3 L 16.768,8 17.375,7.65 a 0.75041655,0.75041655 0 0 0 -0.75,-1.3 L 16.018,6.7 Z"
     clip-rule="evenodd"
     id="path1" />
</svg>`,"objects/credit-card":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="0.0000 0.0000 20.0000 16.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="credit-card.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     fill-rule="evenodd"
     d="M 0,3 A 3,3 0 0 1 3,0 h 14 a 3,3 0 0 1 3,3 V 4 H 0 Z m 0,3 v 7 a 3,3 0 0 0 3,3 h 14 a 3,3 0 0 0 3,-3 V 6 Z m 5,2 a 1,1 0 1 0 0,2 h 5 a 1,1 0 1 0 0,-2 z"
     clip-rule="evenodd"
     id="path1" />
</svg>`,"objects/crypto-material":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-9.0000 0.0000 30.0000 24.0000"
   version="1.1"
   id="svg5"
   sodipodi:docname="crypto-material.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs5" />
  <path
     d="M -6,0 H 18 V 24 H -6 Z"
     fill="none"
     id="path1" />
  <g
     fill="none"
     stroke="currentColor"
     stroke-linejoin="round"
     stroke-width="1.5"
     id="g5"
     transform="translate(-6)">
    <path
       stroke-linecap="round"
       d="m 3.55,6.937 a 5.378,5.378 0 0 1 7.837,2.619 h 9.657 L 23,11.51 21.045,13.466 h -1.467 l -1.467,1.466 -1.467,-1.466 H 15.667 L 14.2,14.933 12.733,13.467 H 11.387 A 5.378,5.378 0 1 1 3.549,6.937"
       id="path2" />
    <path
       stroke-linecap="round"
       d="m 5.404,12.98 a 1.467,1.467 0 1 0 0,-2.934 1.467,1.467 0 0 0 0,2.934"
       id="path3" />
    <path
       d="m 8.088,1.75 a 0.75,0.75 0 1 0 1.5,0 0.75,0.75 0 0 0 -1.5,0 z M 5.404,22.283 a 0.75,0.75 0 1 0 1.5,0 0.75,0.75 0 0 0 -1.5,0 z M 21.533,3.705 a 0.75,0.75 0 1 0 1.5,0 0.75,0.75 0 0 0 -1.5,0 z m 0,15.645 a 0.75,0.75 0 1 0 1.5,0 0.75,0.75 0 0 0 -1.5,0 z"
       id="path4" />
    <path
       stroke-linecap="round"
       d="M 17.378,7.6 V 4.665 c 0,-0.54 0.438,-0.978 0.978,-0.978 h 0.977 M 12,1.733 h 0.977 c 0.54,0 0.978,0.438 0.978,0.978 v 4.89 m 2.445,8.31 v 2.445 c 0,0.54 0.438,0.977 0.978,0.977 h 1.955 m -9.777,2.934 h 1.956 c 0.54,0 0.977,-0.438 0.977,-0.978 v -4.89"
       id="path5" />
  </g>
</svg>`,"objects/data-url":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-7.5030 0.0000 25.0003 20.0002"
   version="1.1"
   id="svg1"
   sodipodi:docname="data-url.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 6.237735,11.281346 c 0,-0.722 -0.282,-1.4159997 -0.785,-1.9339997 a 1.0003181,1.0003181 0 0 1 1.436,-1.393 4.78,4.78 0 0 1 0,6.6539997 l -0.003,0.004 -3.9129997,3.992 a 4.62,4.62 0 0 1 -6.618,0 4.78,4.78 0 0 1 -0.008,-6.664 l 2.607,-2.7399997 a 1.000138,1.000138 0 1 1 1.44800004,1.3799997 l -2.60499994,2.737 -0.009,0.01 a 2.78,2.78 0 0 0 -0.18,3.678 l 0.18,0.202 v 10e-4 a 2.62,2.62 0 0 0 3.7539999,0 l 0.002,-0.002 3.9139997,-3.995 c 0.5,-0.518 0.781,-1.21 0.781,-1.93 m 6.758,-6.5489997 a 2.78,2.78 0 0 0 -0.79,-1.94 v -0.001 a 2.62,2.62 0 0 0 -3.754,0 l -0.003,0.003 -4.0489997,4.12 a 2.78,2.78 0 0 0 -0.232,3.6119997 1,1 0 0 1 -1.6,1.2 4.78,4.78 0 0 1 0.4,-6.2069997 l 0.004,-0.003 4.0499997,-4.123 a 4.62,4.62 0 0 1 6.615,0.002 4.777,4.777 0 0 1 0.019,6.654 l -2.71,2.9309997 a 1.0006051,1.0006051 0 0 1 -1.469,-1.3589997 l 2.71,-2.93 0.018,-0.02 a 2.78,2.78 0 0 0 0.79,-1.94"
     id="path1" />
</svg>`,"objects/ddos-config":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-13.5000 0.0000 35.0000 28.0000"
   version="1.1"
   id="svg2"
   sodipodi:docname="ddos-config.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs2" />
  <path
     fill="currentColor"
     d="m 17,22 v -2 h -2.101 a 5,5 0 0 0 -0.732,-1.753 l 1.49,-1.49 -1.414,-1.414 -1.49,1.49 A 5,5 0 0 0 11,16.101 V 14 H 9 v 2.101 a 5,5 0 0 0 -1.753,0.732 l -1.49,-1.49 -1.414,1.414 1.49,1.49 A 5,5 0 0 0 5.101,20 H 3 v 2 h 2.101 c 0.129,0.626 0.378,1.221 0.732,1.753 l -1.49,1.49 1.414,1.414 1.49,-1.49 A 5,5 0 0 0 9,25.899 V 28 h 2 v -2.101 a 5,5 0 0 0 1.753,-0.732 l 1.49,1.49 1.414,-1.414 -1.49,-1.49 A 5,5 0 0 0 14.899,22 Z m -7,2 a 3,3 0 1 1 0,-6 3,3 0 0 1 0,6"
     id="path1" />
  <path
     fill="currentColor"
     d="M 10.499,7.085 3.707,0.293 A 1,1 0 0 0 3,0 H -7 c -1.1,0 -2,0.9 -2,2 v 24 c 0,1.1 0.9,2 2,2 H 1 V 26 H -7 V 2 h 8 v 6 c 0,1.103 0.897,2 2,2 h 6.292 c 0.693,0 1.312,-0.414 1.577,-1.054 0.266,-0.64 0.12,-1.37 -0.37,-1.861 M 3,8 V 2.414 L 8.585,8 Z"
     id="path2" />
</svg>`,"objects/ddos":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-9.4569 0.0000 26.3047 21.0438"
   version="1.1"
   id="svg2"
   sodipodi:docname="ddos.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs2" />
  <g
     fill="none"
     stroke="currentColor"
     stroke-linecap="round"
     stroke-linejoin="round"
     stroke-width="2"
     id="g2"
     transform="translate(-8.3046,-1.956244)">
    <path
       d="m 6.528,6.536 a 6,6 0 0 0 7.942,7.933 m 2.247,-1.76 A 6,6 0 0 0 8.29,4.284"
       id="path1" />
    <path
       d="m 12,3 q 2,0.5 2,6 0,0.506 -0.017,0.968 m -0.55,3.473 Q 12.934,14.766 12,15 M 12,3 q -1.405,0.351 -1.822,3.167 m -0.16,3.838 Q 10.192,14.549 12,15 M 6,9 h 3 m 4,0 h 5 M 3,20 h 7 m 4,0 h 7 m -11,0 a 2,2 0 1 0 4,0 2,2 0 0 0 -4,0 m 2,-5 v 3 M 3,3 21,21"
       id="path2" />
  </g>
</svg>`,"objects/decoded-barcode":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="0.0000 0.0000 22.0000 14.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="decoded-barcode.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 0,14 V 0 h 2 v 14 z m 3,0 V 0 h 2 v 14 z m 3,0 V 0 h 1 v 14 z m 3,0 V 0 h 2 v 14 z m 3,0 V 0 h 3 v 14 z m 4,0 V 0 h 1 v 14 z m 3,0 V 0 h 3 v 14 z"
     id="path1" />
</svg>`,"objects/decoded-qrcode":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-8.2500 0.0000 27.5000 22.0000"
   version="1.1"
   id="svg7"
   sodipodi:docname="decoded-qrcode.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs7" />
  <path
     fill="currentColor"
     d="m -5.5,0 h 10 v 10 h -10 z m 2,2 v 6 h 6 V 2 Z"
     id="path1" />
  <path
     fill="currentColor"
     fill-rule="evenodd"
     d="m -1.5,4 h 2 v 2 h -2 z"
     id="path2" />
  <path
     fill="currentColor"
     d="m 6.5,0 h 10 v 10 h -10 z m 2,2 v 6 h 6 V 2 Z"
     id="path3" />
  <path
     fill="currentColor"
     fill-rule="evenodd"
     d="m 10.5,4 h 2 v 2 h -2 z"
     id="path4" />
  <path
     fill="currentColor"
     d="m -5.5,12 h 10 v 10 h -10 z m 2,2 v 6 h 6 v -6 z"
     id="path5" />
  <path
     fill="currentColor"
     fill-rule="evenodd"
     d="m -1.5,16 h 2 v 2 h -2 z"
     id="path6" />
  <path
     fill="currentColor"
     d="m 16.5,18 h -4 v 4 h -6 V 12 h 1 -1 v 6 h 2 v 2 h 2 v -6 h -2 v -2 h -1 3 v 2 h 2 v 2 h 2 v -4 h 2 z m 0,2 v 2 h -2 v -2 z"
     id="path7" />
</svg>`,"objects/device":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-0.0000 0.0000 20.0000 16.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="device.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 0,16 v -2 h 10 v 2 z M 3,13 Q 2.175,13 1.588,12.413 1.001,11.826 1,11 V 2 Q 1,1.175 1.588,0.588 2.176,0.001 3,0 H 17 Q 17.825,0 18.413,0.588 19.001,1.176 19,2 H 3 v 9 h 7 v 2 z m 15,1 V 6 h -4 v 8 z m -4.5,2 Q 12.875,16 12.438,15.563 12.001,15.126 12,14.5 v -9 Q 12,4.875 12.438,4.438 12.876,4.001 13.5,4 h 5 Q 19.125,4 19.563,4.438 20.001,4.876 20,5.5 v 9 q 0,0.625 -0.437,1.063 Q 19.126,16.001 18.5,16 Z M 16,8.5 q 0.325,0 0.538,-0.225 Q 16.751,8.05 16.75,7.75 16.75,7.425 16.537,7.213 16.324,7.001 16,7 15.7,7 15.475,7.213 15.25,7.426 15.25,7.75 q 0,0.3 0.225,0.525 Q 15.7,8.5 16,8.5 m 0,1.5"
     id="path1" />
</svg>`,"objects/diamond":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-16.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="diamond.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 3,10 -4,20 -11,10 -4,0"
     id="path1" />
</svg>`,"objects/directory":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="0.0000 0.0000 20.0000 16.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="directory.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 8,0 H 2 C 0.89,0 0,0.89 0,2 v 12 a 2,2 0 0 0 2,2 h 16 a 2,2 0 0 0 2,-2 V 4 A 2,2 0 0 0 18,2 h -8 z"
     id="path1" />
</svg>`,"objects/dkim":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-3.3000 0.0000 22.7000 18.1600"
   version="1.1"
   id="svg1"
   sodipodi:docname="dkim.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 8.8,15 c 0,-3.31 2.69,-6 6,-6 1.1,0 2.12,0.3 3,0.81 V 2 a 2,2 0 0 0 -2,-2 h -16 c -1.11,0 -2,0.89 -2,2 v 12 a 2,2 0 0 0 2,2 H 8.89 C 8.84,15.67 8.8,15.34 8.8,15 M -0.2,4 V 2 l 8,5 8,-5 v 2 l -8,5 z m 13.75,14.16 -2.75,-3 1.16,-1.16 1.59,1.59 3.59,-3.59 1.16,1.41 z"
     id="path1" />
</svg>`,"objects/dns-record":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-11.9859 0.0000 29.9905 23.9924"
   version="1.1"
   id="svg2"
   sodipodi:docname="dns-record.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs2" />
  <path
     fill="currentColor"
     d="m -4.490599,17.492436 h 2 v 3 h -2 z"
     id="path1" />
  <path
     fill="currentColor"
     d="m 12.007401,13.992436 h -17.996 a 2,2 0 0 0 -2.002,2.002 v 5.996 a 2,2 0 0 0 2.002,2.002 h 17.996 a 2,2 0 0 0 2.002,-2.002 v -5.996 a 2,2 0 0 0 -2.002,-2.002 m -12.998,6.5 a 1.473,1.473 0 0 1 -1.5,1.5 h -3.5 v -6 h 3.5 a 1.473,1.473 0 0 1 1.5,1.5 z m 6.5,1.5 h -1.2 l -2.55,-3.5 v 3.5 h -1.25 v -6 h 1.25 l 2.5,3.5 v -3.5 h 1.25 z m 6.5,-4.48 h -3.5 v 0.74 h 2.5 a 1,1 0 0 1 1,1 v 1.74 a 1,1 0 0 1 -1,1 h -4 v -1.5 h 3.51 v -0.74 h -2.51 a 1,1 0 0 1 -1,-1 v -1.76 a 1,1 0 0 1 1,-1 h 4 z m -16.74,-5.52 a 8.2,8.2 0 0 1 -0.26,-2.0000012 8.2,8.2 0 0 1 0.26,-2 h 3.38 a 17,17 0 0 0 -0.14,2 17,17 0 0 0 0.14,2.0000012 h 2.02 a 15,15 0 0 1 -0.16,-2.0000012 15,15 0 0 1 0.16,-2 h 4.68 a 15,15 0 0 1 0.16,2 15,15 0 0 1 -0.16,2.0000012 h 2.02 a 17,17 0 0 0 0.14,-2.0000012 17,17 0 0 0 -0.14,-2 h 3.38 a 8.2,8.2 0 0 1 0.26,2 8.2,8.2 0 0 1 -0.26,2.0000012 h 2.059 a 10,10 0 1 0 -19.599,0 z m 14.66,-6.0000012 h -2.95 a 15.7,15.7 0 0 0 -1.38,-3.56 8.03,8.03 0 0 1 4.33,3.56 m -6.92,-3.96 a 14.1,14.1 0 0 1 1.91,3.96 h -3.82 a 14.1,14.1 0 0 1 1.91,-3.96 m -2.59,0.4 a 15.7,15.7 0 0 0 -1.38,3.56 h -2.95 a 8,8 0 0 1 4.33,-3.56"
     id="path2" />
</svg>`,"objects/domain-ip":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-11.9859 0.0000 29.9905 23.9924"
   version="1.1"
   id="svg2"
   sodipodi:docname="domain-ip.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs2" />
  <path
     fill="currentColor"
     d="m -4.730599,11.992436 a 8.2,8.2 0 0 1 -0.26,-2.0000012 8.2,8.2 0 0 1 0.26,-2 h 3.38 a 17,17 0 0 0 -0.14,2 17,17 0 0 0 0.14,2.0000012 h 2.02 a 15,15 0 0 1 -0.16,-2.0000012 15,15 0 0 1 0.16,-2 h 4.68 a 15,15 0 0 1 0.16,2 15,15 0 0 1 -0.16,2.0000012 h 2.02 a 17,17 0 0 0 0.14,-2.0000012 17,17 0 0 0 -0.14,-2 h 3.38 a 8.2,8.2 0 0 1 0.26,2 8.2,8.2 0 0 1 -0.26,2.0000012 h 2.059 a 10,10 0 1 0 -19.599,0 z m 14.66,-6.0000012 h -2.95 a 15.7,15.7 0 0 0 -1.38,-3.56 8.03,8.03 0 0 1 4.33,3.56 m -6.92,-3.96 a 14.1,14.1 0 0 1 1.91,3.96 h -3.82 a 14.1,14.1 0 0 1 1.91,-3.96 m -2.59,0.4 a 15.7,15.7 0 0 0 -1.38,3.56 h -2.95 a 8,8 0 0 1 4.33,-3.56 m 3.339,15.0550012 h 2 v 1 h -2 z"
     id="path1" />
  <path
     fill="currentColor"
     d="m 12.007401,13.992436 h -17.996 a 2,2 0 0 0 -2.002,2.002 v 5.996 a 2,2 0 0 0 2.002,2.002 h 17.996 a 2,2 0 0 0 2.002,-2.002 v -5.996 a 2,2 0 0 0 -2.002,-2.002 m -11.747,8.005 h -1.5 v -6 h 1.5 z m 6.998,-3.51 a 1.473,1.473 0 0 1 -1.5,1.5 h -2 v 2 h -1.5 v -6 h 3.5 a 1.473,1.473 0 0 1 1.5,1.5 z"
     id="path2" />
</svg>`,"objects/elf":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-7.4940 0.0000 25.0036 20.0029"
   version="1.1"
   id="svg1"
   sodipodi:docname="elf.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 7.625795,6.35 c -0.42,0.28 -1.75,1.04 -1.95,1.19 -0.39,0.31 -0.7500003,0.29 -1.1400003,-0.01 -0.2,-0.16 -1.53,-0.92 -1.95,-1.19 -0.48,-0.31 -0.45,-0.7 0.08,-0.92 1.64,-0.69 3.2800003,-0.64 4.9100003,0.03 0.49,0.21 0.51,0.6 0.05,0.9 m 7.22,7.28 c -0.93,-2.09 -2.2,-3.99 -3.84,-5.66 a 4.3,4.3 0 0 1 -1.06,-1.88 c -0.1,-0.33 -0.17,-0.67 -0.24,-1.01 -0.2,-0.88 -0.29,-1.78 -0.7,-2.61 -0.73,-1.58 -2,-2.4 -3.84,-2.47 -1.8100003,0.05 -3.1600003,0.81 -3.9500003,2.4 -0.21,0.43 -0.36,0.88 -0.46,1.34 -0.17,0.76 -0.32,1.55 -0.5,2.32 -0.15,0.65 -0.45,1.21 -0.96,1.71 -1.61,1.57 -2.9,3.37 -3.88,5.35 -0.14,0.29 -0.28,0.58 -0.37,0.88 -0.19,0.66 0.29,1.12 0.99,0.96 0.44,-0.09 0.88,-0.18 1.3,-0.31 0.41,-0.15 0.57,-0.05 0.67,0.35 0.65,2.15 2.07,3.66 4.24,4.5 4.1200003,1.56 8.9300003,-0.66 9.9700003,-4.58 0.07,-0.27 0.17,-0.37 0.47,-0.27 0.46,0.14 0.93,0.24 1.4,0.35 0.49,0.09 0.85,-0.16 0.92,-0.64 0.03,-0.26 -0.06,-0.49 -0.16,-0.73"
     id="path1" />
</svg>`,"objects/email":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-6.1882 0.0000 20.6275 16.5020"
   version="1.1"
   id="svg4"
   sodipodi:docname="email.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs4" />
  <path
     fill="currentColor"
     d="m 10.8765,8.2512867 a 6.75,6.75 0 1 0 -3.375,5.8460003 0.75,0.75 0 0 1 0.75,1.299 8.251,8.251 0 1 1 4.125,-7.1450003 0.75,0.75 0 0 1 -1.5,0"
     id="path1" />
  <path
     fill="currentColor"
     d="m 7.8765,9.2512867 a 1.5,1.5 0 0 0 3,0 h 1.5 a 3,3 0 0 1 -6,0 z"
     id="path2" />
  <path
     fill="currentColor"
     d="m 6.3765,8.2512867 a 2.25,2.25 0 1 0 -4.5,0 2.25,2.25 0 0 0 4.5,0 m 1.5,0 a 3.75,3.75 0 1 1 -7.5,0 3.75,3.75 0 0 1 7.5,0 m 4.5,-0.75 v 1.75 h -1.5 v -1.75 z"
     id="path3" />
  <path
     fill="currentColor"
     d="M 6.3765,10.251287 V 5.2512867 a 0.75,0.75 0 0 1 1.5,0 v 5.0000003 a 0.75,0.75 0 0 1 -1.5,0"
     id="path4" />
</svg>`,"objects/employee":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-20.2500 0.0000 27.5000 22.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="employee.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m -1.5,2 h -3 v 3 h -4 V 2 h -3 a 2,2 0 0 0 -2,2 v 16 a 2,2 0 0 0 2,2 h 10 a 2,2 0 0 0 2,-2 V 4 a 2,2 0 0 0 -2,-2 m -5,5 a 2,2 0 0 1 2,2 2,2 0 0 1 -2,2 2,2 0 0 1 -2,-2 2,2 0 0 1 2,-2 m 4,8 h -8 v -1 c 0,-1.33 2.67,-2 4,-2 1.33,0 4,0.67 4,2 z m -3,-11 h -2 V 0 h 2 z m 3,14 h -8 v -1 h 8 z m -4,2 h -4 v -1 h 4 z"
     id="path1" />
</svg>`,"objects/event":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-10.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="event.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m -4,0 v 2 h -1 c -1.11,0 -2,0.89 -2,2 v 14 a 2,2 0 0 0 2,2 H 9 c 1.11,0 2,-0.89 2,-2 V 4 A 2,2 0 0 0 9,2 H 8 V 0 H 6 V 2 H -2 V 0 Z M -5,7 H 9 V 18 H -5 Z m 6,1 v 5 H 3 V 8 Z m 0,7 v 2 h 2 v -2 z"
     id="path1" />
</svg>`,"objects/exploit-poc":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-7.0000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="exploit-poc.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m -1.5,17 a 1,1 0 0 0 1,1 h 12 a 1,1 0 0 0 1,-1 c 0,-0.21 -0.07,-0.41 -0.18,-0.57 L 6.5,6.35 V 2 h -2 V 6.35 L -1.32,16.43 C -1.43,16.59 -1.5,16.79 -1.5,17 m 1,3 a 3,3 0 0 1 -3,-3 c 0,-0.6 0.18,-1.16 0.5,-1.63 L 2.5,5.81 V 4 A 1,1 0 0 1 1.5,3 V 2 a 2,2 0 0 1 2,-2 h 4 a 2,2 0 0 1 2,2 v 1 a 1,1 0 0 1 -1,1 v 1.81 l 5.5,9.56 c 0.32,0.47 0.5,1.03 0.5,1.63 a 3,3 0 0 1 -3,3 z M 6.5,14 7.84,12.66 9.77,16 H 1.23 L 3.89,11.39 Z M 6,10 A 0.5,0.5 0 0 1 6.5,10.5 0.5,0.5 0 0 1 6,11 0.5,0.5 0 0 1 5.5,10.5 0.5,0.5 0 0 1 6,10"
     id="path1" />
</svg>`,"objects/exploit":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-7.1250 0.0000 23.7500 19.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="exploit.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 1.5,4 A 3.25,3.25 0 0 1 4.75,0.75 3.25,3.25 0 0 1 8,4 C 8,4.42 8.33,4.75 8.75,4.75 9.17,4.75 9.5,4.42 9.5,4 V 3.25 H 11 V 4 A 2.25,2.25 0 0 1 8.75,6.25 2.25,2.25 0 0 1 6.5,4 1.75,1.75 0 0 0 4.75,2.25 1.75,1.75 0 0 0 3,4 h 1.25 v 1.29 c 2.89,0.86 5,3.54 5,6.71 a 7,7 0 0 1 -7,7 7,7 0 0 1 -7,-7 c 0,-3.17 2.11,-5.85 5,-6.71 V 4 Z m 10.75,0 h 2 v 1 h -2 z m -3,-2 V 0 h 1 v 2 z m 1.91,0.38 1.42,-1.42 0.71,0.71 -1.42,1.42 z"
     id="path1" />
</svg>`,"objects/facebook-account":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-4.9375 0.0000 24.9375 19.9500"
   version="1.1"
   id="svg1"
   sodipodi:docname="facebook-account.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 17.5312,10 c 0,-5.52 -4.48,-10 -10,-10 -5.52,0 -10,4.48 -10,10 0,4.84 3.44,8.87 8,9.8 V 13 h -2 v -3 h 2 V 7.5 c 0,-1.93 1.57,-3.5 3.5,-3.5 h 2.5 v 3 h -2 c -0.55,0 -1,0.45 -1,1 v 2 h 3 v 3 h -3 v 6.95 c 5.05,-0.5 9,-4.76 9,-9.95"
     id="path1" />
</svg>`,"objects/facebook-group":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-7.4062 0.0000 24.9375 19.9500"
   version="1.1"
   id="svg1"
   sodipodi:docname="facebook-group.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 15.0625,10 c 0,-5.52 -4.48,-10 -10,-10 -5.52,0 -10,4.48 -10,10 0,4.84 3.44,8.87 8,9.8 V 13 h -2 v -3 h 2 V 7.5 c 0,-1.93 1.57,-3.5 3.5,-3.5 h 2.5 v 3 h -2 c -0.55,0 -1,0.45 -1,1 v 2 h 3 v 3 h -3 v 6.95 c 5.05,-0.5 9,-4.76 9,-9.95"
     id="path1" />
</svg>`,"objects/facebook-page":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-7.4062 0.0000 24.9375 19.9500"
   version="1.1"
   id="svg1"
   sodipodi:docname="facebook-page.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 15.0625,10 c 0,-5.52 -4.48,-10 -10,-10 -5.52,0 -10,4.48 -10,10 0,4.84 3.44,8.87 8,9.8 V 13 h -2 v -3 h 2 V 7.5 c 0,-1.93 1.57,-3.5 3.5,-3.5 h 2.5 v 3 h -2 c -0.55,0 -1,0.45 -1,1 v 2 h 3 v 3 h -3 v 6.95 c 5.05,-0.5 9,-4.76 9,-9.95"
     id="path1" />
</svg>`,"objects/facebook-post":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-7.4062 0.0000 24.9375 19.9500"
   version="1.1"
   id="svg1"
   sodipodi:docname="facebook-post.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 15.0625,10 c 0,-5.52 -4.48,-10 -10,-10 -5.52,0 -10,4.48 -10,10 0,4.84 3.44,8.87 8,9.8 V 13 h -2 v -3 h 2 V 7.5 c 0,-1.93 1.57,-3.5 3.5,-3.5 h 2.5 v 3 h -2 c -0.55,0 -1,0.45 -1,1 v 2 h 3 v 3 h -3 v 6.95 c 5.05,-0.5 9,-4.76 9,-9.95"
     id="path1" />
</svg>`,"objects/facebook-reaction":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-7.4062 0.0000 24.9375 19.9500"
   version="1.1"
   id="svg1"
   sodipodi:docname="facebook-reaction.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 15.0625,10 c 0,-5.52 -4.48,-10 -10,-10 -5.52,0 -10,4.48 -10,10 0,4.84 3.44,8.87 8,9.8 V 13 h -2 v -3 h 2 V 7.5 c 0,-1.93 1.57,-3.5 3.5,-3.5 h 2.5 v 3 h -2 c -0.55,0 -1,0.45 -1,1 v 2 h 3 v 3 h -3 v 6.95 c 5.05,-0.5 9,-4.76 9,-9.95"
     id="path1" />
</svg>`,"objects/favicon":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="0.0000 0.0000 22.0000 16.0000"
   version="1.1"
   id="svg2"
   sodipodi:docname="favicon.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs2" />
  <g
     fill="none"
     stroke="currentColor"
     stroke-linecap="round"
     stroke-linejoin="round"
     stroke-width="2"
     id="g2"
     transform="translate(-1,-4)">
    <path
       d="M 2,8 A 3,3 0 0 1 5,5 h 14 a 3,3 0 0 1 3,3 v 8 a 3,3 0 0 1 -3,3 H 5 A 3,3 0 0 1 2,16 Z m 4,2 v 4"
       id="path1" />
    <path
       d="m 11,10 a 2,2 0 1 0 0,4 m 3,-2 a 2,2 0 1 0 4,0 2,2 0 1 0 -4,0"
       id="path2" />
  </g>
</svg>`,"objects/file-7z":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-4.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg26"
   sodipodi:docname="file-7z.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs26" />
  <mask
     id="ft-7z">
    <path
       d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
       fill="#ffffff"
       id="path1" />
    <g
       fill="#000000"
       id="g26">
      <rect
         x="5.71"
         y="12.3"
         width="1.14"
         height="1.14"
         id="rect1" />
      <rect
         x="6.8600001"
         y="12.3"
         width="1.14"
         height="1.14"
         id="rect2" />
      <rect
         x="8"
         y="12.3"
         width="1.14"
         height="1.14"
         id="rect3" />
      <rect
         x="9.1400003"
         y="12.3"
         width="1.14"
         height="1.14"
         id="rect4" />
      <rect
         x="10.29"
         y="12.3"
         width="1.14"
         height="1.14"
         id="rect5" />
      <rect
         x="10.29"
         y="13.44"
         width="1.14"
         height="1.14"
         id="rect6" />
      <rect
         x="9.1400003"
         y="14.59"
         width="1.14"
         height="1.14"
         id="rect7" />
      <rect
         x="8"
         y="15.73"
         width="1.14"
         height="1.14"
         id="rect8" />
      <rect
         x="6.8600001"
         y="16.870001"
         width="1.14"
         height="1.14"
         id="rect9" />
      <rect
         x="6.8600001"
         y="18.01"
         width="1.14"
         height="1.14"
         id="rect10" />
      <rect
         x="6.8600001"
         y="19.16"
         width="1.14"
         height="1.14"
         id="rect11" />
      <rect
         x="12.57"
         y="12.3"
         width="1.14"
         height="1.14"
         id="rect12" />
      <rect
         x="13.71"
         y="12.3"
         width="1.14"
         height="1.14"
         id="rect13" />
      <rect
         x="14.86"
         y="12.3"
         width="1.14"
         height="1.14"
         id="rect14" />
      <rect
         x="16"
         y="12.3"
         width="1.14"
         height="1.14"
         id="rect15" />
      <rect
         x="17.139999"
         y="12.3"
         width="1.14"
         height="1.14"
         id="rect16" />
      <rect
         x="17.139999"
         y="13.44"
         width="1.14"
         height="1.14"
         id="rect17" />
      <rect
         x="16"
         y="14.59"
         width="1.14"
         height="1.14"
         id="rect18" />
      <rect
         x="14.86"
         y="15.73"
         width="1.14"
         height="1.14"
         id="rect19" />
      <rect
         x="13.71"
         y="16.870001"
         width="1.14"
         height="1.14"
         id="rect20" />
      <rect
         x="12.57"
         y="18.01"
         width="1.14"
         height="1.14"
         id="rect21" />
      <rect
         x="12.57"
         y="19.16"
         width="1.14"
         height="1.14"
         id="rect22" />
      <rect
         x="13.71"
         y="19.16"
         width="1.14"
         height="1.14"
         id="rect23" />
      <rect
         x="14.86"
         y="19.16"
         width="1.14"
         height="1.14"
         id="rect24" />
      <rect
         x="16"
         y="19.16"
         width="1.14"
         height="1.14"
         id="rect25" />
      <rect
         x="17.139999"
         y="19.16"
         width="1.14"
         height="1.14"
         id="rect26" />
    </g>
  </mask>
  <path
     d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
     fill="currentColor"
     mask="url(#ft-7z)"
     id="path26"
     transform="translate(-4,-2)" />
</svg>`,"objects/file-apk":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-4.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg47"
   sodipodi:docname="file-apk.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs47" />
  <mask
     id="ft-apk">
    <path
       d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
       fill="#ffffff"
       id="path1" />
    <g
       fill="#000000"
       id="g47">
      <rect
         x="6.2600002"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect1" />
      <rect
         x="7.0300002"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect2" />
      <rect
         x="7.79"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect3" />
      <rect
         x="5.5"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect4" />
      <rect
         x="8.5600004"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect5" />
      <rect
         x="5.5"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect6" />
      <rect
         x="8.5600004"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect7" />
      <rect
         x="5.5"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect8" />
      <rect
         x="6.2600002"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect9" />
      <rect
         x="7.0300002"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect10" />
      <rect
         x="7.79"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect11" />
      <rect
         x="8.5600004"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect12" />
      <rect
         x="5.5"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect13" />
      <rect
         x="8.5600004"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect14" />
      <rect
         x="5.5"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect15" />
      <rect
         x="8.5600004"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect16" />
      <rect
         x="5.5"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect17" />
      <rect
         x="8.5600004"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect18" />
      <rect
         x="10.09"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect19" />
      <rect
         x="10.85"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect20" />
      <rect
         x="11.62"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect21" />
      <rect
         x="12.38"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect22" />
      <rect
         x="10.09"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect23" />
      <rect
         x="13.15"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect24" />
      <rect
         x="10.09"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect25" />
      <rect
         x="13.15"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect26" />
      <rect
         x="10.09"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect27" />
      <rect
         x="10.85"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect28" />
      <rect
         x="11.62"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect29" />
      <rect
         x="12.38"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect30" />
      <rect
         x="10.09"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect31" />
      <rect
         x="10.09"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect32" />
      <rect
         x="10.09"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect33" />
      <rect
         x="14.68"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect34" />
      <rect
         x="17.74"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect35" />
      <rect
         x="14.68"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect36" />
      <rect
         x="16.969999"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect37" />
      <rect
         x="14.68"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect38" />
      <rect
         x="16.209999"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect39" />
      <rect
         x="14.68"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect40" />
      <rect
         x="15.44"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect41" />
      <rect
         x="14.68"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect42" />
      <rect
         x="16.209999"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect43" />
      <rect
         x="14.68"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect44" />
      <rect
         x="16.969999"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect45" />
      <rect
         x="14.68"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect46" />
      <rect
         x="17.74"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect47" />
    </g>
  </mask>
  <path
     d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
     fill="currentColor"
     mask="url(#ft-apk)"
     id="path47"
     transform="translate(-4,-2)" />
</svg>`,"objects/file-bat":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-4.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg49"
   sodipodi:docname="file-bat.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs49" />
  <mask
     id="ft-bat">
    <path
       d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
       fill="#ffffff"
       id="path1" />
    <g
       fill="#000000"
       id="g49">
      <rect
         x="5.5"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect1" />
      <rect
         x="6.2600002"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect2" />
      <rect
         x="7.0300002"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect3" />
      <rect
         x="7.79"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect4" />
      <rect
         x="5.5"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect5" />
      <rect
         x="8.5600004"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect6" />
      <rect
         x="5.5"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect7" />
      <rect
         x="8.5600004"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect8" />
      <rect
         x="5.5"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect9" />
      <rect
         x="6.2600002"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect10" />
      <rect
         x="7.0300002"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect11" />
      <rect
         x="7.79"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect12" />
      <rect
         x="5.5"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect13" />
      <rect
         x="8.5600004"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect14" />
      <rect
         x="5.5"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect15" />
      <rect
         x="8.5600004"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect16" />
      <rect
         x="5.5"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect17" />
      <rect
         x="6.2600002"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect18" />
      <rect
         x="7.0300002"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect19" />
      <rect
         x="7.79"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect20" />
      <rect
         x="10.85"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect21" />
      <rect
         x="11.62"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect22" />
      <rect
         x="12.38"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect23" />
      <rect
         x="10.09"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect24" />
      <rect
         x="13.15"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect25" />
      <rect
         x="10.09"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect26" />
      <rect
         x="13.15"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect27" />
      <rect
         x="10.09"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect28" />
      <rect
         x="10.85"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect29" />
      <rect
         x="11.62"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect30" />
      <rect
         x="12.38"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect31" />
      <rect
         x="13.15"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect32" />
      <rect
         x="10.09"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect33" />
      <rect
         x="13.15"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect34" />
      <rect
         x="10.09"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect35" />
      <rect
         x="13.15"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect36" />
      <rect
         x="10.09"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect37" />
      <rect
         x="13.15"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect38" />
      <rect
         x="14.68"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect39" />
      <rect
         x="15.44"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect40" />
      <rect
         x="16.209999"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect41" />
      <rect
         x="16.969999"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect42" />
      <rect
         x="17.74"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect43" />
      <rect
         x="16.209999"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect44" />
      <rect
         x="16.209999"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect45" />
      <rect
         x="16.209999"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect46" />
      <rect
         x="16.209999"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect47" />
      <rect
         x="16.209999"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect48" />
      <rect
         x="16.209999"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect49" />
    </g>
  </mask>
  <path
     d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
     fill="currentColor"
     mask="url(#ft-bat)"
     id="path49"
     transform="translate(-4,-2)" />
</svg>`,"objects/file-css":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-4.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg43"
   sodipodi:docname="file-css.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs43" />
  <mask
     id="ft-css">
    <path
       d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
       fill="#ffffff"
       id="path1" />
    <g
       fill="#000000"
       id="g43">
      <rect
         x="6.2600002"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect1" />
      <rect
         x="7.0300002"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect2" />
      <rect
         x="7.79"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect3" />
      <rect
         x="5.5"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect4" />
      <rect
         x="8.5600004"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect5" />
      <rect
         x="5.5"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect6" />
      <rect
         x="5.5"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect7" />
      <rect
         x="5.5"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect8" />
      <rect
         x="5.5"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect9" />
      <rect
         x="8.5600004"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect10" />
      <rect
         x="6.2600002"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect11" />
      <rect
         x="7.0300002"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect12" />
      <rect
         x="7.79"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect13" />
      <rect
         x="10.85"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect14" />
      <rect
         x="11.62"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect15" />
      <rect
         x="12.38"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect16" />
      <rect
         x="13.15"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect17" />
      <rect
         x="10.09"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect18" />
      <rect
         x="10.09"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect19" />
      <rect
         x="10.85"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect20" />
      <rect
         x="11.62"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect21" />
      <rect
         x="12.38"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect22" />
      <rect
         x="13.15"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect23" />
      <rect
         x="13.15"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect24" />
      <rect
         x="10.09"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect25" />
      <rect
         x="10.85"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect26" />
      <rect
         x="11.62"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect27" />
      <rect
         x="12.38"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect28" />
      <rect
         x="15.44"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect29" />
      <rect
         x="16.209999"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect30" />
      <rect
         x="16.969999"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect31" />
      <rect
         x="17.74"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect32" />
      <rect
         x="14.68"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect33" />
      <rect
         x="14.68"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect34" />
      <rect
         x="15.44"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect35" />
      <rect
         x="16.209999"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect36" />
      <rect
         x="16.969999"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect37" />
      <rect
         x="17.74"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect38" />
      <rect
         x="17.74"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect39" />
      <rect
         x="14.68"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect40" />
      <rect
         x="15.44"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect41" />
      <rect
         x="16.209999"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect42" />
      <rect
         x="16.969999"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect43" />
    </g>
  </mask>
  <path
     d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
     fill="currentColor"
     mask="url(#ft-css)"
     id="path43"
     transform="translate(-4,-2)" />
</svg>`,"objects/file-csv":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-4.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg41"
   sodipodi:docname="file-csv.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs41" />
  <mask
     id="ft-csv">
    <path
       d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
       fill="#ffffff"
       id="path1" />
    <g
       fill="#000000"
       id="g41">
      <rect
         x="6.2600002"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect1" />
      <rect
         x="7.0300002"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect2" />
      <rect
         x="7.79"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect3" />
      <rect
         x="5.5"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect4" />
      <rect
         x="8.5600004"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect5" />
      <rect
         x="5.5"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect6" />
      <rect
         x="5.5"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect7" />
      <rect
         x="5.5"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect8" />
      <rect
         x="5.5"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect9" />
      <rect
         x="8.5600004"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect10" />
      <rect
         x="6.2600002"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect11" />
      <rect
         x="7.0300002"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect12" />
      <rect
         x="7.79"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect13" />
      <rect
         x="10.85"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect14" />
      <rect
         x="11.62"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect15" />
      <rect
         x="12.38"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect16" />
      <rect
         x="13.15"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect17" />
      <rect
         x="10.09"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect18" />
      <rect
         x="10.09"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect19" />
      <rect
         x="10.85"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect20" />
      <rect
         x="11.62"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect21" />
      <rect
         x="12.38"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect22" />
      <rect
         x="13.15"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect23" />
      <rect
         x="13.15"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect24" />
      <rect
         x="10.09"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect25" />
      <rect
         x="10.85"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect26" />
      <rect
         x="11.62"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect27" />
      <rect
         x="12.38"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect28" />
      <rect
         x="14.68"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect29" />
      <rect
         x="17.74"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect30" />
      <rect
         x="14.68"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect31" />
      <rect
         x="17.74"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect32" />
      <rect
         x="14.68"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect33" />
      <rect
         x="17.74"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect34" />
      <rect
         x="14.68"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect35" />
      <rect
         x="17.74"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect36" />
      <rect
         x="15.44"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect37" />
      <rect
         x="16.969999"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect38" />
      <rect
         x="15.44"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect39" />
      <rect
         x="16.969999"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect40" />
      <rect
         x="16.209999"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect41" />
    </g>
  </mask>
  <path
     d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
     fill="currentColor"
     mask="url(#ft-csv)"
     id="path41"
     transform="translate(-4,-2)" />
</svg>`,"objects/file-dll":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-4.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg40"
   sodipodi:docname="file-dll.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs40" />
  <mask
     id="ft-dll">
    <path
       d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
       fill="#ffffff"
       id="path1" />
    <g
       fill="#000000"
       id="g40">
      <rect
         x="5.5"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect1" />
      <rect
         x="6.2600002"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect2" />
      <rect
         x="7.0300002"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect3" />
      <rect
         x="7.79"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect4" />
      <rect
         x="5.5"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect5" />
      <rect
         x="8.5600004"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect6" />
      <rect
         x="5.5"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect7" />
      <rect
         x="8.5600004"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect8" />
      <rect
         x="5.5"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect9" />
      <rect
         x="8.5600004"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect10" />
      <rect
         x="5.5"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect11" />
      <rect
         x="8.5600004"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect12" />
      <rect
         x="5.5"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect13" />
      <rect
         x="8.5600004"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect14" />
      <rect
         x="5.5"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect15" />
      <rect
         x="6.2600002"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect16" />
      <rect
         x="7.0300002"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect17" />
      <rect
         x="7.79"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect18" />
      <rect
         x="10.09"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect19" />
      <rect
         x="10.09"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect20" />
      <rect
         x="10.09"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect21" />
      <rect
         x="10.09"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect22" />
      <rect
         x="10.09"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect23" />
      <rect
         x="10.09"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect24" />
      <rect
         x="10.09"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect25" />
      <rect
         x="10.85"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect26" />
      <rect
         x="11.62"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect27" />
      <rect
         x="12.38"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect28" />
      <rect
         x="13.15"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect29" />
      <rect
         x="14.68"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect30" />
      <rect
         x="14.68"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect31" />
      <rect
         x="14.68"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect32" />
      <rect
         x="14.68"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect33" />
      <rect
         x="14.68"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect34" />
      <rect
         x="14.68"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect35" />
      <rect
         x="14.68"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect36" />
      <rect
         x="15.44"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect37" />
      <rect
         x="16.209999"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect38" />
      <rect
         x="16.969999"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect39" />
      <rect
         x="17.74"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect40" />
    </g>
  </mask>
  <path
     d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
     fill="currentColor"
     mask="url(#ft-dll)"
     id="path40"
     transform="translate(-4,-2)" />
</svg>`,"objects/file-doc":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-4.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg47"
   sodipodi:docname="file-doc.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs47" />
  <mask
     id="ft-doc">
    <path
       d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
       fill="#ffffff"
       id="path1" />
    <g
       fill="#000000"
       id="g47">
      <rect
         x="5.5"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect1" />
      <rect
         x="6.2600002"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect2" />
      <rect
         x="7.0300002"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect3" />
      <rect
         x="7.79"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect4" />
      <rect
         x="5.5"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect5" />
      <rect
         x="8.5600004"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect6" />
      <rect
         x="5.5"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect7" />
      <rect
         x="8.5600004"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect8" />
      <rect
         x="5.5"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect9" />
      <rect
         x="8.5600004"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect10" />
      <rect
         x="5.5"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect11" />
      <rect
         x="8.5600004"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect12" />
      <rect
         x="5.5"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect13" />
      <rect
         x="8.5600004"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect14" />
      <rect
         x="5.5"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect15" />
      <rect
         x="6.2600002"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect16" />
      <rect
         x="7.0300002"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect17" />
      <rect
         x="7.79"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect18" />
      <rect
         x="10.85"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect19" />
      <rect
         x="11.62"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect20" />
      <rect
         x="12.38"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect21" />
      <rect
         x="10.09"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect22" />
      <rect
         x="13.15"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect23" />
      <rect
         x="10.09"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect24" />
      <rect
         x="13.15"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect25" />
      <rect
         x="10.09"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect26" />
      <rect
         x="13.15"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect27" />
      <rect
         x="10.09"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect28" />
      <rect
         x="13.15"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect29" />
      <rect
         x="10.09"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect30" />
      <rect
         x="13.15"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect31" />
      <rect
         x="10.85"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect32" />
      <rect
         x="11.62"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect33" />
      <rect
         x="12.38"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect34" />
      <rect
         x="15.44"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect35" />
      <rect
         x="16.209999"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect36" />
      <rect
         x="16.969999"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect37" />
      <rect
         x="14.68"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect38" />
      <rect
         x="17.74"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect39" />
      <rect
         x="14.68"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect40" />
      <rect
         x="14.68"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect41" />
      <rect
         x="14.68"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect42" />
      <rect
         x="14.68"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect43" />
      <rect
         x="17.74"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect44" />
      <rect
         x="15.44"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect45" />
      <rect
         x="16.209999"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect46" />
      <rect
         x="16.969999"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect47" />
    </g>
  </mask>
  <path
     d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
     fill="currentColor"
     mask="url(#ft-doc)"
     id="path47"
     transform="translate(-4,-2)" />
</svg>`,"objects/file-docx":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-4.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg60"
   sodipodi:docname="file-docx.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs60" />
  <mask
     id="ft-docx">
    <path
       d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
       fill="#ffffff"
       id="path1" />
    <g
       fill="#000000"
       id="g60">
      <rect
         x="5.5"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect1" />
      <rect
         x="6.0700002"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect2" />
      <rect
         x="6.6300001"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect3" />
      <rect
         x="7.1999998"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect4" />
      <rect
         x="5.5"
         y="14.89"
         width="0.56999999"
         height="0.56999999"
         id="rect5" />
      <rect
         x="7.7600002"
         y="14.89"
         width="0.56999999"
         height="0.56999999"
         id="rect6" />
      <rect
         x="5.5"
         y="15.45"
         width="0.56999999"
         height="0.56999999"
         id="rect7" />
      <rect
         x="7.7600002"
         y="15.45"
         width="0.56999999"
         height="0.56999999"
         id="rect8" />
      <rect
         x="5.5"
         y="16.02"
         width="0.56999999"
         height="0.56999999"
         id="rect9" />
      <rect
         x="7.7600002"
         y="16.02"
         width="0.56999999"
         height="0.56999999"
         id="rect10" />
      <rect
         x="5.5"
         y="16.58"
         width="0.56999999"
         height="0.56999999"
         id="rect11" />
      <rect
         x="7.7600002"
         y="16.58"
         width="0.56999999"
         height="0.56999999"
         id="rect12" />
      <rect
         x="5.5"
         y="17.15"
         width="0.56999999"
         height="0.56999999"
         id="rect13" />
      <rect
         x="7.7600002"
         y="17.15"
         width="0.56999999"
         height="0.56999999"
         id="rect14" />
      <rect
         x="5.5"
         y="17.709999"
         width="0.56999999"
         height="0.56999999"
         id="rect15" />
      <rect
         x="6.0700002"
         y="17.709999"
         width="0.56999999"
         height="0.56999999"
         id="rect16" />
      <rect
         x="6.6300001"
         y="17.709999"
         width="0.56999999"
         height="0.56999999"
         id="rect17" />
      <rect
         x="7.1999998"
         y="17.709999"
         width="0.56999999"
         height="0.56999999"
         id="rect18" />
      <rect
         x="9.46"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect19" />
      <rect
         x="10.02"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect20" />
      <rect
         x="10.59"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect21" />
      <rect
         x="8.8900003"
         y="14.89"
         width="0.56999999"
         height="0.56999999"
         id="rect22" />
      <rect
         x="11.15"
         y="14.89"
         width="0.56999999"
         height="0.56999999"
         id="rect23" />
      <rect
         x="8.8900003"
         y="15.45"
         width="0.56999999"
         height="0.56999999"
         id="rect24" />
      <rect
         x="11.15"
         y="15.45"
         width="0.56999999"
         height="0.56999999"
         id="rect25" />
      <rect
         x="8.8900003"
         y="16.02"
         width="0.56999999"
         height="0.56999999"
         id="rect26" />
      <rect
         x="11.15"
         y="16.02"
         width="0.56999999"
         height="0.56999999"
         id="rect27" />
      <rect
         x="8.8900003"
         y="16.58"
         width="0.56999999"
         height="0.56999999"
         id="rect28" />
      <rect
         x="11.15"
         y="16.58"
         width="0.56999999"
         height="0.56999999"
         id="rect29" />
      <rect
         x="8.8900003"
         y="17.15"
         width="0.56999999"
         height="0.56999999"
         id="rect30" />
      <rect
         x="11.15"
         y="17.15"
         width="0.56999999"
         height="0.56999999"
         id="rect31" />
      <rect
         x="9.46"
         y="17.709999"
         width="0.56999999"
         height="0.56999999"
         id="rect32" />
      <rect
         x="10.02"
         y="17.709999"
         width="0.56999999"
         height="0.56999999"
         id="rect33" />
      <rect
         x="10.59"
         y="17.709999"
         width="0.56999999"
         height="0.56999999"
         id="rect34" />
      <rect
         x="12.85"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect35" />
      <rect
         x="13.41"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect36" />
      <rect
         x="13.98"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect37" />
      <rect
         x="12.28"
         y="14.89"
         width="0.56999999"
         height="0.56999999"
         id="rect38" />
      <rect
         x="14.54"
         y="14.89"
         width="0.56999999"
         height="0.56999999"
         id="rect39" />
      <rect
         x="12.28"
         y="15.45"
         width="0.56999999"
         height="0.56999999"
         id="rect40" />
      <rect
         x="12.28"
         y="16.02"
         width="0.56999999"
         height="0.56999999"
         id="rect41" />
      <rect
         x="12.28"
         y="16.58"
         width="0.56999999"
         height="0.56999999"
         id="rect42" />
      <rect
         x="12.28"
         y="17.15"
         width="0.56999999"
         height="0.56999999"
         id="rect43" />
      <rect
         x="14.54"
         y="17.15"
         width="0.56999999"
         height="0.56999999"
         id="rect44" />
      <rect
         x="12.85"
         y="17.709999"
         width="0.56999999"
         height="0.56999999"
         id="rect45" />
      <rect
         x="13.41"
         y="17.709999"
         width="0.56999999"
         height="0.56999999"
         id="rect46" />
      <rect
         x="13.98"
         y="17.709999"
         width="0.56999999"
         height="0.56999999"
         id="rect47" />
      <rect
         x="15.67"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect48" />
      <rect
         x="17.93"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect49" />
      <rect
         x="15.67"
         y="14.89"
         width="0.56999999"
         height="0.56999999"
         id="rect50" />
      <rect
         x="17.93"
         y="14.89"
         width="0.56999999"
         height="0.56999999"
         id="rect51" />
      <rect
         x="16.24"
         y="15.45"
         width="0.56999999"
         height="0.56999999"
         id="rect52" />
      <rect
         x="17.370001"
         y="15.45"
         width="0.56999999"
         height="0.56999999"
         id="rect53" />
      <rect
         x="16.799999"
         y="16.02"
         width="0.56999999"
         height="0.56999999"
         id="rect54" />
      <rect
         x="16.24"
         y="16.58"
         width="0.56999999"
         height="0.56999999"
         id="rect55" />
      <rect
         x="17.370001"
         y="16.58"
         width="0.56999999"
         height="0.56999999"
         id="rect56" />
      <rect
         x="15.67"
         y="17.15"
         width="0.56999999"
         height="0.56999999"
         id="rect57" />
      <rect
         x="17.93"
         y="17.15"
         width="0.56999999"
         height="0.56999999"
         id="rect58" />
      <rect
         x="15.67"
         y="17.709999"
         width="0.56999999"
         height="0.56999999"
         id="rect59" />
      <rect
         x="17.93"
         y="17.709999"
         width="0.56999999"
         height="0.56999999"
         id="rect60" />
    </g>
  </mask>
  <path
     d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
     fill="currentColor"
     mask="url(#ft-docx)"
     id="path60"
     transform="translate(-4,-2)" />
</svg>`,"objects/file-elf":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-4.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg43"
   sodipodi:docname="file-elf.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs43" />
  <mask
     id="ft-elf">
    <path
       d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
       fill="#ffffff"
       id="path1" />
    <g
       fill="#000000"
       id="g43">
      <rect
         x="5.5"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect1" />
      <rect
         x="6.2600002"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect2" />
      <rect
         x="7.0300002"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect3" />
      <rect
         x="7.79"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect4" />
      <rect
         x="8.5600004"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect5" />
      <rect
         x="5.5"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect6" />
      <rect
         x="5.5"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect7" />
      <rect
         x="5.5"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect8" />
      <rect
         x="6.2600002"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect9" />
      <rect
         x="7.0300002"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect10" />
      <rect
         x="7.79"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect11" />
      <rect
         x="5.5"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect12" />
      <rect
         x="5.5"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect13" />
      <rect
         x="5.5"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect14" />
      <rect
         x="6.2600002"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect15" />
      <rect
         x="7.0300002"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect16" />
      <rect
         x="7.79"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect17" />
      <rect
         x="8.5600004"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect18" />
      <rect
         x="10.09"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect19" />
      <rect
         x="10.09"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect20" />
      <rect
         x="10.09"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect21" />
      <rect
         x="10.09"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect22" />
      <rect
         x="10.09"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect23" />
      <rect
         x="10.09"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect24" />
      <rect
         x="10.09"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect25" />
      <rect
         x="10.85"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect26" />
      <rect
         x="11.62"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect27" />
      <rect
         x="12.38"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect28" />
      <rect
         x="13.15"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect29" />
      <rect
         x="14.68"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect30" />
      <rect
         x="15.44"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect31" />
      <rect
         x="16.209999"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect32" />
      <rect
         x="16.969999"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect33" />
      <rect
         x="17.74"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect34" />
      <rect
         x="14.68"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect35" />
      <rect
         x="14.68"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect36" />
      <rect
         x="14.68"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect37" />
      <rect
         x="15.44"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect38" />
      <rect
         x="16.209999"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect39" />
      <rect
         x="16.969999"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect40" />
      <rect
         x="14.68"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect41" />
      <rect
         x="14.68"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect42" />
      <rect
         x="14.68"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect43" />
    </g>
  </mask>
  <path
     d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
     fill="currentColor"
     mask="url(#ft-elf)"
     id="path43"
     transform="translate(-4,-2)" />
</svg>`,"objects/file-eml":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-4.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg47"
   sodipodi:docname="file-eml.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs47" />
  <mask
     id="ft-eml">
    <path
       d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
       fill="#ffffff"
       id="path1" />
    <g
       fill="#000000"
       id="g47">
      <rect
         x="5.5"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect1" />
      <rect
         x="6.2600002"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect2" />
      <rect
         x="7.0300002"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect3" />
      <rect
         x="7.79"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect4" />
      <rect
         x="8.5600004"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect5" />
      <rect
         x="5.5"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect6" />
      <rect
         x="5.5"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect7" />
      <rect
         x="5.5"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect8" />
      <rect
         x="6.2600002"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect9" />
      <rect
         x="7.0300002"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect10" />
      <rect
         x="7.79"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect11" />
      <rect
         x="5.5"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect12" />
      <rect
         x="5.5"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect13" />
      <rect
         x="5.5"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect14" />
      <rect
         x="6.2600002"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect15" />
      <rect
         x="7.0300002"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect16" />
      <rect
         x="7.79"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect17" />
      <rect
         x="8.5600004"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect18" />
      <rect
         x="10.09"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect19" />
      <rect
         x="13.15"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect20" />
      <rect
         x="10.09"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect21" />
      <rect
         x="10.85"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect22" />
      <rect
         x="12.38"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect23" />
      <rect
         x="13.15"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect24" />
      <rect
         x="10.09"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect25" />
      <rect
         x="11.62"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect26" />
      <rect
         x="13.15"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect27" />
      <rect
         x="10.09"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect28" />
      <rect
         x="11.62"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect29" />
      <rect
         x="13.15"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect30" />
      <rect
         x="10.09"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect31" />
      <rect
         x="13.15"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect32" />
      <rect
         x="10.09"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect33" />
      <rect
         x="13.15"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect34" />
      <rect
         x="10.09"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect35" />
      <rect
         x="13.15"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect36" />
      <rect
         x="14.68"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect37" />
      <rect
         x="14.68"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect38" />
      <rect
         x="14.68"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect39" />
      <rect
         x="14.68"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect40" />
      <rect
         x="14.68"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect41" />
      <rect
         x="14.68"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect42" />
      <rect
         x="14.68"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect43" />
      <rect
         x="15.44"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect44" />
      <rect
         x="16.209999"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect45" />
      <rect
         x="16.969999"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect46" />
      <rect
         x="17.74"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect47" />
    </g>
  </mask>
  <path
     d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
     fill="currentColor"
     mask="url(#ft-eml)"
     id="path47"
     transform="translate(-4,-2)" />
</svg>`,"objects/file-exe":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-4.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg49"
   sodipodi:docname="file-exe.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs49" />
  <mask
     id="ft-exe">
    <path
       d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
       fill="#ffffff"
       id="path1" />
    <g
       fill="#000000"
       id="g49">
      <rect
         x="5.5"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect1" />
      <rect
         x="6.2600002"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect2" />
      <rect
         x="7.0300002"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect3" />
      <rect
         x="7.79"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect4" />
      <rect
         x="8.5600004"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect5" />
      <rect
         x="5.5"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect6" />
      <rect
         x="5.5"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect7" />
      <rect
         x="5.5"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect8" />
      <rect
         x="6.2600002"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect9" />
      <rect
         x="7.0300002"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect10" />
      <rect
         x="7.79"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect11" />
      <rect
         x="5.5"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect12" />
      <rect
         x="5.5"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect13" />
      <rect
         x="5.5"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect14" />
      <rect
         x="6.2600002"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect15" />
      <rect
         x="7.0300002"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect16" />
      <rect
         x="7.79"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect17" />
      <rect
         x="8.5600004"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect18" />
      <rect
         x="10.09"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect19" />
      <rect
         x="13.15"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect20" />
      <rect
         x="10.09"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect21" />
      <rect
         x="13.15"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect22" />
      <rect
         x="10.85"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect23" />
      <rect
         x="12.38"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect24" />
      <rect
         x="11.62"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect25" />
      <rect
         x="10.85"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect26" />
      <rect
         x="12.38"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect27" />
      <rect
         x="10.09"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect28" />
      <rect
         x="13.15"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect29" />
      <rect
         x="10.09"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect30" />
      <rect
         x="13.15"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect31" />
      <rect
         x="14.68"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect32" />
      <rect
         x="15.44"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect33" />
      <rect
         x="16.209999"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect34" />
      <rect
         x="16.969999"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect35" />
      <rect
         x="17.74"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect36" />
      <rect
         x="14.68"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect37" />
      <rect
         x="14.68"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect38" />
      <rect
         x="14.68"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect39" />
      <rect
         x="15.44"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect40" />
      <rect
         x="16.209999"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect41" />
      <rect
         x="16.969999"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect42" />
      <rect
         x="14.68"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect43" />
      <rect
         x="14.68"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect44" />
      <rect
         x="14.68"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect45" />
      <rect
         x="15.44"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect46" />
      <rect
         x="16.209999"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect47" />
      <rect
         x="16.969999"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect48" />
      <rect
         x="17.74"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect49" />
    </g>
  </mask>
  <path
     d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
     fill="currentColor"
     mask="url(#ft-exe)"
     id="path49"
     transform="translate(-4,-2)" />
</svg>`,"objects/file-gif":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-4.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg42"
   sodipodi:docname="file-gif.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs42" />
  <mask
     id="ft-gif">
    <path
       d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
       fill="#ffffff"
       id="path1" />
    <g
       fill="#000000"
       id="g42">
      <rect
         x="6.2600002"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect1" />
      <rect
         x="7.0300002"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect2" />
      <rect
         x="7.79"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect3" />
      <rect
         x="5.5"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect4" />
      <rect
         x="8.5600004"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect5" />
      <rect
         x="5.5"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect6" />
      <rect
         x="5.5"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect7" />
      <rect
         x="7.0300002"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect8" />
      <rect
         x="7.79"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect9" />
      <rect
         x="8.5600004"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect10" />
      <rect
         x="5.5"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect11" />
      <rect
         x="8.5600004"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect12" />
      <rect
         x="5.5"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect13" />
      <rect
         x="8.5600004"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect14" />
      <rect
         x="6.2600002"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect15" />
      <rect
         x="7.0300002"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect16" />
      <rect
         x="7.79"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect17" />
      <rect
         x="10.85"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect18" />
      <rect
         x="11.62"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect19" />
      <rect
         x="12.38"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect20" />
      <rect
         x="11.62"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect21" />
      <rect
         x="11.62"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect22" />
      <rect
         x="11.62"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect23" />
      <rect
         x="11.62"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect24" />
      <rect
         x="11.62"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect25" />
      <rect
         x="10.85"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect26" />
      <rect
         x="11.62"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect27" />
      <rect
         x="12.38"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect28" />
      <rect
         x="14.68"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect29" />
      <rect
         x="15.44"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect30" />
      <rect
         x="16.209999"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect31" />
      <rect
         x="16.969999"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect32" />
      <rect
         x="17.74"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect33" />
      <rect
         x="14.68"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect34" />
      <rect
         x="14.68"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect35" />
      <rect
         x="14.68"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect36" />
      <rect
         x="15.44"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect37" />
      <rect
         x="16.209999"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect38" />
      <rect
         x="16.969999"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect39" />
      <rect
         x="14.68"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect40" />
      <rect
         x="14.68"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect41" />
      <rect
         x="14.68"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect42" />
    </g>
  </mask>
  <path
     d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
     fill="currentColor"
     mask="url(#ft-gif)"
     id="path42"
     transform="translate(-4,-2)" />
</svg>`,"objects/file-gz":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-4.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg32"
   sodipodi:docname="file-gz.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs32" />
  <mask
     id="ft-gz">
    <path
       d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
       fill="#ffffff"
       id="path1" />
    <g
       fill="#000000"
       id="g32">
      <rect
         x="6.8600001"
         y="12.3"
         width="1.14"
         height="1.14"
         id="rect1" />
      <rect
         x="8"
         y="12.3"
         width="1.14"
         height="1.14"
         id="rect2" />
      <rect
         x="9.1400003"
         y="12.3"
         width="1.14"
         height="1.14"
         id="rect3" />
      <rect
         x="5.71"
         y="13.44"
         width="1.14"
         height="1.14"
         id="rect4" />
      <rect
         x="10.29"
         y="13.44"
         width="1.14"
         height="1.14"
         id="rect5" />
      <rect
         x="5.71"
         y="14.59"
         width="1.14"
         height="1.14"
         id="rect6" />
      <rect
         x="5.71"
         y="15.73"
         width="1.14"
         height="1.14"
         id="rect7" />
      <rect
         x="8"
         y="15.73"
         width="1.14"
         height="1.14"
         id="rect8" />
      <rect
         x="9.1400003"
         y="15.73"
         width="1.14"
         height="1.14"
         id="rect9" />
      <rect
         x="10.29"
         y="15.73"
         width="1.14"
         height="1.14"
         id="rect10" />
      <rect
         x="5.71"
         y="16.870001"
         width="1.14"
         height="1.14"
         id="rect11" />
      <rect
         x="10.29"
         y="16.870001"
         width="1.14"
         height="1.14"
         id="rect12" />
      <rect
         x="5.71"
         y="18.01"
         width="1.14"
         height="1.14"
         id="rect13" />
      <rect
         x="10.29"
         y="18.01"
         width="1.14"
         height="1.14"
         id="rect14" />
      <rect
         x="6.8600001"
         y="19.16"
         width="1.14"
         height="1.14"
         id="rect15" />
      <rect
         x="8"
         y="19.16"
         width="1.14"
         height="1.14"
         id="rect16" />
      <rect
         x="9.1400003"
         y="19.16"
         width="1.14"
         height="1.14"
         id="rect17" />
      <rect
         x="12.57"
         y="12.3"
         width="1.14"
         height="1.14"
         id="rect18" />
      <rect
         x="13.71"
         y="12.3"
         width="1.14"
         height="1.14"
         id="rect19" />
      <rect
         x="14.86"
         y="12.3"
         width="1.14"
         height="1.14"
         id="rect20" />
      <rect
         x="16"
         y="12.3"
         width="1.14"
         height="1.14"
         id="rect21" />
      <rect
         x="17.139999"
         y="12.3"
         width="1.14"
         height="1.14"
         id="rect22" />
      <rect
         x="17.139999"
         y="13.44"
         width="1.14"
         height="1.14"
         id="rect23" />
      <rect
         x="16"
         y="14.59"
         width="1.14"
         height="1.14"
         id="rect24" />
      <rect
         x="14.86"
         y="15.73"
         width="1.14"
         height="1.14"
         id="rect25" />
      <rect
         x="13.71"
         y="16.870001"
         width="1.14"
         height="1.14"
         id="rect26" />
      <rect
         x="12.57"
         y="18.01"
         width="1.14"
         height="1.14"
         id="rect27" />
      <rect
         x="12.57"
         y="19.16"
         width="1.14"
         height="1.14"
         id="rect28" />
      <rect
         x="13.71"
         y="19.16"
         width="1.14"
         height="1.14"
         id="rect29" />
      <rect
         x="14.86"
         y="19.16"
         width="1.14"
         height="1.14"
         id="rect30" />
      <rect
         x="16"
         y="19.16"
         width="1.14"
         height="1.14"
         id="rect31" />
      <rect
         x="17.139999"
         y="19.16"
         width="1.14"
         height="1.14"
         id="rect32" />
    </g>
  </mask>
  <path
     d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
     fill="currentColor"
     mask="url(#ft-gz)"
     id="path32"
     transform="translate(-4,-2)" />
</svg>`,"objects/file-html":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-4.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg57"
   sodipodi:docname="file-html.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs57" />
  <mask
     id="ft-html">
    <path
       d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
       fill="#ffffff"
       id="path1" />
    <g
       fill="#000000"
       id="g57">
      <rect
         x="5.5"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect1" />
      <rect
         x="7.7600002"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect2" />
      <rect
         x="5.5"
         y="14.89"
         width="0.56999999"
         height="0.56999999"
         id="rect3" />
      <rect
         x="7.7600002"
         y="14.89"
         width="0.56999999"
         height="0.56999999"
         id="rect4" />
      <rect
         x="5.5"
         y="15.45"
         width="0.56999999"
         height="0.56999999"
         id="rect5" />
      <rect
         x="7.7600002"
         y="15.45"
         width="0.56999999"
         height="0.56999999"
         id="rect6" />
      <rect
         x="5.5"
         y="16.02"
         width="0.56999999"
         height="0.56999999"
         id="rect7" />
      <rect
         x="6.0700002"
         y="16.02"
         width="0.56999999"
         height="0.56999999"
         id="rect8" />
      <rect
         x="6.6300001"
         y="16.02"
         width="0.56999999"
         height="0.56999999"
         id="rect9" />
      <rect
         x="7.1999998"
         y="16.02"
         width="0.56999999"
         height="0.56999999"
         id="rect10" />
      <rect
         x="7.7600002"
         y="16.02"
         width="0.56999999"
         height="0.56999999"
         id="rect11" />
      <rect
         x="5.5"
         y="16.58"
         width="0.56999999"
         height="0.56999999"
         id="rect12" />
      <rect
         x="7.7600002"
         y="16.58"
         width="0.56999999"
         height="0.56999999"
         id="rect13" />
      <rect
         x="5.5"
         y="17.15"
         width="0.56999999"
         height="0.56999999"
         id="rect14" />
      <rect
         x="7.7600002"
         y="17.15"
         width="0.56999999"
         height="0.56999999"
         id="rect15" />
      <rect
         x="5.5"
         y="17.709999"
         width="0.56999999"
         height="0.56999999"
         id="rect16" />
      <rect
         x="7.7600002"
         y="17.709999"
         width="0.56999999"
         height="0.56999999"
         id="rect17" />
      <rect
         x="8.8900003"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect18" />
      <rect
         x="9.46"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect19" />
      <rect
         x="10.02"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect20" />
      <rect
         x="10.59"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect21" />
      <rect
         x="11.15"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect22" />
      <rect
         x="10.02"
         y="14.89"
         width="0.56999999"
         height="0.56999999"
         id="rect23" />
      <rect
         x="10.02"
         y="15.45"
         width="0.56999999"
         height="0.56999999"
         id="rect24" />
      <rect
         x="10.02"
         y="16.02"
         width="0.56999999"
         height="0.56999999"
         id="rect25" />
      <rect
         x="10.02"
         y="16.58"
         width="0.56999999"
         height="0.56999999"
         id="rect26" />
      <rect
         x="10.02"
         y="17.15"
         width="0.56999999"
         height="0.56999999"
         id="rect27" />
      <rect
         x="10.02"
         y="17.709999"
         width="0.56999999"
         height="0.56999999"
         id="rect28" />
      <rect
         x="12.28"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect29" />
      <rect
         x="14.54"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect30" />
      <rect
         x="12.28"
         y="14.89"
         width="0.56999999"
         height="0.56999999"
         id="rect31" />
      <rect
         x="12.85"
         y="14.89"
         width="0.56999999"
         height="0.56999999"
         id="rect32" />
      <rect
         x="13.98"
         y="14.89"
         width="0.56999999"
         height="0.56999999"
         id="rect33" />
      <rect
         x="14.54"
         y="14.89"
         width="0.56999999"
         height="0.56999999"
         id="rect34" />
      <rect
         x="12.28"
         y="15.45"
         width="0.56999999"
         height="0.56999999"
         id="rect35" />
      <rect
         x="13.41"
         y="15.45"
         width="0.56999999"
         height="0.56999999"
         id="rect36" />
      <rect
         x="14.54"
         y="15.45"
         width="0.56999999"
         height="0.56999999"
         id="rect37" />
      <rect
         x="12.28"
         y="16.02"
         width="0.56999999"
         height="0.56999999"
         id="rect38" />
      <rect
         x="13.41"
         y="16.02"
         width="0.56999999"
         height="0.56999999"
         id="rect39" />
      <rect
         x="14.54"
         y="16.02"
         width="0.56999999"
         height="0.56999999"
         id="rect40" />
      <rect
         x="12.28"
         y="16.58"
         width="0.56999999"
         height="0.56999999"
         id="rect41" />
      <rect
         x="14.54"
         y="16.58"
         width="0.56999999"
         height="0.56999999"
         id="rect42" />
      <rect
         x="12.28"
         y="17.15"
         width="0.56999999"
         height="0.56999999"
         id="rect43" />
      <rect
         x="14.54"
         y="17.15"
         width="0.56999999"
         height="0.56999999"
         id="rect44" />
      <rect
         x="12.28"
         y="17.709999"
         width="0.56999999"
         height="0.56999999"
         id="rect45" />
      <rect
         x="14.54"
         y="17.709999"
         width="0.56999999"
         height="0.56999999"
         id="rect46" />
      <rect
         x="15.67"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect47" />
      <rect
         x="15.67"
         y="14.89"
         width="0.56999999"
         height="0.56999999"
         id="rect48" />
      <rect
         x="15.67"
         y="15.45"
         width="0.56999999"
         height="0.56999999"
         id="rect49" />
      <rect
         x="15.67"
         y="16.02"
         width="0.56999999"
         height="0.56999999"
         id="rect50" />
      <rect
         x="15.67"
         y="16.58"
         width="0.56999999"
         height="0.56999999"
         id="rect51" />
      <rect
         x="15.67"
         y="17.15"
         width="0.56999999"
         height="0.56999999"
         id="rect52" />
      <rect
         x="15.67"
         y="17.709999"
         width="0.56999999"
         height="0.56999999"
         id="rect53" />
      <rect
         x="16.24"
         y="17.709999"
         width="0.56999999"
         height="0.56999999"
         id="rect54" />
      <rect
         x="16.799999"
         y="17.709999"
         width="0.56999999"
         height="0.56999999"
         id="rect55" />
      <rect
         x="17.370001"
         y="17.709999"
         width="0.56999999"
         height="0.56999999"
         id="rect56" />
      <rect
         x="17.93"
         y="17.709999"
         width="0.56999999"
         height="0.56999999"
         id="rect57" />
    </g>
  </mask>
  <path
     d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
     fill="currentColor"
     mask="url(#ft-html)"
     id="path57"
     transform="translate(-4,-2)" />
</svg>`,"objects/file-iso":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-4.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg42"
   sodipodi:docname="file-iso.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs42" />
  <mask
     id="ft-iso">
    <path
       d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
       fill="#ffffff"
       id="path1" />
    <g
       fill="#000000"
       id="g42">
      <rect
         x="6.2600002"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect1" />
      <rect
         x="7.0300002"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect2" />
      <rect
         x="7.79"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect3" />
      <rect
         x="7.0300002"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect4" />
      <rect
         x="7.0300002"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect5" />
      <rect
         x="7.0300002"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect6" />
      <rect
         x="7.0300002"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect7" />
      <rect
         x="7.0300002"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect8" />
      <rect
         x="6.2600002"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect9" />
      <rect
         x="7.0300002"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect10" />
      <rect
         x="7.79"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect11" />
      <rect
         x="10.85"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect12" />
      <rect
         x="11.62"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect13" />
      <rect
         x="12.38"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect14" />
      <rect
         x="13.15"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect15" />
      <rect
         x="10.09"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect16" />
      <rect
         x="10.09"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect17" />
      <rect
         x="10.85"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect18" />
      <rect
         x="11.62"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect19" />
      <rect
         x="12.38"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect20" />
      <rect
         x="13.15"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect21" />
      <rect
         x="13.15"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect22" />
      <rect
         x="10.09"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect23" />
      <rect
         x="10.85"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect24" />
      <rect
         x="11.62"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect25" />
      <rect
         x="12.38"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect26" />
      <rect
         x="15.44"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect27" />
      <rect
         x="16.209999"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect28" />
      <rect
         x="16.969999"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect29" />
      <rect
         x="14.68"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect30" />
      <rect
         x="17.74"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect31" />
      <rect
         x="14.68"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect32" />
      <rect
         x="17.74"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect33" />
      <rect
         x="14.68"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect34" />
      <rect
         x="17.74"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect35" />
      <rect
         x="14.68"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect36" />
      <rect
         x="17.74"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect37" />
      <rect
         x="14.68"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect38" />
      <rect
         x="17.74"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect39" />
      <rect
         x="15.44"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect40" />
      <rect
         x="16.209999"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect41" />
      <rect
         x="16.969999"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect42" />
    </g>
  </mask>
  <path
     d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
     fill="currentColor"
     mask="url(#ft-iso)"
     id="path42"
     transform="translate(-4,-2)" />
</svg>`,"objects/file-jar":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-4.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg47"
   sodipodi:docname="file-jar.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs47" />
  <mask
     id="ft-jar">
    <path
       d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
       fill="#ffffff"
       id="path1" />
    <g
       fill="#000000"
       id="g47">
      <rect
         x="7.0300002"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect1" />
      <rect
         x="7.79"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect2" />
      <rect
         x="8.5600004"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect3" />
      <rect
         x="7.79"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect4" />
      <rect
         x="7.79"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect5" />
      <rect
         x="7.79"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect6" />
      <rect
         x="7.79"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect7" />
      <rect
         x="5.5"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect8" />
      <rect
         x="7.79"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect9" />
      <rect
         x="6.2600002"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect10" />
      <rect
         x="7.0300002"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect11" />
      <rect
         x="10.85"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect12" />
      <rect
         x="11.62"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect13" />
      <rect
         x="12.38"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect14" />
      <rect
         x="10.09"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect15" />
      <rect
         x="13.15"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect16" />
      <rect
         x="10.09"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect17" />
      <rect
         x="13.15"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect18" />
      <rect
         x="10.09"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect19" />
      <rect
         x="10.85"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect20" />
      <rect
         x="11.62"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect21" />
      <rect
         x="12.38"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect22" />
      <rect
         x="13.15"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect23" />
      <rect
         x="10.09"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect24" />
      <rect
         x="13.15"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect25" />
      <rect
         x="10.09"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect26" />
      <rect
         x="13.15"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect27" />
      <rect
         x="10.09"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect28" />
      <rect
         x="13.15"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect29" />
      <rect
         x="14.68"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect30" />
      <rect
         x="15.44"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect31" />
      <rect
         x="16.209999"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect32" />
      <rect
         x="16.969999"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect33" />
      <rect
         x="14.68"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect34" />
      <rect
         x="17.74"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect35" />
      <rect
         x="14.68"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect36" />
      <rect
         x="17.74"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect37" />
      <rect
         x="14.68"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect38" />
      <rect
         x="15.44"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect39" />
      <rect
         x="16.209999"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect40" />
      <rect
         x="16.969999"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect41" />
      <rect
         x="14.68"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect42" />
      <rect
         x="16.209999"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect43" />
      <rect
         x="14.68"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect44" />
      <rect
         x="16.969999"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect45" />
      <rect
         x="14.68"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect46" />
      <rect
         x="17.74"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect47" />
    </g>
  </mask>
  <path
     d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
     fill="currentColor"
     mask="url(#ft-jar)"
     id="path47"
     transform="translate(-4,-2)" />
</svg>`,"objects/file-jpg":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-4.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg43"
   sodipodi:docname="file-jpg.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs43" />
  <mask
     id="ft-jpg">
    <path
       d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
       fill="#ffffff"
       id="path1" />
    <g
       fill="#000000"
       id="g43">
      <rect
         x="7.0300002"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect1" />
      <rect
         x="7.79"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect2" />
      <rect
         x="8.5600004"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect3" />
      <rect
         x="7.79"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect4" />
      <rect
         x="7.79"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect5" />
      <rect
         x="7.79"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect6" />
      <rect
         x="7.79"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect7" />
      <rect
         x="5.5"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect8" />
      <rect
         x="7.79"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect9" />
      <rect
         x="6.2600002"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect10" />
      <rect
         x="7.0300002"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect11" />
      <rect
         x="10.09"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect12" />
      <rect
         x="10.85"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect13" />
      <rect
         x="11.62"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect14" />
      <rect
         x="12.38"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect15" />
      <rect
         x="10.09"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect16" />
      <rect
         x="13.15"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect17" />
      <rect
         x="10.09"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect18" />
      <rect
         x="13.15"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect19" />
      <rect
         x="10.09"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect20" />
      <rect
         x="10.85"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect21" />
      <rect
         x="11.62"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect22" />
      <rect
         x="12.38"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect23" />
      <rect
         x="10.09"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect24" />
      <rect
         x="10.09"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect25" />
      <rect
         x="10.09"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect26" />
      <rect
         x="15.44"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect27" />
      <rect
         x="16.209999"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect28" />
      <rect
         x="16.969999"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect29" />
      <rect
         x="14.68"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect30" />
      <rect
         x="17.74"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect31" />
      <rect
         x="14.68"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect32" />
      <rect
         x="14.68"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect33" />
      <rect
         x="16.209999"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect34" />
      <rect
         x="16.969999"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect35" />
      <rect
         x="17.74"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect36" />
      <rect
         x="14.68"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect37" />
      <rect
         x="17.74"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect38" />
      <rect
         x="14.68"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect39" />
      <rect
         x="17.74"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect40" />
      <rect
         x="15.44"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect41" />
      <rect
         x="16.209999"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect42" />
      <rect
         x="16.969999"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect43" />
    </g>
  </mask>
  <path
     d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
     fill="currentColor"
     mask="url(#ft-jpg)"
     id="path43"
     transform="translate(-4,-2)" />
</svg>`,"objects/file-js":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-4.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg26"
   sodipodi:docname="file-js.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs26" />
  <mask
     id="ft-js">
    <path
       d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
       fill="#ffffff"
       id="path1" />
    <g
       fill="#000000"
       id="g26">
      <rect
         x="8"
         y="12.3"
         width="1.14"
         height="1.14"
         id="rect1" />
      <rect
         x="9.1400003"
         y="12.3"
         width="1.14"
         height="1.14"
         id="rect2" />
      <rect
         x="10.29"
         y="12.3"
         width="1.14"
         height="1.14"
         id="rect3" />
      <rect
         x="9.1400003"
         y="13.44"
         width="1.14"
         height="1.14"
         id="rect4" />
      <rect
         x="9.1400003"
         y="14.59"
         width="1.14"
         height="1.14"
         id="rect5" />
      <rect
         x="9.1400003"
         y="15.73"
         width="1.14"
         height="1.14"
         id="rect6" />
      <rect
         x="9.1400003"
         y="16.870001"
         width="1.14"
         height="1.14"
         id="rect7" />
      <rect
         x="5.71"
         y="18.01"
         width="1.14"
         height="1.14"
         id="rect8" />
      <rect
         x="9.1400003"
         y="18.01"
         width="1.14"
         height="1.14"
         id="rect9" />
      <rect
         x="6.8600001"
         y="19.16"
         width="1.14"
         height="1.14"
         id="rect10" />
      <rect
         x="8"
         y="19.16"
         width="1.14"
         height="1.14"
         id="rect11" />
      <rect
         x="13.71"
         y="12.3"
         width="1.14"
         height="1.14"
         id="rect12" />
      <rect
         x="14.86"
         y="12.3"
         width="1.14"
         height="1.14"
         id="rect13" />
      <rect
         x="16"
         y="12.3"
         width="1.14"
         height="1.14"
         id="rect14" />
      <rect
         x="17.139999"
         y="12.3"
         width="1.14"
         height="1.14"
         id="rect15" />
      <rect
         x="12.57"
         y="13.44"
         width="1.14"
         height="1.14"
         id="rect16" />
      <rect
         x="12.57"
         y="14.59"
         width="1.14"
         height="1.14"
         id="rect17" />
      <rect
         x="13.71"
         y="15.73"
         width="1.14"
         height="1.14"
         id="rect18" />
      <rect
         x="14.86"
         y="15.73"
         width="1.14"
         height="1.14"
         id="rect19" />
      <rect
         x="16"
         y="15.73"
         width="1.14"
         height="1.14"
         id="rect20" />
      <rect
         x="17.139999"
         y="16.870001"
         width="1.14"
         height="1.14"
         id="rect21" />
      <rect
         x="17.139999"
         y="18.01"
         width="1.14"
         height="1.14"
         id="rect22" />
      <rect
         x="12.57"
         y="19.16"
         width="1.14"
         height="1.14"
         id="rect23" />
      <rect
         x="13.71"
         y="19.16"
         width="1.14"
         height="1.14"
         id="rect24" />
      <rect
         x="14.86"
         y="19.16"
         width="1.14"
         height="1.14"
         id="rect25" />
      <rect
         x="16"
         y="19.16"
         width="1.14"
         height="1.14"
         id="rect26" />
    </g>
  </mask>
  <path
     d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
     fill="currentColor"
     mask="url(#ft-js)"
     id="path26"
     transform="translate(-4,-2)" />
</svg>`,"objects/file-json":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-4.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg59"
   sodipodi:docname="file-json.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs59" />
  <mask
     id="ft-json">
    <path
       d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
       fill="#ffffff"
       id="path1" />
    <g
       fill="#000000"
       id="g59">
      <rect
         x="6.6300001"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect1" />
      <rect
         x="7.1999998"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect2" />
      <rect
         x="7.7600002"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect3" />
      <rect
         x="7.1999998"
         y="14.89"
         width="0.56999999"
         height="0.56999999"
         id="rect4" />
      <rect
         x="7.1999998"
         y="15.45"
         width="0.56999999"
         height="0.56999999"
         id="rect5" />
      <rect
         x="7.1999998"
         y="16.02"
         width="0.56999999"
         height="0.56999999"
         id="rect6" />
      <rect
         x="7.1999998"
         y="16.58"
         width="0.56999999"
         height="0.56999999"
         id="rect7" />
      <rect
         x="5.5"
         y="17.15"
         width="0.56999999"
         height="0.56999999"
         id="rect8" />
      <rect
         x="7.1999998"
         y="17.15"
         width="0.56999999"
         height="0.56999999"
         id="rect9" />
      <rect
         x="6.0700002"
         y="17.709999"
         width="0.56999999"
         height="0.56999999"
         id="rect10" />
      <rect
         x="6.6300001"
         y="17.709999"
         width="0.56999999"
         height="0.56999999"
         id="rect11" />
      <rect
         x="9.46"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect12" />
      <rect
         x="10.02"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect13" />
      <rect
         x="10.59"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect14" />
      <rect
         x="11.15"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect15" />
      <rect
         x="8.8900003"
         y="14.89"
         width="0.56999999"
         height="0.56999999"
         id="rect16" />
      <rect
         x="8.8900003"
         y="15.45"
         width="0.56999999"
         height="0.56999999"
         id="rect17" />
      <rect
         x="9.46"
         y="16.02"
         width="0.56999999"
         height="0.56999999"
         id="rect18" />
      <rect
         x="10.02"
         y="16.02"
         width="0.56999999"
         height="0.56999999"
         id="rect19" />
      <rect
         x="10.59"
         y="16.02"
         width="0.56999999"
         height="0.56999999"
         id="rect20" />
      <rect
         x="11.15"
         y="16.58"
         width="0.56999999"
         height="0.56999999"
         id="rect21" />
      <rect
         x="11.15"
         y="17.15"
         width="0.56999999"
         height="0.56999999"
         id="rect22" />
      <rect
         x="8.8900003"
         y="17.709999"
         width="0.56999999"
         height="0.56999999"
         id="rect23" />
      <rect
         x="9.46"
         y="17.709999"
         width="0.56999999"
         height="0.56999999"
         id="rect24" />
      <rect
         x="10.02"
         y="17.709999"
         width="0.56999999"
         height="0.56999999"
         id="rect25" />
      <rect
         x="10.59"
         y="17.709999"
         width="0.56999999"
         height="0.56999999"
         id="rect26" />
      <rect
         x="12.85"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect27" />
      <rect
         x="13.41"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect28" />
      <rect
         x="13.98"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect29" />
      <rect
         x="12.28"
         y="14.89"
         width="0.56999999"
         height="0.56999999"
         id="rect30" />
      <rect
         x="14.54"
         y="14.89"
         width="0.56999999"
         height="0.56999999"
         id="rect31" />
      <rect
         x="12.28"
         y="15.45"
         width="0.56999999"
         height="0.56999999"
         id="rect32" />
      <rect
         x="14.54"
         y="15.45"
         width="0.56999999"
         height="0.56999999"
         id="rect33" />
      <rect
         x="12.28"
         y="16.02"
         width="0.56999999"
         height="0.56999999"
         id="rect34" />
      <rect
         x="14.54"
         y="16.02"
         width="0.56999999"
         height="0.56999999"
         id="rect35" />
      <rect
         x="12.28"
         y="16.58"
         width="0.56999999"
         height="0.56999999"
         id="rect36" />
      <rect
         x="14.54"
         y="16.58"
         width="0.56999999"
         height="0.56999999"
         id="rect37" />
      <rect
         x="12.28"
         y="17.15"
         width="0.56999999"
         height="0.56999999"
         id="rect38" />
      <rect
         x="14.54"
         y="17.15"
         width="0.56999999"
         height="0.56999999"
         id="rect39" />
      <rect
         x="12.85"
         y="17.709999"
         width="0.56999999"
         height="0.56999999"
         id="rect40" />
      <rect
         x="13.41"
         y="17.709999"
         width="0.56999999"
         height="0.56999999"
         id="rect41" />
      <rect
         x="13.98"
         y="17.709999"
         width="0.56999999"
         height="0.56999999"
         id="rect42" />
      <rect
         x="15.67"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect43" />
      <rect
         x="17.93"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect44" />
      <rect
         x="15.67"
         y="14.89"
         width="0.56999999"
         height="0.56999999"
         id="rect45" />
      <rect
         x="17.93"
         y="14.89"
         width="0.56999999"
         height="0.56999999"
         id="rect46" />
      <rect
         x="15.67"
         y="15.45"
         width="0.56999999"
         height="0.56999999"
         id="rect47" />
      <rect
         x="16.24"
         y="15.45"
         width="0.56999999"
         height="0.56999999"
         id="rect48" />
      <rect
         x="17.93"
         y="15.45"
         width="0.56999999"
         height="0.56999999"
         id="rect49" />
      <rect
         x="15.67"
         y="16.02"
         width="0.56999999"
         height="0.56999999"
         id="rect50" />
      <rect
         x="16.799999"
         y="16.02"
         width="0.56999999"
         height="0.56999999"
         id="rect51" />
      <rect
         x="17.93"
         y="16.02"
         width="0.56999999"
         height="0.56999999"
         id="rect52" />
      <rect
         x="15.67"
         y="16.58"
         width="0.56999999"
         height="0.56999999"
         id="rect53" />
      <rect
         x="17.370001"
         y="16.58"
         width="0.56999999"
         height="0.56999999"
         id="rect54" />
      <rect
         x="17.93"
         y="16.58"
         width="0.56999999"
         height="0.56999999"
         id="rect55" />
      <rect
         x="15.67"
         y="17.15"
         width="0.56999999"
         height="0.56999999"
         id="rect56" />
      <rect
         x="17.93"
         y="17.15"
         width="0.56999999"
         height="0.56999999"
         id="rect57" />
      <rect
         x="15.67"
         y="17.709999"
         width="0.56999999"
         height="0.56999999"
         id="rect58" />
      <rect
         x="17.93"
         y="17.709999"
         width="0.56999999"
         height="0.56999999"
         id="rect59" />
    </g>
  </mask>
  <path
     d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
     fill="currentColor"
     mask="url(#ft-json)"
     id="path59"
     transform="translate(-4,-2)" />
</svg>`,"objects/file-lnk":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-4.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg42"
   sodipodi:docname="file-lnk.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs42" />
  <mask
     id="ft-lnk">
    <path
       d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
       fill="#ffffff"
       id="path1" />
    <g
       fill="#000000"
       id="g42">
      <rect
         x="5.5"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect1" />
      <rect
         x="5.5"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect2" />
      <rect
         x="5.5"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect3" />
      <rect
         x="5.5"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect4" />
      <rect
         x="5.5"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect5" />
      <rect
         x="5.5"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect6" />
      <rect
         x="5.5"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect7" />
      <rect
         x="6.2600002"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect8" />
      <rect
         x="7.0300002"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect9" />
      <rect
         x="7.79"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect10" />
      <rect
         x="8.5600004"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect11" />
      <rect
         x="10.09"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect12" />
      <rect
         x="13.15"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect13" />
      <rect
         x="10.09"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect14" />
      <rect
         x="13.15"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect15" />
      <rect
         x="10.09"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect16" />
      <rect
         x="10.85"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect17" />
      <rect
         x="13.15"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect18" />
      <rect
         x="10.09"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect19" />
      <rect
         x="11.62"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect20" />
      <rect
         x="13.15"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect21" />
      <rect
         x="10.09"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect22" />
      <rect
         x="12.38"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect23" />
      <rect
         x="13.15"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect24" />
      <rect
         x="10.09"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect25" />
      <rect
         x="13.15"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect26" />
      <rect
         x="10.09"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect27" />
      <rect
         x="13.15"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect28" />
      <rect
         x="14.68"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect29" />
      <rect
         x="17.74"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect30" />
      <rect
         x="14.68"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect31" />
      <rect
         x="16.969999"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect32" />
      <rect
         x="14.68"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect33" />
      <rect
         x="16.209999"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect34" />
      <rect
         x="14.68"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect35" />
      <rect
         x="15.44"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect36" />
      <rect
         x="14.68"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect37" />
      <rect
         x="16.209999"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect38" />
      <rect
         x="14.68"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect39" />
      <rect
         x="16.969999"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect40" />
      <rect
         x="14.68"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect41" />
      <rect
         x="17.74"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect42" />
    </g>
  </mask>
  <path
     d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
     fill="currentColor"
     mask="url(#ft-lnk)"
     id="path42"
     transform="translate(-4,-2)" />
</svg>`,"objects/file-mp3":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-4.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg48"
   sodipodi:docname="file-mp3.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs48" />
  <mask
     id="ft-mp3">
    <path
       d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
       fill="#ffffff"
       id="path1" />
    <g
       fill="#000000"
       id="g48">
      <rect
         x="5.5"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect1" />
      <rect
         x="8.5600004"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect2" />
      <rect
         x="5.5"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect3" />
      <rect
         x="6.2600002"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect4" />
      <rect
         x="7.79"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect5" />
      <rect
         x="8.5600004"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect6" />
      <rect
         x="5.5"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect7" />
      <rect
         x="7.0300002"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect8" />
      <rect
         x="8.5600004"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect9" />
      <rect
         x="5.5"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect10" />
      <rect
         x="7.0300002"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect11" />
      <rect
         x="8.5600004"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect12" />
      <rect
         x="5.5"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect13" />
      <rect
         x="8.5600004"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect14" />
      <rect
         x="5.5"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect15" />
      <rect
         x="8.5600004"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect16" />
      <rect
         x="5.5"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect17" />
      <rect
         x="8.5600004"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect18" />
      <rect
         x="10.09"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect19" />
      <rect
         x="10.85"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect20" />
      <rect
         x="11.62"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect21" />
      <rect
         x="12.38"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect22" />
      <rect
         x="10.09"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect23" />
      <rect
         x="13.15"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect24" />
      <rect
         x="10.09"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect25" />
      <rect
         x="13.15"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect26" />
      <rect
         x="10.09"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect27" />
      <rect
         x="10.85"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect28" />
      <rect
         x="11.62"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect29" />
      <rect
         x="12.38"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect30" />
      <rect
         x="10.09"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect31" />
      <rect
         x="10.09"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect32" />
      <rect
         x="10.09"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect33" />
      <rect
         x="14.68"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect34" />
      <rect
         x="15.44"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect35" />
      <rect
         x="16.209999"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect36" />
      <rect
         x="16.969999"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect37" />
      <rect
         x="17.74"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect38" />
      <rect
         x="17.74"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect39" />
      <rect
         x="15.44"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect40" />
      <rect
         x="16.209999"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect41" />
      <rect
         x="16.969999"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect42" />
      <rect
         x="17.74"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect43" />
      <rect
         x="17.74"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect44" />
      <rect
         x="14.68"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect45" />
      <rect
         x="15.44"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect46" />
      <rect
         x="16.209999"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect47" />
      <rect
         x="16.969999"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect48" />
    </g>
  </mask>
  <path
     d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
     fill="currentColor"
     mask="url(#ft-mp3)"
     id="path48"
     transform="translate(-4,-2)" />
</svg>`,"objects/file-mp4":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-4.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg47"
   sodipodi:docname="file-mp4.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs47" />
  <mask
     id="ft-mp4">
    <path
       d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
       fill="#ffffff"
       id="path1" />
    <g
       fill="#000000"
       id="g47">
      <rect
         x="5.5"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect1" />
      <rect
         x="8.5600004"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect2" />
      <rect
         x="5.5"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect3" />
      <rect
         x="6.2600002"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect4" />
      <rect
         x="7.79"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect5" />
      <rect
         x="8.5600004"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect6" />
      <rect
         x="5.5"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect7" />
      <rect
         x="7.0300002"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect8" />
      <rect
         x="8.5600004"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect9" />
      <rect
         x="5.5"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect10" />
      <rect
         x="7.0300002"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect11" />
      <rect
         x="8.5600004"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect12" />
      <rect
         x="5.5"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect13" />
      <rect
         x="8.5600004"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect14" />
      <rect
         x="5.5"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect15" />
      <rect
         x="8.5600004"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect16" />
      <rect
         x="5.5"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect17" />
      <rect
         x="8.5600004"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect18" />
      <rect
         x="10.09"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect19" />
      <rect
         x="10.85"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect20" />
      <rect
         x="11.62"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect21" />
      <rect
         x="12.38"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect22" />
      <rect
         x="10.09"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect23" />
      <rect
         x="13.15"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect24" />
      <rect
         x="10.09"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect25" />
      <rect
         x="13.15"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect26" />
      <rect
         x="10.09"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect27" />
      <rect
         x="10.85"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect28" />
      <rect
         x="11.62"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect29" />
      <rect
         x="12.38"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect30" />
      <rect
         x="10.09"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect31" />
      <rect
         x="10.09"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect32" />
      <rect
         x="10.09"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect33" />
      <rect
         x="16.969999"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect34" />
      <rect
         x="16.209999"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect35" />
      <rect
         x="16.969999"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect36" />
      <rect
         x="15.44"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect37" />
      <rect
         x="16.969999"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect38" />
      <rect
         x="14.68"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect39" />
      <rect
         x="16.969999"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect40" />
      <rect
         x="14.68"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect41" />
      <rect
         x="15.44"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect42" />
      <rect
         x="16.209999"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect43" />
      <rect
         x="16.969999"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect44" />
      <rect
         x="17.74"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect45" />
      <rect
         x="16.969999"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect46" />
      <rect
         x="16.969999"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect47" />
    </g>
  </mask>
  <path
     d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
     fill="currentColor"
     mask="url(#ft-mp4)"
     id="path47"
     transform="translate(-4,-2)" />
</svg>`,"objects/file-msg":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-4.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg50"
   sodipodi:docname="file-msg.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs50" />
  <mask
     id="ft-msg">
    <path
       d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
       fill="#ffffff"
       id="path1" />
    <g
       fill="#000000"
       id="g50">
      <rect
         x="5.5"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect1" />
      <rect
         x="8.5600004"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect2" />
      <rect
         x="5.5"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect3" />
      <rect
         x="6.2600002"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect4" />
      <rect
         x="7.79"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect5" />
      <rect
         x="8.5600004"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect6" />
      <rect
         x="5.5"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect7" />
      <rect
         x="7.0300002"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect8" />
      <rect
         x="8.5600004"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect9" />
      <rect
         x="5.5"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect10" />
      <rect
         x="7.0300002"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect11" />
      <rect
         x="8.5600004"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect12" />
      <rect
         x="5.5"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect13" />
      <rect
         x="8.5600004"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect14" />
      <rect
         x="5.5"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect15" />
      <rect
         x="8.5600004"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect16" />
      <rect
         x="5.5"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect17" />
      <rect
         x="8.5600004"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect18" />
      <rect
         x="10.85"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect19" />
      <rect
         x="11.62"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect20" />
      <rect
         x="12.38"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect21" />
      <rect
         x="13.15"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect22" />
      <rect
         x="10.09"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect23" />
      <rect
         x="10.09"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect24" />
      <rect
         x="10.85"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect25" />
      <rect
         x="11.62"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect26" />
      <rect
         x="12.38"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect27" />
      <rect
         x="13.15"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect28" />
      <rect
         x="13.15"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect29" />
      <rect
         x="10.09"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect30" />
      <rect
         x="10.85"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect31" />
      <rect
         x="11.62"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect32" />
      <rect
         x="12.38"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect33" />
      <rect
         x="15.44"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect34" />
      <rect
         x="16.209999"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect35" />
      <rect
         x="16.969999"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect36" />
      <rect
         x="14.68"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect37" />
      <rect
         x="17.74"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect38" />
      <rect
         x="14.68"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect39" />
      <rect
         x="14.68"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect40" />
      <rect
         x="16.209999"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect41" />
      <rect
         x="16.969999"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect42" />
      <rect
         x="17.74"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect43" />
      <rect
         x="14.68"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect44" />
      <rect
         x="17.74"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect45" />
      <rect
         x="14.68"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect46" />
      <rect
         x="17.74"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect47" />
      <rect
         x="15.44"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect48" />
      <rect
         x="16.209999"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect49" />
      <rect
         x="16.969999"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect50" />
    </g>
  </mask>
  <path
     d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
     fill="currentColor"
     mask="url(#ft-msg)"
     id="path50"
     transform="translate(-4,-2)" />
</svg>`,"objects/file-pcap":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-4.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg61"
   sodipodi:docname="file-pcap.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs61" />
  <mask
     id="ft-pcap">
    <path
       d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
       fill="#ffffff"
       id="path1" />
    <g
       fill="#000000"
       id="g61">
      <rect
         x="5.5"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect1" />
      <rect
         x="6.0700002"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect2" />
      <rect
         x="6.6300001"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect3" />
      <rect
         x="7.1999998"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect4" />
      <rect
         x="5.5"
         y="14.89"
         width="0.56999999"
         height="0.56999999"
         id="rect5" />
      <rect
         x="7.7600002"
         y="14.89"
         width="0.56999999"
         height="0.56999999"
         id="rect6" />
      <rect
         x="5.5"
         y="15.45"
         width="0.56999999"
         height="0.56999999"
         id="rect7" />
      <rect
         x="7.7600002"
         y="15.45"
         width="0.56999999"
         height="0.56999999"
         id="rect8" />
      <rect
         x="5.5"
         y="16.02"
         width="0.56999999"
         height="0.56999999"
         id="rect9" />
      <rect
         x="6.0700002"
         y="16.02"
         width="0.56999999"
         height="0.56999999"
         id="rect10" />
      <rect
         x="6.6300001"
         y="16.02"
         width="0.56999999"
         height="0.56999999"
         id="rect11" />
      <rect
         x="7.1999998"
         y="16.02"
         width="0.56999999"
         height="0.56999999"
         id="rect12" />
      <rect
         x="5.5"
         y="16.58"
         width="0.56999999"
         height="0.56999999"
         id="rect13" />
      <rect
         x="5.5"
         y="17.15"
         width="0.56999999"
         height="0.56999999"
         id="rect14" />
      <rect
         x="5.5"
         y="17.709999"
         width="0.56999999"
         height="0.56999999"
         id="rect15" />
      <rect
         x="9.46"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect16" />
      <rect
         x="10.02"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect17" />
      <rect
         x="10.59"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect18" />
      <rect
         x="8.8900003"
         y="14.89"
         width="0.56999999"
         height="0.56999999"
         id="rect19" />
      <rect
         x="11.15"
         y="14.89"
         width="0.56999999"
         height="0.56999999"
         id="rect20" />
      <rect
         x="8.8900003"
         y="15.45"
         width="0.56999999"
         height="0.56999999"
         id="rect21" />
      <rect
         x="8.8900003"
         y="16.02"
         width="0.56999999"
         height="0.56999999"
         id="rect22" />
      <rect
         x="8.8900003"
         y="16.58"
         width="0.56999999"
         height="0.56999999"
         id="rect23" />
      <rect
         x="8.8900003"
         y="17.15"
         width="0.56999999"
         height="0.56999999"
         id="rect24" />
      <rect
         x="11.15"
         y="17.15"
         width="0.56999999"
         height="0.56999999"
         id="rect25" />
      <rect
         x="9.46"
         y="17.709999"
         width="0.56999999"
         height="0.56999999"
         id="rect26" />
      <rect
         x="10.02"
         y="17.709999"
         width="0.56999999"
         height="0.56999999"
         id="rect27" />
      <rect
         x="10.59"
         y="17.709999"
         width="0.56999999"
         height="0.56999999"
         id="rect28" />
      <rect
         x="12.85"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect29" />
      <rect
         x="13.41"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect30" />
      <rect
         x="13.98"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect31" />
      <rect
         x="12.28"
         y="14.89"
         width="0.56999999"
         height="0.56999999"
         id="rect32" />
      <rect
         x="14.54"
         y="14.89"
         width="0.56999999"
         height="0.56999999"
         id="rect33" />
      <rect
         x="12.28"
         y="15.45"
         width="0.56999999"
         height="0.56999999"
         id="rect34" />
      <rect
         x="14.54"
         y="15.45"
         width="0.56999999"
         height="0.56999999"
         id="rect35" />
      <rect
         x="12.28"
         y="16.02"
         width="0.56999999"
         height="0.56999999"
         id="rect36" />
      <rect
         x="12.85"
         y="16.02"
         width="0.56999999"
         height="0.56999999"
         id="rect37" />
      <rect
         x="13.41"
         y="16.02"
         width="0.56999999"
         height="0.56999999"
         id="rect38" />
      <rect
         x="13.98"
         y="16.02"
         width="0.56999999"
         height="0.56999999"
         id="rect39" />
      <rect
         x="14.54"
         y="16.02"
         width="0.56999999"
         height="0.56999999"
         id="rect40" />
      <rect
         x="12.28"
         y="16.58"
         width="0.56999999"
         height="0.56999999"
         id="rect41" />
      <rect
         x="14.54"
         y="16.58"
         width="0.56999999"
         height="0.56999999"
         id="rect42" />
      <rect
         x="12.28"
         y="17.15"
         width="0.56999999"
         height="0.56999999"
         id="rect43" />
      <rect
         x="14.54"
         y="17.15"
         width="0.56999999"
         height="0.56999999"
         id="rect44" />
      <rect
         x="12.28"
         y="17.709999"
         width="0.56999999"
         height="0.56999999"
         id="rect45" />
      <rect
         x="14.54"
         y="17.709999"
         width="0.56999999"
         height="0.56999999"
         id="rect46" />
      <rect
         x="15.67"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect47" />
      <rect
         x="16.24"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect48" />
      <rect
         x="16.799999"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect49" />
      <rect
         x="17.370001"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect50" />
      <rect
         x="15.67"
         y="14.89"
         width="0.56999999"
         height="0.56999999"
         id="rect51" />
      <rect
         x="17.93"
         y="14.89"
         width="0.56999999"
         height="0.56999999"
         id="rect52" />
      <rect
         x="15.67"
         y="15.45"
         width="0.56999999"
         height="0.56999999"
         id="rect53" />
      <rect
         x="17.93"
         y="15.45"
         width="0.56999999"
         height="0.56999999"
         id="rect54" />
      <rect
         x="15.67"
         y="16.02"
         width="0.56999999"
         height="0.56999999"
         id="rect55" />
      <rect
         x="16.24"
         y="16.02"
         width="0.56999999"
         height="0.56999999"
         id="rect56" />
      <rect
         x="16.799999"
         y="16.02"
         width="0.56999999"
         height="0.56999999"
         id="rect57" />
      <rect
         x="17.370001"
         y="16.02"
         width="0.56999999"
         height="0.56999999"
         id="rect58" />
      <rect
         x="15.67"
         y="16.58"
         width="0.56999999"
         height="0.56999999"
         id="rect59" />
      <rect
         x="15.67"
         y="17.15"
         width="0.56999999"
         height="0.56999999"
         id="rect60" />
      <rect
         x="15.67"
         y="17.709999"
         width="0.56999999"
         height="0.56999999"
         id="rect61" />
    </g>
  </mask>
  <path
     d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
     fill="currentColor"
     mask="url(#ft-pcap)"
     id="path61"
     transform="translate(-4,-2)" />
</svg>`,"objects/file-pdf":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-4.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg47"
   sodipodi:docname="file-pdf.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs47" />
  <mask
     id="ft-pdf">
    <path
       d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
       fill="#ffffff"
       id="path1" />
    <g
       fill="#000000"
       id="g47">
      <rect
         x="5.5"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect1" />
      <rect
         x="6.2600002"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect2" />
      <rect
         x="7.0300002"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect3" />
      <rect
         x="7.79"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect4" />
      <rect
         x="5.5"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect5" />
      <rect
         x="8.5600004"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect6" />
      <rect
         x="5.5"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect7" />
      <rect
         x="8.5600004"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect8" />
      <rect
         x="5.5"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect9" />
      <rect
         x="6.2600002"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect10" />
      <rect
         x="7.0300002"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect11" />
      <rect
         x="7.79"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect12" />
      <rect
         x="5.5"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect13" />
      <rect
         x="5.5"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect14" />
      <rect
         x="5.5"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect15" />
      <rect
         x="10.09"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect16" />
      <rect
         x="10.85"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect17" />
      <rect
         x="11.62"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect18" />
      <rect
         x="12.38"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect19" />
      <rect
         x="10.09"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect20" />
      <rect
         x="13.15"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect21" />
      <rect
         x="10.09"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect22" />
      <rect
         x="13.15"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect23" />
      <rect
         x="10.09"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect24" />
      <rect
         x="13.15"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect25" />
      <rect
         x="10.09"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect26" />
      <rect
         x="13.15"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect27" />
      <rect
         x="10.09"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect28" />
      <rect
         x="13.15"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect29" />
      <rect
         x="10.09"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect30" />
      <rect
         x="10.85"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect31" />
      <rect
         x="11.62"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect32" />
      <rect
         x="12.38"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect33" />
      <rect
         x="14.68"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect34" />
      <rect
         x="15.44"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect35" />
      <rect
         x="16.209999"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect36" />
      <rect
         x="16.969999"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect37" />
      <rect
         x="17.74"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect38" />
      <rect
         x="14.68"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect39" />
      <rect
         x="14.68"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect40" />
      <rect
         x="14.68"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect41" />
      <rect
         x="15.44"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect42" />
      <rect
         x="16.209999"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect43" />
      <rect
         x="16.969999"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect44" />
      <rect
         x="14.68"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect45" />
      <rect
         x="14.68"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect46" />
      <rect
         x="14.68"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect47" />
    </g>
  </mask>
  <path
     d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
     fill="currentColor"
     mask="url(#ft-pdf)"
     id="path47"
     transform="translate(-4,-2)" />
</svg>`,"objects/file-png":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-4.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg49"
   sodipodi:docname="file-png.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs49" />
  <mask
     id="ft-png">
    <path
       d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
       fill="#ffffff"
       id="path1" />
    <g
       fill="#000000"
       id="g49">
      <rect
         x="5.5"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect1" />
      <rect
         x="6.2600002"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect2" />
      <rect
         x="7.0300002"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect3" />
      <rect
         x="7.79"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect4" />
      <rect
         x="5.5"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect5" />
      <rect
         x="8.5600004"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect6" />
      <rect
         x="5.5"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect7" />
      <rect
         x="8.5600004"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect8" />
      <rect
         x="5.5"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect9" />
      <rect
         x="6.2600002"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect10" />
      <rect
         x="7.0300002"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect11" />
      <rect
         x="7.79"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect12" />
      <rect
         x="5.5"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect13" />
      <rect
         x="5.5"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect14" />
      <rect
         x="5.5"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect15" />
      <rect
         x="10.09"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect16" />
      <rect
         x="13.15"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect17" />
      <rect
         x="10.09"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect18" />
      <rect
         x="13.15"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect19" />
      <rect
         x="10.09"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect20" />
      <rect
         x="10.85"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect21" />
      <rect
         x="13.15"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect22" />
      <rect
         x="10.09"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect23" />
      <rect
         x="11.62"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect24" />
      <rect
         x="13.15"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect25" />
      <rect
         x="10.09"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect26" />
      <rect
         x="12.38"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect27" />
      <rect
         x="13.15"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect28" />
      <rect
         x="10.09"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect29" />
      <rect
         x="13.15"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect30" />
      <rect
         x="10.09"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect31" />
      <rect
         x="13.15"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect32" />
      <rect
         x="15.44"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect33" />
      <rect
         x="16.209999"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect34" />
      <rect
         x="16.969999"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect35" />
      <rect
         x="14.68"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect36" />
      <rect
         x="17.74"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect37" />
      <rect
         x="14.68"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect38" />
      <rect
         x="14.68"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect39" />
      <rect
         x="16.209999"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect40" />
      <rect
         x="16.969999"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect41" />
      <rect
         x="17.74"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect42" />
      <rect
         x="14.68"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect43" />
      <rect
         x="17.74"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect44" />
      <rect
         x="14.68"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect45" />
      <rect
         x="17.74"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect46" />
      <rect
         x="15.44"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect47" />
      <rect
         x="16.209999"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect48" />
      <rect
         x="16.969999"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect49" />
    </g>
  </mask>
  <path
     d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
     fill="currentColor"
     mask="url(#ft-png)"
     id="path49"
     transform="translate(-4,-2)" />
</svg>`,"objects/file-ppt":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-4.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg41"
   sodipodi:docname="file-ppt.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs41" />
  <mask
     id="ft-ppt">
    <path
       d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
       fill="#ffffff"
       id="path1" />
    <g
       fill="#000000"
       id="g41">
      <rect
         x="5.5"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect1" />
      <rect
         x="6.2600002"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect2" />
      <rect
         x="7.0300002"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect3" />
      <rect
         x="7.79"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect4" />
      <rect
         x="5.5"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect5" />
      <rect
         x="8.5600004"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect6" />
      <rect
         x="5.5"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect7" />
      <rect
         x="8.5600004"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect8" />
      <rect
         x="5.5"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect9" />
      <rect
         x="6.2600002"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect10" />
      <rect
         x="7.0300002"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect11" />
      <rect
         x="7.79"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect12" />
      <rect
         x="5.5"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect13" />
      <rect
         x="5.5"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect14" />
      <rect
         x="5.5"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect15" />
      <rect
         x="10.09"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect16" />
      <rect
         x="10.85"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect17" />
      <rect
         x="11.62"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect18" />
      <rect
         x="12.38"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect19" />
      <rect
         x="10.09"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect20" />
      <rect
         x="13.15"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect21" />
      <rect
         x="10.09"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect22" />
      <rect
         x="13.15"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect23" />
      <rect
         x="10.09"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect24" />
      <rect
         x="10.85"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect25" />
      <rect
         x="11.62"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect26" />
      <rect
         x="12.38"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect27" />
      <rect
         x="10.09"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect28" />
      <rect
         x="10.09"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect29" />
      <rect
         x="10.09"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect30" />
      <rect
         x="14.68"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect31" />
      <rect
         x="15.44"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect32" />
      <rect
         x="16.209999"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect33" />
      <rect
         x="16.969999"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect34" />
      <rect
         x="17.74"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect35" />
      <rect
         x="16.209999"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect36" />
      <rect
         x="16.209999"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect37" />
      <rect
         x="16.209999"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect38" />
      <rect
         x="16.209999"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect39" />
      <rect
         x="16.209999"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect40" />
      <rect
         x="16.209999"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect41" />
    </g>
  </mask>
  <path
     d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
     fill="currentColor"
     mask="url(#ft-ppt)"
     id="path41"
     transform="translate(-4,-2)" />
</svg>`,"objects/file-pptx":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-4.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg54"
   sodipodi:docname="file-pptx.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs54" />
  <mask
     id="ft-pptx">
    <path
       d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
       fill="#ffffff"
       id="path1" />
    <g
       fill="#000000"
       id="g54">
      <rect
         x="5.5"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect1" />
      <rect
         x="6.0700002"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect2" />
      <rect
         x="6.6300001"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect3" />
      <rect
         x="7.1999998"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect4" />
      <rect
         x="5.5"
         y="14.89"
         width="0.56999999"
         height="0.56999999"
         id="rect5" />
      <rect
         x="7.7600002"
         y="14.89"
         width="0.56999999"
         height="0.56999999"
         id="rect6" />
      <rect
         x="5.5"
         y="15.45"
         width="0.56999999"
         height="0.56999999"
         id="rect7" />
      <rect
         x="7.7600002"
         y="15.45"
         width="0.56999999"
         height="0.56999999"
         id="rect8" />
      <rect
         x="5.5"
         y="16.02"
         width="0.56999999"
         height="0.56999999"
         id="rect9" />
      <rect
         x="6.0700002"
         y="16.02"
         width="0.56999999"
         height="0.56999999"
         id="rect10" />
      <rect
         x="6.6300001"
         y="16.02"
         width="0.56999999"
         height="0.56999999"
         id="rect11" />
      <rect
         x="7.1999998"
         y="16.02"
         width="0.56999999"
         height="0.56999999"
         id="rect12" />
      <rect
         x="5.5"
         y="16.58"
         width="0.56999999"
         height="0.56999999"
         id="rect13" />
      <rect
         x="5.5"
         y="17.15"
         width="0.56999999"
         height="0.56999999"
         id="rect14" />
      <rect
         x="5.5"
         y="17.709999"
         width="0.56999999"
         height="0.56999999"
         id="rect15" />
      <rect
         x="8.8900003"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect16" />
      <rect
         x="9.46"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect17" />
      <rect
         x="10.02"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect18" />
      <rect
         x="10.59"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect19" />
      <rect
         x="8.8900003"
         y="14.89"
         width="0.56999999"
         height="0.56999999"
         id="rect20" />
      <rect
         x="11.15"
         y="14.89"
         width="0.56999999"
         height="0.56999999"
         id="rect21" />
      <rect
         x="8.8900003"
         y="15.45"
         width="0.56999999"
         height="0.56999999"
         id="rect22" />
      <rect
         x="11.15"
         y="15.45"
         width="0.56999999"
         height="0.56999999"
         id="rect23" />
      <rect
         x="8.8900003"
         y="16.02"
         width="0.56999999"
         height="0.56999999"
         id="rect24" />
      <rect
         x="9.46"
         y="16.02"
         width="0.56999999"
         height="0.56999999"
         id="rect25" />
      <rect
         x="10.02"
         y="16.02"
         width="0.56999999"
         height="0.56999999"
         id="rect26" />
      <rect
         x="10.59"
         y="16.02"
         width="0.56999999"
         height="0.56999999"
         id="rect27" />
      <rect
         x="8.8900003"
         y="16.58"
         width="0.56999999"
         height="0.56999999"
         id="rect28" />
      <rect
         x="8.8900003"
         y="17.15"
         width="0.56999999"
         height="0.56999999"
         id="rect29" />
      <rect
         x="8.8900003"
         y="17.709999"
         width="0.56999999"
         height="0.56999999"
         id="rect30" />
      <rect
         x="12.28"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect31" />
      <rect
         x="12.85"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect32" />
      <rect
         x="13.41"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect33" />
      <rect
         x="13.98"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect34" />
      <rect
         x="14.54"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect35" />
      <rect
         x="13.41"
         y="14.89"
         width="0.56999999"
         height="0.56999999"
         id="rect36" />
      <rect
         x="13.41"
         y="15.45"
         width="0.56999999"
         height="0.56999999"
         id="rect37" />
      <rect
         x="13.41"
         y="16.02"
         width="0.56999999"
         height="0.56999999"
         id="rect38" />
      <rect
         x="13.41"
         y="16.58"
         width="0.56999999"
         height="0.56999999"
         id="rect39" />
      <rect
         x="13.41"
         y="17.15"
         width="0.56999999"
         height="0.56999999"
         id="rect40" />
      <rect
         x="13.41"
         y="17.709999"
         width="0.56999999"
         height="0.56999999"
         id="rect41" />
      <rect
         x="15.67"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect42" />
      <rect
         x="17.93"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect43" />
      <rect
         x="15.67"
         y="14.89"
         width="0.56999999"
         height="0.56999999"
         id="rect44" />
      <rect
         x="17.93"
         y="14.89"
         width="0.56999999"
         height="0.56999999"
         id="rect45" />
      <rect
         x="16.24"
         y="15.45"
         width="0.56999999"
         height="0.56999999"
         id="rect46" />
      <rect
         x="17.370001"
         y="15.45"
         width="0.56999999"
         height="0.56999999"
         id="rect47" />
      <rect
         x="16.799999"
         y="16.02"
         width="0.56999999"
         height="0.56999999"
         id="rect48" />
      <rect
         x="16.24"
         y="16.58"
         width="0.56999999"
         height="0.56999999"
         id="rect49" />
      <rect
         x="17.370001"
         y="16.58"
         width="0.56999999"
         height="0.56999999"
         id="rect50" />
      <rect
         x="15.67"
         y="17.15"
         width="0.56999999"
         height="0.56999999"
         id="rect51" />
      <rect
         x="17.93"
         y="17.15"
         width="0.56999999"
         height="0.56999999"
         id="rect52" />
      <rect
         x="15.67"
         y="17.709999"
         width="0.56999999"
         height="0.56999999"
         id="rect53" />
      <rect
         x="17.93"
         y="17.709999"
         width="0.56999999"
         height="0.56999999"
         id="rect54" />
    </g>
  </mask>
  <path
     d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
     fill="currentColor"
     mask="url(#ft-pptx)"
     id="path54"
     transform="translate(-4,-2)" />
</svg>`,"objects/file-ps1":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-4.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg40"
   sodipodi:docname="file-ps1.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs40" />
  <mask
     id="ft-ps1">
    <path
       d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
       fill="#ffffff"
       id="path1" />
    <g
       fill="#000000"
       id="g40">
      <rect
         x="5.5"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect1" />
      <rect
         x="6.2600002"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect2" />
      <rect
         x="7.0300002"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect3" />
      <rect
         x="7.79"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect4" />
      <rect
         x="5.5"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect5" />
      <rect
         x="8.5600004"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect6" />
      <rect
         x="5.5"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect7" />
      <rect
         x="8.5600004"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect8" />
      <rect
         x="5.5"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect9" />
      <rect
         x="6.2600002"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect10" />
      <rect
         x="7.0300002"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect11" />
      <rect
         x="7.79"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect12" />
      <rect
         x="5.5"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect13" />
      <rect
         x="5.5"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect14" />
      <rect
         x="5.5"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect15" />
      <rect
         x="10.85"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect16" />
      <rect
         x="11.62"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect17" />
      <rect
         x="12.38"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect18" />
      <rect
         x="13.15"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect19" />
      <rect
         x="10.09"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect20" />
      <rect
         x="10.09"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect21" />
      <rect
         x="10.85"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect22" />
      <rect
         x="11.62"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect23" />
      <rect
         x="12.38"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect24" />
      <rect
         x="13.15"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect25" />
      <rect
         x="13.15"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect26" />
      <rect
         x="10.09"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect27" />
      <rect
         x="10.85"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect28" />
      <rect
         x="11.62"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect29" />
      <rect
         x="12.38"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect30" />
      <rect
         x="16.209999"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect31" />
      <rect
         x="15.44"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect32" />
      <rect
         x="16.209999"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect33" />
      <rect
         x="16.209999"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect34" />
      <rect
         x="16.209999"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect35" />
      <rect
         x="16.209999"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect36" />
      <rect
         x="16.209999"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect37" />
      <rect
         x="15.44"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect38" />
      <rect
         x="16.209999"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect39" />
      <rect
         x="16.969999"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect40" />
    </g>
  </mask>
  <path
     d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
     fill="currentColor"
     mask="url(#ft-ps1)"
     id="path40"
     transform="translate(-4,-2)" />
</svg>`,"objects/file-py":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-4.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg25"
   sodipodi:docname="file-py.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs25" />
  <mask
     id="ft-py">
    <path
       d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
       fill="#ffffff"
       id="path1" />
    <g
       fill="#000000"
       id="g25">
      <rect
         x="5.71"
         y="12.3"
         width="1.14"
         height="1.14"
         id="rect1" />
      <rect
         x="6.8600001"
         y="12.3"
         width="1.14"
         height="1.14"
         id="rect2" />
      <rect
         x="8"
         y="12.3"
         width="1.14"
         height="1.14"
         id="rect3" />
      <rect
         x="9.1400003"
         y="12.3"
         width="1.14"
         height="1.14"
         id="rect4" />
      <rect
         x="5.71"
         y="13.44"
         width="1.14"
         height="1.14"
         id="rect5" />
      <rect
         x="10.29"
         y="13.44"
         width="1.14"
         height="1.14"
         id="rect6" />
      <rect
         x="5.71"
         y="14.59"
         width="1.14"
         height="1.14"
         id="rect7" />
      <rect
         x="10.29"
         y="14.59"
         width="1.14"
         height="1.14"
         id="rect8" />
      <rect
         x="5.71"
         y="15.73"
         width="1.14"
         height="1.14"
         id="rect9" />
      <rect
         x="6.8600001"
         y="15.73"
         width="1.14"
         height="1.14"
         id="rect10" />
      <rect
         x="8"
         y="15.73"
         width="1.14"
         height="1.14"
         id="rect11" />
      <rect
         x="9.1400003"
         y="15.73"
         width="1.14"
         height="1.14"
         id="rect12" />
      <rect
         x="5.71"
         y="16.870001"
         width="1.14"
         height="1.14"
         id="rect13" />
      <rect
         x="5.71"
         y="18.01"
         width="1.14"
         height="1.14"
         id="rect14" />
      <rect
         x="5.71"
         y="19.16"
         width="1.14"
         height="1.14"
         id="rect15" />
      <rect
         x="12.57"
         y="12.3"
         width="1.14"
         height="1.14"
         id="rect16" />
      <rect
         x="17.139999"
         y="12.3"
         width="1.14"
         height="1.14"
         id="rect17" />
      <rect
         x="12.57"
         y="13.44"
         width="1.14"
         height="1.14"
         id="rect18" />
      <rect
         x="17.139999"
         y="13.44"
         width="1.14"
         height="1.14"
         id="rect19" />
      <rect
         x="13.71"
         y="14.59"
         width="1.14"
         height="1.14"
         id="rect20" />
      <rect
         x="16"
         y="14.59"
         width="1.14"
         height="1.14"
         id="rect21" />
      <rect
         x="14.86"
         y="15.73"
         width="1.14"
         height="1.14"
         id="rect22" />
      <rect
         x="14.86"
         y="16.870001"
         width="1.14"
         height="1.14"
         id="rect23" />
      <rect
         x="14.86"
         y="18.01"
         width="1.14"
         height="1.14"
         id="rect24" />
      <rect
         x="14.86"
         y="19.16"
         width="1.14"
         height="1.14"
         id="rect25" />
    </g>
  </mask>
  <path
     d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
     fill="currentColor"
     mask="url(#ft-py)"
     id="path25"
     transform="translate(-4,-2)" />
</svg>`,"objects/file-rar":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-4.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg54"
   sodipodi:docname="file-rar.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs54" />
  <mask
     id="ft-rar">
    <path
       d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
       fill="#ffffff"
       id="path1" />
    <g
       fill="#000000"
       id="g54">
      <rect
         x="5.5"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect1" />
      <rect
         x="6.2600002"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect2" />
      <rect
         x="7.0300002"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect3" />
      <rect
         x="7.79"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect4" />
      <rect
         x="5.5"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect5" />
      <rect
         x="8.5600004"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect6" />
      <rect
         x="5.5"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect7" />
      <rect
         x="8.5600004"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect8" />
      <rect
         x="5.5"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect9" />
      <rect
         x="6.2600002"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect10" />
      <rect
         x="7.0300002"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect11" />
      <rect
         x="7.79"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect12" />
      <rect
         x="5.5"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect13" />
      <rect
         x="7.0300002"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect14" />
      <rect
         x="5.5"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect15" />
      <rect
         x="7.79"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect16" />
      <rect
         x="5.5"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect17" />
      <rect
         x="8.5600004"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect18" />
      <rect
         x="10.85"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect19" />
      <rect
         x="11.62"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect20" />
      <rect
         x="12.38"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect21" />
      <rect
         x="10.09"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect22" />
      <rect
         x="13.15"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect23" />
      <rect
         x="10.09"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect24" />
      <rect
         x="13.15"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect25" />
      <rect
         x="10.09"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect26" />
      <rect
         x="10.85"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect27" />
      <rect
         x="11.62"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect28" />
      <rect
         x="12.38"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect29" />
      <rect
         x="13.15"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect30" />
      <rect
         x="10.09"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect31" />
      <rect
         x="13.15"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect32" />
      <rect
         x="10.09"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect33" />
      <rect
         x="13.15"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect34" />
      <rect
         x="10.09"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect35" />
      <rect
         x="13.15"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect36" />
      <rect
         x="14.68"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect37" />
      <rect
         x="15.44"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect38" />
      <rect
         x="16.209999"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect39" />
      <rect
         x="16.969999"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect40" />
      <rect
         x="14.68"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect41" />
      <rect
         x="17.74"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect42" />
      <rect
         x="14.68"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect43" />
      <rect
         x="17.74"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect44" />
      <rect
         x="14.68"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect45" />
      <rect
         x="15.44"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect46" />
      <rect
         x="16.209999"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect47" />
      <rect
         x="16.969999"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect48" />
      <rect
         x="14.68"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect49" />
      <rect
         x="16.209999"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect50" />
      <rect
         x="14.68"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect51" />
      <rect
         x="16.969999"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect52" />
      <rect
         x="14.68"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect53" />
      <rect
         x="17.74"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect54" />
    </g>
  </mask>
  <path
     d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
     fill="currentColor"
     mask="url(#ft-rar)"
     id="path54"
     transform="translate(-4,-2)" />
</svg>`,"objects/file-rtf":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-4.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg43"
   sodipodi:docname="file-rtf.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs43" />
  <mask
     id="ft-rtf">
    <path
       d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
       fill="#ffffff"
       id="path1" />
    <g
       fill="#000000"
       id="g43">
      <rect
         x="5.5"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect1" />
      <rect
         x="6.2600002"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect2" />
      <rect
         x="7.0300002"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect3" />
      <rect
         x="7.79"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect4" />
      <rect
         x="5.5"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect5" />
      <rect
         x="8.5600004"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect6" />
      <rect
         x="5.5"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect7" />
      <rect
         x="8.5600004"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect8" />
      <rect
         x="5.5"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect9" />
      <rect
         x="6.2600002"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect10" />
      <rect
         x="7.0300002"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect11" />
      <rect
         x="7.79"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect12" />
      <rect
         x="5.5"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect13" />
      <rect
         x="7.0300002"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect14" />
      <rect
         x="5.5"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect15" />
      <rect
         x="7.79"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect16" />
      <rect
         x="5.5"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect17" />
      <rect
         x="8.5600004"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect18" />
      <rect
         x="10.09"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect19" />
      <rect
         x="10.85"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect20" />
      <rect
         x="11.62"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect21" />
      <rect
         x="12.38"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect22" />
      <rect
         x="13.15"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect23" />
      <rect
         x="11.62"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect24" />
      <rect
         x="11.62"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect25" />
      <rect
         x="11.62"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect26" />
      <rect
         x="11.62"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect27" />
      <rect
         x="11.62"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect28" />
      <rect
         x="11.62"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect29" />
      <rect
         x="14.68"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect30" />
      <rect
         x="15.44"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect31" />
      <rect
         x="16.209999"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect32" />
      <rect
         x="16.969999"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect33" />
      <rect
         x="17.74"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect34" />
      <rect
         x="14.68"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect35" />
      <rect
         x="14.68"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect36" />
      <rect
         x="14.68"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect37" />
      <rect
         x="15.44"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect38" />
      <rect
         x="16.209999"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect39" />
      <rect
         x="16.969999"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect40" />
      <rect
         x="14.68"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect41" />
      <rect
         x="14.68"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect42" />
      <rect
         x="14.68"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect43" />
    </g>
  </mask>
  <path
     d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
     fill="currentColor"
     mask="url(#ft-rtf)"
     id="path43"
     transform="translate(-4,-2)" />
</svg>`,"objects/file-sh":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-4.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg32"
   sodipodi:docname="file-sh.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs32" />
  <mask
     id="ft-sh">
    <path
       d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
       fill="#ffffff"
       id="path1" />
    <g
       fill="#000000"
       id="g32">
      <rect
         x="6.8600001"
         y="12.3"
         width="1.14"
         height="1.14"
         id="rect1" />
      <rect
         x="8"
         y="12.3"
         width="1.14"
         height="1.14"
         id="rect2" />
      <rect
         x="9.1400003"
         y="12.3"
         width="1.14"
         height="1.14"
         id="rect3" />
      <rect
         x="10.29"
         y="12.3"
         width="1.14"
         height="1.14"
         id="rect4" />
      <rect
         x="5.71"
         y="13.44"
         width="1.14"
         height="1.14"
         id="rect5" />
      <rect
         x="5.71"
         y="14.59"
         width="1.14"
         height="1.14"
         id="rect6" />
      <rect
         x="6.8600001"
         y="15.73"
         width="1.14"
         height="1.14"
         id="rect7" />
      <rect
         x="8"
         y="15.73"
         width="1.14"
         height="1.14"
         id="rect8" />
      <rect
         x="9.1400003"
         y="15.73"
         width="1.14"
         height="1.14"
         id="rect9" />
      <rect
         x="10.29"
         y="16.870001"
         width="1.14"
         height="1.14"
         id="rect10" />
      <rect
         x="10.29"
         y="18.01"
         width="1.14"
         height="1.14"
         id="rect11" />
      <rect
         x="5.71"
         y="19.16"
         width="1.14"
         height="1.14"
         id="rect12" />
      <rect
         x="6.8600001"
         y="19.16"
         width="1.14"
         height="1.14"
         id="rect13" />
      <rect
         x="8"
         y="19.16"
         width="1.14"
         height="1.14"
         id="rect14" />
      <rect
         x="9.1400003"
         y="19.16"
         width="1.14"
         height="1.14"
         id="rect15" />
      <rect
         x="12.57"
         y="12.3"
         width="1.14"
         height="1.14"
         id="rect16" />
      <rect
         x="17.139999"
         y="12.3"
         width="1.14"
         height="1.14"
         id="rect17" />
      <rect
         x="12.57"
         y="13.44"
         width="1.14"
         height="1.14"
         id="rect18" />
      <rect
         x="17.139999"
         y="13.44"
         width="1.14"
         height="1.14"
         id="rect19" />
      <rect
         x="12.57"
         y="14.59"
         width="1.14"
         height="1.14"
         id="rect20" />
      <rect
         x="17.139999"
         y="14.59"
         width="1.14"
         height="1.14"
         id="rect21" />
      <rect
         x="12.57"
         y="15.73"
         width="1.14"
         height="1.14"
         id="rect22" />
      <rect
         x="13.71"
         y="15.73"
         width="1.14"
         height="1.14"
         id="rect23" />
      <rect
         x="14.86"
         y="15.73"
         width="1.14"
         height="1.14"
         id="rect24" />
      <rect
         x="16"
         y="15.73"
         width="1.14"
         height="1.14"
         id="rect25" />
      <rect
         x="17.139999"
         y="15.73"
         width="1.14"
         height="1.14"
         id="rect26" />
      <rect
         x="12.57"
         y="16.870001"
         width="1.14"
         height="1.14"
         id="rect27" />
      <rect
         x="17.139999"
         y="16.870001"
         width="1.14"
         height="1.14"
         id="rect28" />
      <rect
         x="12.57"
         y="18.01"
         width="1.14"
         height="1.14"
         id="rect29" />
      <rect
         x="17.139999"
         y="18.01"
         width="1.14"
         height="1.14"
         id="rect30" />
      <rect
         x="12.57"
         y="19.16"
         width="1.14"
         height="1.14"
         id="rect31" />
      <rect
         x="17.139999"
         y="19.16"
         width="1.14"
         height="1.14"
         id="rect32" />
    </g>
  </mask>
  <path
     d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
     fill="currentColor"
     mask="url(#ft-sh)"
     id="path32"
     transform="translate(-4,-2)" />
</svg>`,"objects/file-svg":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-4.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg45"
   sodipodi:docname="file-svg.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs45" />
  <mask
     id="ft-svg">
    <path
       d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
       fill="#ffffff"
       id="path1" />
    <g
       fill="#000000"
       id="g45">
      <rect
         x="6.2600002"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect1" />
      <rect
         x="7.0300002"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect2" />
      <rect
         x="7.79"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect3" />
      <rect
         x="8.5600004"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect4" />
      <rect
         x="5.5"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect5" />
      <rect
         x="5.5"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect6" />
      <rect
         x="6.2600002"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect7" />
      <rect
         x="7.0300002"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect8" />
      <rect
         x="7.79"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect9" />
      <rect
         x="8.5600004"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect10" />
      <rect
         x="8.5600004"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect11" />
      <rect
         x="5.5"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect12" />
      <rect
         x="6.2600002"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect13" />
      <rect
         x="7.0300002"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect14" />
      <rect
         x="7.79"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect15" />
      <rect
         x="10.09"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect16" />
      <rect
         x="13.15"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect17" />
      <rect
         x="10.09"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect18" />
      <rect
         x="13.15"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect19" />
      <rect
         x="10.09"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect20" />
      <rect
         x="13.15"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect21" />
      <rect
         x="10.09"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect22" />
      <rect
         x="13.15"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect23" />
      <rect
         x="10.85"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect24" />
      <rect
         x="12.38"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect25" />
      <rect
         x="10.85"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect26" />
      <rect
         x="12.38"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect27" />
      <rect
         x="11.62"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect28" />
      <rect
         x="15.44"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect29" />
      <rect
         x="16.209999"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect30" />
      <rect
         x="16.969999"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect31" />
      <rect
         x="14.68"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect32" />
      <rect
         x="17.74"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect33" />
      <rect
         x="14.68"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect34" />
      <rect
         x="14.68"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect35" />
      <rect
         x="16.209999"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect36" />
      <rect
         x="16.969999"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect37" />
      <rect
         x="17.74"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect38" />
      <rect
         x="14.68"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect39" />
      <rect
         x="17.74"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect40" />
      <rect
         x="14.68"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect41" />
      <rect
         x="17.74"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect42" />
      <rect
         x="15.44"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect43" />
      <rect
         x="16.209999"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect44" />
      <rect
         x="16.969999"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect45" />
    </g>
  </mask>
  <path
     d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
     fill="currentColor"
     mask="url(#ft-svg)"
     id="path45"
     transform="translate(-4,-2)" />
</svg>`,"objects/file-txt":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-4.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg35"
   sodipodi:docname="file-txt.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs35" />
  <mask
     id="ft-txt">
    <path
       d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
       fill="#ffffff"
       id="path1" />
    <g
       fill="#000000"
       id="g35">
      <rect
         x="5.5"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect1" />
      <rect
         x="6.2600002"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect2" />
      <rect
         x="7.0300002"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect3" />
      <rect
         x="7.79"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect4" />
      <rect
         x="8.5600004"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect5" />
      <rect
         x="7.0300002"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect6" />
      <rect
         x="7.0300002"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect7" />
      <rect
         x="7.0300002"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect8" />
      <rect
         x="7.0300002"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect9" />
      <rect
         x="7.0300002"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect10" />
      <rect
         x="7.0300002"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect11" />
      <rect
         x="10.09"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect12" />
      <rect
         x="13.15"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect13" />
      <rect
         x="10.09"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect14" />
      <rect
         x="13.15"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect15" />
      <rect
         x="10.85"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect16" />
      <rect
         x="12.38"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect17" />
      <rect
         x="11.62"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect18" />
      <rect
         x="10.85"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect19" />
      <rect
         x="12.38"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect20" />
      <rect
         x="10.09"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect21" />
      <rect
         x="13.15"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect22" />
      <rect
         x="10.09"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect23" />
      <rect
         x="13.15"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect24" />
      <rect
         x="14.68"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect25" />
      <rect
         x="15.44"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect26" />
      <rect
         x="16.209999"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect27" />
      <rect
         x="16.969999"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect28" />
      <rect
         x="17.74"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect29" />
      <rect
         x="16.209999"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect30" />
      <rect
         x="16.209999"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect31" />
      <rect
         x="16.209999"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect32" />
      <rect
         x="16.209999"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect33" />
      <rect
         x="16.209999"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect34" />
      <rect
         x="16.209999"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect35" />
    </g>
  </mask>
  <path
     d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
     fill="currentColor"
     mask="url(#ft-txt)"
     id="path35"
     transform="translate(-4,-2)" />
</svg>`,"objects/file-vbs":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-4.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg48"
   sodipodi:docname="file-vbs.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs48" />
  <mask
     id="ft-vbs">
    <path
       d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
       fill="#ffffff"
       id="path1" />
    <g
       fill="#000000"
       id="g48">
      <rect
         x="5.5"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect1" />
      <rect
         x="8.5600004"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect2" />
      <rect
         x="5.5"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect3" />
      <rect
         x="8.5600004"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect4" />
      <rect
         x="5.5"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect5" />
      <rect
         x="8.5600004"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect6" />
      <rect
         x="5.5"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect7" />
      <rect
         x="8.5600004"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect8" />
      <rect
         x="6.2600002"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect9" />
      <rect
         x="7.79"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect10" />
      <rect
         x="6.2600002"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect11" />
      <rect
         x="7.79"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect12" />
      <rect
         x="7.0300002"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect13" />
      <rect
         x="10.09"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect14" />
      <rect
         x="10.85"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect15" />
      <rect
         x="11.62"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect16" />
      <rect
         x="12.38"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect17" />
      <rect
         x="10.09"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect18" />
      <rect
         x="13.15"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect19" />
      <rect
         x="10.09"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect20" />
      <rect
         x="13.15"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect21" />
      <rect
         x="10.09"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect22" />
      <rect
         x="10.85"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect23" />
      <rect
         x="11.62"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect24" />
      <rect
         x="12.38"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect25" />
      <rect
         x="10.09"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect26" />
      <rect
         x="13.15"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect27" />
      <rect
         x="10.09"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect28" />
      <rect
         x="13.15"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect29" />
      <rect
         x="10.09"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect30" />
      <rect
         x="10.85"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect31" />
      <rect
         x="11.62"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect32" />
      <rect
         x="12.38"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect33" />
      <rect
         x="15.44"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect34" />
      <rect
         x="16.209999"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect35" />
      <rect
         x="16.969999"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect36" />
      <rect
         x="17.74"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect37" />
      <rect
         x="14.68"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect38" />
      <rect
         x="14.68"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect39" />
      <rect
         x="15.44"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect40" />
      <rect
         x="16.209999"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect41" />
      <rect
         x="16.969999"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect42" />
      <rect
         x="17.74"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect43" />
      <rect
         x="17.74"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect44" />
      <rect
         x="14.68"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect45" />
      <rect
         x="15.44"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect46" />
      <rect
         x="16.209999"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect47" />
      <rect
         x="16.969999"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect48" />
    </g>
  </mask>
  <path
     d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
     fill="currentColor"
     mask="url(#ft-vbs)"
     id="path48"
     transform="translate(-4,-2)" />
</svg>`,"objects/file-xls":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-4.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg39"
   sodipodi:docname="file-xls.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs39" />
  <mask
     id="ft-xls">
    <path
       d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
       fill="#ffffff"
       id="path1" />
    <g
       fill="#000000"
       id="g39">
      <rect
         x="5.5"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect1" />
      <rect
         x="8.5600004"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect2" />
      <rect
         x="5.5"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect3" />
      <rect
         x="8.5600004"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect4" />
      <rect
         x="6.2600002"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect5" />
      <rect
         x="7.79"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect6" />
      <rect
         x="7.0300002"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect7" />
      <rect
         x="6.2600002"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect8" />
      <rect
         x="7.79"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect9" />
      <rect
         x="5.5"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect10" />
      <rect
         x="8.5600004"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect11" />
      <rect
         x="5.5"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect12" />
      <rect
         x="8.5600004"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect13" />
      <rect
         x="10.09"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect14" />
      <rect
         x="10.09"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect15" />
      <rect
         x="10.09"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect16" />
      <rect
         x="10.09"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect17" />
      <rect
         x="10.09"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect18" />
      <rect
         x="10.09"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect19" />
      <rect
         x="10.09"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect20" />
      <rect
         x="10.85"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect21" />
      <rect
         x="11.62"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect22" />
      <rect
         x="12.38"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect23" />
      <rect
         x="13.15"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect24" />
      <rect
         x="15.44"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect25" />
      <rect
         x="16.209999"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect26" />
      <rect
         x="16.969999"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect27" />
      <rect
         x="17.74"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect28" />
      <rect
         x="14.68"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect29" />
      <rect
         x="14.68"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect30" />
      <rect
         x="15.44"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect31" />
      <rect
         x="16.209999"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect32" />
      <rect
         x="16.969999"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect33" />
      <rect
         x="17.74"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect34" />
      <rect
         x="17.74"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect35" />
      <rect
         x="14.68"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect36" />
      <rect
         x="15.44"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect37" />
      <rect
         x="16.209999"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect38" />
      <rect
         x="16.969999"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect39" />
    </g>
  </mask>
  <path
     d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
     fill="currentColor"
     mask="url(#ft-xls)"
     id="path39"
     transform="translate(-4,-2)" />
</svg>`,"objects/file-xlsx":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-4.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg52"
   sodipodi:docname="file-xlsx.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs52" />
  <mask
     id="ft-xlsx">
    <path
       d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
       fill="#ffffff"
       id="path1" />
    <g
       fill="#000000"
       id="g52">
      <rect
         x="5.5"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect1" />
      <rect
         x="7.7600002"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect2" />
      <rect
         x="5.5"
         y="14.89"
         width="0.56999999"
         height="0.56999999"
         id="rect3" />
      <rect
         x="7.7600002"
         y="14.89"
         width="0.56999999"
         height="0.56999999"
         id="rect4" />
      <rect
         x="6.0700002"
         y="15.45"
         width="0.56999999"
         height="0.56999999"
         id="rect5" />
      <rect
         x="7.1999998"
         y="15.45"
         width="0.56999999"
         height="0.56999999"
         id="rect6" />
      <rect
         x="6.6300001"
         y="16.02"
         width="0.56999999"
         height="0.56999999"
         id="rect7" />
      <rect
         x="6.0700002"
         y="16.58"
         width="0.56999999"
         height="0.56999999"
         id="rect8" />
      <rect
         x="7.1999998"
         y="16.58"
         width="0.56999999"
         height="0.56999999"
         id="rect9" />
      <rect
         x="5.5"
         y="17.15"
         width="0.56999999"
         height="0.56999999"
         id="rect10" />
      <rect
         x="7.7600002"
         y="17.15"
         width="0.56999999"
         height="0.56999999"
         id="rect11" />
      <rect
         x="5.5"
         y="17.709999"
         width="0.56999999"
         height="0.56999999"
         id="rect12" />
      <rect
         x="7.7600002"
         y="17.709999"
         width="0.56999999"
         height="0.56999999"
         id="rect13" />
      <rect
         x="8.8900003"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect14" />
      <rect
         x="8.8900003"
         y="14.89"
         width="0.56999999"
         height="0.56999999"
         id="rect15" />
      <rect
         x="8.8900003"
         y="15.45"
         width="0.56999999"
         height="0.56999999"
         id="rect16" />
      <rect
         x="8.8900003"
         y="16.02"
         width="0.56999999"
         height="0.56999999"
         id="rect17" />
      <rect
         x="8.8900003"
         y="16.58"
         width="0.56999999"
         height="0.56999999"
         id="rect18" />
      <rect
         x="8.8900003"
         y="17.15"
         width="0.56999999"
         height="0.56999999"
         id="rect19" />
      <rect
         x="8.8900003"
         y="17.709999"
         width="0.56999999"
         height="0.56999999"
         id="rect20" />
      <rect
         x="9.46"
         y="17.709999"
         width="0.56999999"
         height="0.56999999"
         id="rect21" />
      <rect
         x="10.02"
         y="17.709999"
         width="0.56999999"
         height="0.56999999"
         id="rect22" />
      <rect
         x="10.59"
         y="17.709999"
         width="0.56999999"
         height="0.56999999"
         id="rect23" />
      <rect
         x="11.15"
         y="17.709999"
         width="0.56999999"
         height="0.56999999"
         id="rect24" />
      <rect
         x="12.85"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect25" />
      <rect
         x="13.41"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect26" />
      <rect
         x="13.98"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect27" />
      <rect
         x="14.54"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect28" />
      <rect
         x="12.28"
         y="14.89"
         width="0.56999999"
         height="0.56999999"
         id="rect29" />
      <rect
         x="12.28"
         y="15.45"
         width="0.56999999"
         height="0.56999999"
         id="rect30" />
      <rect
         x="12.85"
         y="16.02"
         width="0.56999999"
         height="0.56999999"
         id="rect31" />
      <rect
         x="13.41"
         y="16.02"
         width="0.56999999"
         height="0.56999999"
         id="rect32" />
      <rect
         x="13.98"
         y="16.02"
         width="0.56999999"
         height="0.56999999"
         id="rect33" />
      <rect
         x="14.54"
         y="16.58"
         width="0.56999999"
         height="0.56999999"
         id="rect34" />
      <rect
         x="14.54"
         y="17.15"
         width="0.56999999"
         height="0.56999999"
         id="rect35" />
      <rect
         x="12.28"
         y="17.709999"
         width="0.56999999"
         height="0.56999999"
         id="rect36" />
      <rect
         x="12.85"
         y="17.709999"
         width="0.56999999"
         height="0.56999999"
         id="rect37" />
      <rect
         x="13.41"
         y="17.709999"
         width="0.56999999"
         height="0.56999999"
         id="rect38" />
      <rect
         x="13.98"
         y="17.709999"
         width="0.56999999"
         height="0.56999999"
         id="rect39" />
      <rect
         x="15.67"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect40" />
      <rect
         x="17.93"
         y="14.32"
         width="0.56999999"
         height="0.56999999"
         id="rect41" />
      <rect
         x="15.67"
         y="14.89"
         width="0.56999999"
         height="0.56999999"
         id="rect42" />
      <rect
         x="17.93"
         y="14.89"
         width="0.56999999"
         height="0.56999999"
         id="rect43" />
      <rect
         x="16.24"
         y="15.45"
         width="0.56999999"
         height="0.56999999"
         id="rect44" />
      <rect
         x="17.370001"
         y="15.45"
         width="0.56999999"
         height="0.56999999"
         id="rect45" />
      <rect
         x="16.799999"
         y="16.02"
         width="0.56999999"
         height="0.56999999"
         id="rect46" />
      <rect
         x="16.24"
         y="16.58"
         width="0.56999999"
         height="0.56999999"
         id="rect47" />
      <rect
         x="17.370001"
         y="16.58"
         width="0.56999999"
         height="0.56999999"
         id="rect48" />
      <rect
         x="15.67"
         y="17.15"
         width="0.56999999"
         height="0.56999999"
         id="rect49" />
      <rect
         x="17.93"
         y="17.15"
         width="0.56999999"
         height="0.56999999"
         id="rect50" />
      <rect
         x="15.67"
         y="17.709999"
         width="0.56999999"
         height="0.56999999"
         id="rect51" />
      <rect
         x="17.93"
         y="17.709999"
         width="0.56999999"
         height="0.56999999"
         id="rect52" />
    </g>
  </mask>
  <path
     d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
     fill="currentColor"
     mask="url(#ft-xlsx)"
     id="path52"
     transform="translate(-4,-2)" />
</svg>`,"objects/file-xml":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-4.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg42"
   sodipodi:docname="file-xml.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs42" />
  <mask
     id="ft-xml">
    <path
       d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
       fill="#ffffff"
       id="path1" />
    <g
       fill="#000000"
       id="g42">
      <rect
         x="5.5"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect1" />
      <rect
         x="8.5600004"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect2" />
      <rect
         x="5.5"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect3" />
      <rect
         x="8.5600004"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect4" />
      <rect
         x="6.2600002"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect5" />
      <rect
         x="7.79"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect6" />
      <rect
         x="7.0300002"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect7" />
      <rect
         x="6.2600002"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect8" />
      <rect
         x="7.79"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect9" />
      <rect
         x="5.5"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect10" />
      <rect
         x="8.5600004"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect11" />
      <rect
         x="5.5"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect12" />
      <rect
         x="8.5600004"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect13" />
      <rect
         x="10.09"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect14" />
      <rect
         x="13.15"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect15" />
      <rect
         x="10.09"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect16" />
      <rect
         x="10.85"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect17" />
      <rect
         x="12.38"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect18" />
      <rect
         x="13.15"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect19" />
      <rect
         x="10.09"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect20" />
      <rect
         x="11.62"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect21" />
      <rect
         x="13.15"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect22" />
      <rect
         x="10.09"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect23" />
      <rect
         x="11.62"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect24" />
      <rect
         x="13.15"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect25" />
      <rect
         x="10.09"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect26" />
      <rect
         x="13.15"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect27" />
      <rect
         x="10.09"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect28" />
      <rect
         x="13.15"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect29" />
      <rect
         x="10.09"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect30" />
      <rect
         x="13.15"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect31" />
      <rect
         x="14.68"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect32" />
      <rect
         x="14.68"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect33" />
      <rect
         x="14.68"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect34" />
      <rect
         x="14.68"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect35" />
      <rect
         x="14.68"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect36" />
      <rect
         x="14.68"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect37" />
      <rect
         x="14.68"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect38" />
      <rect
         x="15.44"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect39" />
      <rect
         x="16.209999"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect40" />
      <rect
         x="16.969999"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect41" />
      <rect
         x="17.74"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect42" />
    </g>
  </mask>
  <path
     d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
     fill="currentColor"
     mask="url(#ft-xml)"
     id="path42"
     transform="translate(-4,-2)" />
</svg>`,"objects/file-zip":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-4.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg41"
   sodipodi:docname="file-zip.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs41" />
  <mask
     id="ft-zip">
    <path
       d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
       fill="#ffffff"
       id="path1" />
    <g
       fill="#000000"
       id="g41">
      <rect
         x="5.5"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect1" />
      <rect
         x="6.2600002"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect2" />
      <rect
         x="7.0300002"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect3" />
      <rect
         x="7.79"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect4" />
      <rect
         x="8.5600004"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect5" />
      <rect
         x="8.5600004"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect6" />
      <rect
         x="7.79"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect7" />
      <rect
         x="7.0300002"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect8" />
      <rect
         x="6.2600002"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect9" />
      <rect
         x="5.5"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect10" />
      <rect
         x="5.5"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect11" />
      <rect
         x="6.2600002"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect12" />
      <rect
         x="7.0300002"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect13" />
      <rect
         x="7.79"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect14" />
      <rect
         x="8.5600004"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect15" />
      <rect
         x="10.85"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect16" />
      <rect
         x="11.62"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect17" />
      <rect
         x="12.38"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect18" />
      <rect
         x="11.62"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect19" />
      <rect
         x="11.62"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect20" />
      <rect
         x="11.62"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect21" />
      <rect
         x="11.62"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect22" />
      <rect
         x="11.62"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect23" />
      <rect
         x="10.85"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect24" />
      <rect
         x="11.62"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect25" />
      <rect
         x="12.38"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect26" />
      <rect
         x="14.68"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect27" />
      <rect
         x="15.44"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect28" />
      <rect
         x="16.209999"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect29" />
      <rect
         x="16.969999"
         y="13.62"
         width="0.75999999"
         height="0.75999999"
         id="rect30" />
      <rect
         x="14.68"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect31" />
      <rect
         x="17.74"
         y="14.39"
         width="0.75999999"
         height="0.75999999"
         id="rect32" />
      <rect
         x="14.68"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect33" />
      <rect
         x="17.74"
         y="15.15"
         width="0.75999999"
         height="0.75999999"
         id="rect34" />
      <rect
         x="14.68"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect35" />
      <rect
         x="15.44"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect36" />
      <rect
         x="16.209999"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect37" />
      <rect
         x="16.969999"
         y="15.92"
         width="0.75999999"
         height="0.75999999"
         id="rect38" />
      <rect
         x="14.68"
         y="16.68"
         width="0.75999999"
         height="0.75999999"
         id="rect39" />
      <rect
         x="14.68"
         y="17.450001"
         width="0.75999999"
         height="0.75999999"
         id="rect40" />
      <rect
         x="14.68"
         y="18.209999"
         width="0.75999999"
         height="0.75999999"
         id="rect41" />
    </g>
  </mask>
  <path
     d="M 13,9 V 3.5 L 18.5,9 M 6,2 C 4.89,2 4,2.89 4,4 v 16 a 2,2 0 0 0 2,2 h 12 a 2,2 0 0 0 2,-2 V 8 L 14,2 Z"
     fill="currentColor"
     mask="url(#ft-zip)"
     id="path41"
     transform="translate(-4,-2)" />
</svg>`,"objects/file":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-13.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="file.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 0,7 V 1.5 L 5.5,7 M -7,0 c -1.11,0 -2,0.89 -2,2 v 16 a 2,2 0 0 0 2,2 H 5 A 2,2 0 0 0 7,18 V 6 L 1,0 Z"
     id="path1" />
</svg>`,"objects/forensic-case":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-129.0000 0.0000 270.0000 216.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="forensic-case.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 94.49,59.52 -56,-56 A 12,12 0 0 0 30,0 h -96 a 20,20 0 0 0 -20,20 v 176 a 20,20 0 0 0 20,20 H 78 A 20,20 0 0 0 98,196 V 68 A 12,12 0 0 0 94.49,59.52 M 61,60 H 38 V 37 Z M -62,192 V 24 h 76 v 48 a 12,12 0 0 0 12,12 h 48 v 108 z m 96.48,-48.49 a 36,36 0 1 0 -17,17 l 12,12 a 12.020815,12.020815 0 0 0 17,-17 z M -10,128 a 12,12 0 1 1 12,12 12,12 0 0 1 -12,-12"
     id="path1" />
</svg>`,"objects/forensic-evidence":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-129.0000 0.0000 270.0000 216.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="forensic-evidence.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 94.49,59.52 -56,-56 A 12,12 0 0 0 30,0 h -96 a 20,20 0 0 0 -20,20 v 176 a 20,20 0 0 0 20,20 H 78 A 20,20 0 0 0 98,196 V 68 A 12,12 0 0 0 94.49,59.52 M 61,60 H 38 V 37 Z M -62,192 V 24 h 76 v 48 a 12,12 0 0 0 12,12 h 48 v 108 z m 96.48,-48.49 a 36,36 0 1 0 -17,17 l 12,12 a 12.020815,12.020815 0 0 0 17,-17 z M -10,128 a 12,12 0 1 1 12,12 12,12 0 0 1 -12,-12"
     id="path1" />
</svg>`,"objects/forged-document":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-129.0000 0.0000 270.0000 216.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="forged-document.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 94.49,59.52 -56,-56 A 12,12 0 0 0 30,0 h -96 a 20,20 0 0 0 -20,20 v 176 a 20,20 0 0 0 20,20 H 78 A 20,20 0 0 0 98,196 V 68 A 12,12 0 0 0 94.49,59.52 M 61,60 H 38 V 37 Z M -62,192 V 24 h 76 v 48 a 12,12 0 0 0 12,12 h 48 v 108 z m 96.48,-48.49 a 36,36 0 1 0 -17,17 l 12,12 a 12.020815,12.020815 0 0 0 17,-17 z M -10,128 a 12,12 0 1 1 12,12 12,12 0 0 1 -12,-12"
     id="path1" />
</svg>`,"objects/geojson":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-54.7464 0.0000 125.0002 100.0002"
   version="1.1"
   id="svg2"
   sodipodi:docname="geojson.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs2" />
  <path
     fill="currentColor"
     d="M -22.5016,1.8341494e-4 A 2.5,2.5 0 0 0 -25.0016,2.5001834 V 70.000183 h -11.496 v 22 h 11.496 v 5.5 a 2.5,2.5 0 0 0 2.5,2.499997 h 72 a 2.5,2.5 0 0 0 2.5,-2.499997 v -75.875 c 0.027,-1.113 0.004,-1.777 -0.732,-2.59 L 32.9624,0.73218341 A 2.5,2.5 0 0 0 31.1644,1.8341494e-4 Z m 2.5,4.99999998506 h 48.902 l 1.252,14.5679996 a 2.5,2.5 0 0 0 2.278,2.278 l 14.568,1.252 v 71.902 h -67 v -3 h 63.504 v -22 h -63.504 z m 54.275,4.115 8.61,8.6099996 -7.928,-0.682 z m -60.291,63.8849996 q 2.055,0 3.207,1.137 1.158,1.127 1.49,3.125 l -2.213,0.543 q -0.234,-1.067 -0.881,-1.68 -0.64,-0.623 -1.603,-0.623 -1.46,0 -2.325,1.217 -0.859,1.215 -0.86,3.607 0,2.581 0.874,3.877 0.874,1.285 2.289,1.285 0.7,0 1.398,-0.355 a 4.7,4.7 0 0 0 1.213,-0.881 v -1.838 h -2.55 v -2.443 h 4.8 v 5.775 q -0.7,0.89 -2.03,1.572 -1.326,0.673 -2.688,0.672 -1.731,0 -3.018,-0.949 -1.287,-0.96 -1.936,-2.728 -0.647,-1.781 -0.647,-3.868 0,-2.264 0.723,-4.023 0.722,-1.76 2.115,-2.7 1.06,-0.721 2.64,-0.722 m 37.33,0 q 2.076,0 3.123,1.197 1.053,1.197 1.105,3.194 l -2.226,0.129 q -0.144,-1.119 -0.618,-1.604 -0.466,-0.494 -1.408,-0.494 -0.97,0 -1.52,0.525 -0.353,0.335 -0.353,0.899 0,0.514 0.33,0.88 0.421,0.465 2.047,0.97 1.626,0.505 2.402,1.048 0.782,0.534 1.22,1.473 0.443,0.93 0.443,2.304 0,1.245 -0.526,2.333 -0.527,1.088 -1.49,1.623 -0.964,0.523 -2.402,0.523 -2.093,0 -3.213,-1.266 -1.122,-1.274 -1.34,-3.707 l 2.168,-0.277 q 0.194,1.433 0.789,2.105 0.602,0.673 1.619,0.672 1.075,0 1.617,-0.591 0.55,-0.604 0.551,-1.405 0,-0.515 -0.234,-0.87 -0.225,-0.367 -0.797,-0.634 -0.391,-0.178 -1.783,-0.632 -1.792,-0.584 -2.514,-1.434 -1.017,-1.197 -1.018,-2.916 a 4.6,4.6 0 0 1 0.475,-2.066 3.36,3.36 0 0 1 1.377,-1.475 q 0.904,-0.504 2.177,-0.504 m 11.318,0 q 2.439,0 3.898,1.988 1.47,1.988 1.47,5.528 -10e-4,3.508 -1.454,5.496 -1.452,1.977 -3.883,1.978 -2.461,0 -3.914,-1.969 -1.453,-1.977 -1.453,-5.437 0,-2.216 0.504,-3.719 0.376,-1.107 1.023,-1.986 0.656,-0.88 1.432,-1.305 1.03,-0.574 2.377,-0.574 m -19.777,0.248 h 2.218 v 9.176 q 0,1.799 -0.24,2.767 -0.324,1.266 -1.174,2.038 -0.85,0.76 -2.242,0.761 -1.633,0 -2.514,-1.197 -0.88,-1.206 -0.888,-3.53 l 2.1,-0.316 q 0.037,1.245 0.279,1.76 0.36,0.78 1.097,0.781 0.746,0 1.055,-0.552 0.309,-0.564 0.309,-2.325 z m 26.898,0 h 2.166 l 4.516,9.68 v -9.68 h 2.07 v 14.494 h -2.234 l -4.45,-9.451 v 9.451 h -2.068 z m -7.098,2.254 q -1.377,0 -2.22,1.246 -0.843,1.236 -0.842,3.736 0,2.463 0.865,3.739 0.866,1.265 2.197,1.265 1.332,0 2.182,-1.256 0.859,-1.265 0.86,-3.787 0,-2.491 -0.837,-3.716 -0.826,-1.227 -2.205,-1.227 m -38.752,1.502 q 1.785,0 2.815,1.553 1.03,1.542 0.986,4.736 h -5.299 q 0.023,1.236 0.512,1.928 0.489,0.683 1.219,0.683 0.497,0 0.836,-0.357 0.338,-0.356 0.512,-1.147 l 2.107,0.465 q -0.407,1.523 -1.287,2.324 -0.873,0.791 -2.19,0.791 -2.084,0.001 -3.086,-1.789 -0.79,-1.433 -0.79,-3.619 0,-2.61 1.038,-4.084 1.04,-1.484 2.627,-1.484 m 9.159,0 q 1.815,0 2.974,1.553 1.159,1.542 1.158,3.906 0,2.383 -1.173,3.955 -1.168,1.562 -2.944,1.562 -1.098,0 -2.1,-0.652 -0.992,-0.652 -1.511,-1.908 -0.52,-1.266 -0.52,-3.076 0,-1.384 0.52,-2.68 0.519,-1.294 1.467,-1.977 a 3.58,3.58 0 0 1 2.129,-0.683 m -9.032,2.127 q -0.691,0 -1.142,0.662 -0.452,0.662 -0.445,1.799 h 3.162 q -0.023,-1.206 -0.475,-1.828 -0.452,-0.633 -1.1,-0.633 m 9.04,0.139 q -0.828,0 -1.393,0.83 -0.565,0.83 -0.565,2.392 0,1.562 0.565,2.393 0.565,0.831 1.392,0.832 0.828,-0.001 1.385,-0.832 0.565,-0.831 0.565,-2.412 0,-1.543 -0.565,-2.373 -0.557,-0.83 -1.385,-0.83"
     color="currentColor"
     id="path1" />
  <path
     fill="currentColor"
     d="m 14.7544,18.000183 v 10.11 h 8.852 a 25.6,25.6 0 0 0 -1.707,-3.881 c -1.985,-3.606 -4.507,-5.78 -7.145,-6.229 m -2.504,0.1 c -2.469,0.613 -4.813,2.735 -6.682,6.13 a 25.6,25.6 0 0 0 -1.706,3.881 h 8.388 z m -5.769,0.678 a 22.55,22.55 0 0 0 -12.005,9.333 h 6.739 c 0.594,-1.851 1.318,-3.562 2.16,-5.089 0.897,-1.63 1.942,-3.067 3.106,-4.244 m 14.729,0.231 c 1.074,1.134 2.044,2.488 2.883,4.013 0.841,1.527 1.564,3.238 2.157,5.089 h 6.278 a 22.56,22.56 0 0 0 -11.318,-9.102 m -28.113,11.606 a 22.4,22.4 0 0 0 -2.095,8.329 h 8.408 c 0.097,-2.941 0.48,-5.744 1.103,-8.329 z m 10.004,0 c -0.662,2.542 -1.078,5.357 -1.184,8.329 h 10.333 v -8.329 z m 11.653,0 v 8.329 h 10.797 c -0.106,-2.972 -0.523,-5.787 -1.184,-8.329 z m 12.197,0 a 41.5,41.5 0 0 1 1.1,8.329 h 7.951 a 22.4,22.4 0 0 0 -2.095,-8.329 z m -35.949,10.832 a 22.4,22.4 0 0 0 2.095,8.329 h 7.298 c -0.588,-2.593 -0.934,-5.396 -0.999,-8.329 z m 10.898,0 c 0.07,2.962 0.452,5.774 1.075,8.329 h 9.275 v -8.329 z m 12.854,0 v 8.329 h 9.738 c 0.624,-2.555 1.005,-5.367 1.075,-8.329 z m 13.31,0 c -0.065,2.932 -0.409,5.736 -0.995,8.329 h 6.838 a 22.4,22.4 0 0 0 2.095,-8.329 z m -33.589,10.833 a 22.57,22.57 0 0 0 11.33,9.105 20,20 0 0 1 -2.432,-3.514 c -0.917,-1.666 -1.697,-3.546 -2.319,-5.591 z m 9.212,0 c 0.532,1.61 1.165,3.084 1.88,4.383 1.753,3.182 3.923,5.246 6.222,5.997 0.154,0.01 0.306,0.03 0.46,0.03 v -10.415 z m 11.066,0 v 10.415 c 0.357,-0.02 0.713,-0.04 1.065,-0.08 2.247,-0.789 4.364,-2.834 6.08,-5.951 0.716,-1.299 1.349,-2.773 1.88,-4.383 z m 11.656,0 c -0.62,2.045 -1.4,3.926 -2.317,5.591 a 20.4,20.4 0 0 1 -2.197,3.243 22.57,22.57 0 0 0 10.632,-8.834 z"
     color="currentColor"
     id="path2" />
</svg>`,"objects/geolocation":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-14.9994 0.0000 19.9995 15.9996"
   version="1.1"
   id="svg1"
   sodipodi:docname="geolocation.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     fill-rule="evenodd"
     d="m -8.9996,3.999627 a 4,4 0 1 1 4.5,3.969 v 5.531 a 0.5,0.5 0 0 1 -1,0 v -5.53 a 4,4 0 0 1 -3.5,-3.971 z m 2.493,8.574 a 0.5,0.5 0 0 1 -0.411,0.575 c -0.712,0.118 -1.28,0.295 -1.655,0.493 a 1.3,1.3 0 0 0 -0.37,0.265 0.3,0.3 0 0 0 -0.057,0.09 v 0.003 l 0.002,0.008 0.016,0.033 a 0.6,0.6 0 0 0 0.145,0.15 c 0.165,0.13 0.435,0.27 0.813,0.395 0.751,0.25 1.82,0.414 3.024,0.414 1.204,0 2.273,-0.163 3.024,-0.414 0.378,-0.126 0.648,-0.265 0.813,-0.395 a 0.6,0.6 0 0 0 0.146,-0.15 l 0.015,-0.033 0.002,-0.008 v -0.004 a 0.3,0.3 0 0 0 -0.057,-0.09 1.3,1.3 0 0 0 -0.37,-0.264 c -0.376,-0.198 -0.943,-0.375 -1.655,-0.493 a 0.5,0.5 0 1 1 0.164,-0.986 c 0.77,0.127 1.452,0.328 1.957,0.594 0.461,0.243 0.961,0.643 0.961,1.243 0,0.426 -0.26,0.752 -0.544,0.977 -0.29,0.228 -0.68,0.413 -1.116,0.558 -0.878,0.293 -2.059,0.465 -3.34,0.465 -1.281,0 -2.462,-0.172 -3.34,-0.465 -0.436,-0.145 -0.826,-0.33 -1.116,-0.558 -0.284,-0.225 -0.544,-0.551 -0.544,-0.977 0,-0.599 0.5,-1 0.961,-1.243 0.505,-0.266 1.187,-0.467 1.957,-0.594 a 0.5,0.5 0 0 1 0.575,0.411"
     id="path1" />
</svg>`,"objects/ghidra-function":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-48.0279 0.0000 159.9986 127.9989"
   version="1.1"
   id="svg1"
   sodipodi:docname="ghidra-function.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 30.6944,0.01916255 c -2,0.037 -4.431,0.159 -5.494,0.277 -1.05,0.116 -2.907,0.38 -4.131,0.586 a 74,74 0 0 0 -4.541,0.94700005 78,78 0 0 0 -4.325,1.22 79,79 0 0 0 -3.787,1.348 c -0.98,0.385 -2.928,1.258 -4.33,1.938 -1.402,0.68 -3.175,1.597 -3.941,2.037 a 81,81 0 0 0 -3.236,2.0080004 82,82 0 0 0 -3.249,2.252 84,84 0 0 0 -2.988,2.363 c -0.87,0.725 -2.673,2.407 -4.004,3.738 -1.331,1.332 -3.014,3.134 -3.738,4.004 a 90,90 0 0 0 -2.436,3.08 71,71 0 0 0 -1.935,2.743 93,93 0 0 0 -1.549,2.445 76,76 0 0 0 -1.531,2.693 76,76 0 0 0 -1.625,3.248 76,76 0 0 0 -1.523,3.535 78,78 0 0 0 -1.283,3.561 84,84 0 0 0 -1.03,3.434 68,68 0 0 0 -0.82,3.496 84,84 0 0 0 -0.627,3.559 100,100 0 0 0 -0.422,3.242 c -0.107,0.98 -0.168,3.208 -0.168,6.23 0,3.022 0.06,5.251 0.166,6.231 0.092,0.84 0.283,2.299 0.424,3.243 a 83,83 0 0 0 0.574,3.306 c 0.174,0.874 0.43,2.048 0.568,2.608 0.139,0.56 0.516,1.904 0.836,2.988 0.32,1.084 0.924,2.886 1.342,4.006 a 80,80 0 0 0 1.644,4.004 70,70 0 0 0 1.838,3.73 88,88 0 0 0 1.852,3.242 69,69 0 0 0 1.734,2.691997 86,86 0 0 0 1.782,2.467 c 0.522,0.693 1.505,1.929 2.185,2.746 0.68,0.817 1.946,2.219 2.81,3.115 0.866,0.897 2.217,2.22 3.005,2.94 0.788,0.72 2.17,1.9 3.072,2.622 a 82,82 0 0 0 3.082,2.34 73,73 0 0 0 2.65,1.787 88,88 0 0 0 2.479,1.5 c 0.7,0.404 2.22,1.208 3.379,1.787 a 81,81 0 0 0 3.814,1.776 c 0.94,0.397 2.881,1.114 4.315,1.594 1.433,0.48 3.52,1.1 4.64,1.378 1.119,0.279 2.778,0.65 3.688,0.827 a 72,72 0 0 0 3.687,0.58 c 2.898,0.37 6.11,0.575 9.154,0.45 3.496,-0.034 4.916,-0.1 6.614,-0.306 a 86,86 0 0 0 4.004,-0.595 80,80 0 0 0 4.132,-0.9 76,76 0 0 0 4.706,-1.374 78,78 0 0 0 4.406,-1.637 77,77 0 0 0 3.941,-1.808 81,81 0 0 0 3.287,-1.742 c 0.735,-0.421 2.152,-1.3 3.15,-1.954 1,-0.653 2.46,-1.67 3.245,-2.26 a 88,88 0 0 0 2.824,-2.236 80,80 0 0 0 2.916,-2.586 70,70 0 0 0 3.037,-3.074 80,80 0 0 0 2.945,-3.431 82,82 0 0 0 2.584,-3.434 78,78 0 0 0 2.387,-3.687997 c 0.674,-1.118 1.815,-3.236 2.537,-4.705 0.722,-1.469 1.64,-3.5 2.04,-4.513 a 84,84 0 0 0 1.331,-3.688 74,74 0 0 0 1.06,-3.56 c 0.25,-0.944 0.654,-2.718 0.9,-3.942 0.244,-1.223 0.56,-3.14 0.699,-4.26 0.139,-1.12 0.312,-2.803 0.384,-3.744 0.072,-0.94 0.131,-2.976 0.131,-4.521 0,-1.546 -0.059,-3.58 -0.13,-4.52 a 95,95 0 0 0 -0.387,-3.744 72,72 0 0 0 -0.7,-4.26 82,82 0 0 0 -0.896,-3.94 75,75 0 0 0 -1.06,-3.561 82,82 0 0 0 -1.337,-3.688 c -0.4,-1.014 -1.23,-2.874 -1.841,-4.133 -0.61,-1.258 -1.553,-3.059 -2.096,-4 a 85,85 0 0 0 -1.943,-3.178 76,76 0 0 0 -2.387,-3.376 82,82 0 0 0 -2.684,-3.37 c -0.688,-0.804 -2.17,-2.379 -3.29,-3.5 -1.122,-1.12 -2.697,-2.6 -3.5,-3.289 a 80,80 0 0 0 -3.2,-2.56 84,84 0 0 0 -2.861,-2.065 90,90 0 0 0 -2.967,-1.8670004 c -1.014,-0.611 -2.904,-1.638 -4.197,-2.281 -1.293,-0.643 -3.154,-1.5 -4.133,-1.904 -0.979,-0.405 -2.867,-1.096 -4.195,-1.54 a 74,74 0 0 0 -4.514,-1.332 76,76 0 0 0 -3.772,-0.834 87,87 0 0 0 -3.56,-0.55800005 83,83 0 0 0 -3.96,-0.402 c -1.283,-0.094 -3.436,-0.126 -5.657,-0.084 m 1.252,3.52500005 c 1.48,0 3.428,0.057 4.33,0.127 a 85,85 0 0 1 2.785,0.264 c 0.63,0.075 2.002,0.278 3.05,0.45 1.05,0.174 2.958,0.568 4.24,0.88 1.284,0.311 3.429,0.934 4.768,1.382 1.34,0.449 3.202,1.138 4.14,1.534 a 78,78 0 0 1 3.716,1.728 68,68 0 0 1 3.422,1.8460004 c 0.369,0.219 0.919,0.59 1.44,0.922 -0.07,-0.018 -0.08,-0.027 -0.159,-0.047 -0.11,-0.027 -0.92,-0.203 -1.795,-0.426 a 49,49 0 0 0 -3.115,-0.668 c -1.123,-0.193 -2.314,-0.278 -4.514,-0.326 -2.31,-0.05 -3.406,-0.016 -4.832,0.148 a 52,52 0 0 0 -3.129,0.461 c -0.707,0.136 -2.002,0.442 -2.877,0.682 q -1.568,0.443 -3.1,1.002 a 58,58 0 0 0 -2.915,1.2 49,49 0 0 0 -3.047,1.552 52,52 0 0 0 -3.11,1.916 55,55 0 0 0 -2.865,2.113 c -0.77,0.615 -2.232,1.951 -3.25,2.967 -1.017,1.015 -2.351,2.475 -2.965,3.244 a 52,52 0 0 0 -1.959,2.645 c -0.772,1.14 -0.873,1.24 -1.168,1.164 -0.176,-0.046 -0.922,-0.22 -1.656,-0.387 a 34,34 0 0 0 -2.416,-0.45 c -0.617,-0.082 -1.656,-0.11 -2.42,-0.068 -0.806,0.046 -1.692,0.184 -2.226,0.348 -0.488,0.15 -1.088,0.377 -1.334,0.502 -0.247,0.125 -0.797,0.49 -1.223,0.81 -0.426,0.32 -1.074,0.97 -1.44,1.442 -0.365,0.473 -0.92,1.385 -1.232,2.025 -0.405,0.832 -0.725,1.804 -1.123,3.4 -0.386,1.553 -0.732,2.607 -1.129,3.444 a 19,19 0 0 1 -1.23,2.16 c -0.363,0.524 -1.243,1.515 -1.957,2.203 -0.715,0.689 -1.837,1.612 -2.492,2.051 -0.657,0.44 -1.798,1.1 -2.536,1.469 q -1.377,0.674 -2.8,1.244 c -0.805,0.316 -1.949,0.729 -2.543,0.916 -0.594,0.187 -1.997,0.57 -3.116,0.85 -1.118,0.279 -2.463,0.678 -2.988,0.888 -0.525,0.21 -1.46,0.671 -2.08,1.026 -0.619,0.354 -1.533,0.97 -2.033,1.367 -0.5,0.397 -1.19,1.034 -1.533,1.414 -0.344,0.38 -0.875,1.076 -1.182,1.547 a 14,14 0 0 0 -0.938,1.75 c -0.21,0.493 -0.578,1.614 -0.818,2.49 -0.24,0.876 -0.524,2.22 -0.63,2.988 -0.108,0.768 -0.196,1.849 -0.196,2.4 q 0.011,0.997 0.137,1.985 c 0.075,0.54 0.279,1.472 0.453,2.074 0.174,0.603 0.563,1.611 0.863,2.24 0.306,0.641 1.317,2.236 2.297,3.624 a 177,177 0 0 0 1.84,2.578 c 0.048,0.054 0.33,-1.348 0.627,-3.115 0.313,-1.864 0.696,-3.68 0.91,-4.323 0.203,-0.61 0.543,-1.453 0.756,-1.875 0.213,-0.422 0.407,-0.767 0.433,-0.767 0.026,0 0.247,0.418 0.49,0.93 a 6.5,6.5 0 0 0 1.133,1.638 10,10 0 0 0 1.416,1.172 c 0.399,0.255 1.157,0.636 1.686,0.848 0.529,0.212 1.743,0.557 2.701,0.767 q 1.708,0.368 3.424,0.692 c 0.925,0.17 1.718,0.31 1.764,0.31 0.045,0 0.015,-0.08 -0.067,-0.178 -0.11,-0.132 -0.11,-0.204 -0.006,-0.27 0.09,-0.054 -0.022,-0.198 -0.295,-0.384 -0.24,-0.163 -1.088,-1.185 -1.884,-2.27 -0.797,-1.084 -1.546,-2.216 -1.664,-2.517 -0.119,-0.3 -0.22,-0.855 -0.223,-1.23 l -0.006,-0.684 0.285,0.21 q 0.515,0.365 1.04,0.716 c 0.414,0.278 1.216,0.654 1.78,0.834 0.566,0.18 1.427,0.355 1.917,0.39 0.595,0.043 1.904,-0.065 3.957,-0.328 a 199,199 0 0 1 3.175,-0.392 c 0.06,0 -0.975,-0.801 -2.302,-1.782 -1.327,-0.979 -2.49,-1.893 -2.584,-2.029 -0.113,-0.163 -0.144,-0.414 -0.09,-0.732 0.045,-0.267 0.128,-0.557 0.183,-0.647 0.079,-0.127 0.31,-0.081 1.043,0.207 a 15,15 0 0 0 1.641,0.537 c 0.385,0.091 1.1,0.162 1.59,0.16 a 5.5,5.5 0 0 0 1.695,-0.279 9.4,9.4 0 0 0 1.621,-0.793 c 0.449,-0.283 1.075,-0.809 1.389,-1.168 a 9,9 0 0 0 1,-1.482 q 0.417,-0.835 0.717,-1.719 c 0.158,-0.49 0.418,-1.148 0.576,-1.463 0.158,-0.315 0.392,-0.663 0.521,-0.775 a 1.8,1.8 0 0 1 0.467,-0.285 c 0.178,-0.064 0.216,-0.03 0.164,0.14 -0.037,0.122 -0.124,0.478 -0.195,0.793 -0.07,0.315 -0.131,0.99 -0.133,1.5 -0.002,0.51 0.087,1.364 0.197,1.897 0.11,0.533 0.37,1.393 0.577,1.914 0.207,0.521 1.007,2.185 1.779,3.699 1.045,2.05 1.45,2.98 1.584,3.643 0.104,0.514 0.18,1.647 0.181,2.687 a 41,41 0 0 1 -0.183,3.56 168,168 0 0 0 -0.381,4.497 c -0.107,1.503 -0.258,2.962 -0.336,3.242 -0.078,0.28 -0.224,0.666 -0.322,0.857 a 1.4,1.4 0 0 1 -0.526,0.522 c -0.19,0.097 -0.748,0.255 -1.238,0.351 -0.58,0.114 -1.666,0.168 -3.115,0.155 -1.436,-0.013 -3.583,-0.16 -6.049,-0.412 -2.103,-0.216 -3.95,-0.391 -4.103,-0.391 -0.225,0 0.135,0.486 1.853,2.51 1.173,1.38 2.615,3.015 3.205,3.63 0.59,0.617 1.642,1.59 2.336,2.163 a 42,42 0 0 0 2.404,1.832 25,25 0 0 0 2.243,1.351 c 0.604,0.31 1.656,0.772 2.337,1.026 0.682,0.253 1.682,0.569997 2.225,0.704997 q 0.81,0.201 1.611,0.443 c 0.344,0.11 0.985,0.2 1.426,0.2 0.497,0 1.067,-0.1 1.5,-0.262 0.384,-0.144 0.978,-0.513 1.32,-0.819997 a 8.5,8.5 0 0 0 1.088,-1.237 c 0.257,-0.372 0.833,-1.505 1.28,-2.518 a 273,273 0 0 1 1.724,-3.81 188,188 0 0 0 1.969,-4.451 508,508 0 0 0 2.994,-7.31 594,594 0 0 0 3.551,-9.093 l 1.611,-4.26 1.52,-0.076 c 1.166,-0.058 1.75,-0.155 2.514,-0.416 0.547,-0.186 1.233,-0.46 1.525,-0.609 0.292,-0.149 0.856,-0.49 1.254,-0.76 a 22,22 0 0 0 1.596,-1.242 17,17 0 0 0 1.62,-1.652 q 0.725,-0.882 1.372,-1.823 c 0.34,-0.508 0.88,-1.453 1.197,-2.101 0.317,-0.648 0.795,-1.852 1.062,-2.672 l 0.487,-1.49 1.63,-0.543 1.63,-0.543 1.716,0.06 a 19.5,19.5 0 0 1 3.297,0.389 c 0.87,0.181 2.293,0.562 3.164,0.846 0.872,0.283 2.021,0.743 2.553,1.023 0.533,0.28 1.254,0.713 1.604,0.963 q 0.676,0.494 1.314,1.037 c 0.373,0.32 0.982,0.954 1.354,1.408 0.371,0.455 0.931,1.342 1.244,1.971 0.312,0.63 0.722,1.533 0.91,2.008 0.187,0.476 0.506,1.506 0.709,2.289 0.203,0.783 0.456,2.025 0.562,2.76 0.106,0.735 0.259,2.165 0.34,3.18 0.087,1.096 0.116,2.771 0.068,4.132 -0.043,1.26 -0.136,2.802 -0.207,3.432 -0.071,0.63 -0.218,1.717 -0.33,2.416 a 49,49 0 0 1 -1.273,5.512 c -0.183,0.605 -0.647,1.901 -1.031,2.88 a 50,50 0 0 1 -1.598,3.555 c -0.494,0.976 -1.285,2.35 -1.756,3.053 -0.47,0.702 -1.31,1.82 -1.867,2.484 -0.556,0.665 -1.405,1.580997 -1.889,2.036997 a 33,33 0 0 1 -1.957,1.668 58,58 0 0 1 -2.732,1.951 c -0.91,0.611 -2.324,1.51 -3.145,1.997 -0.82,0.486 -2.48,1.36 -3.687,1.943 -1.207,0.583 -2.968,1.348 -3.912,1.7 q -1.73,0.629 -3.496,1.15 c -0.98,0.28 -2.61,0.68 -3.623,0.888 -1.013,0.208 -2.703,0.48 -3.752,0.608 -1.475,0.178 -2.846,0.232 -6.04,0.234 -2.591,0.001 -4.7,-0.06 -5.658,-0.166 a 82,82 0 0 1 -3.752,-0.545 76,76 0 0 1 -4.322,-0.885 c -1.154,-0.279 -3.643,-0.962 -5.531,-1.517 -1.888,-0.556 -5.895,-1.836 -8.902,-2.844 q -5.281,-1.774 -10.553,-3.574 c -2.797,-0.958 -5.229,-1.832 -5.403,-1.944 l -0.177,-0.115 a 85,85 0 0 1 -1.002,-1.262 72,72 0 0 1 -2.164,-3.112997 74,74 0 0 1 -2.262,-3.741 c -0.335,-0.602 -0.705,-1.38 -1.096,-2.154 a 0.9,0.9 0 0 0 0.215,0.31 c 0.14,0.14 0.254,0.31 0.254,0.38 0,0.067 0.154,0.439 0.344,0.825 0.19,0.386 0.362,0.701 0.383,0.701 0.02,0 0.037,-0.572 0.037,-1.271 v -1.271 l -0.35,0.001 a 3,3 0 0 0 -0.637,0.079 c -0.152,0.04 -0.27,0.122 -0.277,0.183 -0.277,-0.55 -0.59,-1.12 -0.781,-1.535 a 80,80 0 0 1 -1.43,-3.316 78,78 0 0 1 -1.162,-3.21 67,67 0 0 1 -1.08,-3.675 78,78 0 0 1 -0.88,-3.912 66,66 0 0 1 -0.577,-3.56 88,88 0 0 1 -0.326,-3.23 c -0.072,-0.901 -0.13,-2.968 -0.13,-4.591 0,-1.623 0.059,-3.688 0.13,-4.59 a 79,79 0 0 1 0.318,-3.129 75,75 0 0 1 0.508,-3.242 70,70 0 0 1 0.764,-3.555 77,77 0 0 1 0.906,-3.302 c 0.253,-0.827 0.76,-2.305 1.125,-3.286 a 78,78 0 0 1 1.453,-3.562 62,62 0 0 1 1.564,-3.244 86,86 0 0 1 1.602,-2.86 72,72 0 0 1 1.719,-2.734 74,74 0 0 1 1.94,-2.734 83,83 0 0 1 1.864,-2.366 c 0.007,0.004 0.006,0.014 0.014,0.014 0.026,0 0.127,-0.1 0.223,-0.223 0.143,-0.182 0.132,-0.184 -0.016,-0.07 l 0.02,-0.025 c 0.58,-0.7 1.944,-2.18 3.029,-3.29 1.086,-1.109 2.575,-2.543 3.309,-3.187 a 77,77 0 0 1 2.542,-2.123 77,77 0 0 1 2.385,-1.795 70,70 0 0 1 2.684,-1.795 78,78 0 0 1 3.256,-1.924 67,67 0 0 1 3.549,-1.8040004 74,74 0 0 1 3.513,-1.502 79,79 0 0 1 3.516,-1.256 c 0.99,-0.323 2.708,-0.809 3.816,-1.082 a 81,81 0 0 1 3.795,-0.826 68,68 0 0 1 3.305,-0.518 84,84 0 0 1 3.236,-0.32 c 0.94,-0.072 2.92,-0.131 4.399,-0.131 m 23.49,9.6700004 c 0.037,0.002 0.118,-0.002 0.154,0 0.03,0.001 0.054,0.006 0.084,0.008 z m -1.416,0.98 c -0.152,0.014 -0.354,0.02 -0.49,0.034 a 96,96 0 0 0 -4.17,0.517 98,98 0 0 1 4.132,-0.52 c 0.134,-0.013 0.376,-0.017 0.528,-0.03 m 15.43,2.434 c 0.551,0.427 1.22,0.94 1.335,1.05 l 0.006,0.007 -2.32,0.046 a 60,60 0 0 0 -4.197,0.243 c -1.03,0.108 -2.523,0.31 -3.32,0.449 -0.798,0.138 -2.151,0.427 -3.006,0.642 -0.856,0.216 -1.579,0.368 -1.608,0.338 -0.029,-0.03 0.474,-0.3 1.123,-0.601 a 29,29 0 0 1 2.442,-0.977 c 0.695,-0.234 1.812,-0.54 2.48,-0.681 0.831,-0.175 2.117,-0.296 4.065,-0.38 1.524,-0.065 2.898,-0.11 3,-0.136 m -34.186,0.863 -0.203,0.139 c 0.041,-0.03 0.198,-0.132 0.18,-0.125 z m 35.838,0.467 c 0.064,0.058 0.197,0.173 0.285,0.252 l -0.055,-0.045 z m -4.096,1.342 c -0.146,0.01 -0.267,0.013 -0.402,0.023 0.047,-0.004 0.113,-0.016 0.158,-0.02 0.063,-0.004 0.176,0.001 0.244,-0.003 m 13.287,8.51 c 0.297,0.399 0.553,0.7 0.813,1.064 0.531,0.744 1.004,1.496 1.547,2.316 a 96,96 0 0 1 -2.43,-0.49 c -1.142,-0.242 -2.112,-0.46 -2.148,-0.496 -0.036,-0.036 0.45,-0.596 1.082,-1.244 z m -37.218,1.35 c -0.062,0.058 -0.17,0.135 -0.221,0.188 l 0.031,-0.043 c 0.013,-0.017 0.163,-0.12 0.19,-0.145 m -0.67,0.783 c -0.012,0.06 -0.016,0.1 0.021,0.08 l -0.039,0.026 z m -22.05,2.426 0.026,0.002 v 0.002 z m -7.538,2.787 c 0.07,-0.104 0.092,0.015 0.134,0.258 0.047,0.27 0.15,2.142 0.229,4.164 0.079,2.022 0.097,3.72 0.041,3.774 -0.056,0.054 -1.44,0.647 -3.076,1.316 -1.637,0.67 -2.999,1.217 -3.028,1.217 -0.029,0 -0.015,-0.057 0.028,-0.127 0.043,-0.07 0.437,-0.601 0.873,-1.18 a 37,37 0 0 0 1.543,-2.258 c 0.412,-0.662 1.108,-2.005 1.549,-2.984 0.441,-0.979 1.016,-2.372 1.279,-3.096 0.237,-0.653 0.357,-0.98 0.428,-1.084 m 52.576,19.764 0.01,0.006 c 0.004,0.004 0.01,0.012 0.015,0.015 z m -78.352,2.566 c 0.066,-0.039 0.076,0.327 0.022,0.873 -0.052,0.518 -0.104,0.949 -0.115,0.96 -0.012,0.01 -0.936,0.11 -2.055,0.222 -1.119,0.112 -2.32,0.235 -2.67,0.273 l -0.637,0.069 0.573,-0.27 c 0.314,-0.148 1.516,-0.671 2.67,-1.164 a 95,95 0 0 0 2.212,-0.963 m 47.444,4.996 c -0.454,0.254 -0.821,0.476 -0.825,0.497 h -0.003 c 0,-0.02 0.372,-0.242 0.828,-0.497 m -29.125,10.133 c -0.579,0.048 -0.78,0.132 -1.131,0.473 a 2.5,2.5 0 0 0 -0.584,0.969 3,3 0 0 0 -0.069,1.123 c 0.047,0.312 0.212,0.758 0.368,0.99 0.155,0.233 0.481,0.522 0.724,0.644 0.243,0.123 0.577,0.223 0.74,0.223 0.165,0 0.496,-0.092 0.735,-0.205 0.239,-0.113 0.548,-0.364 0.685,-0.559 0.139,-0.193 0.315,-0.63 0.393,-0.97 0.107,-0.466 0.104,-0.758 -0.012,-1.186 -0.096,-0.356 -0.339,-0.752 -0.65,-1.064 -0.48,-0.48 -0.52,-0.494 -1.2,-0.438 m 0.05,0.608 c 0.263,0 0.474,0.117 0.7,0.386 0.178,0.212 0.363,0.589 0.41,0.838 0.046,0.25 0.022,0.668 -0.057,0.93 -0.078,0.261 -0.244,0.564 -0.367,0.672 a 1.4,1.4 0 0 1 -0.477,0.263 0.9,0.9 0 0 1 -0.445,-0.001 1.6,1.6 0 0 1 -0.414,-0.264 c -0.123,-0.107 -0.285,-0.42 -0.36,-0.697 a 2.8,2.8 0 0 1 -0.052,-0.989 c 0.046,-0.267 0.218,-0.633 0.385,-0.812 0.192,-0.208 0.437,-0.326 0.677,-0.326 m 67.57,1.673 c 0.048,0.735 0.078,1.582 0.054,2.514 l -0.004,0.06 c 0.032,-0.882 -0.017,-1.723 -0.05,-2.574 m -73.058,2.524 c -0.162,0 -0.565,0.091 -0.894,0.203 -0.52,0.177 -0.588,0.24 -0.516,0.477 0.046,0.15 0.094,0.286 0.107,0.302 0.014,0.017 0.207,-0.022 0.43,-0.086 l 0.404,-0.117 v 3.67 h 0.764 v -4.45 z m 73.084,0.426 a 34,34 0 0 1 -0.162,2.25 c 0.064,-0.757 0.128,-1.496 0.162,-2.25 m -78.045,1.353 c -0.2,0 -0.545,0.087 -0.765,0.192 -0.22,0.105 -0.544,0.401 -0.72,0.658 -0.26,0.384 -0.315,0.615 -0.312,1.303 0.003,0.547 0.081,0.98 0.229,1.255 0.123,0.23 0.407,0.53 0.63,0.666 0.225,0.137 0.636,0.248 0.917,0.248 0.28,0 0.691,-0.11 0.916,-0.248 0.224,-0.136 0.507,-0.435 0.629,-0.666 0.137,-0.258 0.224,-0.712 0.228,-1.183 0.005,-0.533 -0.071,-0.913 -0.254,-1.26 -0.144,-0.277 -0.454,-0.6 -0.697,-0.73 -0.24,-0.13 -0.6,-0.235 -0.8,-0.235 m -5.353,0.127 a 1.7,1.7 0 0 0 -0.963,0.287 2.4,2.4 0 0 0 -0.654,0.729 c -0.141,0.265 -0.234,0.7 -0.233,1.082 0.002,0.351 0.114,0.877 0.248,1.174 0.141,0.31 0.422,0.647 0.664,0.795 0.232,0.14 0.611,0.255 0.846,0.255 0.235,0 0.612,-0.086 0.838,-0.193 0.235,-0.112 0.538,-0.421 0.707,-0.723 0.212,-0.377 0.297,-0.729 0.297,-1.236 0,-0.404 -0.089,-0.878 -0.207,-1.105 a 2.9,2.9 0 0 0 -0.604,-0.73 c -0.291,-0.246 -0.538,-0.335 -0.94,-0.335 m -0.073,0.637 c 0.241,0 0.462,0.121 0.672,0.371 0.173,0.205 0.35,0.564 0.393,0.797 0.044,0.232 0.023,0.617 -0.045,0.855 a 2.1,2.1 0 0 1 -0.402,0.73 c -0.154,0.165 -0.398,0.296 -0.543,0.294 a 1.2,1.2 0 0 1 -0.487,-0.133 c -0.122,-0.071 -0.309,-0.295 -0.414,-0.498 -0.105,-0.203 -0.191,-0.654 -0.191,-1.002 0,-0.495 0.072,-0.717 0.33,-1.023 0.224,-0.267 0.443,-0.391 0.687,-0.391 m 5.483,0.023 c 0.318,0.03 0.499,0.151 0.725,0.485 0.248,0.365 0.291,0.564 0.248,1.113 -0.039,0.475 -0.142,0.76 -0.354,0.986 a 0.94,0.94 0 0 1 -0.71,0.317 c -0.295,0 -0.49,-0.095 -0.675,-0.33 a 2.1,2.1 0 0 1 -0.34,-0.764 2.8,2.8 0 0 1 -0.002,-0.857 1.5,1.5 0 0 1 0.381,-0.707 c 0.216,-0.203 0.425,-0.272 0.727,-0.243 m -0.025,4.9 c -0.255,0 -0.645,0.107 -0.866,0.237 -0.221,0.13 -0.514,0.472 -0.652,0.758 a 3,3 0 0 0 -0.252,1.152 2.75,2.75 0 0 0 0.287,1.2 c 0.183,0.363 0.446,0.65 0.73,0.796 a 1.6,1.6 0 0 0 0.942,0.168 c 0.274,-0.033 0.64,-0.167 0.814,-0.297 0.174,-0.13 0.421,-0.434 0.551,-0.675 0.152,-0.283 0.237,-0.7 0.237,-1.176 0,-0.489 -0.087,-0.909 -0.256,-1.24 -0.143,-0.28 -0.435,-0.594 -0.662,-0.711 a 2.3,2.3 0 0 0 -0.873,-0.211 m -5.58,0.079 c -0.447,0.046 -0.655,0.154 -0.977,0.506 -0.226,0.246 -0.477,0.69 -0.557,0.986 -0.08,0.296 -0.107,0.745 -0.06,0.996 a 4.4,4.4 0 0 0 0.287,0.885 c 0.11,0.235 0.378,0.536 0.594,0.668 0.233,0.142 0.629,0.238 0.978,0.238 0.41,0 0.692,-0.082 0.938,-0.275 0.193,-0.152 0.456,-0.51 0.586,-0.795 0.13,-0.285 0.236,-0.782 0.238,-1.104 a 2.5,2.5 0 0 0 -0.287,-1.13 c -0.168,-0.318 -0.474,-0.648 -0.73,-0.79 -0.317,-0.175 -0.604,-0.227 -1.01,-0.185 m -5.35,0.084 c -0.51,0 -0.7,0.068 -1.055,0.38 -0.238,0.21 -0.505,0.553 -0.592,0.762 -0.091,0.223 -0.137,0.714 -0.107,1.182 0.036,0.58 0.134,0.918 0.351,1.223 0.166,0.232 0.479,0.503 0.696,0.601 0.22,0.1 0.615,0.153 0.892,0.121 0.274,-0.03 0.64,-0.16 0.813,-0.29 0.174,-0.13 0.421,-0.435 0.55,-0.676 0.145,-0.27 0.237,-0.698 0.237,-1.112 0,-0.37 -0.078,-0.861 -0.174,-1.09 -0.095,-0.228 -0.357,-0.569 -0.582,-0.757 -0.322,-0.271 -0.539,-0.344 -1.03,-0.344 m -5.111,0.053 c -0.053,-0.052 -0.43,0.006 -0.838,0.13 -0.674,0.204 -0.739,0.255 -0.686,0.534 0.052,0.273 0.106,0.296 0.488,0.224 l 0.43,-0.08 v 3.461 h 0.79 l -0.046,-2.088 c -0.025,-1.147 -0.087,-2.13 -0.138,-2.181 m 16.04,0.455 c 0.203,0 0.468,0.128 0.635,0.306 0.158,0.168 0.334,0.51 0.39,0.762 0.058,0.252 0.056,0.673 -0.003,0.936 -0.06,0.262 -0.257,0.604 -0.44,0.761 -0.182,0.158 -0.398,0.284 -0.482,0.28 a 1.8,1.8 0 0 1 -0.432,-0.122 c -0.153,-0.061 -0.367,-0.284 -0.476,-0.494 -0.109,-0.21 -0.197,-0.666 -0.197,-1.013 0,-0.495 0.07,-0.718 0.328,-1.024 q 0.33,-0.392 0.678,-0.392 m -5.353,0.062 c 0.102,-0.002 0.2,0.024 0.324,0.08 0.178,0.081 0.42,0.349 0.535,0.594 0.144,0.303 0.192,0.643 0.15,1.066 q -0.059,0.623 -0.353,0.936 c -0.18,0.192 -0.436,0.314 -0.66,0.314 -0.215,0 -0.49,-0.125 -0.668,-0.302 -0.184,-0.185 -0.335,-0.528 -0.389,-0.883 -0.066,-0.443 -0.03,-0.697 0.149,-1.065 0.13,-0.265 0.39,-0.556 0.576,-0.644 a 0.8,0.8 0 0 1 0.336,-0.096 m -5.617,0.065 c 0.157,0 0.444,0.137 0.637,0.302 0.3,0.259 0.356,0.416 0.402,1.139 0.05,0.798 0.035,0.857 -0.332,1.225 -0.213,0.212 -0.503,0.386 -0.645,0.386 -0.141,0 -0.41,-0.133 -0.597,-0.295 -0.264,-0.226 -0.357,-0.44 -0.405,-0.945 -0.035,-0.359 -0.026,-0.798 0.018,-0.975 a 1.4,1.4 0 0 1 0.357,-0.58 c 0.153,-0.141 0.407,-0.257 0.565,-0.257 m 5.72,4.908 c -0.392,-0.008 -0.678,0.07 -0.92,0.25 a 3.6,3.6 0 0 0 -0.605,0.603 c -0.165,0.22 -0.273,0.608 -0.308,1.098 -0.044,0.596 0.004,0.879 0.22,1.326 0.2,0.412 0.422,0.644 0.809,0.84 0.367,0.186 0.672,0.25 0.976,0.203 0.244,-0.036 0.586,-0.173 0.762,-0.305 0.177,-0.131 0.43,-0.427 0.565,-0.656 0.163,-0.28 0.244,-0.656 0.244,-1.146 0,-0.48 -0.086,-0.895 -0.252,-1.215 -0.14,-0.267 -0.403,-0.6 -0.586,-0.736 -0.206,-0.154 -0.553,-0.255 -0.904,-0.262 m -5.015,0.05 c -0.128,0 -0.5,0.092 -0.826,0.204 -0.328,0.111 -0.596,0.25 -0.596,0.308 0,0.058 0.032,0.189 0.072,0.293 0.056,0.145 0.162,0.166 0.446,0.084 l 0.373,-0.107 v 1.57 c 0,0.864 0.034,1.661 0.076,1.772 0.043,0.11 0.215,0.2 0.383,0.2 h 0.302 v -2.161 c 0,-2.007 -0.015,-2.162 -0.23,-2.162 m 4.959,0.637 c 0.197,0 0.47,0.11 0.605,0.246 0.136,0.136 0.314,0.468 0.395,0.737 0.109,0.364 0.11,0.624 0.004,1.017 -0.08,0.295 -0.29,0.645 -0.475,0.791 -0.182,0.144 -0.41,0.26 -0.504,0.26 -0.094,0 -0.357,-0.167 -0.586,-0.371 -0.388,-0.347 -0.416,-0.425 -0.416,-1.197 0,-0.7 0.048,-0.877 0.309,-1.155 0.19,-0.202 0.445,-0.328 0.668,-0.328 m 27.926,0.48 v 0.003 c -0.285,0.3 -0.692,0.635 -0.907,0.746 -0.33,0.17 -0.746,0.193 -2.685,0.137 -1.351,-0.04 -2.734,-0.155 -3.36,-0.28 -0.583,-0.115 -1.082,-0.185 -1.113,-0.156 h -0.002 v -0.002 c 0.03,-0.03 0.531,0.042 1.115,0.158 0.626,0.125 2.01,0.238 3.36,0.278 1.939,0.056 2.356,0.035 2.685,-0.135 0.215,-0.111 0.622,-0.448 0.907,-0.748 m -33.254,4.259 c -0.489,-0.046 -0.695,0.002 -1.053,0.244 a 2.3,2.3 0 0 0 -0.668,0.742 c -0.122,0.243 -0.223,0.72 -0.223,1.06 0,0.51 0.083,0.735 0.467,1.272 0.257,0.36 0.554,0.724997 0.66,0.811997 0.107,0.088 0.437,0.159 0.733,0.159 0.4,0 0.642,-0.09 0.945,-0.343997 0.225,-0.19 0.488,-0.53 0.584,-0.758 0.096,-0.228 0.172,-0.705 0.172,-1.059 0,-0.354 -0.078,-0.83 -0.174,-1.054 a 2.5,2.5 0 0 0 -0.504,-0.713 c -0.222,-0.204 -0.53,-0.323 -0.94,-0.361 m 0.037,0.68 c 0.182,0.045 0.441,0.262 0.574,0.48 0.149,0.243 0.242,0.63 0.242,1.006 0,0.335 -0.083,0.773 -0.185,0.97 -0.102,0.198 -0.277,0.395 -0.39,0.438 -0.114,0.044 -0.34,0.08 -0.503,0.08 -0.174,0 -0.433,-0.162 -0.627,-0.393 -0.181,-0.215 -0.337,-0.543 -0.347,-0.73 a 7,7 0 0 1 0.01,-0.72 1.7,1.7 0 0 1 0.21,-0.665 c 0.1,-0.155 0.293,-0.342 0.432,-0.416 0.138,-0.074 0.4,-0.096 0.584,-0.05 m 0.44,5.215997 c 0.048,0.048 0.107,0.112 0.138,0.135 -0.007,-0.002 -0.053,-0.034 -0.057,-0.033 z m 0.19,0.24 c 0.016,0.019 0.079,0.074 0.1,0.098 l -0.074,-0.066 z m 85.227,0.23 c -0.028,0.045 -0.058,0.113 -0.086,0.155 -0.031,0.048 -0.08,0.092 -0.113,0.14 z m -80.258,3.862 0.47,0.334 c -0.077,-0.053 -0.168,-0.107 -0.24,-0.158 -0.077,-0.057 -0.151,-0.119 -0.23,-0.176 m 6.333,4.086 c 0.463,0.27 0.886,0.497 1.39,0.78 -0.297,-0.162 -0.682,-0.354 -0.91,-0.485 -0.14,-0.08 -0.322,-0.2 -0.48,-0.295"
     id="path1" />
</svg>`,"objects/github-action":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-6.5916 0.0000 24.3944 19.5155"
   version="1.1"
   id="svg1"
   sodipodi:docname="github-action.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 5.6056,0 a 10,10 0 0 0 -10,10 c 0,4.42 2.87,8.17 6.84,9.5 0.5,0.08 0.66,-0.23 0.66,-0.5 v -1.69 c -2.77,0.6 -3.36,-1.34 -3.36,-1.34 -0.46,-1.16 -1.11,-1.47 -1.11,-1.47 -0.91,-0.62 0.07,-0.6 0.07,-0.6 1,0.07 1.53,1.03 1.53,1.03 0.87,1.52 2.34,1.07 2.91,0.83 0.09,-0.65 0.35,-1.09 0.63,-1.34 -2.22,-0.25 -4.55,-1.11 -4.55,-4.92 0,-1.11 0.38,-2 1.03,-2.71 -0.1,-0.25 -0.45,-1.29 0.1,-2.64 0,0 0.84,-0.27 2.75,1.02 0.79,-0.22 1.65,-0.33 2.5,-0.33 0.85,0 1.71,0.11 2.5,0.33 1.91,-1.29 2.75,-1.02 2.75,-1.02 0.55,1.35 0.2,2.39 0.1,2.64 0.65,0.71 1.03,1.6 1.03,2.71 0,3.82 -2.34,4.66 -4.57,4.91 0.36,0.31 0.69,0.92 0.69,1.85 V 19 c 0,0.27 0.16,0.59 0.67,0.5 3.97,-1.34 6.83,-5.08 6.83,-9.5 a 10,10 0 0 0 -10,-10"
     id="path1" />
</svg>`,"objects/github-repo":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-4.3944 0.0000 24.3944 19.5155"
   version="1.1"
   id="svg1"
   sodipodi:docname="github-repo.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 7.8028,0 a 10,10 0 0 0 -10,10 c 0,4.42 2.87,8.17 6.84,9.5 0.5,0.08 0.66,-0.23 0.66,-0.5 v -1.69 c -2.77,0.6 -3.36,-1.34 -3.36,-1.34 -0.46,-1.16 -1.11,-1.47 -1.11,-1.47 -0.91,-0.62 0.07,-0.6 0.07,-0.6 1,0.07 1.53,1.03 1.53,1.03 0.87,1.52 2.34,1.07 2.91,0.83 0.09,-0.65 0.35,-1.09 0.63,-1.34 -2.22,-0.25 -4.55,-1.11 -4.55,-4.92 0,-1.11 0.38,-2 1.03,-2.71 -0.1,-0.25 -0.45,-1.29 0.1,-2.64 0,0 0.84,-0.27 2.75,1.02 0.79,-0.22 1.65,-0.33 2.5,-0.33 0.85,0 1.71,0.11 2.5,0.33 1.91,-1.29 2.75,-1.02 2.75,-1.02 0.55,1.35 0.2,2.39 0.1,2.64 0.65,0.71 1.03,1.6 1.03,2.71 0,3.82 -2.34,4.66 -4.57,4.91 0.36,0.31 0.69,0.92 0.69,1.85 V 19 c 0,0.27 0.16,0.59 0.67,0.5 3.97,-1.34 6.83,-5.08 6.83,-9.5 a 10,10 0 0 0 -10,-10"
     id="path1" />
</svg>`,"objects/github-user":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-6.5916 0.0000 24.3944 19.5155"
   version="1.1"
   id="svg1"
   sodipodi:docname="github-user.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 5.6056,0 a 10,10 0 0 0 -10,10 c 0,4.42 2.87,8.17 6.84,9.5 0.5,0.08 0.66,-0.23 0.66,-0.5 v -1.69 c -2.77,0.6 -3.36,-1.34 -3.36,-1.34 -0.46,-1.16 -1.11,-1.47 -1.11,-1.47 -0.91,-0.62 0.07,-0.6 0.07,-0.6 1,0.07 1.53,1.03 1.53,1.03 0.87,1.52 2.34,1.07 2.91,0.83 0.09,-0.65 0.35,-1.09 0.63,-1.34 -2.22,-0.25 -4.55,-1.11 -4.55,-4.92 0,-1.11 0.38,-2 1.03,-2.71 -0.1,-0.25 -0.45,-1.29 0.1,-2.64 0,0 0.84,-0.27 2.75,1.02 0.79,-0.22 1.65,-0.33 2.5,-0.33 0.85,0 1.71,0.11 2.5,0.33 1.91,-1.29 2.75,-1.02 2.75,-1.02 0.55,1.35 0.2,2.39 0.1,2.64 0.65,0.71 1.03,1.6 1.03,2.71 0,3.82 -2.34,4.66 -4.57,4.91 0.36,0.31 0.69,0.92 0.69,1.85 V 19 c 0,0.27 0.16,0.59 0.67,0.5 3.97,-1.34 6.83,-5.08 6.83,-9.5 a 10,10 0 0 0 -10,-10"
     id="path1" />
</svg>`,"objects/gitlab-user":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-4.6875 0.0000 23.1235 18.4988"
   version="1.1"
   id="svg1"
   sodipodi:docname="gitlab-user.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 16.81422,10.36 -1.05,-3.22 c 0,-0.03 -0.01,-0.06 -0.02,-0.09 l -2.11,-6.48 a 0.86,0.86 0 0 0 -0.8,-0.57 c -0.36,0 -0.68,0.25 -0.79,0.58 l -2,6.17 H 3.7142197 l -2.01,-6.17 A 0.85,0.85 0 0 0 0.91421969,0 c -0.37,0 -0.69,0.25 -0.8,0.58 L -1.9957803,7.07 v 0.01 l -1.07,3.28 c -0.16,0.5 0.01,1.04 0.44,1.34 l 9.22,6.71 c 0.17,0.12 0.3900003,0.12 0.5600003,-0.01 l 9.22,-6.7 c 0.43,-0.3 0.6,-0.84 0.44,-1.34 M 3.0242197,7.7 l 2.57,7.91 -6.17000001,-7.91 m 8.73000031,7.92 2.47,-7.59 0.1,-0.33 h 3.61 l -5.59,7.16 m 4.1,-13.67 1.81,5.56 h -3.62 m -1.3,0.95 -1.79,5.51 -1.0700003,3.28 -2.86,-8.79 M 0.90421969,1.19 2.7142197,6.75 h -3.61000001 m -1.17999999,4.19 c -0.09,-0.07 -0.13,-0.19 -0.09,-0.29 l 0.79,-2.43 5.82,7.45 m 11.3800003,-4.73 -6.51,4.73 0.02,-0.03 5.79,-7.42 0.79,2.43 c 0.04,0.1 0,0.22 -0.09,0.29"
     id="path1" />
</svg>`,"objects/google-account":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-5.5300 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="google-account.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 16.555,9.1 h -9.17 v 2.73 h 6.51 c -0.33,3.81 -3.5,5.44 -6.5,5.44 -3.83,0 -7.19,-3.02 -7.19,-7.27 0,-4.1 3.2,-7.27 7.2,-7.27 3.09,0 4.9,1.97 4.9,1.97 l 1.9,-1.98 c 0,0 -2.44,-2.72 -6.9,-2.72 -5.68,0 -10.07,4.8 -10.07,10 0,5.05 4.13,10 10.22,10 5.35,0 9.25,-3.67 9.25,-9.09 0,-1.15 -0.15,-1.81 -0.15,-1.81"
     id="path1" />
</svg>`,"objects/google-threat-intelligence-report":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-5.5300 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="google-threat-intelligence-report.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 16.555,9.1 h -9.17 v 2.73 h 6.51 c -0.33,3.81 -3.5,5.44 -6.5,5.44 -3.83,0 -7.19,-3.02 -7.19,-7.27 0,-4.1 3.2,-7.27 7.2,-7.27 3.09,0 4.9,1.97 4.9,1.97 l 1.9,-1.98 c 0,0 -2.44,-2.72 -6.9,-2.72 -5.68,0 -10.07,4.8 -10.07,10 0,5.05 4.13,10 10.22,10 5.35,0 9.25,-3.67 9.25,-9.09 0,-1.15 -0.15,-1.81 -0.15,-1.81"
     id="path1" />
</svg>`,"objects/gpx":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-54.7464 0.0000 125.0002 100.0002"
   version="1.1"
   id="svg4"
   sodipodi:docname="gpx.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs4" />
  <path
     fill="currentColor"
     d="M -22.5016,1.8341494e-4 A 2.5,2.5 0 0 0 -25.0016,2.5001834 V 70.000183 h -11.496 v 22 h 11.496 v 5.5 a 2.5,2.5 0 0 0 2.5,2.499997 h 72 a 2.5,2.5 0 0 0 2.5,-2.499997 v -75.875 c 0.027,-1.113 0.004,-1.777 -0.732,-2.59 L 32.9624,0.73218341 A 2.5,2.5 0 0 0 31.1644,1.8341494e-4 Z m 2.5,4.99999998506 h 48.902 l 1.252,14.5679996 a 2.5,2.5 0 0 0 2.278,2.278 l 14.568,1.252 v 71.902 h -67 v -3 h 63.504 v -22 h -63.504 z m 3.98,67.9999996 q 3.556,0 5.547,1.139 2.005,1.127 2.577,3.125 l -3.827,0.545 q -0.404,-1.069 -1.523,-1.682 -1.108,-0.624 -2.773,-0.623 -2.526,0 -4.022,1.217 -1.484,1.217 -1.484,3.611 0,2.583 1.51,3.879 1.51,1.285 3.956,1.285 1.212,0 2.422,-0.355 1.224,-0.366 2.096,-0.881 v -1.84 h -4.412 v -2.443 h 8.305 v 5.777 q -1.211,0.891 -3.516,1.574 a 16.4,16.4 0 0 1 -4.646,0.672 q -2.995,0 -5.221,-0.95 -2.226,-0.96 -3.346,-2.732 a 7.13,7.13 0 0 1 -1.119,-3.867 q 0,-2.265 1.25,-4.027 1.25,-1.762 3.658,-2.701 1.835,-0.723 4.569,-0.723 m 11.913,0.248 h 6.183 q 3.514,0 4.582,0.217 1.64,0.327 2.746,1.426 1.108,1.087 1.108,2.818 0,1.336 -0.639,2.246 a 4.6,4.6 0 0 1 -1.627,1.436 q -0.976,0.514 -1.992,0.681 -1.38,0.21 -3.996,0.21 h -2.512 v 5.47 h -3.853 z m 16.48,0 h 4.504 l 3.826,4.66 3.75,-4.66 h 4.465 l -5.935,7.045 6.52,7.459 h -4.646 l -4.233,-5.016 -4.242,5.016 h -4.623 l 6.523,-7.568 z m -12.627,2.453 v 4.115 h 2.108 q 2.277,0.001 3.046,-0.226 0.769,-0.228 1.198,-0.713 a 1.62,1.62 0 0 0 0.443,-1.127 q 0,-0.792 -0.611,-1.307 -0.613,-0.514 -1.551,-0.642 -0.69,-0.1 -2.771,-0.1 z"
     color="currentColor"
     id="path1" />
  <path
     fill="currentColor"
     d="m 34.2734,9.1151834 8.61,8.6099996 -7.928,-0.682 z"
     color="currentColor"
     id="path2" />
  <path
     fill="currentColor"
     d="m -5.3906,14.432183 c -4.23,0 -7.694,3.455 -7.694,7.672 0,1.634 0.521,3.153 1.405,4.401 l 5.35,9.249 c 0.75,0.979 1.248,0.793 1.87,-0.052 l 5.902,-10.042 c 0.119,-0.216 0.212,-0.446 0.294,-0.68 0.364,-0.89 0.567,-1.86 0.567,-2.876 0,-4.217 -3.465,-7.672 -7.694,-7.672 m 0,3.595 a 4.06,4.06 0 0 1 4.088,4.077 4.06,4.06 0 0 1 -4.088,4.077 4.06,4.06 0 0 1 -4.089,-4.077 4.06,4.06 0 0 1 4.09,-4.077"
     id="path3" />
  <path
     fill="currentColor"
     d="m -12.0246,50.660183 c -1.522,3.044 -0.752,6.755 2.27,8.47 3.02,1.713 6.483,0.694 8.467,-2.27 1.14,-1.974 1.047,-4.328 -0.022,-6.18 l 10.412,-8.457 c 2.731,1.044 5.912,0.02 7.485,-2.524 l 10.867,2.277 c 0.208,1.903 1.277,3.691 3.048,4.714 2.947,1.701 6.767,0.677 8.468,-2.27 1.643,-2.845 0.728,-6.485 -1.988,-8.266 a 1.7,1.7 0 0 0 -0.596,-0.344 c -2.9,-1.462 -6.51,-0.435 -8.153,2.41 -0.066,0.115 -0.121,0.232 -0.179,0.349 l -10.554,-2.212 a 6.23,6.23 0 0 0 -2.799,-5.081 1.7,1.7 0 0 0 -0.596,-0.344 c -2.9,-1.462 -6.51,-0.435 -8.153,2.41 -1.26,2.182 -1.023,4.84 0.379,6.764 l -10.129,8.171 -0.074,-0.028 c -2.9,-1.461 -6.684,-0.528 -8.153,2.411 m 2.994,1.729 a 2.716,2.716 0 0 1 3.745,-1.003 2.715,2.715 0 0 1 1.004,3.745 2.716,2.716 0 0 1 -3.745,1.004 2.716,2.716 0 0 1 -1.004,-3.746 m 17.977,-17.317 a 2.716,2.716 0 0 1 3.745,-1.003 2.715,2.715 0 0 1 1.004,3.745 2.716,2.716 0 0 1 -3.745,1.004 2.716,2.716 0 0 1 -1.004,-3.746 m 22.281,4.879 a 2.716,2.716 0 0 1 3.745,-1.003 2.715,2.715 0 0 1 1.004,3.744 2.716,2.716 0 0 1 -3.745,1.004 2.716,2.716 0 0 1 -1.004,-3.745"
     color="currentColor"
     id="path4" />
</svg>`,"objects/http-request":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="0.0000 0.0000 22.0000 6.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="http-request.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 0,6 V 0 h 1.5 v 2 h 2 V 0 H 5 V 6 H 3.5 V 3.5 h -2 V 6 Z M 7.5,6 V 1.5 H 6 V 0 h 4.5 V 1.5 H 9 V 6 Z M 13,6 V 1.5 H 11.5 V 0 H 16 V 1.5 H 14.5 V 6 Z m 4,0 V 0 h 3.5 Q 21.1,0 21.55,0.45 22,0.9 22,1.5 v 1 Q 22,3.1 21.55,3.55 21.1,4 20.5,4 h -2 v 2 z m 1.5,-3.5 h 2 v -1 h -2 z"
     id="path1" />
</svg>`,"objects/identity":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-6.0000 0.0000 20.0000 16.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="identity.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 4,2 C 5.1,2 6,2.9 6,4 6,5.1 5.1,6 4,6 2.9,6 2,5.1 2,4 2,2.9 2.9,2 4,2 m 0,9 c 2.7,0 5.8,1.29 6,2 v 1 H -2 V 13.01 C -1.8,12.29 1.3,11 4,11 M 4,0 C 1.79,0 0,1.79 0,4 0,6.21 1.79,8 4,8 6.21,8 8,6.21 8,4 8,1.79 6.21,0 4,0 m 0,9 c -2.67,0 -8,1.34 -8,4 v 3 H 12 V 13 C 12,10.34 6.67,9 4,9"
     id="path1" />
</svg>`,"objects/image":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-9.0000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="image.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 4.5,7 H 10 L 4.5,1.5 Z m -7,-7 h 8 l 6,6 v 12 a 2,2 0 0 1 -2,2 h -12 a 2,2 0 0 1 -2,-2 V 2 c 0,-1.11 0.89,-2 2,-2 m 0,18 h 12 v -8 l -4,4 -2,-2 z m 2,-11 a 2,2 0 0 0 -2,2 2,2 0 0 0 2,2 2,2 0 0 0 2,-2 2,2 0 0 0 -2,-2"
     id="path1" />
</svg>`,"objects/impersonation":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-7.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="impersonation.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 5,0 C 10.5,0 15,4.5 15,10 15,15.5 10.5,20 5,20 -0.5,20 -5,15.5 -5,10 -5,4.5 -0.5,0 5,0 m 2.92,10.81 c -1.08,0 -1.97,0.75 -2.21,1.75 -0.54,-0.23 -1.05,-0.17 -1.42,-0.01 -0.24,-1 -1.14,-1.74 -2.21,-1.74 -1.25,0 -2.26,1.01 -2.26,2.26 0,1.25 1.01,2.26 2.26,2.26 1.2,0 2.16,-0.91 2.25,-2.08 0.2,-0.13 0.71,-0.39 1.34,0.01 a 2.258,2.258 0 0 0 4.51,-0.19 c 0,-1.25 -1.01,-2.26 -2.26,-2.26 m -5.84,0.64 c 0.92,0 1.62,0.73 1.62,1.62 0,0.89 -0.7,1.62 -1.62,1.62 -0.89,0 -1.62,-0.73 -1.62,-1.62 0,-0.89 0.73,-1.62 1.62,-1.62 m 5.84,0 c 0.89,0 1.62,0.73 1.62,1.62 0,0.89 -0.73,1.62 -1.62,1.62 C 7,14.69 6.3,13.96 6.3,13.07 6.3,12.18 7,11.45 7.92,11.45 M 10.83,9.5 H -0.83 v 0.67 H 10.83 Z M 7.15,4.89 A 0.67,0.67 0 0 0 6.35,4.53 L 5,5 3.65,4.53 3.61,4.5 A 0.67,0.67 0 0 0 2.84,4.92 L 1.36,8.83 H 8.64 L 7.16,4.92 Z"
     id="path1" />
</svg>`,"objects/incident":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-7.1256 0.0000 33.7500 27.0000"
   version="1.1"
   id="svg2"
   sodipodi:docname="incident.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs2" />
  <path
     fill="currentColor"
     d="m 14.2672,23.722 0.998,1.732 2.978,-1.722 V 27 h 1.997 v -3.268 l 3.01,1.74 0.999,-1.732 -3.01,-1.74 3,-1.735 -0.998,-1.733 -3.001,1.736 V 17 h -1.997 v 3.267 l -2.996,-1.732 -0.998,1.733 2.995,1.732 z M 9.2492,20 a 1.5,1.5 0 1 0 0,3 1.5,1.5 0 0 0 0,-3 m -1,-11 h 2 v 9 h -2 z"
     id="path1" />
  <path
     fill="currentColor"
     d="M 11.2492,27 H -3.7508001 a 1,1 0 0 1 -0.887,-1.461 L 8.3622,0.539 C 8.5342,0.208 8.8922,0 9.2492,0 c 0.357,0 0.715,0.208 0.887,0.539 l 6.76,13 -1.774,0.922 L 9.2492,3.168 -2.1038001,25 H 11.2492 Z"
     id="path2" />
</svg>`,"objects/infrastructure":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-4.4926 0.0000 32.4970 25.9976"
   version="1.1"
   id="svg2"
   sodipodi:docname="infrastructure.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs2" />
  <path
     fill="currentColor"
     d="m 13.758097,23.997618 h 12 v 2 h -12 z m 0,-5 h 12 v 2 h -12 z m 0,-5 h 12 v 2 h -12 z"
     id="path1" />
  <path
     fill="currentColor"
     d="M 9.7580973,22.997618 H 5.2580977 a 7.496,7.496 0 0 1 -1.322,-14.8759998 10,10 0 0 1 19.8219993,1.876 h -2 a 7.999,7.999 0 0 0 -15.9499993,-0.87 l -0.09,0.834 -0.837,0.056 a 5.496,5.496 0 0 0 0.377,10.98 h 4.4999996 z"
     id="path2" />
</svg>`,"objects/instagram-account":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-7.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="instagram-account.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 0.8,0 H 9.2 C 12.4,0 15,2.6 15,5.8 v 8.4 A 5.8,5.8 0 0 1 9.2,20 H 0.8 C -2.4,20 -5,17.4 -5,14.2 V 5.8 A 5.8,5.8 0 0 1 0.8,0 M 0.6,2 A 3.6,3.6 0 0 0 -3,5.6 v 8.8 c 0,1.99 1.61,3.6 3.6,3.6 H 9.4 A 3.6,3.6 0 0 0 13,14.4 V 5.6 C 13,3.61 11.39,2 9.4,2 Z m 9.65,1.5 A 1.25,1.25 0 0 1 11.5,4.75 1.25,1.25 0 0 1 10.25,6 1.25,1.25 0 0 1 9,4.75 1.25,1.25 0 0 1 10.25,3.5 M 5,5 A 5,5 0 0 1 10,10 5,5 0 0 1 5,15 5,5 0 0 1 0,10 5,5 0 0 1 5,5 M 5,7 A 3,3 0 0 0 2,10 3,3 0 0 0 5,13 3,3 0 0 0 8,10 3,3 0 0 0 5,7"
     id="path1" />
</svg>`,"objects/instant-message":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-5.0000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="instant-message.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 15.5,0 h -16 c -1.1,0 -1.99,0.9 -1.99,2 l -0.01,18 4,-4 h 14 c 1.1,0 2,-0.9 2,-2 V 2 c 0,-1.1 -0.9,-2 -2,-2 m -2,12 h -12 v -2 h 12 z m 0,-3 H 1.5 V 7 h 12 z m 0,-3 H 1.5 V 4 h 12 z"
     id="path1" />
</svg>`,"objects/intelligence-report":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-10.8750 0.0000 26.2500 21.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="intelligence-report.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 5.75,16 c 0.56,0 1,0.44 1,1 0,0.56 -0.44,1 -1,1 -0.56,0 -1,-0.44 -1,-1 0,-0.56 0.44,-1 1,-1 m 0,-3 c -2.73,0 -5.06,1.66 -6,4 0.94,2.34 3.27,4 6,4 2.73,0 5.06,-1.66 6,-4 -0.94,-2.34 -3.27,-4 -6,-4 m 0,6.5 A 2.5,2.5 0 0 1 3.25,17 2.5,2.5 0 0 1 5.75,14.5 2.5,2.5 0 0 1 8.25,17 2.5,2.5 0 0 1 5.75,19.5 M -2.11,17.75 -2.4,17 -2.11,16.26 C -0.82,13.06 2.25,11 5.75,11 c 1.05,0 2.06,0.21 3,0.56 V 6 l -6,-6 h -8 c -1.11,0 -2,0.89 -2,2 v 16 a 2,2 0 0 0 2,2 h 4.5 c -0.55,-0.66 -1,-1.42 -1.36,-2.25 M 1.75,1.5 7.25,7 h -5.5 z"
     id="path1" />
</svg>`,"objects/intrusion-set":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-5.6289 0.0000 23.7526 19.0021"
   version="1.1"
   id="svg1"
   sodipodi:docname="intrusion-set.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 11.3074,11.002069 c -1.86,0 -3.42,1.33 -3.82,3.1 -0.95,-0.41 -1.82,-0.3 -2.48,-0.01 -0.41,-1.78 -1.97,-3.09 -3.82,-3.09 -2.17,0 -3.94,1.79 -3.94,4 0,2.21 1.77,4 3.94,4 2.06,0 3.74,-1.62 3.9,-3.68 0.34,-0.24 1.23,-0.69 2.32,0.02 0.18,2.05 1.84,3.66 3.9,3.66 2.17,0 3.94,-1.79 3.94,-4 0,-2.21 -1.77,-4 -3.94,-4 m -10.12,6.86 c -1.56,0 -2.81,-1.28 -2.81,-2.86 0,-1.58 1.26,-2.86 2.81,-2.86 1.56,0 2.81,1.28 2.81,2.86 0,1.58 -1.25,2.86 -2.81,2.86 m 10.12,0 c -1.56,0 -2.81,-1.28 -2.81,-2.86 0,-1.58 1.25,-2.86 2.81,-2.86 1.56,0 2.82,1.28 2.82,2.86 0,1.58 -1.27,2.86 -2.82,2.86 m 4.94,-9.3599997 h -20 v 1.4999997 h 20 z m -6.47,-7.86999998 c -0.22,-0.49 -0.78,-0.75 -1.31,-0.58 l -2.22,0.74 -2.23,-0.74 -0.05,-0.01 c -0.53,-0.15 -1.09,0.13 -1.29,0.64 l -2.43,6.31999998 h 12 l -2.44,-6.31999998 z"
     id="path1" />
</svg>`,"objects/iot-device":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-6.1440 0.0000 26.2500 21.0000"
   version="1.1"
   id="svg3"
   sodipodi:docname="iot-device.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs3" />
  <path
     fill="currentColor"
     d="m -0.056,11.999982 v 9 h -2 v -9 z m 18,0 v 2 h -2 v 7 h -2 v -7 h -2 v -2 z m -11,-2.0000001 a 7.54,7.54 0 0 1 3.96,1.1490001 l 1.447,-1.4500001 a 9.5,9.5 0 0 0 -5.407,-1.699 9.36,9.36 0 0 0 -5.333,1.68 L 3.06,11.132982 A 7.36,7.36 0 0 1 6.944,9.9999819"
     id="path1" />
  <path
     fill="currentColor"
     d="m 6.944,5.9999819 a 11.5,11.5 0 0 1 6.834,2.27 l 1.427,-1.43 a 13.48,13.48 0 0 0 -8.261,-2.84 13.33,13.33 0 0 0 -8.186,2.822 l 1.426,1.43 a 11.34,11.34 0 0 1 6.76,-2.252"
     id="path2" />
  <path
     fill="currentColor"
     d="m 6.944,1.9999819 a 15.47,15.47 0 0 1 9.687,3.41 l 1.427,-1.429 a 17.43,17.43 0 0 0 -22.154,-0.017 l 1.427,1.429 a 15.33,15.33 0 0 1 9.613,-3.393 m 0,10.0000001 a 4.5,4.5 0 1 0 4.5,4.5 4.5,4.5 0 0 0 -4.5,-4.5 m 0,7 a 2.5,2.5 0 1 1 2.5,-2.5 2.5,2.5 0 0 1 -2.5,2.5"
     id="path3" />
</svg>`,"objects/iot-firmware":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-6.1440 0.0000 26.2500 21.0000"
   version="1.1"
   id="svg3"
   sodipodi:docname="iot-firmware.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs3" />
  <path
     fill="currentColor"
     d="m -0.056,11.999982 v 9 h -2 v -9 z m 18,0 v 2 h -2 v 7 h -2 v -7 h -2 v -2 z m -11,-2.0000001 a 7.54,7.54 0 0 1 3.96,1.1490001 l 1.447,-1.4500001 a 9.5,9.5 0 0 0 -5.407,-1.699 9.36,9.36 0 0 0 -5.333,1.68 L 3.06,11.132982 A 7.36,7.36 0 0 1 6.944,9.9999819"
     id="path1" />
  <path
     fill="currentColor"
     d="m 6.944,5.9999819 a 11.5,11.5 0 0 1 6.834,2.27 l 1.427,-1.43 a 13.48,13.48 0 0 0 -8.261,-2.84 13.33,13.33 0 0 0 -8.186,2.822 l 1.426,1.43 a 11.34,11.34 0 0 1 6.76,-2.252"
     id="path2" />
  <path
     fill="currentColor"
     d="m 6.944,1.9999819 a 15.47,15.47 0 0 1 9.687,3.41 l 1.427,-1.429 a 17.43,17.43 0 0 0 -22.154,-0.017 l 1.427,1.429 a 15.33,15.33 0 0 1 9.613,-3.393 m 0,10.0000001 a 4.5,4.5 0 1 0 4.5,4.5 4.5,4.5 0 0 0 -4.5,-4.5 m 0,7 a 2.5,2.5 0 1 1 2.5,-2.5 2.5,2.5 0 0 1 -2.5,2.5"
     id="path3" />
</svg>`,"objects/ip-port":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-7.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="ip-port.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 8,6 H 6 V 4 h 2 z m 7,11 v 2 H 8 A 1,1 0 0 1 7,20 H 3 A 1,1 0 0 1 2,19 H -5 V 17 H 2 A 1,1 0 0 1 3,16 H 4 V 14 H 0 A 2,2 0 0 1 -2,12 V 2 A 2,2 0 0 1 0,0 h 10 a 2,2 0 0 1 2,2 v 10 a 2,2 0 0 1 -2,2 H 6 v 2 h 1 a 1,1 0 0 1 1,1 z M 2,2 H 0 V 12 H 2 Z M 4,12 H 6 V 8 H 8 A 2,2 0 0 0 10,6 V 4 A 2,2 0 0 0 8,2 H 4 Z"
     id="path1" />
</svg>`,"objects/irc":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-3.7500 0.0000 22.5000 18.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="irc.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 7.5,0 c 5.5,0 10,3.58 10,8 0,4.42 -4.5,8 -10,8 C 6.26,16 5.07,15.82 3.97,15.5 1.05,18 -2.5,18 -2.5,18 -0.17,15.67 0.2,14.1 0.25,13.5 -1.45,12.07 -2.5,10.13 -2.5,8 -2.5,3.58 2,0 7.5,0"
     id="path1" />
</svg>`,"objects/ja3":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-7.0130 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="ja3.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 11.300151,2.47 c -0.08,0 -0.16,-0.02 -0.23,-0.06 -1.92,-0.99 -3.58,-1.41 -5.5799998,-1.41 -1.97,0 -3.85,0.47 -5.56,1.41 -0.24,0.13 -0.54,0.04 -0.68,-0.2 a 0.506,0.506 0 0 1 0.2,-0.68 c 1.86,-1.03 3.9,-1.53 6.04,-1.53 2.1399998,0 3.9999998,0.47 6.0399998,1.5 0.25,0.15 0.34,0.45 0.21,0.69 a 0.48,0.48 0 0 1 -0.44,0.28 M -3.0098488,7.72 c -0.1,0 -0.2,-0.03 -0.29,-0.09 a 0.517,0.517 0 0 1 -0.12,-0.7 c 0.99,-1.4 2.25,-2.5 3.75,-3.27 3.16,-1.62 7.1599998,-1.63 10.3099998,-0.01 1.5,0.77 2.76,1.85 3.75,3.25 0.16,0.22 0.1,0.54 -0.12,0.7 -0.23,0.16 -0.54,0.11 -0.7,-0.1 a 9.26,9.26 0 0 0 -3.39,-2.96 c -2.87,-1.47 -6.5399998,-1.47 -9.3999998,0.01 -1.36,0.7 -2.5,1.7 -3.4,2.95 -0.08,0.15 -0.23,0.22 -0.39,0.22 m 6.25,12.07 c -0.13,0 -0.25,-0.05 -0.35,-0.15 -0.87,-0.87 -1.34,-1.43 -2.01,-2.64 -0.69,-1.23 -1.05,-2.73 -1.05,-4.34 0,-2.97 2.54,-5.39 5.66,-5.39 3.1199998,0 5.6599998,2.42 5.6599998,5.39 a 0.5,0.5 0 0 1 -0.5,0.5 0.5,0.5 0 0 1 -0.5,-0.5 c 0,-2.42 -2.09,-4.39 -4.6599998,-4.39 -2.57,0 -4.66,1.97 -4.66,4.39 0,1.44 0.32,2.77 0.93,3.84 0.64,1.16 1.08,1.65 1.85,2.43 0.19,0.2 0.19,0.51 0,0.71 -0.12,0.1 -0.24,0.15 -0.37,0.15 m 7.1699998,-1.85 c -1.19,0 -2.24,-0.3 -3.1,-0.89 C 5.8201512,16.04 4.9301512,14.4 4.9301512,12.66 a 0.5,0.5 0 0 1 0.5,-0.5 0.5,0.5 0 0 1 0.5,0.5 c 0,1.41 0.7199998,2.74 1.9399998,3.56 0.71,0.48 1.54,0.71 2.54,0.71 0.24,0 0.64,-0.03 1.04,-0.1 0.27,-0.05 0.54,0.13 0.58,0.41 0.05,0.26 -0.13,0.53 -0.41,0.58 -0.57,0.11 -1.07,0.12 -1.21,0.12 m -2.01,2.06 h -0.13 c -1.59,-0.46 -2.6299998,-1.05 -3.7199998,-2.12 a 7.28,7.28 0 0 1 -2.17,-5.22 c 0,-1.62 1.38,-2.94 3.08,-2.94 1.6999998,0 3.0799998,1.32 3.0799998,2.94 0,1.07 0.95,1.94 2.08,1.94 1.15,0 2.08,-0.87 2.08,-1.94 0,-3.77 -3.25,-6.83 -7.2499998,-6.83 -2.84,0 -5.46,1.58 -6.61,4.03 -0.39,0.81 -0.59,1.76 -0.59,2.8 0,0.78 0.07,2.01 0.67,3.61 0.1,0.26 -0.03,0.55 -0.29,0.64 a 0.504,0.504 0 0 1 -0.64,-0.29 c -0.5,-1.31 -0.73,-2.62 -0.73,-3.96 0,-1.2 0.23,-2.29 0.68,-3.24 1.33,-2.79 4.28,-4.6 7.51,-4.6 4.5399998,0 8.2499998,3.51 8.2499998,7.83 0,1.62 -1.38,2.94 -3.08,2.94 -1.7,0 -3.08,-1.32 -3.08,-2.94 0,-1.07 -0.93,-1.94 -2.0799998,-1.94 -1.15,0 -2.08,0.87 -2.08,1.94 0,1.71 0.66,3.31 1.87,4.51 0.95,0.94 1.8599998,1.46 3.2699998,1.84 0.27,0.08 0.42,0.36 0.35,0.62 -0.05,0.23 -0.26,0.38 -0.47,0.38"
     id="path1" />
</svg>`,"objects/keybase-account":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-252.3756 0.0000 640.0000 512.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="keybase-account.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     fill-rule="evenodd"
     d="m -17.94235,182.819 c -7.814,-15.421 -10.87,-33.354 -8.88,-52.529 -51.560001,0.435 -56.840001,-20.355 -57.715001,-40.875 l 1.854,-29.93 c 1.215,-19.6 18.697001,-34.919 38.338001,-34.919 41.422,1.62 45.335,2.598 56.818,15.284 l 28.38,-39.85 23.498,13.825 c -15.545,33.091 -10.105,41.39 -10.046,41.458 71.697,1.631 113.497,60.152 89.407,123.388 144.315,54.947 195.315,198.537 134.752,333.329 h -31.234 c 27.055,-45.44 34.305,-102.158 25.54,-153.485 -72.846,107.605 -171.848,-71.037 -366.178001,90.307 l 21.625,-67.794 -45.545999,48.305 c 5.46,30.528 17.899999,58.664 35.650999,82.667 h -32.991999 a 224.5,224.5 0 0 1 -25.328,-58.626 l -27.2,28.848 c -7.765,-144.584 26.024,-244.466 149.256,-299.403 m 56.376,273.007 c 0,-18.139 -19.77,-29.537 -35.502,-20.468 -15.732,9.069 -15.732,31.866 0,40.935 15.732,9.069 35.502,-2.329 35.502,-20.467 m 126.412,0 c 0,-18.139 -19.771,-29.537 -35.503,-20.468 -15.732,9.069 -15.731,31.866 0,40.935 15.731,9.069 35.503,-2.329 35.503,-20.467 M -6.06335,69.553 c -6.145,11.102 -11.254,22.234 -14.946,33.664 l -26.94,-1.667 c -5.425,-0.332 -9.576,-5.017 -9.26,-10.442 l 1.854,-29.928 c 0.324,-5.225 4.658,-9.268 9.866,-9.268 0.197,0 30.513,1.87 30.513,1.87 8.238,1.306 10.363,6.505 8.913,15.771 m 73.157,113.457 77.43,95.3 c 6.872,8.423 -5.703,18.684 -12.576,10.261 l -7.71,-9.505 -32.092,26.12 -20.398,-24.869 32.225,-26.23 -11.242,-13.857 -15.472,12.697 -10.374,-13.122 15.31,-12.564 -27.676,-33.97 c -6.61,-8.1 5.966,-18.36 12.575,-10.261"
     clip-rule="evenodd"
     id="path1" />
</svg>`,"objects/leaked-document":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-9.3750 0.0000 21.2500 17.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="leaked-document.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 2.75,0 V 4.5 A 1.5,1.5 0 0 0 4.25,6 h 4.5 v 8.5 A 1.5,1.5 0 0 1 7.25,16 H 2.493 A 5.5,5.5 0 0 0 -3.25,7.207 V 1.5 A 1.5,1.5 0 0 1 -1.75,0 Z m 1,0.25 V 4.5 A 0.5,0.5 0 0 0 4.25,5 H 8.5 Z m -1,12.25 a 4.5,4.5 0 1 1 -9,0 4.5,4.5 0 0 1 9,0 M -1.75,10 a 0.5,0.5 0 0 0 -0.5,0.5 v 2 a 0.5,0.5 0 0 0 1,0 v -2 A 0.5,0.5 0 0 0 -1.75,10 m 0,5.125 a 0.625,0.625 0 1 0 0,-1.25 0.625,0.625 0 0 0 0,1.25"
     id="path1" />
</svg>`,"objects/legal-entity":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-5.3235 0.0000 23.7500 19.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="legal-entity.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 6.53809,0 C 5.2680901,0 4.1380901,0.8 3.7180901,2 h -6.18 v 2 h 1.94999999 l -2.94999999,7 c -0.47,2 1,3 3.49999999,3 C 2.5380901,14 4.0980901,13 3.5380901,11 L 0.58809009,4 H 3.7080901 c 0.33,0.85 0.98,1.5 1.83,1.83 V 17 h -9 v 2 H 16.53809 v -2 h -9 V 5.82 c 0.85,-0.32 1.5,-0.97 1.82,-1.82 h 3.13 l -2.95,7 c -0.47,2 1,3 3.5,3 2.5,0 4.06,-1 3.5,-3 l -2.95,-7 h 1.95 V 2 h -6.17 c -0.43,-1.2 -1.56,-2 -2.83,-2 m 0,2 a 1,1 0 0 1 1,1 1,1 0 0 1 -1,1 A 1,1 0 0 1 5.5380901,3 1,1 0 0 1 6.53809,2 M 0.03809009,7.25 1.5380901,11 h -3 z m 12.99999991,0 1.5,3.75 h -3 z"
     id="path1" />
</svg>`,"objects/lnk":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-13.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="lnk.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 1,0 h -8 c -1.11,0 -2,0.89 -2,2 v 16 c 0,1.11 0.89,2 2,2 H 5 c 1.11,0 2,-0.89 2,-2 V 6 Z m -3,18 h -1 c -1.61,0 -4,-1.06 -4,-4 0,-2.93 2.39,-4 4,-4 h 1 v 2 h -1 c -0.46,0 -2,0.17 -2,2 0,1.9 1.67,2 2,2 h 1 z m 4,-5 v 2 H -4 V 13 Z M 1,18 H 0 V 16 H 1 C 1.46,16 3,15.83 3,14 3,12.1 1.33,12 1,12 H 0 v -2 h 1 c 1.61,0 4,1.07 4,4 0,2.94 -2.39,4 -4,4 M 0,7 V 1.5 L 5.5,7 Z"
     id="path1" />
</svg>`,"objects/macho":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-8.7760 0.0000 25.0017 20.0013"
   version="1.1"
   id="svg1"
   sodipodi:docname="macho.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 10.45759,17.5 c -0.83,1.24 -1.71,2.45 -3.05,2.47 -1.34,0.03 -1.77,-0.79 -3.29,-0.79 -1.53,0 -2,0.77 -3.27,0.82 -1.31,0.05 -2.3,-1.32 -3.14,-2.53 -1.71,-2.47 -3.02,-7.02 -1.26,-10.08 0.87,-1.52 2.43,-2.48 4.12,-2.51 1.28,-0.02 2.5,0.87 3.29,0.87 0.78,0 2.26,-1.07 3.81,-0.91 0.65,0.03 2.47,0.26 3.64,1.98 -0.09,0.06 -2.17,1.28 -2.15,3.81 0.03,3.02 2.65,4.03 2.68,4.04 -0.03,0.07 -0.42,1.44 -1.38,2.83 m -5.71,-16 c 0.73,-0.83 1.94,-1.46 2.94,-1.5 0.13,1.17 -0.34,2.35 -1.04,3.19 -0.69,0.85 -1.83,1.51 -2.95,1.42 -0.15,-1.15 0.41,-2.35 1.05,-3.11"
     id="path1" />
</svg>`,"objects/malicious-website":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-7.8750 0.0000 26.2500 21.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="malicious-website.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 6.57,12 H 2.41 C 2.31,11.34 2.25,10.68 2.25,10 2.25,9.32 2.31,8.65 2.41,8 h 4.68 c 0.09,0.65 0.16,1.32 0.16,2 0,0.5 -0.04,1 -0.1,1.46 0.6,-0.5 1.32,-0.89 2.1,-1.14 V 10 C 9.25,9.32 9.19,8.66 9.11,8 h 3.38 c 0.16,0.64 0.26,1.31 0.26,2 v 0.18 c 0.7,0.17 1.35,0.45 1.95,0.82 0.05,-0.32 0.05,-0.66 0.05,-1 0,-5.5 -4.5,-10 -10,-10 -5.53,0 -10,4.5 -10,10 0,5.5 4.5,10 10,10 0.34,0 0.68,0 1,-0.05 C 5.34,19.29 5.04,18.55 4.88,17.75 4.84,17.82 4.8,17.89 4.75,17.96 3.92,16.76 3.25,15.43 2.84,14 h 2.41 c 0.31,-0.75 0.76,-1.42 1.32,-2 m 5.1,-6 H 8.72 A 15.7,15.7 0 0 0 7.34,2.44 C 9.18,3.07 10.71,4.34 11.67,6 M 4.75,2.03 C 5.58,3.23 6.25,4.57 6.66,6 H 2.84 C 3.25,4.57 3.92,3.23 4.75,2.03 M -2.99,12 c -0.16,-0.64 -0.26,-1.31 -0.26,-2 0,-0.69 0.1,-1.36 0.26,-2 h 3.38 c -0.08,0.66 -0.14,1.32 -0.14,2 0,0.68 0.06,1.34 0.14,2 z m 0.82,2 h 2.92 c 0.35,1.25 0.8,2.45 1.4,3.56 A 8,8 0 0 1 -2.17,14 M 0.75,6 H -2.17 A 7.92,7.92 0 0 1 2.15,2.44 C 1.55,3.55 1.1,4.75 0.75,6 m 10.5,6 c -2.5,0 -4.5,2 -4.5,4.5 0,2.5 2,4.5 4.5,4.5 2.5,0 4.5,-2 4.5,-4.5 0,-2.5 -2,-4.5 -4.5,-4.5 m 0,7.5 c -1.66,0 -3,-1.34 -3,-3 0,-0.56 0.15,-1.08 0.42,-1.5 l 4.08,4.08 c -0.42,0.27 -0.94,0.42 -1.5,0.42 M 13.83,18 9.75,13.92 c 0.42,-0.27 0.94,-0.42 1.5,-0.42 1.66,0 3,1.34 3,3 0,0.56 -0.15,1.08 -0.42,1.5"
     id="path1" />
</svg>`,"objects/malware-analysis":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-10.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="malware-analysis.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m -4,20 a 3,3 0 0 1 -3,-3 c 0,-0.6 0.18,-1.16 0.5,-1.63 L -1,5.81 V 4 A 1,1 0 0 1 -2,3 V 2 A 2,2 0 0 1 0,0 H 4 A 2,2 0 0 1 6,2 V 3 A 1,1 0 0 1 5,4 v 1.81 l 5.5,9.56 C 10.82,15.84 11,16.4 11,17 a 3,3 0 0 1 -3,3 z m -1,-3 a 1,1 0 0 0 1,1 H 8 A 1,1 0 0 0 9,17 C 9,16.79 8.93,16.59 8.82,16.43 L 6.53,12.47 4,15 -1.07,9.93 -4.82,16.43 C -4.93,16.59 -5,16.79 -5,17 M 3,8 A 1,1 0 0 0 2,9 1,1 0 0 0 3,10 1,1 0 0 0 4,9 1,1 0 0 0 3,8"
     id="path1" />
</svg>`,"objects/malware-config":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-5.2500 0.0000 17.5000 14.0000"
   version="1.1"
   id="svg2"
   sodipodi:docname="malware-config.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs2" />
  <g
     fill="none"
     stroke="currentColor"
     stroke-linecap="round"
     stroke-linejoin="round"
     id="g2"
     transform="translate(-3.5)">
    <path
       d="m 3.5,11.5 h -2 a 1,1 0 0 1 -1,-1 v -9 a 1,1 0 0 1 1,-1 h 6 l 3,3 V 4 M 6,6.5 7.3,7.8 M 6,13.5 7.3,12.2 M 7,10 H 5.5 M 13,6.5 11.7,7.8 m 1.3,5.7 -1.3,-1.3"
       id="path1" />
    <path
       d="m 7,9 a 2.5,2.5 0 1 1 5,0 v 2 a 2.5,2.5 0 0 1 -5,0 z m 5,1 h 1.5 M 7,9.5 h 5"
       id="path2" />
  </g>
</svg>`,"objects/malware":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-5.2500 0.0000 17.5000 14.0000"
   version="1.1"
   id="svg2"
   sodipodi:docname="malware.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs2" />
  <g
     fill="none"
     stroke="currentColor"
     stroke-linecap="round"
     stroke-linejoin="round"
     id="g2"
     transform="translate(-3.5)">
    <path
       d="m 3.5,11.5 h -2 a 1,1 0 0 1 -1,-1 v -9 a 1,1 0 0 1 1,-1 h 6 l 3,3 V 4 M 6,6.5 7.3,7.8 M 6,13.5 7.3,12.2 M 7,10 H 5.5 M 13,6.5 11.7,7.8 m 1.3,5.7 -1.3,-1.3"
       id="path1" />
    <path
       d="m 7,9 a 2.5,2.5 0 1 1 5,0 v 2 a 2.5,2.5 0 0 1 -5,0 z m 5,1 h 1.5 M 7,9.5 h 5"
       id="path2" />
  </g>
</svg>`,"objects/microblog":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-6.0000 0.0000 30.0000 24.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="microblog.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M -3,20 H 7 v 2 H -3 Z m 0,-6 H 7 v 2 H -3 Z M 19,10 H -1 A 2,2 0 0 1 -3,8 V 2 a 2,2 0 0 1 2,-2 h 20 a 2,2 0 0 1 2,2 v 6 a 2,2 0 0 1 -2,2 M -1,2 V 8 H 19 V 2 Z m 20,22 h -6 a 2,2 0 0 1 -2,-2 v -6 a 2,2 0 0 1 2,-2 h 6 a 2,2 0 0 1 2,2 v 6 a 2,2 0 0 1 -2,2 m -6,-8 v 6 h 6 v -6 z"
     id="path1" />
</svg>`,"objects/mutex":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-10.2500 0.0000 26.2500 21.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="mutex.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 2.875,16 a 2,2 0 0 0 2,-2 2,2 0 0 0 -2,-2 2,2 0 0 0 -2,2 2,2 0 0 0 2,2 m 6,-9 a 2,2 0 0 1 2,2 v 10 a 2,2 0 0 1 -2,2 h -12 a 2,2 0 0 1 -2,-2 V 9 a 2,2 0 0 1 2,-2 h 1 V 5 a 5,5 0 0 1 5,-5 5,5 0 0 1 5,5 v 2 z m -6,-5 a 3,3 0 0 0 -3,3 v 2 h 6 V 5 a 3,3 0 0 0 -3,-3"
     id="path1" />
</svg>`,"objects/netflow":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-9.7500 0.0000 17.5000 14.0000"
   version="1.1"
   id="svg2"
   sodipodi:docname="netflow.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs2" />
  <g
     fill="none"
     stroke="currentColor"
     stroke-linecap="round"
     stroke-linejoin="round"
     id="g2"
     transform="translate(-8)">
    <path
       d="m 7,10.5 v 3 m -5,0 h 10 m -5,-3 a 5,5 0 1 0 0,-10 5,5 0 0 0 0,10 m -5,-5 h 10"
       id="path1" />
    <path
       d="M 7,10.5 C 10,7.08 10,3.74 7,0.5 4.06,3.62 4,6.94 7,10.5"
       id="path2" />
  </g>
</svg>`,"objects/network-connection":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-6.5000 0.0000 17.5000 14.0000"
   version="1.1"
   id="svg2"
   sodipodi:docname="network-connection.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs2" />
  <g
     fill="none"
     stroke="currentColor"
     stroke-linecap="round"
     stroke-linejoin="round"
     id="g2"
     transform="translate(-4.75)">
    <path
       d="m 7,10.5 v 3 m -5,0 h 10 m -5,-3 a 5,5 0 1 0 0,-10 5,5 0 0 0 0,10 m -5,-5 h 10"
       id="path1" />
    <path
       d="M 7,10.5 C 10,7.08 10,3.74 7,0.5 4.06,3.62 4,6.94 7,10.5"
       id="path2" />
  </g>
</svg>`,"objects/network-data":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-9.7500 0.0000 17.5000 14.0000"
   version="1.1"
   id="svg2"
   sodipodi:docname="network-data.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs2" />
  <g
     fill="none"
     stroke="currentColor"
     stroke-linecap="round"
     stroke-linejoin="round"
     id="g2"
     transform="translate(-8)">
    <path
       d="m 7,10.5 v 3 m -5,0 h 10 m -5,-3 a 5,5 0 1 0 0,-10 5,5 0 0 0 0,10 m -5,-5 h 10"
       id="path1" />
    <path
       d="M 7,10.5 C 10,7.08 10,3.74 7,0.5 4.06,3.62 4,6.94 7,10.5"
       id="path2" />
  </g>
</svg>`,"objects/network-profile":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-9.7500 0.0000 17.5000 14.0000"
   version="1.1"
   id="svg2"
   sodipodi:docname="network-profile.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs2" />
  <g
     fill="none"
     stroke="currentColor"
     stroke-linecap="round"
     stroke-linejoin="round"
     id="g2"
     transform="translate(-8)">
    <path
       d="m 7,10.5 v 3 m -5,0 h 10 m -5,-3 a 5,5 0 1 0 0,-10 5,5 0 0 0 0,10 m -5,-5 h 10"
       id="path1" />
    <path
       d="M 7,10.5 C 10,7.08 10,3.74 7,0.5 4.06,3.62 4,6.94 7,10.5"
       id="path2" />
  </g>
</svg>`,"objects/network-socket":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-9.7500 0.0000 17.5000 14.0000"
   version="1.1"
   id="svg2"
   sodipodi:docname="network-socket.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs2" />
  <g
     fill="none"
     stroke="currentColor"
     stroke-linecap="round"
     stroke-linejoin="round"
     id="g2"
     transform="translate(-8)">
    <path
       d="m 7,10.5 v 3 m -5,0 h 10 m -5,-3 a 5,5 0 1 0 0,-10 5,5 0 0 0 0,10 m -5,-5 h 10"
       id="path1" />
    <path
       d="M 7,10.5 C 10,7.08 10,3.74 7,0.5 4.06,3.62 4,6.94 7,10.5"
       id="path2" />
  </g>
</svg>`,"objects/network-traffic":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-9.7500 0.0000 17.5000 14.0000"
   version="1.1"
   id="svg2"
   sodipodi:docname="network-traffic.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs2" />
  <g
     fill="none"
     stroke="currentColor"
     stroke-linecap="round"
     stroke-linejoin="round"
     id="g2"
     transform="translate(-8)">
    <path
       d="m 7,10.5 v 3 m -5,0 h 10 m -5,-3 a 5,5 0 1 0 0,-10 5,5 0 0 0 0,10 m -5,-5 h 10"
       id="path1" />
    <path
       d="M 7,10.5 C 10,7.08 10,3.74 7,0.5 4.06,3.62 4,6.94 7,10.5"
       id="path2" />
  </g>
</svg>`,"objects/news-agency":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-3.7500 0.0000 22.5000 18.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="news-agency.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M -0.5,18 Q -1.325,18 -1.912,17.413 -2.499,16.826 -2.5,16 V 0 L -0.825,1.675 0.825,0 2.5,1.675 4.175,0 5.825,1.675 7.5,0 9.175,1.675 10.825,0 12.5,1.675 14.175,0 15.825,1.675 17.5,0 v 16 q 0,0.825 -0.587,1.413 Q 16.326,18.001 15.5,18 Z m 0,-2 h 7 v -6 h -7 z m 9,0 h 7 v -2 h -7 z m 0,-4 h 7 v -2 h -7 z m -9,-4 h 16 V 5 h -16 z"
     id="path1" />
</svg>`,"objects/news-media":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-2.5000 0.0000 22.5000 18.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="news-media.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 0.75,18 Q -0.075,18 -0.662,17.413 -1.249,16.826 -1.25,16 V 0 L 0.425,1.675 2.075,0 3.75,1.675 5.425,0 7.075,1.675 8.75,0 10.425,1.675 12.075,0 13.75,1.675 15.425,0 17.075,1.675 18.75,0 v 16 q 0,0.825 -0.587,1.413 Q 17.576,18.001 16.75,18 Z m 0,-2 h 7 v -6 h -7 z m 9,0 h 7 v -2 h -7 z m 0,-4 h 7 v -2 h -7 z m -9,-4 h 16 V 5 h -16 z"
     id="path1" />
</svg>`,"objects/nse-script":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="0.0000 0.0000 511.9998 236.5239"
   version="1.1"
   id="svg1"
   sodipodi:docname="nse-script.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 450.3915,130.4779 c 2.128,1.475 4.178,2.3 6.484,3.554 1.87,1.017 3.773,1.97 5.649,2.973 1.462,0.781 4.171,2.425 2.529,4.345 -1.067,1.251 -3.65,1.055 -5.163,1.267 -2.399,0.333 -5.349,0.206 -7.74,0 -2.93,-0.254 -5.992,0.44 -8.974,0.44 -2.152,0 -4.32,0.093 -6.449,0.087 -0.767,-0.002 -1.734,0.176 -2.258,-0.5 -0.545,-0.702 -0.163,-1.482 0.263,-2.066 0.511,-0.696 0.992,-1.625 1.607,-2.169 0.55,-0.484 1.273,-0.82 1.825,-1.246 1.344,-1.036 1.811,-2.132 0.62,-3.47 -1.184,-1.333 -2.054,-2.276 -2.115,-4.162 -0.077,-2.409 1.453,-2.904 3.503,-3.43 3.07,-0.787 2.81,-0.26 5.381,1.21 1.231,0.705 4.256,2.763 4.838,3.167 m -391.837998,0.965 c -2.166,1.418 -4.237,2.19 -6.576,3.382 -1.895,0.968 -3.823,1.87 -5.724,2.825 -1.483,0.742 -4.234,2.313 -2.641,4.277 1.033,1.279 3.62,1.15 5.128,1.401 2.388,0.396 5.34,0.346 7.737,0.204 2.935,-0.179 5.978,0.597 8.958,0.673 2.152,0.059 4.316,0.208 6.445,0.257 0.766,0.018 1.728,0.222 2.27,-0.441 0.564,-0.686 0.202,-1.476 -0.209,-2.07 -0.492,-0.71 -0.949,-1.651 -1.549,-2.211 -0.538,-0.5 -1.25,-0.853 -1.791,-1.293 -1.317,-1.072 -1.756,-2.18 -0.53,-3.486 1.22,-1.302 2.114,-2.221 2.224,-4.105 0.14,-2.406 -1.303,-3.343 -3.413,-3.522 -2.714,-0.23 -2.609,0.327 -5.304,1.333 -1.33,0.496 -4.432,2.387 -5.025,2.776 m 451.021998,17.014 c -16.683,19.24 -48.328,9.606 -100.566,34.597 -69.325,33.167 -73.89,52.895 -153.634,53.459 -82.488,0.584 -84.365,-22.069 -157.444998,-54.632 -57.686,-25.703 -89.6310005,-14.17 -96.4600005,-34.303 -9.305,-26.434 27.8000005,-50.804996 48.0830005,-65.089996 C 141.5775,17.685904 181.6635,0.22890375 253.4225,0.29690375 c 77.032,-4.39699995 151.521,40.85100025 207.19,82.19200025 19.829,14.725 61.893,42.909996 48.963,65.967996 m -250.977,-16.505 -0.008,16.347 c 17.096,-1.496 30.743,-15.325 32.38,-32.767 l -16.36,0.032 c -1.384,8.431 -7.852,15.066 -16.012,16.388 m 9.442,-16.374 -9.435,0.018 -0.004,9.8 c 4.622,-1.169 8.253,-4.966 9.439,-9.818 m 0.1,-6.415 c -1.09,-5.014 -4.8,-8.955 -9.527,-10.154996 l -0.004,10.173996 z m -48.105,0.095 16.537,-0.033 c 1.223,-8.462 7.553,-15.199996 15.63,-16.707996 l 0.008,-16.795 c -17.234,1.628 -30.88,15.813 -32.175,33.535996 m 32.151,15.989 0.005,-9.638 -8.976,0.018 c 1.157,4.666 4.584,8.326 8.971,9.62 m -15.545,-9.607 -16.56,0.033 c 1.687,17.282 15.173,30.996 32.094,32.611 l 0.008,-16.405 c -7.92,-1.487 -14.159,-8.001 -15.542,-16.24 m 15.553,-6.446 0.005,-10.045996 c -4.534,1.332996 -8.07,5.181996 -9.114,10.063996 z m 38.809,-0.077 c -1.362,-17.727996 -15.091,-31.876996 -32.378,-33.405996 l -0.008,16.74 c 8.252,1.345 14.768,8.125996 16.04,16.698996 z m -71.367,86.084 c -34.085,-13.75 -58.083,-46.557 -58.083,-84.859 0,-20.927996 7.177,-40.209996 19.234,-55.647996 -25.098,10.645 -58.524,30.852 -113.736998,69.211996 -8.738,6.07 -35.162,13.14 -28.931,18.98 4.69,4.399 29.905,1.173 48.67,7.037 66.901998,20.907 96.913998,38.248 132.846998,45.278 m 226.023,-71.078 c -51.504,-36.985996 -86.776,-57.899996 -115.565,-69.266996 11.981,15.412 19.104,34.632 19.104,55.486996 0,37.031 -22.436,68.917 -54.727,83.42 43.165,-9.94 86.137,-32.789 127.146,-44.132 28.016,-7.751 38.995,-1.466 51.31,-7.623 4.965,-2.483 -20.128,-12.76 -27.268,-17.885"
     id="path1" />
</svg>`,"objects/organization":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-3.7500 0.0000 22.5000 18.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="organization.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 13.5,12 h -2 v 2 h 2 m 0,-6 h -2 v 2 h 2 m 2,6 h -8 v -2 h 2 v -2 h -2 v -2 h 2 V 8 h -2 V 6 h 8 M 5.5,4 h -2 V 2 h 2 m 0,6 h -2 V 6 h 2 m 0,6 h -2 v -2 h 2 m 0,6 h -2 v -2 h 2 M 1.5,4 h -2 V 2 h 2 m 0,6 h -2 V 6 h 2 m 0,6 h -2 v -2 h 2 m 0,6 h -2 v -2 h 2 M 7.5,4 V 0 h -10 v 18 h 20 V 4 Z"
     id="path1" />
</svg>`,"objects/passive-dns-dnsdbflex":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-10.5000 0.0000 35.0000 28.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="passive-dns-dnsdbflex.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 7,0 A 8,8 0 1 0 15,8 8.01,8.01 0 0 0 7,0 m 5.91,7 H 10.472 A 15.3,15.3 0 0 0 9.681,2.64 6.01,6.01 0 0 1 12.91,7 M 7.022,13.999 H 7.014 C 6.634,13.879 5.705,12.178 5.535,9 h 2.93 c -0.17,3.176 -1.094,4.877 -1.443,4.999 M 5.535,7 C 5.705,3.824 6.629,2.123 6.978,2.001 H 6.986 C 7.366,2.121 8.295,3.822 8.465,7 Z M 4.32,2.64 A 15.3,15.3 0 0 0 3.528,7 H 1.09 A 6.01,6.01 0 0 1 4.32,2.64 M 1.09,9 H 3.527 A 15.3,15.3 0 0 0 4.319,13.36 6.01,6.01 0 0 1 1.09,9 m 8.59,4.36 A 15.3,15.3 0 0 0 10.472,9 H 12.91 A 6.01,6.01 0 0 1 9.68,13.36 M 19,28 H -5 a 2,2 0 0 1 -2,-2 v -6 a 2,2 0 0 1 2,-2 h 24 a 2,2 0 0 1 2,2 v 6 a 2,2 0 0 1 -2,2 M -5,20 v 6 h 24 v -6 z"
     id="path1" />
  <circle
     cx="-2"
     cy="23"
     r="1"
     fill="currentColor"
     id="circle1" />
</svg>`,"objects/passive-dns":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-10.5000 0.0000 35.0000 28.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="passive-dns.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 7,0 A 8,8 0 1 0 15,8 8.01,8.01 0 0 0 7,0 m 5.91,7 H 10.472 A 15.3,15.3 0 0 0 9.681,2.64 6.01,6.01 0 0 1 12.91,7 M 7.022,13.999 H 7.014 C 6.634,13.879 5.705,12.178 5.535,9 h 2.93 c -0.17,3.176 -1.094,4.877 -1.443,4.999 M 5.535,7 C 5.705,3.824 6.629,2.123 6.978,2.001 H 6.986 C 7.366,2.121 8.295,3.822 8.465,7 Z M 4.32,2.64 A 15.3,15.3 0 0 0 3.528,7 H 1.09 A 6.01,6.01 0 0 1 4.32,2.64 M 1.09,9 H 3.527 A 15.3,15.3 0 0 0 4.319,13.36 6.01,6.01 0 0 1 1.09,9 m 8.59,4.36 A 15.3,15.3 0 0 0 10.472,9 H 12.91 A 6.01,6.01 0 0 1 9.68,13.36 M 19,28 H -5 a 2,2 0 0 1 -2,-2 v -6 a 2,2 0 0 1 2,-2 h 24 a 2,2 0 0 1 2,2 v 6 a 2,2 0 0 1 -2,2 M -5,20 v 6 h 24 v -6 z"
     id="path1" />
  <circle
     cx="-2"
     cy="23"
     r="1"
     fill="currentColor"
     id="circle1" />
</svg>`,"objects/passive-ssh":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="0.0000 0.0000 17.0000 6.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="passive-ssh.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 1,0 C 0.4,0 0,0.5 0,1 v 1.75 c 0,0.5 0.4,1 1,1 H 3.5 V 4.5 H 0 V 6 H 4 C 4.6,6 5,5.5 5,5 V 3.25 c 0,-0.5 -0.4,-1 -1,-1 H 1.5 V 1.5 H 5 V 0 Z M 7,0 C 6.4,0 6,0.5 6,1 v 1.75 c 0,0.5 0.4,1 1,1 H 9.5 V 4.5 H 6 V 6 h 4 c 0.6,0 1,-0.5 1,-1 V 3.25 c 0,-0.5 -0.4,-1 -1,-1 H 7.5 V 1.5 H 11 V 0 Z m 5,0 v 6 h 1.5 V 3.5 h 2 V 6 H 17 V 0 h -1.5 v 2 h -2 V 0 Z"
     id="path1" />
</svg>`,"objects/paste":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-14.2500 0.0000 27.5000 22.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="paste.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 6.5,20 h -14 V 4 h 2 v 3 h 10 V 4 h 2 m -7,-2 a 1,1 0 0 1 1,1 1,1 0 0 1 -1,1 1,1 0 0 1 -1,-1 1,1 0 0 1 1,-1 m 7,0 H 2.32 C 1.9,0.84 0.8,0 -0.5,0 -1.8,0 -2.9,0.84 -3.32,2 H -7.5 a 2,2 0 0 0 -2,2 v 16 a 2,2 0 0 0 2,2 h 14 a 2,2 0 0 0 2,-2 V 4 a 2,2 0 0 0 -2,-2"
     id="path1" />
</svg>`,"objects/pe-section":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-21.2550 0.0000 24.9700 19.9760"
   version="1.1"
   id="svg1"
   sodipodi:docname="pe-section.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M -5.1,2.42 A 6.1,6.1 0 0 0 -8.32,1.56 c -1.58,0 -2.79,0.78 -2.79,2 0,1.4 1.34,1.91 3.34,2.58 2.5,0.81 4.4,1.83 4.4,4.24 a 4.01,4.01 0 0 1 -1.8,3.23 c 0.65,0.61 1.01,1.47 1,2.36 0,2.82 -2.6,4 -5.1,4 -1.46,0.06 -2.91,-0.33 -4.15,-1.1 l 0.65,-1.53 c 1.04,0.71 2.27,1.09 3.53,1.1 1.72,0 3,-0.78 3,-2.2 0,-1.24 -0.78,-1.93 -3.28,-2.79 -2.75,-0.95 -4.65,-1.95 -4.65,-4.24 0.07,-1.32 0.83,-2.52 2,-3.14 -0.63,-0.57 -0.99,-1.4 -1,-2.26 0,-2.36 2.17,-3.81 4.93,-3.81 1.29,0 2.56,0.29 3.7,0.89 z m -4.32,9 c 1.06,0.33 2.09,0.76 3.06,1.29 0.65,-0.49 1.02,-1.26 1,-2.07 0,-1 -0.64,-1.88 -2.41,-2.5 -1.11,-0.37 -2.22,-0.83 -3.28,-1.37 -0.75,0.45 -1.22,1.26 -1.22,2.14 0,0.97 0.73,1.77 2.85,2.51"
     id="path1" />
</svg>`,"objects/pe":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-10.1250 0.0000 23.7500 19.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="pe.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M -6.75,9 V 3.75 l 6,-1.32 v 6.48 z m 17,-9 V 8.75 L 0.25,8.9 V 2.21 Z m -17,10 6,0.09 v 6.81 l -6,-1.15 z m 17,0.25 V 19 l -10,-1.91 V 10.1 Z"
     id="path1" />
</svg>`,"objects/person":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-6.0000 0.0000 20.0000 16.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="person.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 1.175,6.825 Q 0,5.65 0,4 0,2.35 1.175,1.175 2.35,0 4,0 5.65,0 6.825,1.175 8,2.35 8,4 8,5.65 6.825,6.825 5.65,8 4,8 2.35,8 1.175,6.825 M -4,16 V 13.2 Q -4,12.35 -3.562,11.638 -3.124,10.926 -2.4,10.55 -0.85,9.775 0.75,9.388 2.35,9.001 4,9 5.65,8.999 7.25,9.388 q 1.6,0.389 3.15,1.162 0.725,0.375 1.163,1.088 Q 12.001,12.351 12,13.2 V 16 Z"
     id="path1" />
</svg>`,"objects/personification":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-6.0000 0.0000 20.0000 16.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="personification.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 1.175,6.825 Q 0,5.65 0,4 0,2.35 1.175,1.175 2.35,0 4,0 5.65,0 6.825,1.175 8,2.35 8,4 8,5.65 6.825,6.825 5.65,8 4,8 2.35,8 1.175,6.825 M -4,16 V 13.2 Q -4,12.35 -3.562,11.638 -3.124,10.926 -2.4,10.55 -0.85,9.775 0.75,9.388 2.35,9.001 4,9 5.65,8.999 7.25,9.388 q 1.6,0.389 3.15,1.162 0.725,0.375 1.163,1.088 Q 12.001,12.351 12,13.2 V 16 Z"
     id="path1" />
</svg>`,"objects/phishing-kit":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-48.0000 0.0000 2080.0000 1664.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="phishing-kit.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 2016,0 V 1280 L 1888,1050 V 264 L 992,711 96,264 v 888 h 845 l -64,128 H -32 V 0 Z M 992,569 1873,128 H 111 Z m 384,455 h 128 v 320 h -128 z m 0,384 h 128 v 128 h -128 z m 64,-896 576,1152 H 864 Z m 395,1040 -395,-790 -395,790 z"
     id="path1" />
</svg>`,"objects/phishing":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-48.0000 0.0000 2080.0000 1664.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="phishing.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 2016,0 V 1280 L 1888,1050 V 264 L 992,711 96,264 v 888 h 845 l -64,128 H -32 V 0 Z M 992,569 1873,128 H 111 Z m 384,455 h 128 v 320 h -128 z m 0,384 h 128 v 128 h -128 z m 64,-896 576,1152 H 864 Z m 395,1040 -395,-790 -395,790 z"
     id="path1" />
</svg>`,"objects/phone-number":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-6.7500 0.0000 22.5000 18.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="phone-number.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m -0.88,7.79 c 1.44,2.83 3.76,5.14 6.59,6.59 l 2.2,-2.2 c 0.27,-0.27 0.67,-0.36 1.02,-0.24 1.12,0.37 2.33,0.57 3.57,0.57 0.55,0 1,0.45 1,1 V 17 c 0,0.55 -0.45,1 -1,1 -9.39,0 -17,-7.61 -17,-17 0,-0.55 0.45,-1 1,-1 H 0 C 0.55,0 1,0.45 1,1 1,2.25 1.2,3.45 1.57,4.57 1.68,4.92 1.6,5.31 1.32,5.59 Z"
     id="path1" />
</svg>`,"objects/phone":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-6.7500 0.0000 22.5000 18.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="phone.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m -0.88,7.79 c 1.44,2.83 3.76,5.14 6.59,6.59 l 2.2,-2.2 c 0.27,-0.27 0.67,-0.36 1.02,-0.24 1.12,0.37 2.33,0.57 3.57,0.57 0.55,0 1,0.45 1,1 V 17 c 0,0.55 -0.45,1 -1,1 -9.39,0 -17,-7.61 -17,-17 0,-0.55 0.45,-1 1,-1 H 0 C 0.55,0 1,0.45 1,1 1,2.25 1.2,3.45 1.57,4.57 1.68,4.92 1.6,5.31 1.32,5.59 Z"
     id="path1" />
</svg>`,"objects/physical-impact":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-251.8422 0.0000 680.0000 544.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="physical-impact.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 88.12484,0 c 13.3,0 24,10.7 24,24 v 48 c 0,13.3 -10.7,24 -24,24 -13.3,0 -24,-10.7 -24,-24 V 24 c 0,-13.3 10.7,-24 24,-24 m 0,160 c 12.4,0 22.7,9.4 23.9,21.7 l 13.5,141.9 174.2,-280.3 c 6.7,-10.7 20.5,-14.5 31.7,-8.5 11.2,6 15.8,19.5 10.6,31 l -137.1,304.8 c 2.2,2.3 4.3,4.7 6.3,7.1 l 97.2,-54.7 c 10.5,-5.9 23.6,-3.1 30.9,6.4 7.3,9.5 6.3,23 -2.2,31.5 l -87,87 h -71.4 c -13.2,-37.3 -48.7,-64 -90.5,-64 -41.8,0 -77.4,26.7 -90.4999999,64 H -81.875159 l -75.500001,-52.3 c -9.9,-6.6 -13.3,-19.5 -8.1,-30.1 5.2,-10.6 17.4,-15.9 28.7,-12.4 l 97.2,30.4 c 3,-3.9 6.1,-7.6 9.4,-11.3 L -92.475159,268.3 c -6.1,-10.1 -3.9,-23.1 5.1,-30.7 9,-7.6 22.199999,-7.5 31.099999,0.1 l 102.4,87.9 c 1.5,-0.4 3,-0.8 4.5,-1.1 l 13.6,-142.7 c 1.2,-12.3 11.5,-21.7 23.9,-21.7 z m -224,336 h 456 c 13.3,0 24,10.7 24,24 0,13.3 -10.7,24 -24,24 h -464 c -13.3,0 -24,-10.7 -24,-24 0,-13.3 10.7,-24 24,-24 z"
     id="path1" />
</svg>`,"objects/postal-address":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-48.7518 0.0000 62.5012 50.0010"
   version="1.1"
   id="svg1"
   sodipodi:docname="postal-address.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m -17.5012,0 c -8.284,0 -15,6.656 -15,14.866 0,8.21 15,35.135 15,35.135 0,0 15,-26.924 15,-35.135 0,-8.211 -6.716,-14.866 -15,-14.866 m -0.049,19.312 c -2.557,0 -4.629,-2.055 -4.629,-4.588 0,-2.535 2.072,-4.589 4.629,-4.589 2.559,0 4.631,2.054 4.631,4.589 0,2.533 -2.072,4.588 -4.631,4.588"
     id="path1" />
</svg>`,"objects/process":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-7.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg2"
   sodipodi:docname="process.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs2" />
  <g
     fill="none"
     stroke="currentColor"
     stroke-linecap="round"
     stroke-linejoin="round"
     stroke-width="2"
     id="g2"
     transform="translate(-7,-2)">
    <path
       d="M 5,6 A 1,1 0 0 1 6,5 h 12 a 1,1 0 0 1 1,1 v 12 a 1,1 0 0 1 -1,1 H 6 A 1,1 0 0 1 5,18 Z"
       id="path1" />
    <path
       d="m 9,9 h 6 v 6 H 9 Z M 3,10 H 5 M 3,14 H 5 M 10,3 v 2 m 4,-2 v 2 m 7,5 h -2 m 2,4 h -2 m -5,7 v -2 m -4,2 v -2"
       id="path2" />
  </g>
</svg>`,"objects/query":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-8.7713 0.0000 24.2375 19.3900"
   version="1.1"
   id="svg1"
   sodipodi:docname="query.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 8.8325,9.32 a 4.49,4.49 0 0 0 -6.36,0.01 4.49,4.49 0 0 0 0,6.36 4.51,4.51 0 0 0 5.57,0.63 l 3.11,3.07 1.39,-1.39 -3.09,-3.11 c 1.13,-1.77 0.87,-4.09 -0.62,-5.57 m -1.41,4.95 c -0.98,0.98 -2.56,0.97 -3.54,0 -0.97,-0.98 -0.97,-2.56 0.01,-3.54 0.97,-0.97 2.55,-0.97 3.53,0 0.97,0.98 0.97,2.56 0,3.54 m -6.37,2.83 a 6.5,6.5 0 0 1 -1.48,-2.32 c -3.15,-0.53 -5.42,-2.02 -5.42,-3.78 v 3 c 0,2.21 3.58,4 8,4 -0.4,-0.26 -0.77,-0.56 -1.1,-0.9 M -5.8475,6 v 3 c 0,1.68 2.07,3.12 5,3.7 v -0.2 c 0,-0.93 0.2,-1.85 0.58,-2.69 -3.24,-0.51 -5.58,-2.02 -5.58,-3.81 m 8,-6 c -4.42,0 -8,1.79 -8,4 0,2 3,3.68 6.85,4 h 0.05 c 1.2,-1.26 2.86,-2 4.6,-2 0.91,0 1.81,0.19 2.64,0.56 A 3.22,3.22 0 0 0 10.1525,4 c 0,-2.21 -3.58,-4 -8,-4"
     id="path1" />
</svg>`,"objects/reddit-account":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-7.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg2"
   sodipodi:docname="reddit-account.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs2" />
  <path
     fill="currentColor"
     d="M 3.75,11.04 C 3.75,10.47 3.28,10 2.71,10 2.14,10 1.67,10.47 1.67,11.04 a 1.04,1.04 0 1 0 2.08,0 m 3.34,2.37 C 6.64,13.86 5.68,14.02 5,14.02 4.32,14.02 3.36,13.86 2.91,13.41 a 0.26,0.26 0 0 0 -0.38,0 0.26,0.26 0 0 0 0,0.38 c 0.71,0.71 2.07,0.77 2.47,0.77 0.4,0 1.76,-0.06 2.47,-0.77 a 0.26,0.26 0 0 0 0,-0.38 c -0.1,-0.1 -0.27,-0.1 -0.38,0 M 7.29,10 c -0.57,0 -1.04,0.47 -1.04,1.04 0,0.57 0.47,1.04 1.04,1.04 0.57,0 1.04,-0.47 1.04,-1.04 C 8.33,10.47 7.87,10 7.29,10"
     id="path1" />
  <path
     fill="currentColor"
     d="M 5,0 C -0.52,0 -5,4.48 -5,10 -5,15.52 -0.52,20 5,20 10.52,20 15,15.52 15,10 15,4.48 10.52,0 5,0 m 5.8,11.33 c 0.02,0.14 0.03,0.29 0.03,0.44 0,2.24 -2.61,4.06 -5.83,4.06 -3.22,0 -5.83,-1.82 -5.83,-4.06 0,-0.15 0.01,-0.3 0.03,-0.44 C -1.31,11.1 -1.66,10.59 -1.66,10 A 1.455,1.455 0 0 1 0.81,8.95 C 1.82,8.22 3.22,7.76 4.77,7.71 L 5.51,4.22 C 5.52,4.15 5.56,4.09 5.62,4.06 5.68,4.02 5.75,4.01 5.82,4.02 l 2.42,0.52 a 1.04,1.04 0 1 1 0.93,1.5 C 8.61,6.04 8.16,5.6 8.13,5.05 L 5.96,4.59 5.3,7.71 c 1.53,0.05 2.9,0.52 3.9,1.24 a 1.455,1.455 0 1 1 1.6,2.38"
     id="path2" />
</svg>`,"objects/reddit-comment":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-7.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg2"
   sodipodi:docname="reddit-comment.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs2" />
  <path
     fill="currentColor"
     d="M 3.75,11.04 C 3.75,10.47 3.28,10 2.71,10 2.14,10 1.67,10.47 1.67,11.04 a 1.04,1.04 0 1 0 2.08,0 m 3.34,2.37 C 6.64,13.86 5.68,14.02 5,14.02 4.32,14.02 3.36,13.86 2.91,13.41 a 0.26,0.26 0 0 0 -0.38,0 0.26,0.26 0 0 0 0,0.38 c 0.71,0.71 2.07,0.77 2.47,0.77 0.4,0 1.76,-0.06 2.47,-0.77 a 0.26,0.26 0 0 0 0,-0.38 c -0.1,-0.1 -0.27,-0.1 -0.38,0 M 7.29,10 c -0.57,0 -1.04,0.47 -1.04,1.04 0,0.57 0.47,1.04 1.04,1.04 0.57,0 1.04,-0.47 1.04,-1.04 C 8.33,10.47 7.87,10 7.29,10"
     id="path1" />
  <path
     fill="currentColor"
     d="M 5,0 C -0.52,0 -5,4.48 -5,10 -5,15.52 -0.52,20 5,20 10.52,20 15,15.52 15,10 15,4.48 10.52,0 5,0 m 5.8,11.33 c 0.02,0.14 0.03,0.29 0.03,0.44 0,2.24 -2.61,4.06 -5.83,4.06 -3.22,0 -5.83,-1.82 -5.83,-4.06 0,-0.15 0.01,-0.3 0.03,-0.44 C -1.31,11.1 -1.66,10.59 -1.66,10 A 1.455,1.455 0 0 1 0.81,8.95 C 1.82,8.22 3.22,7.76 4.77,7.71 L 5.51,4.22 C 5.52,4.15 5.56,4.09 5.62,4.06 5.68,4.02 5.75,4.01 5.82,4.02 l 2.42,0.52 a 1.04,1.04 0 1 1 0.93,1.5 C 8.61,6.04 8.16,5.6 8.13,5.05 L 5.96,4.59 5.3,7.71 c 1.53,0.05 2.9,0.52 3.9,1.24 a 1.455,1.455 0 1 1 1.6,2.38"
     id="path2" />
</svg>`,"objects/reddit-post":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-5.0000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg2"
   sodipodi:docname="reddit-post.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs2" />
  <path
     fill="currentColor"
     d="M 6.25,11.04 C 6.25,10.47 5.78,10 5.21,10 4.64,10 4.17,10.47 4.17,11.04 a 1.04,1.04 0 1 0 2.08,0 m 3.34,2.37 c -0.45,0.45 -1.41,0.61 -2.09,0.61 -0.68,0 -1.64,-0.16 -2.09,-0.61 a 0.26,0.26 0 0 0 -0.38,0 0.26,0.26 0 0 0 0,0.38 c 0.71,0.71 2.07,0.77 2.47,0.77 0.4,0 1.76,-0.06 2.47,-0.77 a 0.26,0.26 0 0 0 0,-0.38 c -0.1,-0.1 -0.27,-0.1 -0.38,0 M 9.79,10 c -0.57,0 -1.04,0.47 -1.04,1.04 0,0.57 0.47,1.04 1.04,1.04 0.57,0 1.04,-0.47 1.04,-1.04 C 10.83,10.47 10.37,10 9.79,10"
     id="path1" />
  <path
     fill="currentColor"
     d="m 7.5,0 c -5.52,0 -10,4.48 -10,10 0,5.52 4.48,10 10,10 5.52,0 10,-4.48 10,-10 0,-5.52 -4.48,-10 -10,-10 m 5.8,11.33 c 0.02,0.14 0.03,0.29 0.03,0.44 0,2.24 -2.61,4.06 -5.83,4.06 -3.22,0 -5.83,-1.82 -5.83,-4.06 0,-0.15 0.01,-0.3 0.03,-0.44 C 1.19,11.1 0.84,10.59 0.84,10 A 1.455,1.455 0 0 1 3.31,8.95 C 4.32,8.22 5.72,7.76 7.27,7.71 L 8.01,4.22 C 8.02,4.15 8.06,4.09 8.12,4.06 8.18,4.02 8.25,4.01 8.32,4.02 l 2.42,0.52 a 1.04,1.04 0 1 1 0.93,1.5 C 11.11,6.04 10.66,5.6 10.63,5.05 L 8.46,4.59 7.8,7.71 c 1.53,0.05 2.9,0.52 3.9,1.24 a 1.455,1.455 0 1 1 1.6,2.38"
     id="path2" />
</svg>`,"objects/reddit-subreddit":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-7.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg2"
   sodipodi:docname="reddit-subreddit.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs2" />
  <path
     fill="currentColor"
     d="M 3.75,11.04 C 3.75,10.47 3.28,10 2.71,10 2.14,10 1.67,10.47 1.67,11.04 a 1.04,1.04 0 1 0 2.08,0 m 3.34,2.37 C 6.64,13.86 5.68,14.02 5,14.02 4.32,14.02 3.36,13.86 2.91,13.41 a 0.26,0.26 0 0 0 -0.38,0 0.26,0.26 0 0 0 0,0.38 c 0.71,0.71 2.07,0.77 2.47,0.77 0.4,0 1.76,-0.06 2.47,-0.77 a 0.26,0.26 0 0 0 0,-0.38 c -0.1,-0.1 -0.27,-0.1 -0.38,0 M 7.29,10 c -0.57,0 -1.04,0.47 -1.04,1.04 0,0.57 0.47,1.04 1.04,1.04 0.57,0 1.04,-0.47 1.04,-1.04 C 8.33,10.47 7.87,10 7.29,10"
     id="path1" />
  <path
     fill="currentColor"
     d="M 5,0 C -0.52,0 -5,4.48 -5,10 -5,15.52 -0.52,20 5,20 10.52,20 15,15.52 15,10 15,4.48 10.52,0 5,0 m 5.8,11.33 c 0.02,0.14 0.03,0.29 0.03,0.44 0,2.24 -2.61,4.06 -5.83,4.06 -3.22,0 -5.83,-1.82 -5.83,-4.06 0,-0.15 0.01,-0.3 0.03,-0.44 C -1.31,11.1 -1.66,10.59 -1.66,10 A 1.455,1.455 0 0 1 0.81,8.95 C 1.82,8.22 3.22,7.76 4.77,7.71 L 5.51,4.22 C 5.52,4.15 5.56,4.09 5.62,4.06 5.68,4.02 5.75,4.01 5.82,4.02 l 2.42,0.52 a 1.04,1.04 0 1 1 0.93,1.5 C 8.61,6.04 8.16,5.6 8.13,5.05 L 5.96,4.59 5.3,7.71 c 1.53,0.05 2.9,0.52 3.9,1.24 a 1.455,1.455 0 1 1 1.6,2.38"
     id="path2" />
</svg>`,"objects/regexp":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-4.0000 0.0000 20.0000 16.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="regexp.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 9,11.92 C 8.67,11.97 8.34,12 8,12 7.66,12 7.33,11.97 7,11.92 V 8.41 L 4.5,10.89 C 4,10.5 3.5,10 3.11,9.5 L 5.59,7 H 2.08 C 2.03,6.67 2,6.34 2,6 2,5.66 2.03,5.33 2.08,5 H 5.59 L 3.11,2.5 C 3.3,2.25 3.5,2 3.76,1.76 4,1.5 4.25,1.3 4.5,1.11 L 7,3.59 V 0.08 C 7.33,0.03 7.66,0 8,0 8.34,0 8.67,0.03 9,0.08 V 3.59 L 11.5,1.11 C 12,1.5 12.5,2 12.89,2.5 L 10.41,5 h 3.51 C 13.97,5.33 14,5.66 14,6 14,6.34 13.97,6.67 13.92,7 h -3.51 l 2.48,2.5 C 12.7,9.75 12.5,10 12.24,10.24 12,10.5 11.75,10.7 11.5,10.89 L 9,8.41 Z M -2,14 a 2,2 0 0 1 2,-2 2,2 0 0 1 2,2 2,2 0 0 1 -2,2 2,2 0 0 1 -2,-2"
     id="path1" />
</svg>`,"objects/registry-key-value":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-744.0000 0.0000 2480.0000 1984.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="registry-key-value.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 656,832 h 512 V 1984 H -496 V 320 H 656 Z M 144,448 V 832 H 528 V 448 Z m 384,896 V 960 H 144 v 384 z M -368,448 V 832 H 16 V 448 Z m 0,512 v 384 H 16 V 960 Z m 384,896 v -384 h -384 v 384 z m 512,0 V 1472 H 144 v 384 z m 512,0 V 1472 H 656 v 384 z M 656,1344 h 384 V 960 H 656 Z M 1488,384 1104,768 720,384 1104,0 Z M 1104,145 865,384 1104,623 1343,384 Z"
     id="path1" />
</svg>`,"objects/registry-key":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-744.0000 0.0000 2480.0000 1984.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="registry-key.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 656,832 h 512 V 1984 H -496 V 320 H 656 Z M 144,448 V 832 H 528 V 448 Z m 384,896 V 960 H 144 v 384 z M -368,448 V 832 H 16 V 448 Z m 0,512 v 384 H 16 V 960 Z m 384,896 v -384 h -384 v 384 z m 512,0 V 1472 H 144 v 384 z m 512,0 V 1472 H 656 v 384 z M 656,1344 h 384 V 960 H 656 Z M 1488,384 1104,768 720,384 1104,0 Z M 1104,145 865,384 1104,623 1343,384 Z"
     id="path1" />
</svg>`,"objects/report":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-9.3750 0.0000 26.2500 21.0000"
   version="1.1"
   id="svg2"
   sodipodi:docname="report.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs2" />
  <g
     fill="none"
     stroke="currentColor"
     stroke-linecap="round"
     stroke-linejoin="round"
     stroke-width="2"
     id="g2"
     transform="translate(-9.25,-2)">
    <path
       d="M 8,5 H 6 A 2,2 0 0 0 4,7 v 12 a 2,2 0 0 0 2,2 h 5.697 M 18,14 v 4 h 4 M 18,11 V 7 A 2,2 0 0 0 16,5 h -2"
       id="path1" />
    <path
       d="m 8,5 a 2,2 0 0 1 2,-2 h 2 a 2,2 0 0 1 2,2 2,2 0 0 1 -2,2 H 10 A 2,2 0 0 1 8,5 m 6,13 a 4,4 0 1 0 8,0 4,4 0 1 0 -8,0 M 8,11 h 4 m -4,4 h 3"
       id="path2" />
  </g>
</svg>`,"objects/risk-assessment-report":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-9.3750 0.0000 26.2500 21.0000"
   version="1.1"
   id="svg2"
   sodipodi:docname="risk-assessment-report.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs2" />
  <g
     fill="none"
     stroke="currentColor"
     stroke-linecap="round"
     stroke-linejoin="round"
     stroke-width="2"
     id="g2"
     transform="translate(-9.25,-2)">
    <path
       d="M 8,5 H 6 A 2,2 0 0 0 4,7 v 12 a 2,2 0 0 0 2,2 h 5.697 M 18,14 v 4 h 4 M 18,11 V 7 A 2,2 0 0 0 16,5 h -2"
       id="path1" />
    <path
       d="m 8,5 a 2,2 0 0 1 2,-2 h 2 a 2,2 0 0 1 2,2 2,2 0 0 1 -2,2 H 10 A 2,2 0 0 1 8,5 m 6,13 a 4,4 0 1 0 8,0 4,4 0 1 0 -8,0 M 8,11 h 4 m -4,4 h 3"
       id="path2" />
  </g>
</svg>`,"objects/sandbox-report":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-22.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="sandbox-report.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m -15,0 v 2 h 1 v 14 a 4,4 0 0 0 4,4 4,4 0 0 0 4,-4 V 2 h 1 V 0 Z m 4,14 c -0.6,0 -1,-0.4 -1,-1 0,-0.6 0.4,-1 1,-1 0.6,0 1,0.4 1,1 0,0.6 -0.4,1 -1,1 m 2,-4 c -0.6,0 -1,-0.4 -1,-1 0,-0.6 0.4,-1 1,-1 0.6,0 1,0.4 1,1 0,0.6 -0.4,1 -1,1 m 1,-5 h -4 V 2 h 4 z"
     id="path1" />
</svg>`,"objects/scan-result":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-4.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="scan-result.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 9,7 h 5 L 9,2 Z M 2,20 Q 1.175,20 0.588,19.413 10e-4,18.826 0,18 v -3 h 16 v 3 q 0,0.825 -0.587,1.413 Q 14.826,20.001 14,20 Z m -5,-7 v -2 h 22 v 2 z M 0,9 V 2 Q 0,1.175 0.588,0.588 1.176,0.001 2,0 h 8 l 6,6 v 3 z"
     id="path1" />
</svg>`,"objects/scheduled-event":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-6.0000 0.0000 20.0000 16.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="scheduled-event.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     fill-rule="evenodd"
     d="m 4,14.5 a 6.5,6.5 0 1 1 0,-13 6.5,6.5 0 0 1 0,13 M -4,8 A 8,8 0 1 1 12,8 8,8 0 0 1 -4,8 M 5,9 V 4 H 3.5 v 3.5 h -2 V 9 Z"
     clip-rule="evenodd"
     id="path1" />
</svg>`,"objects/scheduled-task":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-6.0000 0.0000 20.0000 16.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="scheduled-task.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     fill-rule="evenodd"
     d="m 4,14.5 a 6.5,6.5 0 1 1 0,-13 6.5,6.5 0 0 1 0,13 M -4,8 A 8,8 0 1 1 12,8 8,8 0 0 1 -4,8 M 5,9 V 4 H 3.5 v 3.5 h -2 V 9 Z"
     clip-rule="evenodd"
     id="path1" />
</svg>`,"objects/script":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-8.2500 0.0000 17.5000 14.0000"
   version="1.1"
   id="svg2"
   sodipodi:docname="script.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs2" />
  <path
     fill="currentColor"
     d="m -2.35,6.1500008 a 0.5,0.5 0 0 1 0.707,0 l 2,2 a 0.5,0.5 0 0 1 0,0.707 l -2,2.0000002 a 0.5,0.5 0 0 1 -0.707,-0.707 l 1.65,-1.6500002 -1.65,-1.65 a 0.5,0.5 0 0 1 0,-0.707 z M 3.5,10.500001 a 0.5,0.5 0 0 0 -0.5,-0.5 H 1 a 0.5,0.5 0 0 0 0,1 h 2 a 0.5,0.5 0 0 0 0.5,-0.5"
     id="path1" />
  <path
     fill="currentColor"
     fill-rule="evenodd"
     d="m -3.5,7.9741689e-7 c -1.1,0 -2,0.89500000258311 -2,2.00000000258311 V 12.000001 c 0,1.1 0.895,2 2,2 h 8 c 1.1,0 2,-0.895 2,-2 V 4.5000008 a 0.5,0.5 0 0 0 -0.146,-0.354 l -4,-4 A 0.5,0.5 0 0 0 2,7.9741689e-7 Z M -4.5,2.0000008 a 1,1 0 0 1 1,-1 h 5 v 3.5 a 0.5,0.5 0 0 0 0.5,0.5 h 3.5 v 7.0000002 a 1,1 0 0 1 -1,1 h -8 a 1,1 0 0 1 -1,-1 z m 9.29,2 -2.29,-2.29 v 2.29 z"
     clip-rule="evenodd"
     id="path2" />
</svg>`,"objects/service":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-14.2500 0.0000 27.5000 22.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="service.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m -8.5,0 h 16 a 1,1 0 0 1 1,1 v 4 a 1,1 0 0 1 -1,1 h -16 a 1,1 0 0 1 -1,-1 V 1 a 1,1 0 0 1 1,-1 m 0,8 h 16 a 1,1 0 0 1 1,1 v 4 a 1,1 0 0 1 -1,1 h -16 a 1,1 0 0 1 -1,-1 V 9 a 1,1 0 0 1 1,-1 m 0,8 h 16 a 1,1 0 0 1 1,1 v 4 a 1,1 0 0 1 -1,1 h -16 a 1,1 0 0 1 -1,-1 v -4 a 1,1 0 0 1 1,-1 m 5,-12 h 1 V 2 h -1 z m 0,8 h 1 v -2 h -1 z m 0,8 h 1 v -2 h -1 z m -4,-18 v 2 h 2 V 2 Z m 0,8 v 2 h 2 v -2 z m 0,8 v 2 h 2 v -2 z"
     id="path1" />
</svg>`,"objects/shell-commands":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-4.8752 0.0000 24.3761 19.5009"
   version="1.1"
   id="svg2"
   sodipodi:docname="shell-commands.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs2" />
  <g
     fill="none"
     stroke="currentColor"
     stroke-linecap="round"
     stroke-linejoin="round"
     stroke-width="1.5"
     id="g2"
     transform="translate(-4.6871558,-2.2495558)">
    <path
       d="M 7,7 8.227,8.057 C 8.742,8.502 9,8.724 9,9 9,9.276 8.742,9.498 8.227,9.943 L 7,11 m 4,0 h 3"
       id="path1" />
    <path
       d="m 12,21 c 3.75,0 5.625,0 6.939,-0.955 a 5,5 0 0 0 1.106,-1.106 C 21,17.625 21,15.749 21,12 21,8.251 21,6.375 20.045,5.061 A 5,5 0 0 0 18.939,3.955 C 17.625,3 15.749,3 12,3 8.251,3 6.375,3 5.061,3.955 A 5,5 0 0 0 3.955,5.06 C 3,6.375 3,8.251 3,12 c 0,3.749 0,5.625 0.955,6.939 a 5,5 0 0 0 1.106,1.106 C 6.375,21 8.251,21 12,21"
       id="path2" />
  </g>
</svg>`,"objects/shortened-link":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-6.9321 0.0000 23.1067 18.4854"
   version="1.1"
   id="svg1"
   sodipodi:docname="shortened-link.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 3.2112916,10.652692 c 0.41,0.39 0.41,1.03 0,1.42 -0.39,0.39 -1.03,0.39 -1.42,0 a 5.003,5.003 0 0 1 0,-7.0700004 l 3.54,-3.54 a 5.003,5.003 0 0 1 7.0700004,0 5.003,5.003 0 0 1 0,7.07 l -1.49,1.4900004 c 0.01,-0.8200004 -0.12,-1.6400004 -0.4,-2.4200004 l 0.47,-0.48 a 2.98,2.98 0 0 0 0,-4.24 2.98,2.98 0 0 0 -4.2399999,0 l -3.5300005,3.53 a 2.98,2.98 0 0 0 0,4.2400004 M 6.0312921,6.4126916 c 0.39,-0.39 1.03,-0.39 1.42,0 a 5.003,5.003 0 0 1 0,7.0700004 l -3.5400005,3.54 a 5.003,5.003 0 0 1 -7.07,0 5.003,5.003 0 0 1 0,-7.0700004 l 1.49,-1.49 c -0.01,0.82 0.12,1.6400004 0.4,2.4300004 l -0.47,0.47 a 2.98,2.98 0 0 0 0,4.24 2.98,2.98 0 0 0 4.24,0 l 3.5300005,-3.53 a 2.98,2.98 0 0 0 0,-4.2400004 0.973,0.973 0 0 1 0,-1.42"
     id="path1" />
</svg>`,"objects/software-package":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-11.0571 0.0000 26.8748 21.4998"
   version="1.1"
   id="svg4"
   sodipodi:docname="software-package.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs4" />
  <g
     fill="none"
     stroke="currentColor"
     stroke-width="1.5"
     id="g4"
     transform="translate(-9.6196898,-1.2502351)">
    <path
       d="m 10,10 a 2,2 0 1 0 4,0 2,2 0 0 0 -4,0 z"
       id="path1" />
    <path
       stroke-linecap="round"
       d="M 18.245,15 A 8,8 0 1 0 5.755,15"
       id="path2" />
    <path
       d="M 3,18.5 C 3,17.096 3,16.393 3.303,15.889 3.435,15.671 3.603,15.483 3.8,15.337 4.254,15 4.886,15 6.15,15 h 11.7 c 1.264,0 1.896,0 2.35,0.337 0.197,0.146 0.365,0.334 0.497,0.552 C 21,16.393 21,17.096 21,18.5 c 0,1.404 0,2.107 -0.303,2.611 -0.132,0.218 -0.3,0.406 -0.497,0.552 C 19.746,22 19.114,22 17.85,22 H 6.15 C 4.886,22 4.254,22 3.8,21.663 A 1.9,1.9 0 0 1 3.303,21.111 C 3,20.607 3,19.904 3,18.5 Z"
       id="path3" />
    <path
       stroke-linecap="round"
       stroke-linejoin="round"
       d="m 11,18 h 2 M 15.89,6.61 17.902,4.6"
       id="path4" />
  </g>
</svg>`,"objects/software":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-7.3714 0.0000 26.8748 21.4998"
   version="1.1"
   id="svg4"
   sodipodi:docname="software.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs4" />
  <g
     fill="none"
     stroke="currentColor"
     stroke-width="1.5"
     id="g4"
     transform="translate(-5.9339898,-1.2502351)">
    <path
       d="m 10,10 a 2,2 0 1 0 4,0 2,2 0 0 0 -4,0 z"
       id="path1" />
    <path
       stroke-linecap="round"
       d="M 18.245,15 A 8,8 0 1 0 5.755,15"
       id="path2" />
    <path
       d="M 3,18.5 C 3,17.096 3,16.393 3.303,15.889 3.435,15.671 3.603,15.483 3.8,15.337 4.254,15 4.886,15 6.15,15 h 11.7 c 1.264,0 1.896,0 2.35,0.337 0.197,0.146 0.365,0.334 0.497,0.552 C 21,16.393 21,17.096 21,18.5 c 0,1.404 0,2.107 -0.303,2.611 -0.132,0.218 -0.3,0.406 -0.497,0.552 C 19.746,22 19.114,22 17.85,22 H 6.15 C 4.886,22 4.254,22 3.8,21.663 A 1.9,1.9 0 0 1 3.303,21.111 C 3,20.607 3,19.904 3,18.5 Z"
       id="path3" />
    <path
       stroke-linecap="round"
       stroke-linejoin="round"
       d="m 11,18 h 2 M 15.89,6.61 17.902,4.6"
       id="path4" />
  </g>
</svg>`,"objects/spearphishing-attachment":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-48.0000 0.0000 2080.0000 1664.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="spearphishing-attachment.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 2016,0 V 1280 L 1888,1050 V 264 L 992,711 96,264 v 888 h 845 l -64,128 H -32 V 0 Z M 992,569 1873,128 H 111 Z m 384,455 h 128 v 320 h -128 z m 0,384 h 128 v 128 h -128 z m 64,-896 576,1152 H 864 Z m 395,1040 -395,-790 -395,790 z"
     id="path1" />
</svg>`,"objects/spearphishing-campaign":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-48.0000 0.0000 2080.0000 1664.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="spearphishing-campaign.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 2016,0 V 1280 L 1888,1050 V 264 L 992,711 96,264 v 888 h 845 l -64,128 H -32 V 0 Z M 992,569 1873,128 H 111 Z m 384,455 h 128 v 320 h -128 z m 0,384 h 128 v 128 h -128 z m 64,-896 576,1152 H 864 Z m 395,1040 -395,-790 -395,790 z"
     id="path1" />
</svg>`,"objects/spearphishing-link":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-48.0000 0.0000 2080.0000 1664.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="spearphishing-link.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 2016,0 V 1280 L 1888,1050 V 264 L 992,711 96,264 v 888 h 845 l -64,128 H -32 V 0 Z M 992,569 1873,128 H 111 Z m 384,455 h 128 v 320 h -128 z m 0,384 h 128 v 128 h -128 z m 64,-896 576,1152 H 864 Z m 395,1040 -395,-790 -395,790 z"
     id="path1" />
</svg>`,"objects/splunk":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="0.0000 0.0000 24.0000 7.1200"
   version="1.1"
   id="svg1"
   sodipodi:docname="splunk.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 23.348,3.471 21.107,2.38 V 1.73 L 24,3.181 V 3.774 L 21.107,5.212 V 4.576 Z M 17.951,5.312 H 16.99 v -5.31 h 0.961 v 3.116 h 0.102 l 1.28,-1.481 0.723,0.31 -1.23,1.316 1.453,1.809 -0.888,0.311 -1.44,-1.996 z M 15.374,5.31 V 3.242 a 3,3 0 0 0 -0.026,-0.42 0.8,0.8 0 0 0 -0.09,-0.26 Q 15.09,2.259 14.668,2.258 a 0.9,0.9 0 0 0 -0.461,0.113 0.67,0.67 0 0 0 -0.286,0.33 1,1 0 0 0 -0.07,0.263 q -0.019,0.195 -0.017,0.395 v 1.95 H 12.873 V 1.695 h 0.961 l 0.002,0.485 q 0.277,-0.302 0.566,-0.437 0.29,-0.134 0.673,-0.134 0.43,0 0.721,0.177 a 1.02,1.02 0 0 1 0.475,0.665 2,2 0 0 1 0.054,0.448 q 0.003,0.15 0.004,0.358 V 5.31 Z M 11.259,5.312 11.257,4.827 a 1.8,1.8 0 0 1 -0.565,0.437 1.6,1.6 0 0 1 -0.674,0.135 q -0.427,0 -0.72,-0.17 A 0.97,0.97 0 0 1 8.873,4.725 1,1 0 0 1 8.819,4.558 2,2 0 0 1 8.786,4.359 2,2 0 0 1 8.769,4.101 L 8.764,3.746 V 1.69 H 9.72 v 2.07 q -0.004,0.212 0.026,0.42 0.023,0.139 0.09,0.26 0.168,0.306 0.59,0.306 0.54,0 0.74,-0.449 0.053,-0.123 0.074,-0.257 0.025,-0.201 0.022,-0.403 v -1.95 h 0.955 V 5.311 Z M 7.184,0 H 8.139 V 5.31 H 7.184 Z M 5.759,3.46 q 0,-0.594 -0.24,-0.937 A 0.76,0.76 0 0 0 4.862,2.178 0.8,0.8 0 0 0 4.169,2.544 q -0.257,0.367 -0.253,0.99 0,0.607 0.25,0.957 A 0.8,0.8 0 0 0 4.856,4.838 0.7,0.7 0 0 0 5.289,4.703 1,1 0 0 0 5.566,4.363 C 5.637,4.223 5.687,4.071 5.713,3.915 Q 5.756,3.691 5.759,3.46 M 6.769,3.424 C 6.772,3.69 6.729,3.956 6.64,4.21 Q 6.517,4.557 6.276,4.836 C 5.966,5.197 5.512,5.403 5.036,5.399 A 1.7,1.7 0 0 1 4.723,5.371 1,1 0 0 1 4.448,5.273 1.3,1.3 0 0 1 4.191,5.095 2.4,2.4 0 0 1 3.926,4.827 V 7.12 H 2.997 V 1.695 h 0.93 L 3.931,2.224 Q 4.185,1.906 4.481,1.756 4.776,1.606 5.169,1.609 a 1.5,1.5 0 0 1 1.156,0.507 c 0.148,0.166 0.259,0.361 0.33,0.571 0.08,0.236 0.12,0.485 0.115,0.737 M 2.56,4.314 A 0.95,0.95 0 0 1 2.458,4.755 1,1 0 0 1 2.176,5.1 Q 1.98,5.25 1.746,5.32 A 1.8,1.8 0 0 1 1.2,5.4 2,2 0 0 1 0.563,5.303 2,2 0 0 1 0,4.983 L 0.312,4.478 Q 0.536,4.667 0.717,4.753 0.891,4.839 1.085,4.84 A 0.56,0.56 0 0 0 1.458,4.72 0.4,0.4 0 0 0 1.598,4.398 0.48,0.48 0 0 0 1.478,4.08 1.3,1.3 0 0 0 1.291,3.907 9,9 0 0 0 0.983,3.675 7,7 0 0 1 0.702,3.465 2,2 0 0 1 0.45,3.233 1,1 0 0 1 0.27,2.958 0.8,0.8 0 0 1 0.201,2.611 0.9,0.9 0 0 1 0.295,2.202 0.9,0.9 0 0 1 0.55,1.888 1.2,1.2 0 0 1 0.94,1.685 Q 1.182,1.61 1.434,1.613 q 0.278,0 0.545,0.076 0.262,0.075 0.488,0.219 L 2.185,2.362 A 1.05,1.05 0 0 0 1.577,2.161 0.5,0.5 0 0 0 1.254,2.263 0.3,0.3 0 0 0 1.128,2.516 c 0,0.098 0.041,0.193 0.113,0.26 Q 1.353,2.893 1.626,3.101 1.903,3.304 2.083,3.456 C 2.187,3.541 2.285,3.638 2.369,3.742 Q 2.468,3.864 2.514,4.015 A 0.8,0.8 0 0 1 2.56,4.314"
     id="path1" />
</svg>`,"objects/ssh-authorized-keys":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-8.0208 0.0000 22.6773 18.1419"
   version="1.1"
   id="svg2"
   sodipodi:docname="ssh-authorized-keys.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs2" />
  <g
     fill="currentColor"
     fill-rule="evenodd"
     clip-rule="evenodd"
     id="g2"
     transform="translate(-9.0018036,-3.3117535)">
    <path
       d="m 20.854,10.308 c 0.6,2.411 -0.923,4.867 -3.403,5.486 q -0.466,0.115 -0.928,0.137 l -2.666,4.298 a 2,2 0 0 1 -1.216,0.887 l -1.236,0.308 a 1,1 0 0 1 -1.212,-0.729 l -0.28,-1.12 a 2,2 0 0 1 0.241,-1.538 l 2.445,-3.943 a 4.4,4.4 0 0 1 -0.728,-1.547 c -0.6,-2.411 0.922,-4.867 3.403,-5.486 2.481,-0.619 4.978,0.835 5.58,3.247 m -3.872,1.48 c 0.552,-0.137 0.89,-0.683 0.756,-1.219 -0.133,-0.536 -0.688,-0.859 -1.24,-0.721 -0.55,0.137 -0.89,0.683 -0.756,1.219 0.134,0.536 0.69,0.859 1.24,0.721"
       id="path1" />
    <path
       d="M 11.251,12.187 C 13.731,11.568 15.255,9.112 14.654,6.701 14.053,4.289 11.554,2.836 9.074,3.454 6.594,4.072 5.07,6.529 5.672,8.94 A 4.4,4.4 0 0 0 6.4,10.487 l -2.445,3.942 a 2,2 0 0 0 -0.241,1.538 l 0.28,1.121 a 1,1 0 0 0 1.211,0.728 l 1.236,-0.308 a 2,2 0 0 0 1.216,-0.886 l 2.666,-4.298 q 0.462,-0.022 0.928,-0.137 M 11.539,6.962 C 11.672,7.498 11.334,8.044 10.783,8.181 10.232,8.318 9.677,7.995 9.543,7.46 9.409,6.924 9.748,6.378 10.299,6.24 c 0.551,-0.138 1.106,0.186 1.24,0.722"
       id="path2" />
  </g>
</svg>`,"objects/stix2-pattern":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-6.7500 0.0000 22.5000 18.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="stix2-pattern.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 0.5,0 a 2,2 0 0 0 -2,2 v 4 a 2,2 0 0 1 -2,2 h -1 v 2 h 1 a 2,2 0 0 1 2,2 v 4 a 2,2 0 0 0 2,2 h 2 v -2 h -2 v -5 a 2,2 0 0 0 -2,-2 2,2 0 0 0 2,-2 V 2 h 2 V 0 m 6,0 a 2,2 0 0 1 2,2 v 4 a 2,2 0 0 0 2,2 h 1 v 2 h -1 a 2,2 0 0 0 -2,2 v 4 a 2,2 0 0 1 -2,2 h -2 v -2 h 2 v -5 a 2,2 0 0 1 2,-2 2,2 0 0 1 -2,-2 V 2 h -2 V 0 Z"
     id="path1" />
</svg>`,"objects/suricata":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-14.2500 0.0000 27.5000 22.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="suricata.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m -0.5,8 a 3,3 0 0 1 3,3 3,3 0 0 1 -3,3 3,3 0 0 1 -3,-3 3,3 0 0 1 3,-3 M 5.36,18.31 C 3.73,20.22 1.78,21.45 -0.5,22 -3.06,21.39 -5.2,19.93 -6.92,17.63 -8.64,15.34 -9.5,12.8 -9.5,10 V 4 l 9,-4 9,4 v 6 c 0,2.39 -0.64,4.61 -1.92,6.67 L 3.67,13.76 C 4.19,12.97 4.5,12 4.5,11 a 5,5 0 0 0 -5,-5 5,5 0 0 0 -5,5 5,5 0 0 0 5,5 c 1,0 1.97,-0.31 2.76,-0.83 z"
     id="path1" />
</svg>`,"objects/task":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-10.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="task.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 9,2 H 4.82 C 4.4,0.84 3.3,0 2,0 0.7,0 -0.4,0.84 -0.82,2 H -5 c -1.1,0 -2,0.9 -2,2 v 14 c 0,1.1 0.9,2 2,2 H 9 c 1.1,0 2,-0.9 2,-2 V 4 C 11,2.9 10.1,2 9,2 M 2,2 C 2.55,2 3,2.45 3,3 3,3.55 2.55,4 2,4 1.45,4 1,3.55 1,3 1,2.45 1.45,2 2,2 M -3,6 H 7 V 4 H 9 V 18 H -5 V 4 h 2 z m 5,10 v -2 h 5 v 2 z M 2,10 V 8 h 5 v 2 z m -4,1 V 8 H -3 V 7 h 2 v 4 z m 1.25,2 c 0.41,0 0.75,0.34 0.75,0.75 0,0.2 -0.08,0.39 -0.21,0.52 L -1.88,16 H 0 v 1 H -3 V 16.08 L -1,14 h -2 v -1 z"
     id="path1" />
</svg>`,"objects/telegram-account":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-5.0000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="telegram-account.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 7.5,0 c -5.52,0 -10,4.48 -10,10 0,5.52 4.48,10 10,10 5.52,0 10,-4.48 10,-10 0,-5.52 -4.48,-10 -10,-10 m 4.64,6.8 c -0.15,1.58 -0.8,5.42 -1.13,7.19 -0.14,0.75 -0.42,1 -0.68,1.03 C 9.75,15.07 9.31,14.64 8.75,14.27 7.87,13.69 7.37,13.33 6.52,12.77 5.53,12.12 6.17,11.76 6.74,11.18 6.89,11.03 9.45,8.7 9.5,8.49 A 0.2,0.2 0 0 0 9.45,8.31 C 9.39,8.26 9.31,8.28 9.24,8.29 9.15,8.31 7.75,9.24 5.02,11.08 4.62,11.35 4.26,11.49 3.94,11.48 3.58,11.47 2.9,11.28 2.39,11.11 1.76,10.91 1.27,10.8 1.31,10.45 1.33,10.27 1.58,10.09 2.05,9.9 4.97,8.63 6.91,7.79 7.88,7.39 c 2.78,-1.16 3.35,-1.36 3.73,-1.36 0.08,0 0.27,0.02 0.39,0.12 0.1,0.08 0.13,0.19 0.14,0.27 -0.01,0.06 0.01,0.24 0,0.38"
     id="path1" />
</svg>`,"objects/telegram-bot":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-5.0000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="telegram-bot.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 7.5,0 c -5.52,0 -10,4.48 -10,10 0,5.52 4.48,10 10,10 5.52,0 10,-4.48 10,-10 0,-5.52 -4.48,-10 -10,-10 m 4.64,6.8 c -0.15,1.58 -0.8,5.42 -1.13,7.19 -0.14,0.75 -0.42,1 -0.68,1.03 C 9.75,15.07 9.31,14.64 8.75,14.27 7.87,13.69 7.37,13.33 6.52,12.77 5.53,12.12 6.17,11.76 6.74,11.18 6.89,11.03 9.45,8.7 9.5,8.49 A 0.2,0.2 0 0 0 9.45,8.31 C 9.39,8.26 9.31,8.28 9.24,8.29 9.15,8.31 7.75,9.24 5.02,11.08 4.62,11.35 4.26,11.49 3.94,11.48 3.58,11.47 2.9,11.28 2.39,11.11 1.76,10.91 1.27,10.8 1.31,10.45 1.33,10.27 1.58,10.09 2.05,9.9 4.97,8.63 6.91,7.79 7.88,7.39 c 2.78,-1.16 3.35,-1.36 3.73,-1.36 0.08,0 0.27,0.02 0.39,0.12 0.1,0.08 0.13,0.19 0.14,0.27 -0.01,0.06 0.01,0.24 0,0.38"
     id="path1" />
</svg>`,"objects/temporal-event":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-10.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="temporal-event.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 2.725,15.275 Q 2,14.55 2,13.5 2,12.45 2.725,11.725 3.45,11 4.5,11 5.55,11 6.275,11.725 7,12.45 7,13.5 7,14.55 6.275,15.275 5.55,16 4.5,16 3.45,16 2.725,15.275 M -5,20 Q -5.825,20 -6.412,19.413 -6.999,18.826 -7,18 V 4 Q -7,3.175 -6.412,2.588 -5.824,2.001 -5,2 h 1 V 0 h 2 V 2 H 6 V 0 H 8 V 2 H 9 Q 9.825,2 10.413,2.588 11.001,3.176 11,4 v 14 q 0,0.825 -0.587,1.413 Q 9.826,20.001 9,20 Z m 0,-2 H 9 V 8 H -5 Z"
     id="path1" />
</svg>`,"objects/terminal-output":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-4.8752 0.0000 24.3761 19.5009"
   version="1.1"
   id="svg2"
   sodipodi:docname="terminal-output.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs2" />
  <g
     fill="none"
     stroke="currentColor"
     stroke-linecap="round"
     stroke-linejoin="round"
     stroke-width="1.5"
     id="g2"
     transform="translate(-4.6871558,-2.2495558)">
    <path
       d="M 7,7 8.227,8.057 C 8.742,8.502 9,8.724 9,9 9,9.276 8.742,9.498 8.227,9.943 L 7,11 m 4,0 h 3"
       id="path1" />
    <path
       d="m 12,21 c 3.75,0 5.625,0 6.939,-0.955 a 5,5 0 0 0 1.106,-1.106 C 21,17.625 21,15.749 21,12 21,8.251 21,6.375 20.045,5.061 A 5,5 0 0 0 18.939,3.955 C 17.625,3 15.749,3 12,3 8.251,3 6.375,3 5.061,3.955 A 5,5 0 0 0 3.955,5.06 C 3,6.375 3,8.251 3,12 c 0,3.749 0,5.625 0.955,6.939 a 5,5 0 0 0 1.106,1.106 C 6.375,21 8.251,21 12,21"
       id="path2" />
  </g>
</svg>`,"objects/timestamp":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-10.9011 0.0000 27.2675 21.8140"
   version="1.1"
   id="svg2"
   sodipodi:docname="timestamp.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs2" />
  <g
     fill="none"
     id="g2"
     transform="translate(-9.2674,-2)">
    <path
       d="m 12.593,23.258 -0.011,0.002 -0.071,0.035 -0.02,0.004 -0.014,-0.004 -0.071,-0.035 q -0.016,-0.005 -0.024,0.005 l -0.004,0.01 -0.017,0.428 0.005,0.02 0.01,0.013 0.104,0.074 0.015,0.004 0.012,-0.004 0.104,-0.074 0.012,-0.016 0.004,-0.017 -0.017,-0.427 Q 12.606,23.26 12.593,23.258 m 0.265,-0.113 -0.013,0.002 -0.185,0.093 -0.01,0.01 -0.003,0.011 0.018,0.43 0.005,0.012 0.008,0.007 0.201,0.093 q 0.019,0.005 0.029,-0.008 l 0.004,-0.014 -0.034,-0.614 q -0.005,-0.018 -0.02,-0.022 m -0.715,0.002 a 0.02,0.02 0 0 0 -0.027,0.006 l -0.006,0.014 -0.034,0.614 q 10e-4,0.018 0.017,0.024 l 0.015,-0.002 0.201,-0.093 0.01,-0.008 0.004,-0.011 0.017,-0.43 -0.003,-0.012 -0.01,-0.01 z"
       id="path1" />
    <path
       fill="currentColor"
       d="M 12,2 C 17.523,2 22,6.477 22,12 22,17.523 17.523,22 12,22 6.477,22 2,17.523 2,12 2,6.477 6.477,2 12,2 m 0,4 a 1,1 0 0 0 -1,1 v 5 a 1,1 0 0 0 0.293,0.707 l 3,3 a 1,1 0 0 0 1.414,-1.414 L 13,11.586 V 7 A 1,1 0 0 0 12,6"
       id="path2" />
  </g>
</svg>`,"objects/tor-hiddenservice":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-19.1664 0.0000 40.0012 32.0010"
   version="1.1"
   id="svg1"
   sodipodi:docname="tor-hiddenservice.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 8.271508,16.265 c -1.016,-0.922 -2.297,-1.667 -3.604,-2.411 -0.594,-0.328 -2.417,-1.755 -1.786,-3.781 l -1.135,-0.479 c 1.786,-2.771 4.115,-5.51 6.969,-8.073 -2.292,0.771 -4.318,1.964 -5.839,4.078 0.896,-1.875 2.354,-3.724 3.964,-5.599 -2.203,1.578 -4.109,3.365 -5.302,5.75 l 0.833,-3.339 c -1.193,2.146 -2.0259997,4.323 -2.3539997,6.495 l -1.755,-0.714 -0.297,0.24 c 1.547,2.771 0.745,4.229 -0.031,4.74 -1.547,1.042 -3.781,2.38 -4.917,3.542 -2.146,2.208 -2.771,4.292 -2.563,7.063 0.208,3.547 2.802,6.495 6.229,7.656 1.521,0.51 2.917,0.568 4.4689997,0.568 2.5,0 5.063,-0.656 6.943,-2.234 a 8.73,8.73 0 0 0 3.156,-6.703 9.17,9.17 0 0 0 -2.979,-6.797 z m -4.74,11.833 c -0.12,0.536 -0.505,1.193 -0.979,1.786 0.177,-0.328 0.328,-0.656 0.417,-1.016 0.745,-2.651 1.073,-3.87 0.714,-6.792 -0.057,-0.297 -0.177,-1.25 -0.625,-2.292 -0.625,-1.583 -1.578,-3.073 -1.698,-3.401 -0.208,-0.505 -0.505,-2.651 -0.536,-4.109 0.031,1.25 0.12,3.542 0.448,4.438 0.089,0.302 0.953,1.641 1.578,3.276 0.417,1.135 0.505,2.177 0.594,2.474 0.302,1.344 -0.057,3.609 -0.531,5.75 -0.151,0.776 -0.568,1.672 -1.104,2.354 0.297,-0.417 0.536,-0.953 0.714,-1.578 0.359,-1.25 0.505,-2.859 0.474,-3.875 -0.026,-0.594 -0.297,-1.875 -0.745,-3.036 -0.266,-0.625 -0.656,-1.281 -0.922,-1.729 -0.297,-0.448 -0.297,-1.427 -0.417,-2.563 0.026,1.224 -0.089,1.849 0.208,2.714 0.177,0.505 0.833,1.219 1.01,1.906 0.271,0.922 0.536,1.938 0.51,2.563 0,0.714 -0.031,2.026 -0.359,3.458 -0.208,1.068 -0.688,1.995 -1.458,2.589 a 3,3 0 0 0 0.594,-1.25 c 0.12,-0.625 0.151,-1.224 0.208,-1.969 a 8,8 0 0 0 -0.146,-2.292 c -0.24,-1.073 -0.625,-2.146 -0.807,-2.891 0.031,0.833 0.359,1.875 0.51,2.979 0.115,0.807 0.057,1.609 0.026,2.323 -0.026,0.833 -0.297,2.297 -0.656,3.01 -0.3589997,-0.151 -0.4739997,-0.359 -0.7139997,-0.656 -0.302,-0.385 -0.479,-0.802 -0.656,-1.281 a 7,7 0 0 1 -0.391,-1.219 4.1,4.1 0 0 1 0.745,-2.953 c 0.625,-0.896 0.75,-0.953 0.9529997,-1.995 -0.2969997,0.922 -0.5049997,1.01 -1.1609997,1.786 -0.745,0.865 -0.859,2.115 -0.859,3.13 0,0.417 0.177,0.896 0.328,1.344 0.177,0.474 0.354,0.948 0.594,1.307 0.177,0.297 0.417,0.505 0.625,0.656 -0.776,-0.208 -1.578,-0.505 -2.083,-0.922 -1.25,-1.078 -2.354,-2.891 -2.505,-4.5 -0.12,-1.313 1.073,-3.219 2.771,-4.172 1.432,-0.833 1.76,-1.76 2.057,-3.281 -0.417,1.313 -0.833,2.448 -2.208,3.13 -1.964,1.073 -2.979,2.802 -2.885,4.469 0.146,2.115 0.979,3.578 2.682,4.74 0.385,0.271 0.922,0.536 1.49,0.745 -2.12,-0.505 -2.385,-0.802 -3.099,-1.635 0,-0.063 -0.182,-0.182 -0.182,-0.208 -0.953,-1.073 -2.141,-2.922 -2.563,-4.62 -0.146,-0.594 -0.297,-1.219 -0.115,-1.818 0.771,-2.802 2.469,-3.875 4.167,-5.031 0.422,-0.302 0.839,-0.568 1.224,-0.865 0.953,-0.75 1.193,-2.682 1.401,-3.786 -0.385,1.344 -0.807,3.01 -1.552,3.547 -0.385,0.297 -0.865,0.536 -1.25,0.802 -1.755,1.193 -3.516,2.328 -4.318,5.214 -0.182,0.75 -0.063,1.286 0.115,2 0.448,1.755 1.641,3.661 2.656,4.797 l 0.177,0.177 a 4.3,4.3 0 0 0 1.698,1.161 8,8 0 0 1 -1.729,-0.625 c -2.771,-1.339 -4.615,-4.229 -4.734,-6.583 -0.24,-4.797 2.057,-6.198 4.198,-7.958 1.193,-0.979 2.865,-1.458 3.818,-3.214 0.177,-0.391 0.297,-1.224 0.057,-2.12 -0.089,-0.297 -0.536,-1.37 -0.714,-1.609 l 2.6509997,1.167 c -0.057,1.25 -0.089,2.26 0.146,3.188 0.271,1.01 1.583,2.469 2.12,4.172 1.042,3.214 0.776,7.411 0.026,10.693 z"
     id="path1" />
</svg>`,"objects/tor-node":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-28.7496 0.0000 40.0012 32.0010"
   version="1.1"
   id="svg1"
   sodipodi:docname="tor-node.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m -1.311692,16.265 c -1.016,-0.922 -2.297,-1.667 -3.604,-2.411 -0.594,-0.328 -2.417,-1.755 -1.786,-3.781 l -1.135,-0.479 c 1.786,-2.771 4.115,-5.51 6.96899997,-8.073 C -3.159692,2.292 -5.185692,3.485 -6.706692,5.599 c 0.896,-1.875 2.354,-3.724 3.964,-5.599 -2.203,1.578 -4.109,3.365 -5.302,5.75 l 0.833,-3.339 c -1.193,2.146 -2.0259997,4.323 -2.3539997,6.495 l -1.7550003,-0.714 -0.297,0.24 c 1.547,2.771 0.745,4.229 -0.031,4.74 -1.547,1.042 -3.781,2.38 -4.917,3.542 -2.146,2.208 -2.771,4.292 -2.563,7.063 0.208,3.547 2.802,6.495 6.229,7.656 1.521,0.51 2.9170003,0.568 4.469,0.568 2.5,0 5.063,-0.656 6.943,-2.234 a 8.73,8.73 0 0 0 3.156,-6.703 9.17,9.17 0 0 0 -2.979,-6.797 z m -4.74,11.833 c -0.12,0.536 -0.505,1.193 -0.979,1.786 0.177,-0.328 0.328,-0.656 0.417,-1.016 0.745,-2.651 1.073,-3.87 0.714,-6.792 -0.057,-0.297 -0.177,-1.25 -0.625,-2.292 -0.625,-1.583 -1.578,-3.073 -1.698,-3.401 -0.208,-0.505 -0.505,-2.651 -0.536,-4.109 0.031,1.25 0.12,3.542 0.448,4.438 0.089,0.302 0.953,1.641 1.578,3.276 0.417,1.135 0.505,2.177 0.594,2.474 0.302,1.344 -0.057,3.609 -0.531,5.75 -0.151,0.776 -0.568,1.672 -1.104,2.354 0.297,-0.417 0.536,-0.953 0.714,-1.578 0.359,-1.25 0.505,-2.859 0.474,-3.875 -0.026,-0.594 -0.297,-1.875 -0.745,-3.036 -0.266,-0.625 -0.656,-1.281 -0.922,-1.729 -0.297,-0.448 -0.297,-1.427 -0.417,-2.563 0.026,1.224 -0.089,1.849 0.208,2.714 0.177,0.505 0.833,1.219 1.01,1.906 0.271,0.922 0.536,1.938 0.51,2.563 0,0.714 -0.031,2.026 -0.359,3.458 -0.208,1.068 -0.688,1.995 -1.458,2.589 a 3,3 0 0 0 0.594,-1.25 c 0.12,-0.625 0.151,-1.224 0.208,-1.969 a 8,8 0 0 0 -0.146,-2.292 c -0.24,-1.073 -0.625,-2.146 -0.807,-2.891 0.031,0.833 0.359,1.875 0.51,2.979 0.115,0.807 0.057,1.609 0.026,2.323 -0.026,0.833 -0.297,2.297 -0.656,3.01 -0.3589997,-0.151 -0.4739997,-0.359 -0.7139997,-0.656 -0.3020003,-0.385 -0.4790003,-0.802 -0.6560003,-1.281 a 7,7 0 0 1 -0.391,-1.219 4.1,4.1 0 0 1 0.745,-2.953 c 0.6250003,-0.896 0.7500003,-0.953 0.953,-1.995 -0.2969997,0.922 -0.5049997,1.01 -1.161,1.786 -0.745,0.865 -0.859,2.115 -0.859,3.13 0,0.417 0.177,0.896 0.328,1.344 0.177,0.474 0.354,0.948 0.594,1.307 0.177,0.297 0.4170003,0.505 0.6250003,0.656 -0.7760003,-0.208 -1.5780003,-0.505 -2.0830003,-0.922 -1.25,-1.078 -2.354,-2.891 -2.505,-4.5 -0.12,-1.313 1.073,-3.219 2.771,-4.172 1.4320003,-0.833 1.7600003,-1.76 2.0570003,-3.281 -0.417,1.313 -0.8330003,2.448 -2.2080003,3.13 -1.964,1.073 -2.979,2.802 -2.885,4.469 0.146,2.115 0.979,3.578 2.682,4.74 0.385,0.271 0.922,0.536 1.49,0.745 -2.12,-0.505 -2.385,-0.802 -3.099,-1.635 0,-0.063 -0.182,-0.182 -0.182,-0.208 -0.953,-1.073 -2.141,-2.922 -2.563,-4.62 -0.146,-0.594 -0.297,-1.219 -0.115,-1.818 0.771,-2.802 2.469,-3.875 4.167,-5.031 0.422,-0.302 0.839,-0.568 1.224,-0.865 0.9530003,-0.75 1.1930003,-2.682 1.4010003,-3.786 -0.385,1.344 -0.8070003,3.01 -1.5520003,3.547 -0.385,0.297 -0.865,0.536 -1.25,0.802 -1.755,1.193 -3.516,2.328 -4.318,5.214 -0.182,0.75 -0.063,1.286 0.115,2 0.448,1.755 1.641,3.661 2.656,4.797 l 0.177,0.177 a 4.3,4.3 0 0 0 1.698,1.161 8,8 0 0 1 -1.729,-0.625 c -2.771,-1.339 -4.615,-4.229 -4.734,-6.583 -0.24,-4.797 2.057,-6.198 4.198,-7.958 1.193,-0.979 2.865,-1.458 3.818,-3.214 0.177,-0.391 0.297,-1.224 0.057,-2.12 -0.089,-0.297 -0.536,-1.37 -0.714,-1.609 l 2.651,1.167 c -0.057,1.25 -0.089,2.26 0.146,3.188 0.271,1.01 1.583,2.469 2.12,4.172 1.042,3.214 0.776,7.411 0.026,10.693 z"
     id="path1" />
</svg>`,"objects/transaction":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-2.6266 0.0000 25.6250 20.5000"
   version="1.1"
   id="svg3"
   sodipodi:docname="transaction.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs3" />
  <g
     fill="none"
     id="g3"
     transform="translate(-1.3133,-1)">
    <path
       d="M 19.781,14.555 13.5,16 h -0.375 a 1.875,1.875 0 0 0 0,-3.75 H 8.438 A 2.25,2.25 0 0 0 6.844,12.906 L 4.5,15.25 v 5.25 h 6.75 l 6,-1.5 3.64,-1.552 A 1.555,1.555 0 0 0 19.781,14.555 M 4.5,15.25 V 20.5 H 1 v -5.25 z"
       id="path1" />
    <path
       d="m 18.5,2 a 3.5,3.5 0 1 1 -2,6.373 L 16.51,8.365 A 3.5,3.5 0 1 1 16.5,2.627 3.5,3.5 0 0 1 18.5,2"
       clip-rule="evenodd"
       id="path2" />
    <path
       stroke="currentColor"
       stroke-linecap="square"
       stroke-width="2"
       d="m 4.5,20.5 h 6.75 l 6,-1.5 3.64,-1.552 A 1.555,1.555 0 0 0 19.781,14.555 L 13.5,16 H 13.125 M 4.5,20.5 v -5.25 m 0,5.25 H 1 v -5.25 h 3.5 m 0,0 2.344,-2.344 A 2.25,2.25 0 0 1 8.437,12.25 h 4.688 a 1.875,1.875 0 0 1 0,3.75 H 11 M 17,2.337 a 3.5,3.5 0 1 1 0,6.326 M 14.5,9 a 3.5,3.5 0 1 1 0,-7 3.5,3.5 0 0 1 0,7 z"
       id="path3" />
  </g>
</svg>`,"objects/translation":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-1.5000 0.0000 20.0000 16.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="translation.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 10,4 H 8.49 C 7.86,4 7.24,4.3 6.9,4.7 L 6,2 H 3.13 L 0.74,9 H 2.43 L 3.17,7 H 6 v 4 H 1 C -0.1,11 -1,10.1 -1,9 V 2 C -1,0.9 -0.1,0 1,0 h 7 c 1.1,0 2,0.9 2,2 z M 5.51,6 H 3.49 l 1,-2.93 z M 9,5 h 7 c 1.1,0 2,0.9 2,2 v 7 c 0,1.1 -0.9,2 -2,2 H 9 C 7.9,16 7,15.1 7,14 V 7 C 7,5.9 7.9,5 9,5 m 7.25,5 V 8.92 H 13.08 V 6.75 H 11.92 V 8.92 H 8.75 V 10 h 1.28 c 0.11,0.85 0.56,1.85 1.28,2.62 -0.87,0.36 -1.89,0.62 -2.31,0.62 -0.01,0.02 0.22,0.97 0.2,1.46 0.84,0 2.21,-0.5 3.28,-1.15 1.09,0.65 2.48,1.15 3.34,1.15 -0.02,-0.49 0.2,-1.44 0.2,-1.46 -0.43,0 -1.49,-0.27 -2.38,-0.63 0.7,-0.77 1.14,-1.77 1.25,-2.61 z m -3.81,1.93 C 11.94,11.47 11.59,10.8 11.43,10 h 2.09 c -0.17,0.8 -0.51,1.47 -1,1.93 l -0.04,0.03 c 0,0 -0.03,-0.02 -0.04,-0.03"
     id="path1" />
</svg>`,"objects/transport-ticket":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-179.9460 0.0000 599.9451 479.9561"
   version="1.1"
   id="svg1"
   sodipodi:docname="transport-ticket.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 354.21402,165.39802 -44.13,-44.13 a 20,20 0 0 0 -27,-1 30.81,30.81 0 0 1 -41.68,-1.6 30.81,30.81 0 0 1 -1.6,-41.669999 20,20 0 0 0 -1,-27 l -44.17,-44.1800001 a 19.91,19.91 0 0 0 -28.13,0 l -70.35,70.3400001 a 39.9,39.9 0 0 0 -9.57,15.5 7.71,7.71 0 0 1 -4.83,4.83 39.8,39.8 0 0 0 -15.5,9.579999 l -180.4,180.4 a 19.91,19.91 0 0 0 0,28.13 l 44.180001,44.13 a 20,20 0 0 0 27,1 30.69,30.69 0 0 1 43.2799989,43.28 20,20 0 0 0 1,27 l 44.1300001,44.13 a 19.91,19.91 0 0 0 28.13,0 l 180.4,-180.4 a 39.8,39.8 0 0 0 9.58,-15.49 7.69,7.69 0 0 1 4.84,-4.84 39.84,39.84 0 0 0 15.49,-9.57 l 70.34,-70.35 a 19.91,19.91 0 0 0 -0.01,-28.09 m -228.37,-29.65 a 16,16 0 0 1 -22.63,0 l -11.51,-11.51 a 16,16 0 0 1 22.63,-22.62 l 11.51,11.5 a 16,16 0 0 1 0,22.63 m 44,44 a 16,16 0 0 1 -22.62,0 l -11,-11 a 16.001826,16.001826 0 1 1 22.63,-22.63 l 11,11 a 16,16 0 0 1 0.01,22.66 z m 44,44 a 16,16 0 0 1 -22.63,0 l -11,-11 a 16,16 0 0 1 22.63,-22.62 l 11,11 a 16,16 0 0 1 0.05,22.67 z m 44.43,44.54 a 16,16 0 0 1 -22.63,0 l -11.44,-11.5 a 16,16 0 1 1 22.68,-22.57 l 11.45,11.49 a 16,16 0 0 1 -0.01,22.63 z"
     id="path1" />
</svg>`,"objects/twitter-account":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-0.3300 0.0000 21.2500 17.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="twitter-account.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 20.755,2 c -0.77,0.35 -1.6,0.58 -2.46,0.69 0.88,-0.53 1.56,-1.37 1.88,-2.38 -0.83,0.5 -1.75,0.85 -2.72,1.05 C 16.665,0.5 15.555,0 14.295,0 c -2.35,0 -4.27,1.92 -4.27,4.29 0,0.34 0.04,0.67 0.11,0.98 -3.56,-0.18 -6.73,-1.89 -8.84,-4.48 -0.37,0.63 -0.58,1.37 -0.58,2.15 0,1.49 0.75,2.81 1.91,3.56 -0.71,0 -1.37,-0.2 -1.95,-0.5 v 0.03 c 0,2.08 1.48,3.82 3.44,4.21 a 4.2,4.2 0 0 1 -1.93,0.07 4.28,4.28 0 0 0 4,2.98 8.52,8.52 0 0 1 -5.33,1.84 q -0.51,0 -1.02,-0.06 c 1.9,1.22 4.16,1.93 6.58,1.93 7.88,0 12.21,-6.54 12.21,-12.21 0,-0.19 0,-0.37 -0.01,-0.56 0.84,-0.6 1.56,-1.36 2.14,-2.23"
     id="path1" />
</svg>`,"objects/twitter-list":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-0.3300 0.0000 21.2500 17.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="twitter-list.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 20.755,2 c -0.77,0.35 -1.6,0.58 -2.46,0.69 0.88,-0.53 1.56,-1.37 1.88,-2.38 -0.83,0.5 -1.75,0.85 -2.72,1.05 C 16.665,0.5 15.555,0 14.295,0 c -2.35,0 -4.27,1.92 -4.27,4.29 0,0.34 0.04,0.67 0.11,0.98 -3.56,-0.18 -6.73,-1.89 -8.84,-4.48 -0.37,0.63 -0.58,1.37 -0.58,2.15 0,1.49 0.75,2.81 1.91,3.56 -0.71,0 -1.37,-0.2 -1.95,-0.5 v 0.03 c 0,2.08 1.48,3.82 3.44,4.21 a 4.2,4.2 0 0 1 -1.93,0.07 4.28,4.28 0 0 0 4,2.98 8.52,8.52 0 0 1 -5.33,1.84 q -0.51,0 -1.02,-0.06 c 1.9,1.22 4.16,1.93 6.58,1.93 7.88,0 12.21,-6.54 12.21,-12.21 0,-0.19 0,-0.37 -0.01,-0.56 0.84,-0.6 1.56,-1.36 2.14,-2.23"
     id="path1" />
</svg>`,"objects/twitter-post":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-0.4950 0.0000 21.2500 17.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="twitter-post.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 20.59,2 C 19.82,2.35 18.99,2.58 18.13,2.69 19.01,2.16 19.69,1.32 20.01,0.31 19.18,0.81 18.26,1.16 17.29,1.36 16.5,0.5 15.39,0 14.13,0 11.78,0 9.86,1.92 9.86,4.29 9.86,4.63 9.9,4.96 9.97,5.27 6.41,5.09 3.24,3.38 1.13,0.79 0.76,1.42 0.55,2.16 0.55,2.94 0.55,4.43 1.3,5.75 2.46,6.5 1.75,6.5 1.09,6.3 0.51,6 v 0.03 c 0,2.08 1.48,3.82 3.44,4.21 a 4.2,4.2 0 0 1 -1.93,0.07 4.28,4.28 0 0 0 4,2.98 8.52,8.52 0 0 1 -5.33,1.84 q -0.51,0 -1.02,-0.06 c 1.9,1.22 4.16,1.93 6.58,1.93 7.88,0 12.21,-6.54 12.21,-12.21 0,-0.19 0,-0.37 -0.01,-0.56 0.84,-0.6 1.56,-1.36 2.14,-2.23"
     id="path1" />
</svg>`,"objects/uav":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="0.0000 0.0000 22.0250 16.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="uav.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 3,16 Q 3,14.125 4.025,12.637 5.05,11.149 6.675,10.475 L 6.425,8 H 3 V 2 H 0 V 0 H 8 V 2 H 5 V 6 H 6.2 L 6,4 H 16 L 15.8,6 H 17 V 2 H 14 V 0 h 8.025 v 2 h -3 V 8 H 15.6 l -0.25,2.475 q 1.625,0.675 2.638,2.163 Q 19.001,14.126 19,16 H 17 Q 17,14.35 15.825,13.175 14.65,12 13,12 H 9 Q 7.35,12 6.175,13.175 5,14.35 5,16 Z"
     id="path1" />
</svg>`,"objects/url":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-7.5030 0.0000 25.0003 20.0002"
   version="1.1"
   id="svg1"
   sodipodi:docname="url.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 6.237735,11.281346 c 0,-0.722 -0.282,-1.4159997 -0.785,-1.9339997 a 1.0003181,1.0003181 0 0 1 1.436,-1.393 4.78,4.78 0 0 1 0,6.6539997 l -0.003,0.004 -3.9129997,3.992 a 4.62,4.62 0 0 1 -6.618,0 4.78,4.78 0 0 1 -0.008,-6.664 l 2.607,-2.7399997 a 1.000138,1.000138 0 1 1 1.44800004,1.3799997 l -2.60499994,2.737 -0.009,0.01 a 2.78,2.78 0 0 0 -0.18,3.678 l 0.18,0.202 v 10e-4 a 2.62,2.62 0 0 0 3.7539999,0 l 0.002,-0.002 3.9139997,-3.995 c 0.5,-0.518 0.781,-1.21 0.781,-1.93 m 6.758,-6.5489997 a 2.78,2.78 0 0 0 -0.79,-1.94 v -0.001 a 2.62,2.62 0 0 0 -3.754,0 l -0.003,0.003 -4.0489997,4.12 a 2.78,2.78 0 0 0 -0.232,3.6119997 1,1 0 0 1 -1.6,1.2 4.78,4.78 0 0 1 0.4,-6.2069997 l 0.004,-0.003 4.0499997,-4.123 a 4.62,4.62 0 0 1 6.615,0.002 4.777,4.777 0 0 1 0.019,6.654 l -2.71,2.9309997 a 1.0006051,1.0006051 0 0 1 -1.469,-1.3589997 l 2.71,-2.93 0.018,-0.02 a 2.78,2.78 0 0 0 0.79,-1.94"
     id="path1" />
</svg>`,"objects/user-account":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-0.3750 0.0000 21.8750 17.5000"
   version="1.1"
   id="svg2"
   sodipodi:docname="user-account.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs2" />
  <g
     fill="none"
     stroke="currentColor"
     stroke-linecap="round"
     stroke-linejoin="round"
     stroke-width="1.5"
     id="g2"
     transform="translate(-1.4374848,-3.2499848)">
    <path
       d="M 2,12 C 2,8.229 2,6.343 3.172,5.172 4.344,4.001 6.229,4 10,4 h 4 c 3.771,0 5.657,0 6.828,1.172 C 21.999,6.344 22,8.229 22,12 c 0,3.771 0,5.657 -1.172,6.828 C 19.656,19.999 17.771,20 14,20 H 10 C 6.229,20 4.343,20 3.172,18.828 2.001,17.656 2,15.771 2,12"
       id="path1" />
    <path
       d="m 9,12.5 a 2.5,2.5 0 1 1 0,-5 2.5,2.5 0 0 1 0,5 m 0,0 a 4,4 0 0 1 4,4 m -4,-4 a 4,4 0 0 0 -4,4 M 15,9 h 4 m -4,3 h 4"
       id="path2" />
  </g>
</svg>`,"objects/user-action":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-12.9000 0.0000 22.5000 18.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="user-action.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m -3.7,4 a 1,1 0 0 1 1,-1 1,1 0 0 1 1,1 v 4.47 l 1.21,0.13 4.94,2.19 c 0.53,0.24 0.85,0.77 0.85,1.35 V 16.5 C 5.27,17.32 4.62,17.97 3.8,18 h -6.5 c -0.38,0 -0.74,-0.15 -1,-0.43 l -4.9,-4.2 0.74,-0.77 c 0.19,-0.21 0.46,-0.32 0.74,-0.32 H -6.9 L -3.7,14 Z m 1,-4 a 4,4 0 0 1 4,4 c 0,1.5 -0.8,2.77 -2,3.46 V 6.24 C -0.09,5.69 0.3,4.89 0.3,4 a 3,3 0 0 0 -3,-3 3,3 0 0 0 -3,3 c 0,0.89 0.39,1.69 1,2.24 V 7.46 C -5.9,6.77 -6.7,5.5 -6.7,4 a 4,4 0 0 1 4,-4"
     id="path1" />
</svg>`,"objects/vehicle":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-3.0000 0.0000 20.0000 16.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="vehicle.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 0,6 1.5,1.5 h 11 L 14,6 m -1.5,5 A 1.5,1.5 0 0 1 11,9.5 1.5,1.5 0 0 1 12.5,8 1.5,1.5 0 0 1 14,9.5 1.5,1.5 0 0 1 12.5,11 m -11,0 A 1.5,1.5 0 0 1 0,9.5 1.5,1.5 0 0 1 1.5,8 1.5,1.5 0 0 1 3,9.5 1.5,1.5 0 0 1 1.5,11 M 13.92,1 C 13.72,0.42 13.16,0 12.5,0 H 1.5 C 0.84,0 0.28,0.42 0.08,1 L -2,7 v 8 a 1,1 0 0 0 1,1 h 1 a 1,1 0 0 0 1,-1 v -1 h 12 v 1 a 1,1 0 0 0 1,1 h 1 a 1,1 0 0 0 1,-1 V 7 Z"
     id="path1" />
</svg>`,"objects/victim":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-7.8750 0.0000 26.2500 21.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="victim.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 14.2,9.5 h 1.55 v 2 H 14.2 C 13.75,15.67 10.42,19 6.25,19.45 V 21 h -2 V 19.45 C 0.08,19 -3.25,15.67 -3.7,11.5 h -1.55 v -2 H -3.7 C -3.25,5.33 0.08,2 4.25,1.55 V 0 h 2 V 1.55 C 10.42,2 13.75,5.33 14.2,9.5 m -15.88,0 h 1.43 v 2 h -1.43 a 6.98,6.98 0 0 0 5.93,5.93 V 16 h 2 v 1.43 a 6.98,6.98 0 0 0 5.93,-5.93 h -1.43 v -2 h 1.43 A 6.98,6.98 0 0 0 6.25,3.57 V 5 h -2 V 3.57 A 6.98,6.98 0 0 0 -1.68,9.5 m 10.93,5 h -8 v -1 c 0,-1.33 2.67,-2 4,-2 1.33,0 4,0.67 4,2 z m -4,-8 a 2,2 0 0 1 2,2 2,2 0 0 1 -2,2 2,2 0 0 1 -2,-2 2,2 0 0 1 2,-2"
     id="path1" />
</svg>`,"objects/virustotal-graph":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-4.0500 0.0000 26.7000 21.3600"
   version="1.1"
   id="svg1"
   sodipodi:docname="virustotal-graph.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 8.17,10.68 -2.7,21.36 h 24 V 0 h -24 z M 18.9,19.2 H 2.58 L 11.217,10.752 2.58,2.16 H 18.9 Z"
     id="path1" />
</svg>`,"objects/virustotal-report":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-2.7000 0.0000 26.7000 21.3600"
   version="1.1"
   id="svg1"
   sodipodi:docname="virustotal-report.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 9.52,10.68 -1.35,21.36 h 24 V 0 h -24 z M 20.25,19.2 H 3.93 L 12.567,10.752 3.93,2.16 h 16.32 z"
     id="path1" />
</svg>`,"objects/virustotal-submission":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-4.0500 0.0000 26.7000 21.3600"
   version="1.1"
   id="svg1"
   sodipodi:docname="virustotal-submission.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 8.17,10.68 -2.7,21.36 h 24 V 0 h -24 z M 18.9,19.2 H 2.58 L 11.217,10.752 2.58,2.16 H 18.9 Z"
     id="path1" />
</svg>`,"objects/vulnerability":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-6.0000 0.0000 30.0000 24.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="vulnerability.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="none"
     stroke="currentColor"
     stroke-width="2"
     d="M 9,0 V 24 Z M -3,12 h 24 z m 17,0 C 14,9.243 11.757,7 9,7 6.243,7 4,9.243 4,12 c 0,2.757 2.243,5 5,5 2.757,0 5,-2.243 5,-5 z M 9,21 C 4.038,21 0,16.963 0,12 0,7.037 4.038,3 9,3 c 4.962,0 9,4.037 9,9 0,4.963 -4.038,9 -9,9 z"
     id="path1" />
</svg>`,"objects/weakness":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-9.0000 0.0000 30.0000 24.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="weakness.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="none"
     stroke="currentColor"
     stroke-width="2"
     d="M 6,0 V 24 Z M -6,12 h 24 z m 17,0 C 11,9.243 8.757,7 6,7 3.243,7 1,9.243 1,12 c 0,2.757 2.243,5 5,5 2.757,0 5,-2.243 5,-5 z m -5,9 c -4.962,0 -9,-4.037 -9,-9 0,-4.963 4.038,-9 9,-9 4.962,0 9,4.037 9,9 0,4.963 -4.038,9 -9,9 z"
     id="path1" />
</svg>`,"objects/whois":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-7.5000 0.0000 25.0000 20.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="whois.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 8,6 H 6 V 4 h 2 z m 7,11 v 2 H 8 A 1,1 0 0 1 7,20 H 3 A 1,1 0 0 1 2,19 H -5 V 17 H 2 A 1,1 0 0 1 3,16 H 4 V 14 H 0 A 2,2 0 0 1 -2,12 V 2 A 2,2 0 0 1 0,0 h 10 a 2,2 0 0 1 2,2 v 10 a 2,2 0 0 1 -2,2 H 6 v 2 h 1 a 1,1 0 0 1 1,1 z M 2,2 H 0 V 12 H 2 Z M 4,12 H 6 V 8 H 8 A 2,2 0 0 0 10,6 V 4 A 2,2 0 0 0 8,2 H 4 Z"
     id="path1" />
</svg>`,"objects/wifi-connection":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="0.0000 0.0000 24.0000 17.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="wifi-connection.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 10.225,16.275 Q 9.5,15.55 9.5,14.5 9.5,13.45 10.225,12.725 10.95,12 12,12 q 1.05,0 1.775,0.725 0.725,0.725 0.725,1.775 0,1.05 -0.725,1.775 Q 13.05,17 12,17 10.95,17 10.225,16.275 M 6.35,11.35 4.25,9.2 Q 5.725,7.725 7.713,6.863 9.701,6.001 12,6 14.299,5.999 16.288,6.875 18.277,7.751 19.75,9.25 l -2.1,2.1 Q 16.55,10.25 15.1,9.625 13.65,9 12,9 10.35,9 8.9,9.625 7.45,10.25 6.35,11.35 M 2.1,7.1 0,5 Q 2.3,2.65 5.375,1.325 8.45,0 12,0 15.55,0 18.625,1.325 21.7,2.65 24,5 L 21.9,7.1 Q 19.975,5.175 17.438,4.088 14.901,3.001 12,3 9.099,2.999 6.563,4.088 4.027,5.177 2.1,7.1"
     id="path1" />
</svg>`,"objects/windows-service":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-6.7485 0.0000 22.5000 18.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="windows-service.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M -4.498,2.479 2.879,1.463 V 8.59 h -7.378 z m 0,13.042 7.377,1.017 V 9.498 H -4.499 Z M 3.69,16.646 13.502,18 V 9.498 H 3.69 Z m 0,-15.292 V 8.59 h 9.812 V 0 Z"
     id="path1" />
</svg>`,"objects/x-header":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-0.2500 0.0000 18.7500 15.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="x-header.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 4.375,0.5 h 14 v 2 h -14 z m 0,8 v -2 h 14 v 2 z m -3,-8.5 a 1.5,1.5 0 0 1 1.5,1.5 1.5,1.5 0 0 1 -1.5,1.5 1.5,1.5 0 0 1 -1.5,-1.5 1.5,1.5 0 0 1 1.5,-1.5 m 0,6 a 1.5,1.5 0 0 1 1.5,1.5 1.5,1.5 0 0 1 -1.5,1.5 1.5,1.5 0 0 1 -1.5,-1.5 1.5,1.5 0 0 1 1.5,-1.5 m 3,8.5 v -2 h 14 v 2 z m -3,-2.5 a 1.5,1.5 0 0 1 1.5,1.5 1.5,1.5 0 0 1 -1.5,1.5 1.5,1.5 0 0 1 -1.5,-1.5 1.5,1.5 0 0 1 1.5,-1.5"
     id="path1" />
</svg>`,"objects/x509":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-7.5000 0.0000 45.0000 36.0000"
   version="1.1"
   id="svg4"
   sodipodi:docname="x509.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs3">
    <mask
       id="SVG91XdkcRe">
      <g
         fill="none"
         stroke="#ffffff"
         stroke-width="4"
         id="g3">
        <path
           stroke-linecap="round"
           stroke-linejoin="round"
           d="M 26,36 H 6 A 2,2 0 0 1 4,34 V 8 A 2,2 0 0 1 6,6 h 36 a 2,2 0 0 1 2,2 v 26 a 2,2 0 0 1 -2,2 H 34 M 12,14 h 24 m -24,7 h 6 m -6,7 h 4"
           id="path1" />
        <path
           fill="#555555"
           d="m 30,33 a 6,6 0 1 0 0,-12 6,6 0 0 0 0,12 z"
           id="path2" />
        <path
           fill="#555555"
           stroke-linecap="round"
           stroke-linejoin="round"
           d="m 30,40 4,2 V 31.472 c 0,0 -1.14,1.528 -4,1.528 -2.86,0 -4,-1.5 -4,-1.5 V 42 Z"
           id="path3" />
      </g>
    </mask>
  </defs>
  <path
     fill="currentColor"
     d="M 0,0 H 48 V 48 H 0 Z"
     mask="url(#SVG91XdkcRe)"
     id="path4"
     transform="translate(-9,-6)" />
</svg>`,"objects/yara":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-29.6305 0.0000 531.7538 425.4030"
   version="1.1"
   id="svg1"
   sodipodi:docname="yara.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 247.78237,290.33 c 23.076,21.492 39.486,29.073 77.529,29.037 h 89.177 c 0,0 1.031,17.786 -3.018,25.073 -5.83,10.494 -16.259,17.888 -29.608,17.888 h -157.692 v 63.075 h 151.709 c 31.4,-0.416 52.922,-3.323 79.203,-22.16 15.066,-10.798 35.976,-13.983 37.164,-70.825 V 33.348 h -77.758 v 222.943 h -71.234 c -30.093,0 -45.132,-14.318 -45.132,-42.96 V 33.348 h -78.846 v 185.968 c -0.654,29.295 8.469,52.351 28.506,71.014 m -98.241,-238.419 c -45.638,-3.94 -46.19,13.006 -40.731,50.116 7.157,38.136 26.23,66.65 20.936,82.355 -2.368,7.527 -16.548,10.018 -32.83,15.129 -21.324999,6.695 -42.962999,12.151 -42.039999,13.862 21.251,7.798 47.692999,15.943 54.844999,19.036 13.292,5.554 9.947,18.735 3.746,28.18 -14.378,23.14 -26.832,37.69 -37.357999,53.734 -5.013,7.64 -7.027,14.492 -13.725,25.027 -5.351,8.659 -4.592,17.276 -0.104,24.544 5.552,8.993 9.149,9.15 36.419999,8.001 4.26,-0.296 11.58,5.329 5.01,17.24 -12.357,23.534 -7.893,35.676 -14.604,36.254 H 22.933371 c -18.6900001,-0.583 -35.783001,-21.78 -40.506001,-38.852 -8.595999,-31.076 9.0880008,-72.322 37.736001,-104.714 11.94,-15.671 22.678,-26.41 17.953,-29.116 C 1.0493709,235.836 -3.4196292,240.9 -2.6936292,226.283 c 0.702,-9.522 2.20299995,-19.18 4.4530001,-28.966 4.627,-13.28 10.7200001,-9.473 27.2870001,-16.46 18.121,-7.414 26.222,-5.199 24.075,-14.805 -11.439,-38.95 -25.915,-78.817 -19.902,-110.666 4.32,-22.883 20.264,-43.56 51.423999,-55.386 h 78.374 c 2.964,0.552 1.448,10.578 1.415,21.418 -0.966,19.756 5.993,32.443 -14.891,30.493"
     id="path1" />
</svg>`,"objects/youtube-channel":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="0.0000 0.0000 20.0000 14.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="youtube-channel.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 8,10 13.19,7 8,4 Z M 19.56,2.17 c 0.13,0.47 0.22,1.1 0.28,1.9 0.07,0.8 0.1,1.49 0.1,2.09 L 20,7 c 0,2.19 -0.16,3.8 -0.44,4.83 -0.25,0.9 -0.83,1.48 -1.73,1.73 -0.47,0.13 -1.33,0.22 -2.65,0.28 -1.3,0.07 -2.49,0.1 -3.59,0.1 L 10,14 C 5.81,14 3.2,13.84 2.17,13.56 1.27,13.31 0.69,12.73 0.44,11.83 0.31,11.36 0.22,10.73 0.16,9.93 0.09,9.13 0.06,8.44 0.06,7.84 L 0,7 C 0,4.81 0.16,3.2 0.44,2.17 0.69,1.27 1.27,0.69 2.17,0.44 2.64,0.31 3.5,0.22 4.82,0.16 6.12,0.09 7.31,0.06 8.41,0.06 L 10,0 c 4.19,0 6.8,0.16 7.83,0.44 0.9,0.25 1.48,0.83 1.73,1.73"
     id="path1" />
</svg>`,"objects/youtube-comment":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="0.0000 0.0000 20.0000 14.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="youtube-comment.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 8,10 13.19,7 8,4 Z M 19.56,2.17 c 0.13,0.47 0.22,1.1 0.28,1.9 0.07,0.8 0.1,1.49 0.1,2.09 L 20,7 c 0,2.19 -0.16,3.8 -0.44,4.83 -0.25,0.9 -0.83,1.48 -1.73,1.73 -0.47,0.13 -1.33,0.22 -2.65,0.28 -1.3,0.07 -2.49,0.1 -3.59,0.1 L 10,14 C 5.81,14 3.2,13.84 2.17,13.56 1.27,13.31 0.69,12.73 0.44,11.83 0.31,11.36 0.22,10.73 0.16,9.93 0.09,9.13 0.06,8.44 0.06,7.84 L 0,7 C 0,4.81 0.16,3.2 0.44,2.17 0.69,1.27 1.27,0.69 2.17,0.44 2.64,0.31 3.5,0.22 4.82,0.16 6.12,0.09 7.31,0.06 8.41,0.06 L 10,0 c 4.19,0 6.8,0.16 7.83,0.44 0.9,0.25 1.48,0.83 1.73,1.73"
     id="path1" />
</svg>`,"objects/youtube-playlist":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="0.0000 0.0000 20.0000 14.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="youtube-playlist.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 8,10 13.19,7 8,4 Z M 19.56,2.17 c 0.13,0.47 0.22,1.1 0.28,1.9 0.07,0.8 0.1,1.49 0.1,2.09 L 20,7 c 0,2.19 -0.16,3.8 -0.44,4.83 -0.25,0.9 -0.83,1.48 -1.73,1.73 -0.47,0.13 -1.33,0.22 -2.65,0.28 -1.3,0.07 -2.49,0.1 -3.59,0.1 L 10,14 C 5.81,14 3.2,13.84 2.17,13.56 1.27,13.31 0.69,12.73 0.44,11.83 0.31,11.36 0.22,10.73 0.16,9.93 0.09,9.13 0.06,8.44 0.06,7.84 L 0,7 C 0,4.81 0.16,3.2 0.44,2.17 0.69,1.27 1.27,0.69 2.17,0.44 2.64,0.31 3.5,0.22 4.82,0.16 6.12,0.09 7.31,0.06 8.41,0.06 L 10,0 c 4.19,0 6.8,0.16 7.83,0.44 0.9,0.25 1.48,0.83 1.73,1.73"
     id="path1" />
</svg>`,"objects/youtube-video":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="0.0000 0.0000 20.0000 14.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="youtube-video.svg"
  
  
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 8,10 13.19,7 8,4 Z M 19.56,2.17 c 0.13,0.47 0.22,1.1 0.28,1.9 0.07,0.8 0.1,1.49 0.1,2.09 L 20,7 c 0,2.19 -0.16,3.8 -0.44,4.83 -0.25,0.9 -0.83,1.48 -1.73,1.73 -0.47,0.13 -1.33,0.22 -2.65,0.28 -1.3,0.07 -2.49,0.1 -3.59,0.1 L 10,14 C 5.81,14 3.2,13.84 2.17,13.56 1.27,13.31 0.69,12.73 0.44,11.83 0.31,11.36 0.22,10.73 0.16,9.93 0.09,9.13 0.06,8.44 0.06,7.84 L 0,7 C 0,4.81 0.16,3.2 0.44,2.17 0.69,1.27 1.27,0.69 2.17,0.44 2.64,0.31 3.5,0.22 4.82,0.16 6.12,0.09 7.31,0.06 8.41,0.06 L 10,0 c 4.19,0 6.8,0.16 7.83,0.44 0.9,0.25 1.48,0.83 1.73,1.73"
     id="path1" />
</svg>`,"attributes/as":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="m5.931 6.936l1.275 4.249m5.607 5.609l4.251 1.275m-5.381-5.752l5.759-5.759M4 5.5a1.5 1.5 0 1 0 3 0a1.5 1.5 0 1 0-3 0m13 0a1.5 1.5 0 1 0 3 0a1.5 1.5 0 1 0-3 0m0 13a1.5 1.5 0 1 0 3 0a1.5 1.5 0 1 0-3 0m-13-3a4.5 4.5 0 1 0 9 0a4.5 4.5 0 1 0-9 0"/></svg>',"attributes/attachment":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="m15 7l-6.5 6.5a1.5 1.5 0 0 0 3 3L18 10a3 3 0 0 0-6-6l-6.5 6.5a4.5 4.5 0 0 0 9 9L21 13"/></svg>',"attributes/btc":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 6h8a3 3 0 0 1 0 6a3 3 0 0 1 0 6H6M8 6v12m0-6h6M9 3v3m4-3v3M9 18v3m4-3v3"/></svg>',"attributes/campaign-name":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 5a5 5 0 0 1 7 0a5 5 0 0 0 7 0v9a5 5 0 0 1-7 0a5 5 0 0 0-7 0zm0 16v-7"/></svg>',"attributes/cc-number":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8a3 3 0 0 1 3-3h12a3 3 0 0 1 3 3v8a3 3 0 0 1-3 3H6a3 3 0 0 1-3-3zm0 2h18M7 15h.01M11 15h2"/></svg>',"attributes/comment":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 9h8m-8 4h6m4-9a3 3 0 0 1 3 3v8a3 3 0 0 1-3 3h-5l-5 3v-3H6a3 3 0 0 1-3-3V7a3 3 0 0 1 3-3z"/></svg>',"attributes/cookie":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 13v.01M12 17v.01M12 12v.01M16 14v.01M11 8v.01m2.148-4.534l2.667 1.104a4 4 0 0 0 4.656 6.14l.053.132a3 3 0 0 1 0 2.296Q19.779 14.328 19.5 15q-.283.684-.66 2.216a3 3 0 0 1-1.624 1.623q-1.572.394-2.216.661q-.712.295-1.852 1.024a3 3 0 0 1-2.296 0Q9.649 19.77 9 19.5q-.707-.292-2.216-.66a3 3 0 0 1-1.623-1.624Q4.764 15.639 4.5 15q-.298-.718-1.024-1.852a3 3 0 0 1 0-2.296Q4.195 9.736 4.5 9q.257-.62.66-2.216a3 3 0 0 1 1.624-1.623Q8.331 4.777 9 4.5q.687-.285 1.852-1.024a3 3 0 0 1 2.296 0"/></svg>',"attributes/cpe":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="m12 3l8 4.5v9L12 21l-8-4.5v-9zm0 9l8-4.5M12 12v9m0-9L4 7.5m12-2.25l-8 4.5"/></svg>',"attributes/datetime":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><path d="M3 12a9 9 0 1 0 18 0a9 9 0 0 0-18 0"/><path d="M12 7v5l3 3"/></g></svg>',"attributes/domain-ip":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 19a2 2 0 1 0 4 0a2 2 0 0 0-4 0M19 7a2 2 0 1 0 0-4a2 2 0 0 0 0 4m-8 12h5.5a3.5 3.5 0 0 0 0-7h-8a3.5 3.5 0 0 1 0-7H13"/></svg>',"attributes/domain":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><path d="M3 12a9 9 0 1 0 18 0a9 9 0 0 0-18 0m.6-3h16.8M3.6 15h16.8"/><path d="M11.5 3a17 17 0 0 0 0 18m1-18a17 17 0 0 1 0 18"/></g></svg>',"attributes/email-dst":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><path d="M12 19H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v5.5M19 16v6m3-3l-3 3l-3-3"/><path d="m3 7l9 6l9-6"/></g></svg>',"attributes/email-src":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><path d="M12 18H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v7.5"/><path d="m3 6l9 6l9-6m-6 12h6m-3-3l3 3l-3 3"/></g></svg>',"attributes/email":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><path d="M3 7a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="m3 7l9 6l9-6"/></g></svg>',"attributes/filename-md5":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><path d="M14 3v4a1 1 0 0 0 1 1h4M9 13a1 1 0 0 1 1-1h1a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1h-1a1 1 0 0 1-1-1z"/><path d="M17 21H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h7l5 5v11a2 2 0 0 1-2 2m-2-9v5"/></g></svg>',"attributes/filename-sha256":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><path d="M14 3v4a1 1 0 0 0 1 1h4M9 13a1 1 0 0 1 1-1h1a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1h-1a1 1 0 0 1-1-1z"/><path d="M17 21H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h7l5 5v11a2 2 0 0 1-2 2m-2-9v5"/></g></svg>',"attributes/filename":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><path d="M14 3v4a1 1 0 0 0 1 1h4"/><path d="M17 21H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h7l5 5v11a2 2 0 0 1-2 2"/></g></svg>',"attributes/full-name":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7a4 4 0 1 0 8 0a4 4 0 0 0-8 0M6 21v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2"/></svg>',"attributes/github-username":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19c-4.3 1.4-4.3-2.5-6-3m12 5v-3.5c0-1 .1-1.4-.5-2c2.8-.3 5.5-1.4 5.5-6a4.6 4.6 0 0 0-1.3-3.2a4.2 4.2 0 0 0-.1-3.2s-1.1-.3-3.5 1.3a12.3 12.3 0 0 0-6.2 0C6.5 2.8 5.4 3.1 5.4 3.1a4.2 4.2 0 0 0-.1 3.2A4.6 4.6 0 0 0 4 9.5c0 4.6 2.7 5.7 5.5 6c-.6.6-.6 1.2-.5 2V21"/></svg>',"attributes/hostname":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7a3 3 0 0 1 3-3h12a3 3 0 0 1 3 3v2a3 3 0 0 1-3 3H6a3 3 0 0 1-3-3m0 6a3 3 0 0 1 3-3h12a3 3 0 0 1 3 3v2a3 3 0 0 1-3 3H6a3 3 0 0 1-3-3zm4-7v.01M7 16v.01"/></svg>',"attributes/iban":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 21h18M3 10h18M5 6l7-3l7 3M4 10v11m16-11v11M8 14v3m4-3v3m4-3v3"/></svg>',"attributes/ip-dst-port":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="m7 12l5 5l-1.5 1.5a3.536 3.536 0 1 1-5-5zm10 0l-5-5l1.5-1.5a3.536 3.536 0 1 1 5 5zM3 21l2.5-2.5m13-13L21 3m-11 8l-2 2m5 1l-2 2"/></svg>',"attributes/ip-dst":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><path d="M21 12a9 9 0 1 0-9 9M3.6 9h16.8M3.6 15H12"/><path d="M11.578 3a17 17 0 0 0 0 18M12.5 3c1.719 2.755 2.5 5.876 2.5 9m3 2v7m-3-3l3 3l3-3"/></g></svg>',"attributes/ip-src":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><path d="M21 12a9 9 0 1 0-9 9M3.6 9h16.8M3.6 15H12"/><path d="M11.578 3a17 17 0 0 0 0 18M12.5 3c1.719 2.755 2.5 5.876 2.5 9m3 9v-7m3 3l-3-3l-3 3"/></g></svg>',"attributes/link":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6H6a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-6m-7 1l9-9m-5 0h5v5"/></svg>',"attributes/mac-address":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><path d="M3 7a3 3 0 0 1 3-3h12a3 3 0 0 1 3 3v10a3 3 0 0 1-3 3H6a3 3 0 0 1-3-3z"/><path d="M7 10a2 2 0 1 0 4 0a2 2 0 1 0-4 0m8-2h2m-2 4h2M7 16h10"/></g></svg>',"attributes/malware-sample":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 9V8a3 3 0 0 1 6 0v1M8 9h8a6 6 0 0 1 1 3v3a5 5 0 0 1-10 0v-3a6 6 0 0 1 1-3m-5 4h4m10 0h4m-9 7v-6m-8 5l3.35-2M20 19l-3.35-2M4 7l3.75 2.4M20 7l-3.75 2.4"/></svg>',"attributes/md5":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 9h14M5 15h14M11 4L7 20M17 4l-4 16"/></svg>',"attributes/mutex":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><path d="M5 13a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v6a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2z"/><path d="M11 16a1 1 0 1 0 2 0a1 1 0 0 0-2 0m-3-5V7a4 4 0 1 1 8 0v4"/></g></svg>',"attributes/pattern-in-file":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><path d="M14 3v4a1 1 0 0 0 1 1h4"/><path d="M12 21H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h7l5 5v4.5"/><path d="M14 17.5a2.5 2.5 0 1 0 5 0a2.5 2.5 0 1 0-5 0m4.5 2L21 22"/></g></svg>',"attributes/pgp-public-key":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><path d="M12 3a12 12 0 0 0 8.5 3A12 12 0 0 1 12 21A12 12 0 0 1 3.5 6A12 12 0 0 0 12 3"/><path d="M11 11a1 1 0 1 0 2 0a1 1 0 1 0-2 0m1 1v2.5"/></g></svg>',"attributes/phone-number":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 4h4l2 5l-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2"/></svg>',"attributes/port":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.785 6L18 14.215l-2.054 2.054a5.81 5.81 0 1 1-8.215-8.215zM4 20l3.5-3.5M15 4l-3.5 3.5M20 9l-3.5 3.5"/></svg>',"attributes/regkey":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="m16.555 3.843l3.602 3.602a2.877 2.877 0 0 1 0 4.069l-2.643 2.643a2.877 2.877 0 0 1-4.069 0l-.301-.301l-6.558 6.558a2 2 0 0 1-1.239.578L5.172 21H4a1 1 0 0 1-.993-.883L3 20v-1.172a2 2 0 0 1 .467-1.284l.119-.13L4 17h2v-2h2v-2l2.144-2.144l-.301-.301a2.877 2.877 0 0 1 0-4.069l2.643-2.643a2.877 2.877 0 0 1 4.069 0M15 9h.01"/></svg>',"attributes/sha1":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 9h14M5 15h14M11 4L7 20M17 4l-4 16"/></svg>',"attributes/sha256":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 9h14M5 15h14M11 4L7 20M17 4l-4 16"/></svg>',"attributes/sigma":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18 16v2a1 1 0 0 1-1 1H6l6-7l-6-7h11a1 1 0 0 1 1 1v2"/></svg>',"attributes/snort":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><path d="M21 12h-8a1 1 0 1 0-1 1v8a9 9 0 0 0 9-9"/><path d="M16 9a5 5 0 1 0-7 7"/><path d="M20.486 9A9 9 0 1 0 9.004 20.495"/></g></svg>',"attributes/ssh-fingerprint":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><path d="M18.9 7a8 8 0 0 1 1.1 5v1a6 6 0 0 0 .8 3M8 11a4 4 0 0 1 8 0v1a10 10 0 0 0 2 6"/><path d="M12 11v2a14 14 0 0 0 2.5 8M8 15a18 18 0 0 0 1.8 6m-4.9-2a22 22 0 0 1-.9-7v-1a8 8 0 0 1 12-6.95"/></g></svg>',"attributes/text":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><path d="M14 3v4a1 1 0 0 0 1 1h4"/><path d="M17 21H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h7l5 5v11a2 2 0 0 1-2 2M9 9h1m-1 4h6m-6 4h6"/></g></svg>',"attributes/threat-actor":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 11h18M5 11V7a3 3 0 0 1 3-3h8a3 3 0 0 1 3 3v4M4 17a3 3 0 1 0 6 0a3 3 0 1 0-6 0m10 0a3 3 0 1 0 6 0a3 3 0 1 0-6 0m-4 0h4"/></svg>',"attributes/twitter-id":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="m4 4l11.733 16H20L8.267 4zm0 16l6.768-6.768m2.46-2.46L20 4"/></svg>',"attributes/uri":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="m9 15l6-6m-4-3l.463-.536a5 5 0 0 1 7.071 7.072L18 13m-5 5l-.397.534a5.07 5.07 0 0 1-7.127 0a4.97 4.97 0 0 1 0-7.071L6 11"/></svg>',"attributes/url":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="m9 15l6-6m-4-3l.463-.536a5 5 0 0 1 7.071 7.072L18 13m-5 5l-.397.534a5.07 5.07 0 0 1-7.127 0a4.97 4.97 0 0 1 0-7.071L6 11"/></svg>',"attributes/user-agent":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8h16M4 6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2zm4-2v4"/></svg>',"attributes/vulnerability":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.04 19.745c-.942.551-1.964.976-3.04 1.255A12 12 0 0 1 3.5 6A12 12 0 0 0 12 3a12 12 0 0 0 8.5 3a12 12 0 0 1 .195 6.015M19 16v3m0 3v.01"/></svg>',"attributes/windows-scheduled-task":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><path d="M11.795 21H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v4"/><path d="M14 18a4 4 0 1 0 8 0a4 4 0 1 0-8 0m1-15v4M7 3v4m-4 4h16"/><path d="M18 16.496V18l1 1"/></g></svg>',"attributes/windows-service-name":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><path d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 0 0 2.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 0 0 1.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 0 0-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 0 0-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 0 0-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 0 0-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 0 0 1.066-2.573c-.94-1.543.826-3.31 2.37-2.37c1 .608 2.296.07 2.572-1.065"/><path d="M9 12a3 3 0 1 0 6 0a3 3 0 0 0-6 0"/></g></svg>',"attributes/x509-fingerprint-sha1":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><path d="M12 15a3 3 0 1 0 6 0a3 3 0 1 0-6 0"/><path d="M13 17.5V22l2-1.5l2 1.5v-4.5"/><path d="M10 19H5a2 2 0 0 1-2-2V7c0-1.1.9-2 2-2h14a2 2 0 0 1 2 2v10a2 2 0 0 1-1 1.73M6 9h12M6 12h3m-3 3h2"/></g></svg>',"attributes/yara":'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><path d="M14 3v4a1 1 0 0 0 1 1h4"/><path d="M17 21H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h7l5 5v11a2 2 0 0 1-2 2"/><path d="m10 13l-1 2l1 2m4-4l1 2l-1 2"/></g></svg>',"galaxies/360net":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-95.9909 0.0000 639.9818 511.9854"
   version="1.1"
   id="svg1"
   sodipodi:docname="360net.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 383.9,308.28542 23.9,-62.6 c 4,-10.5 -3.7,-21.7 -15,-21.7 h -58.5 c 11,-18.9 17.8,-40.6 17.8,-64 v -0.3 c 39.2,-7.8 64,-19.1 64,-31.7 0,-13.3 -27.3,-25.1 -70.1,-32.999997 -9.2,-32.8 -27,-65.8 -40.6,-82.8 C 295.9,0.28542306 279.5,-3.4145769 265.9,3.3854231 L 238.3,17.185423 c -9,4.5 -19.6,4.5 -28.6,0 L 182.1,3.3854231 c -13.6,-6.8 -30,-3.10000004 -39.5,8.7999999 -13.5,17 -31.4,50 -40.6,82.8 -42.7,7.899997 -70,19.699997 -70,32.999997 0,12.6 24.8,23.9 64,31.7 v 0.3 c 0,23.4 6.8,45.1 17.8,64 H 56.3 c -11.5,0 -19.2,11.7 -14.7,22.3 l 25.8,60.2 c -40.1,23.3 -67.4,66.2 -67.4,115.9 v 44.8 c 0,24.7 20.1,44.8 44.8,44.8 h 358.4 c 24.7,0 44.8,-20.1 44.8,-44.8 v -44.8 c 0,-48.4 -25.8,-90.4 -64.1,-114.1 m -207.9,171.7 -41.6,-192 49.6,32 24,40 z m 96,0 -32,-120 24,-40 49.6,-32 z m 41.7,-298.5 c -3.9,11.9 -7,24.6 -16.5,33.4 -10.1,9.3 -48,22.4 -64,-25 -2.8,-8.4 -15.4,-8.4 -18.3,0 -17,50.2 -56,32.4 -64,25 -9.5,-8.8 -12.7,-21.5 -16.5,-33.4 -0.8,-2.5 -6.3,-5.7 -6.3,-5.8 v -10.8 c 28.3,3.6 61,5.8 96,5.8 35,0 67.7,-2.1 96,-5.8 v 10.8 c -0.1,0.1 -5.6,3.2 -6.4,5.8"
     id="path1" />
</svg>`,"galaxies/agent-threat-rules":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-80.0008 0.0000 640.0016 512.0013"
   version="1.1"
   id="svg1"
   sodipodi:docname="agent-threat-rules.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 208.00002,192 a 16,16 0 1 0 16,16 16,16 0 0 0 -16,-16 m 242.5,-108.32 -192,-80 a 57.4,57.4 0 0 0 -18.45,-3.68 57.4,57.4 0 0 0 -18.46,3.67 l -191.999996,80 A 47.93,47.93 0 0 0 2.3644917e-5,128 C 2.3644917e-5,326.5 114.50002,463.72 221.50002,508.32 a 48.1,48.1 0 0 0 36.91,0 c 85.68,-35.71 221.59,-159.02 221.59,-380.32 a 48,48 0 0 0 -29.5,-44.32 m -82.5,172.32 h -12.12 c -28.51,0 -42.79,34.47 -22.63,54.63 l 8.58,8.57 a 16.001826,16.001826 0 1 1 -22.63,22.63 l -8.57,-8.58 c -20.16,-20.16 -54.63,-5.88 -54.63,22.63 V 368 a 16,16 0 0 1 -32,0 v -12.12 c 0,-28.51 -34.47,-42.79 -54.63,-22.63 l -8.57,8.58 a 16.001826,16.001826 0 0 1 -22.63,-22.63 l 8.58,-8.57 c 20.16,-20.16 5.88,-54.63 -22.63,-54.63 h -12.12 a 16,16 0 0 1 0,-32 h 12.12 c 28.51,0 42.79,-34.47 22.63,-54.63 l -8.58,-8.57 a 16.001826,16.001826 0 0 1 22.63,-22.63 l 8.57,8.58 c 20.16,20.16 54.63,5.88 54.63,-22.63 V 112 a 16,16 0 0 1 32,0 v 12.12 c 0,28.51 34.47,42.79 54.63,22.63 l 8.57,-8.58 a 16.001826,16.001826 0 0 1 22.63,22.63 l -8.58,8.57 c -20.16,20.16 -5.88,54.63 22.63,54.63 h 12.12 a 16,16 0 0 1 0,32 m -96,0 a 16,16 0 1 0 16,16 16,16 0 0 0 -16,-16"
     id="path1" />
</svg>`,"galaxies/ammunitions":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="0.0000 0.0000 640.0000 320.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="ammunitions.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 544,64 v 64 h 32 v 64 h -32 v 64 H 64 V 64 Z M 560,0 H 48 C 21.49,0 0,21.49 0,48 v 224 c 0,26.51 21.49,48 48,48 h 512 c 26.51,0 48,-21.49 48,-48 v -16 h 8 c 13.255,0 24,-10.745 24,-24 V 88 C 640,74.745 629.255,64 616,64 h -8 V 48 C 608,21.49 586.51,0 560,0 M 512,96 H 96 v 128 h 416 z"
     id="path1" />
</svg>`,"galaxies/android":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="0.0000 0.0000 576.0000 325.1219"
   version="1.1"
   id="svg1"
   sodipodi:docname="android.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 420.55,243.05193 a 24,24 0 1 1 24,-24 24,24 0 0 1 -24,24 m -265.1,0 a 24,24 0 1 1 24,-24 24,24 0 0 1 -24,24 m 273.7,-144.480001 47.94,-83 A 10,10 0 1 0 459.82,5.5719285 L 411.28,89.641929 a 301.25,301.25 0 0 0 -246.56,0 L 116.18,5.5719285 A 10,10 0 1 0 98.91,15.571929 l 47.94,83 C 64.53,143.34193 8.24,226.67193 0,325.12193 h 576 c -8.24,-98.45 -64.54,-181.78 -146.85,-226.550001"
     id="path1" />
</svg>`,"galaxies/atrm":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="0.0000 0.0000 576.0000 448.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="atrm.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 0,85.66 v 346.32 c 0,11.32 11.43,19.06 21.94,14.86 L 160,384 V 0 L 20.12,55.95 A 32.01,32.01 0 0 0 0,85.66 M 192,384 384,448 V 64 L 192,0 Z M 554.06,1.16 416,64 V 448 L 555.88,392.05 A 32,32 0 0 0 576,362.34 V 16.02 C 576,4.7 564.57,-3.04 554.06,1.16"
     id="path1" />
</svg>`,"galaxies/attck4fraud":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="0.0000 0.0000 576.0000 448.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="attck4fraud.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 0,85.66 v 346.32 c 0,11.32 11.43,19.06 21.94,14.86 L 160,384 V 0 L 20.12,55.95 A 32.01,32.01 0 0 0 0,85.66 M 192,384 384,448 V 64 L 192,0 Z M 554.06,1.16 416,64 V 448 L 555.88,392.05 A 32,32 0 0 0 576,362.34 V 16.02 C 576,4.7 564.57,-3.04 554.06,1.16"
     id="path1" />
</svg>`,"galaxies/backdoor":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="0.0000 0.0000 640.0000 511.9990"
   version="1.1"
   id="svg1"
   sodipodi:docname="backdoor.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 624,447.99903 h -80 v -334.55 C 544,86.189026 522.47,63.999026 496,63.999026 H 384 v 64.000004 h 96 v 384 h 144 c 8.84,0 16,-7.16 16,-16 v -32 c 0,-8.84 -7.16,-16 -16,-16 M 312.24,1.0090259 120.24,50.749026 c -14.25,3.69 -24.24,16.95 -24.24,32.17 V 447.99903 H 16 c -8.84,0 -16,7.16 -16,16 v 32 c 0,8.84 7.16,16 16,16 H 352 V 33.179026 c 0,-21.58 -19.56,-37.4100001 -39.76,-32.1700001 M 264,287.99903 c -13.25,0 -24,-14.33 -24,-32 0,-17.67 10.75,-32 24,-32 13.25,0 24,14.33 24,32 0,17.67 -10.75,32 -24,32"
     id="path1" />
</svg>`,"galaxies/banker":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-176.0309 0.0000 640.0000 512.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="banker.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 209.16357,233.4 -108,-31.6 c -12.500002,-3.6 -21.200002,-15.3 -21.200002,-28.3 0,-16.3 13.2,-29.5 29.500002,-29.5 h 66.3 c 12.2,0 24.2,3.7 34.2,10.5 6.1,4.1 14.3,3.1 19.5,-2 l 34.8,-34 c 7.1,-6.9 6.1,-18.4 -1.8,-24.5 -24.5,-19.2 -55.1,-29.9 -86.5,-30 V 16 c 0,-8.8 -7.2,-16 -16,-16 h -32 c -8.8,0 -16,7.2 -16,16 v 48 h -2.5 C 45.763568,64 -5.4364316,118.7 0.46356844,183.6 4.6635684,229.7 39.863568,267.2 84.263568,280.2 l 102.500002,30 c 12.5,3.7 21.2,15.3 21.2,28.3 0,16.3 -13.2,29.5 -29.5,29.5 h -66.3 c -12.200002,0 -24.200002,-3.7 -34.200002,-10.5 -6.1,-4.1 -14.3,-3.1 -19.5,2 l -34.8,34 c -7.1,6.9 -6.1,18.4 1.8,24.5 24.5,19.2 55.1,29.9 86.500002,30 v 48 c 0,8.8 7.2,16 16,16 h 32 c 8.8,0 16,-7.2 16,-16 v -48.2 c 46.6,-0.9 90.3,-28.6 105.7,-72.7 21.5,-61.6 -14.6,-124.8 -72.5,-141.7"
     id="path1" />
</svg>`,"galaxies/bhadra-framework":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-160.0000 0.0000 640.0000 512.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="bhadra-framework.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 272,0 H 48 C 21.5,0 0,21.5 0,48 v 416 c 0,26.5 21.5,48 48,48 h 224 c 26.5,0 48,-21.5 48,-48 V 48 C 320,21.5 298.5,0 272,0 M 160,480 c -17.7,0 -32,-14.3 -32,-32 0,-17.7 14.3,-32 32,-32 17.7,0 32,14.3 32,32 0,17.7 -14.3,32 -32,32"
     id="path1" />
</svg>`,"galaxies/bitns":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-96.0000 0.0000 640.0000 512.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="bitns.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 224,256 C 294.7,256 352,198.7 352,128 352,57.3 294.7,0 224,0 153.3,0 96,57.3 96,128 c 0,70.7 57.3,128 128,128 M 319.8,288.6 272,480 240,344 272,288 h -96 l 32,56 -32,136 -47.8,-191.4 C 56.9,292 0,350.3 0,422.4 V 464 c 0,26.5 21.5,48 48,48 h 352 c 26.5,0 48,-21.5 48,-48 V 422.4 C 448,350.3 391.1,292 319.8,288.6"
     id="path1" />
</svg>`,"galaxies/botnet":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="0.0000 0.0000 640.0000 512.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="botnet.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 128,352 H 32 C 14.33,352 0,366.33 0,384 v 96 c 0,17.67 14.33,32 32,32 h 96 c 17.67,0 32,-14.33 32,-32 v -96 c 0,-17.67 -14.33,-32 -32,-32 m -24,-80 h 192 v 48 h 48 v -48 h 192 v 48 h 48 V 262.41 C 584,241.24 566.77,224 545.59,224 H 344 v -64 h 40 c 17.67,0 32,-14.33 32,-32 V 32 C 416,14.33 401.67,0 384,0 H 256 c -17.67,0 -32,14.33 -32,32 v 96 c 0,17.67 14.33,32 32,32 h 40 v 64 H 94.41 C 73.23,224 56,241.23 56,262.41 V 320 h 48 z m 264,80 h -96 c -17.67,0 -32,14.33 -32,32 v 96 c 0,17.67 14.33,32 32,32 h 96 c 17.67,0 32,-14.33 32,-32 v -96 c 0,-17.67 -14.33,-32 -32,-32 m 240,0 h -96 c -17.67,0 -32,14.33 -32,32 v 96 c 0,17.67 14.33,32 32,32 h 96 c 17.67,0 32,-14.33 32,-32 v -96 c 0,-17.67 -14.33,-32 -32,-32"
     id="path1" />
</svg>`,"galaxies/branded-vulnerability":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-64.0004 0.0000 640.0005 512.0004"
   version="1.1"
   id="svg1"
   sodipodi:docname="branded-vulnerability.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 511.9874,288.9 c -0.478,17.43 -15.217,31.1 -32.653,31.1 h -55.335 v 16 c 0,21.864 -4.882,42.584 -13.6,61.145 l 60.228,60.228 c 12.496,12.497 12.496,32.758 0,45.255 -12.498,12.497 -32.759,12.496 -45.256,0 l -54.736,-54.736 C 345.8854,467.965 314.3504,480 279.9994,480 V 236 c 0,-6.627 -5.373,-12 -12,-12 h -24 c -6.627,0 -12,5.373 -12,12 v 244 c -34.351,0 -65.886,-12.035 -90.636,-32.108 l -54.736004,54.736 c -12.498,12.497 -32.759,12.496 -45.256,0 -12.497,-12.496 -12.496,-32.758 0,-45.255 L 101.5994,397.145 C 92.881396,378.584 87.999396,357.864 87.999396,336 v -16 h -55.334 C 15.229396,320 0.49039597,306.33 0.01239597,288.9 -0.48460403,270.816 14.027396,256 31.999396,256 h 56 v -58.745 l -46.628,-46.628 c -12.496,-12.497 -12.496,-32.758 0,-45.255 12.498,-12.497 32.758,-12.497 45.256,0 L 141.2544,160 h 229.489 l 54.627,-54.627 c 12.498,-12.497 32.758,-12.497 45.256,0 12.496,12.497 12.496,32.758 0,45.255 l -46.627,46.627 V 256 h 56 c 17.972,0 32.484,14.816 31.988,32.9 M 256.9994,0 c -61.856,0 -112,50.144 -112,112 h 224 c 0,-61.856 -50.144,-112 -112,-112"
     id="path1" />
</svg>`,"galaxies/cancer":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="0.0000 0.0000 576.0000 325.1219"
   version="1.1"
   id="svg1"
   sodipodi:docname="cancer.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 420.55,243.05193 a 24,24 0 1 1 24,-24 24,24 0 0 1 -24,24 m -265.1,0 a 24,24 0 1 1 24,-24 24,24 0 0 1 -24,24 m 273.7,-144.480001 47.94,-83 A 10,10 0 1 0 459.82,5.5719285 L 411.28,89.641929 a 301.25,301.25 0 0 0 -246.56,0 L 116.18,5.5719285 A 10,10 0 1 0 98.91,15.571929 l 47.94,83 C 64.53,143.34193 8.24,226.67193 0,325.12193 h 576 c -8.24,-98.45 -64.54,-181.78 -146.85,-226.550001"
     id="path1" />
</svg>`,"galaxies/cert-eu-govsector":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-62.0500 0.0000 620.0000 496.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="cert-eu-govsector.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 336.5,152 C 322,62.7 287.8,0 248,0 208.2,0 174,62.7 159.5,152 Z M 152,248 c 0,22.2 1.2,43.5 3.3,64 h 185.3 c 2.1,-20.5 3.3,-41.8 3.3,-64 0,-22.2 -1.2,-43.5 -3.3,-64 H 155.3 c -2.1,20.5 -3.3,41.8 -3.3,64 M 476.7,152 C 448.1,84.1 390.2,31.6 318.7,10.4 c 24.4,33.8 41.2,84.7 50,141.6 z M 177.2,10.4 C 105.8,31.6 47.8,84.1 19.3,152 h 108 C 136,95.1 152.8,44.2 177.2,10.4 M 487.4,184 H 372.7 c 2.1,21 3.3,42.5 3.3,64 0,21.5 -1.2,43 -3.3,64 h 114.6 c 5.5,-20.5 8.6,-41.8 8.6,-64 0,-22.2 -3.1,-43.5 -8.5,-64 M 120,248 c 0,-21.5 1.2,-43 3.3,-64 H 8.6 C 3.2,204.5 0,225.8 0,248 c 0,22.2 3.2,43.5 8.6,64 h 114.6 c -2,-21 -3.2,-42.5 -3.2,-64 m 39.5,96 c 14.5,89.3 48.7,152 88.5,152 39.8,0 74,-62.7 88.5,-152 z m 159.3,141.6 c 71.4,-21.2 129.4,-73.7 158,-141.6 h -108 c -8.8,56.9 -25.6,107.8 -50,141.6 M 19.3,344 c 28.6,67.9 86.5,120.4 158,141.6 -24.4,-33.8 -41.2,-84.7 -50,-141.6 z"
     id="path1" />
</svg>`,"galaxies/china-defence-universities":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-62.0500 0.0000 620.0000 496.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="china-defence-universities.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 336.5,152 C 322,62.7 287.8,0 248,0 208.2,0 174,62.7 159.5,152 Z M 152,248 c 0,22.2 1.2,43.5 3.3,64 h 185.3 c 2.1,-20.5 3.3,-41.8 3.3,-64 0,-22.2 -1.2,-43.5 -3.3,-64 H 155.3 c -2.1,20.5 -3.3,41.8 -3.3,64 M 476.7,152 C 448.1,84.1 390.2,31.6 318.7,10.4 c 24.4,33.8 41.2,84.7 50,141.6 z M 177.2,10.4 C 105.8,31.6 47.8,84.1 19.3,152 h 108 C 136,95.1 152.8,44.2 177.2,10.4 M 487.4,184 H 372.7 c 2.1,21 3.3,42.5 3.3,64 0,21.5 -1.2,43 -3.3,64 h 114.6 c 5.5,-20.5 8.6,-41.8 8.6,-64 0,-22.2 -3.1,-43.5 -8.5,-64 M 120,248 c 0,-21.5 1.2,-43 3.3,-64 H 8.6 C 3.2,204.5 0,225.8 0,248 c 0,22.2 3.2,43.5 8.6,64 h 114.6 c -2,-21 -3.2,-42.5 -3.2,-64 m 39.5,96 c 14.5,89.3 48.7,152 88.5,152 39.8,0 74,-62.7 88.5,-152 z m 159.3,141.6 c 71.4,-21.2 129.4,-73.7 158,-141.6 h -108 c -8.8,56.9 -25.6,107.8 -50,141.6 M 19.3,344 c 28.6,67.9 86.5,120.4 158,141.6 -24.4,-33.8 -41.2,-84.7 -50,-141.6 z"
     id="path1" />
</svg>`,"galaxies/cloak":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-95.9909 0.0000 639.9818 511.9854"
   version="1.1"
   id="svg1"
   sodipodi:docname="cloak.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 383.9,308.28542 23.9,-62.6 c 4,-10.5 -3.7,-21.7 -15,-21.7 h -58.5 c 11,-18.9 17.8,-40.6 17.8,-64 v -0.3 c 39.2,-7.8 64,-19.1 64,-31.7 0,-13.3 -27.3,-25.1 -70.1,-32.999997 -9.2,-32.8 -27,-65.8 -40.6,-82.8 C 295.9,0.28542306 279.5,-3.4145769 265.9,3.3854231 L 238.3,17.185423 c -9,4.5 -19.6,4.5 -28.6,0 L 182.1,3.3854231 c -13.6,-6.8 -30,-3.10000004 -39.5,8.7999999 -13.5,17 -31.4,50 -40.6,82.8 -42.7,7.899997 -70,19.699997 -70,32.999997 0,12.6 24.8,23.9 64,31.7 v 0.3 c 0,23.4 6.8,45.1 17.8,64 H 56.3 c -11.5,0 -19.2,11.7 -14.7,22.3 l 25.8,60.2 c -40.1,23.3 -67.4,66.2 -67.4,115.9 v 44.8 c 0,24.7 20.1,44.8 44.8,44.8 h 358.4 c 24.7,0 44.8,-20.1 44.8,-44.8 v -44.8 c 0,-48.4 -25.8,-90.4 -64.1,-114.1 m -207.9,171.7 -41.6,-192 49.6,32 24,40 z m 96,0 -32,-120 24,-40 49.6,-32 z m 41.7,-298.5 c -3.9,11.9 -7,24.6 -16.5,33.4 -10.1,9.3 -48,22.4 -64,-25 -2.8,-8.4 -15.4,-8.4 -18.3,0 -17,50.2 -56,32.4 -64,25 -9.5,-8.8 -12.7,-21.5 -16.5,-33.4 -0.8,-2.5 -6.3,-5.7 -6.3,-5.8 v -10.8 c 28.3,3.6 61,5.8 96,5.8 35,0 67.7,-2.1 96,-5.8 v 10.8 c -0.1,0.1 -5.6,3.2 -6.4,5.8"
     id="path1" />
</svg>`,"galaxies/cmtmf-attack-pattern":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-160.0000 0.0000 640.0000 512.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="cmtmf-attack-pattern.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 272,0 H 48 C 21.5,0 0,21.5 0,48 v 416 c 0,26.5 21.5,48 48,48 h 224 c 26.5,0 48,-21.5 48,-48 V 48 C 320,21.5 298.5,0 272,0 M 160,480 c -17.7,0 -32,-14.3 -32,-32 0,-17.7 14.3,-32 32,-32 17.7,0 32,14.3 32,32 0,17.7 -14.3,32 -32,32"
     id="path1" />
</svg>`,"galaxies/country":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-62.0500 0.0000 620.0000 496.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="country.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 336.5,152 C 322,62.7 287.8,0 248,0 208.2,0 174,62.7 159.5,152 Z M 152,248 c 0,22.2 1.2,43.5 3.3,64 h 185.3 c 2.1,-20.5 3.3,-41.8 3.3,-64 0,-22.2 -1.2,-43.5 -3.3,-64 H 155.3 c -2.1,20.5 -3.3,41.8 -3.3,64 M 476.7,152 C 448.1,84.1 390.2,31.6 318.7,10.4 c 24.4,33.8 41.2,84.7 50,141.6 z M 177.2,10.4 C 105.8,31.6 47.8,84.1 19.3,152 h 108 C 136,95.1 152.8,44.2 177.2,10.4 M 487.4,184 H 372.7 c 2.1,21 3.3,42.5 3.3,64 0,21.5 -1.2,43 -3.3,64 h 114.6 c 5.5,-20.5 8.6,-41.8 8.6,-64 0,-22.2 -3.1,-43.5 -8.5,-64 M 120,248 c 0,-21.5 1.2,-43 3.3,-64 H 8.6 C 3.2,204.5 0,225.8 0,248 c 0,22.2 3.2,43.5 8.6,64 h 114.6 c -2,-21 -3.2,-42.5 -3.2,-64 m 39.5,96 c 14.5,89.3 48.7,152 88.5,152 39.8,0 74,-62.7 88.5,-152 z m 159.3,141.6 c 71.4,-21.2 129.4,-73.7 158,-141.6 h -108 c -8.8,56.9 -25.6,107.8 -50,141.6 M 19.3,344 c 28.6,67.9 86.5,120.4 158,141.6 -24.4,-33.8 -41.2,-84.7 -50,-141.6 z"
     id="path1" />
</svg>`,"galaxies/cryptominers":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-13.5444 0.0000 603.2721 482.6177"
   version="1.1"
   id="svg1"
   sodipodi:docname="cryptominers.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 572.756,406.76941 c 5.6,-9.5 4.7,-15.2 -5.4,-11.6 -3,-4.9 -7,-9.5 -11.1,-13.8 2.9,-9.7 -0.7,-14.2 -10.8,-9.2 -4.6,-3.2 -10.3,-6.5 -15.9,-9.2 0,-15.1 -11.6,-11.6 -17.6,-5.7 -10.4,-1.5 -18.7,-0.3 -26.8,5.7 0.3,-6.5 0.3,-13 0.3,-19.7 12.6,0 40.2,-11 45.9,-36.2 1.4,-6.8 1.6,-13.8 -0.3,-21.9 -3,-13.5 -14.3,-21.3 -25.1,-25.7 -0.8,-5.9 -7.6,-14.3 -14.9,-15.9 -7.3,-1.6 -12.4,4.9 -14.1,10.3 -8.5,0 -19.2,2.8 -21.1,8.4 -5.4,-0.5 -11.1,-1.4 -16.8,-1.9 2.7,-1.9 5.4,-3.5 8.4,-4.6 5.4,-9.2 14.6,-11.4 25.7,-11.6 v -2.8 c 19.5,-0.5 43,-5.9 53.8,-18.1 12.7,-13.8 14.6,-37.3 12.4,-55.1 -2.4,-17.3 -9.7,-37.6 -24.6,-48.1 -8.4,-5.9 -21.6,-0.8 -22.7,9.5 -2.2,19.6 1.2,30 -38.6,25.1 -10.3,-23.8 -24.6,-44.6 -42.7,-60.000005 -69.6,-59.7 -167.7,-53.8 -244.2,-37.6 19.7,4.6 41.1,8.6 59.7,16.5 -26.2,2.4 -52.7,11.3 -76.2,23.2 -32.8,17.000005 -44,29.900005 -56.7,42.400005 14.9,-2.2 28.9,-5.1 43.8,-3.8 -9.7,5.4 -18.4,12.2 -26.5,20 -25.8,0.9 -23.8,-5.3 -26.2,-25.9 -1.1,-10.5 -14.3,-15.4 -22.7,-9.7 -28.1,19.9 -33.5,79.9 -12.2,103.5 10.8,12.2 35.1,17.3 54.9,17.8 -0.3,1.1 -0.3,1.9 -0.3,2.7 10.8,0.5 19.5,2.7 24.6,11.6 3,1.1 5.7,2.7 8.1,4.6 -5.4,0.5 -11.1,1.4 -16.5,1.9 -3.3,-6.6 -13.7,-8.1 -21.1,-8.1 -1.6,-5.7 -6.5,-12.2 -14.1,-10.3 -6.8,1.9 -14.1,10 -14.9,15.9 -22.5,9.5 -30.1,26.8 -25.1,47.6 5.3,24.8 33,36.2 45.9,36.2 v 19.7 c -6.6,-5 -14.3,-7.5 -26.8,-5.7 -5.5,-5.5 -17.3,-10.1 -17.3,5.7 -5.9,2.7 -11.4,5.9 -15.9,9.2 -9.8,-4.9 -13.6,-1.7 -11.1,9.2 -4.1,4.3 -7.8,8.6 -11.1,13.8 -10.2,-3.7 -11,2.2 -5.4,11.6 -1.1,3.5 -1.6,7 -1.9,10.8 -0.5,31.6 44.6,64 73.5,65.1 17.3,0.5 34.6,-8.4 43,-23.5 113.2,4.9 226.7,4.1 340.2,0 8.1,15.1 25.4,24.3 42.7,23.5 29.2,-1.1 74.3,-33.5 73.5,-65.1 0.2,-3.7 -0.7,-7.2 -1.7,-10.7 m -73.8,-254 c 1.1,-3 2.4,-8.4 2.4,-14.6 0,-5.9 6.8,-8.1 14.1,-0.8 11.1,11.6 14.9,40.5 13.8,51.1 -4.1,-13.6 -13,-29 -30.3,-35.7 m -4.6,6.7 c 19.5,6.2 28.6,27.6 29.7,48.9 -1.1,2.7 -3,5.4 -4.9,7.6 -5.7,5.9 -15.4,10 -26.2,12.2 4.3,-21.3 0.3,-47.3 -12.7,-63 4.9,-0.8 10.9,-2.4 14.1,-5.7 m -24.1,6.8 c 13.8,11.9 20,39.2 14.1,63.5 -4.1,0.5 -8.1,0.8 -11.6,0.8 -1.9,-21.9 -6.8,-44 -14.3,-64.6 3.7,0.3 8.1,0.3 11.8,0.3 m -422.6,22.1 c -1.1,-10.5 2.4,-39.5 13.8,-51.1 7,-7.3 14.1,-5.1 14.1,0.8 0,6.2 1.4,11.6 2.4,14.6 -17.3,6.8 -26.2,22.2 -30.3,35.7 m 9.7,27.6 c -1.9,-2.2 -3.5,-4.9 -4.9,-7.6 1.4,-21.3 10.3,-42.7 29.7,-48.9 3.2,3.2 9.2,4.9 14.1,5.7 -13,15.7 -17,41.6 -12.7,63 -10.8,-2.2 -20.5,-6 -26.2,-12.2 m 47.9,14.6 c -4.1,0 -8.1,-0.3 -12.7,-0.8 -4.6,-18.6 -1.9,-38.9 5.4,-53 v 0.3 l 12.2,-5.1 c 4.9,-1.9 9.7,-3.8 14.9,-4.9 -10.7,19.7 -17.4,41.3 -19.8,63.5 m 184,-162.700005 c 41.9,0 76.2,34.000005 76.2,75.900005 0,42.2 -34.3,76.2 -76.2,76.2 -41.9,0 -76.2,-34 -76.2,-76.2 0,-41.8 34.3,-75.900005 76.2,-75.900005 m 115.6,174.300005 c -0.3,17.8 -7,48.9 -23,57 -13.2,6.6 -6.5,-7.5 -16.5,-58.1 13.3,0.3 26.6,0.3 39.5,1.1 m -54,-1.6 c 0.8,4.9 3.8,40.3 -1.6,41.9 -11.6,3.5 -40,4.3 -51.1,-1.1 -4.1,-3 -4.6,-35.9 -4.3,-41.1 v 0.3 c 18.9,-0.3 38.1,-0.3 57,0 m -72.4,53.8 c -13,3.5 -41.6,4.1 -54.6,-1.6 -6.5,-2.7 -3.8,-42.4 -1.9,-51.6 19.2,-0.5 38.4,-0.5 57.8,-0.8 v 0.3 c 1.1,8.3 3.3,51.2 -1.3,53.7 m -106.5,-51.1 c 12.2,-0.8 24.6,-1.4 36.8,-1.6 -2.4,15.4 -3,43.5 -4.9,52.2 -1.1,6.8 -4.3,6.8 -9.7,4.3 -21.9,-9.8 -27.6,-35.2 -22.2,-54.9 m -35.4,31.3 c 7.8,-1.1 15.7,-1.9 23.5,-2.7 1.6,6.2 3.8,11.9 7,17.6 10,17 44,35.7 45.1,7 6.2,14.9 40.8,12.2 54.9,10.8 15.7,-1.4 23.8,-1.4 26.8,-14.3 12.4,4.3 30.8,4.1 44,3 11.3,-0.8 20.8,-0.5 24.6,-8.9 1.1,5.1 1.9,11.6 4.6,16.8 10.8,21.3 37.3,1.4 46.8,-31.6 8.6,0.8 17.6,1.9 26.5,2.7 -0.4,1.3 -3.8,7.3 7.3,11.6 -47.6,47 -95.7,87.8 -163.2,107 -63.2,-20.8 -112.1,-59.5 -155.9,-106.5 9.6,-3.4 10.4,-8.8 8,-12.5 m -21.6,172.5 c -3.8,17.8 -21.9,29.7 -39.7,28.9 -19.2,-0.8 -46.5,-17 -59.2,-36.5 -2.7,-31.1 43.8,-61.3 66.2,-54.6 14.9,4.3 27.8,30.8 33.5,54 0,3 -0.3,5.7 -0.8,8.2 m -8.7,-66 c -0.5,-13.5 -0.5,-27 -0.3,-40.5 h 0.3 c 2.7,-1.6 5.7,-3.8 7.8,-6.5 6.5,-1.6 13,-5.1 15.1,-9.2 3.3,-7.1 -7,-7.5 -5.4,-12.4 2.7,-1.1 5.7,-2.2 7.8,-3.5 29.2,29.2 58.6,56.5 97.3,77 -36.8,11.3 -72.4,27.6 -105.9,47 -1.2,-18.6 -7.7,-35.9 -16.7,-51.9 m 337.6,64.6 c -103,3.5 -206.2,4.1 -309.4,0 0,0.3 0,0.3 -0.3,0.3 v -0.3 h 0.3 c 35.1,-21.6 72.2,-39.2 112.4,-50.8 11.6,5.1 23,9.5 34.9,13.2 2.2,0.8 2.2,0.8 4.3,0 14.3,-4.1 28.4,-9.2 42.2,-15.4 41.5,11.7 78.8,31.7 115.6,53 m 10.5,-12.4 c -35.9,-19.5 -73,-35.9 -111.9,-47.6 38.1,-20 71.9,-47.3 103.5,-76.7 2.2,1.4 4.6,2.4 7.6,3.2 0,0.8 0.3,1.9 0.5,2.4 -4.6,2.7 -7.8,6.2 -5.9,10.3 2.2,3.8 8.6,7.6 15.1,8.9 2.4,2.7 5.1,5.1 8.1,6.8 0,13.8 -0.3,27.6 -0.8,41.3 l 0.3,-0.3 c -9.3,15.9 -15.5,37 -16.5,51.7 m 105.9,6.2 c -12.7,19.5 -40,35.7 -59.2,36.5 -19.3,0.9 -40.5,-13.2 -40.5,-37 5.7,-23.2 18.9,-49.7 33.5,-54 22.7,-6.9 69.2,23.4 66.2,54.5 M 373.056,60.569405 c -3.8,-72.1 -100.8,-79.7 -126,-23.5 44.6,-24.3 90.3,-15.7 126,23.5 M 74.956,392.46941 c -15.7,1.6 -49.5,25.4 -49.5,43.2 0,11.6 15.7,19.5 32.2,14.9 12.2,-3.2 31.1,-17.6 35.9,-27.3 6,-11.6 -3.7,-32.7 -18.6,-30.8 m 215.9,-176.2 c 28.6,0 51.9,-21.6 51.9,-48.4 0,-36.1 -40.5,-58.1 -72.2,-44.3 9.5,3 16.5,11.6 16.5,21.6 0,23.3 -33.3,32 -46.5,11.3 -7.3,34.1 19.4,59.8 50.3,59.8 m -222.7,243.2 c 0.5,6.5 12.2,12.7 21.6,9.5 6.8,-2.7 14.6,-10.5 17.3,-16.2 3,-7 -1.1,-20 -9.7,-18.4 -8.9,1.6 -29.7,16.7 -29.2,25.1 m 433.2,-67 c -14.9,-1.9 -24.6,19.2 -18.9,30.8 4.9,9.7 24.1,24.1 36.2,27.3 16.5,4.6 32.2,-3.2 32.2,-14.9 0,-17.8 -33.8,-41.6 -49.5,-43.2 m -22.4,41.9 c -8.4,-1.6 -12.4,11.3 -9.5,18.4 2.4,5.7 10.3,13.5 17.3,16.2 9.2,3.2 21.1,-3 21.3,-9.5 0.9,-8.4 -20.2,-23.5 -29.1,-25.1"
     id="path1" />
</svg>`,"galaxies/cti-cmm-1-3":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="0.0000 0.0000 576.0000 448.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="cti-cmm-1-3.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 0,85.66 v 346.32 c 0,11.32 11.43,19.06 21.94,14.86 L 160,384 V 0 L 20.12,55.95 A 32.01,32.01 0 0 0 0,85.66 M 192,384 384,448 V 64 L 192,0 Z M 554.06,1.16 416,64 V 448 L 555.88,392.05 A 32,32 0 0 0 576,362.34 V 16.02 C 576,4.7 564.57,-3.04 554.06,1.16"
     id="path1" />
</svg>`,"galaxies/cyfun-assurance-requirements-2023":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="0.0000 0.0000 576.0000 448.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="cyfun-assurance-requirements-2023.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 0,85.66 v 346.32 c 0,11.32 11.43,19.06 21.94,14.86 L 160,384 V 0 L 20.12,55.95 A 32.01,32.01 0 0 0 0,85.66 M 192,384 384,448 V 64 L 192,0 Z M 554.06,1.16 416,64 V 448 L 555.88,392.05 A 32,32 0 0 0 576,362.34 V 16.02 C 576,4.7 564.57,-3.04 554.06,1.16"
     id="path1" />
</svg>`,"galaxies/cyfun-control-catalogue-2023":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-4.0000 0.0000 520.0000 416.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="cyfun-control-catalogue-2023.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 80,320 H 16 A 16,16 0 0 0 0,336 v 64 a 16,16 0 0 0 16,16 H 80 A 16,16 0 0 0 96,400 V 336 A 16,16 0 0 0 80,320 M 80,0 H 16 A 16,16 0 0 0 0,16 V 80 A 16,16 0 0 0 16,96 H 80 A 16,16 0 0 0 96,80 V 16 A 16,16 0 0 0 80,0 m 0,160 H 16 A 16,16 0 0 0 0,176 v 64 a 16,16 0 0 0 16,16 H 80 A 16,16 0 0 0 96,240 V 176 A 16,16 0 0 0 80,160 M 496,336 H 176 a 16,16 0 0 0 -16,16 v 32 a 16,16 0 0 0 16,16 h 320 a 16,16 0 0 0 16,-16 V 352 A 16,16 0 0 0 496,336 M 496,16 H 176 a 16,16 0 0 0 -16,16 v 32 a 16,16 0 0 0 16,16 H 496 A 16,16 0 0 0 512,64 V 32 A 16,16 0 0 0 496,16 m 0,160 H 176 a 16,16 0 0 0 -16,16 v 32 a 16,16 0 0 0 16,16 h 320 a 16,16 0 0 0 16,-16 v -32 a 16,16 0 0 0 -16,-16"
     id="path1" />
</svg>`,"galaxies/dima-techniques":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="0.0000 0.0000 640.0000 512.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="dima-techniques.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 384,320 H 256 c -17.67,0 -32,14.33 -32,32 v 128 c 0,17.67 14.33,32 32,32 h 128 c 17.67,0 32,-14.33 32,-32 V 352 c 0,-17.67 -14.33,-32 -32,-32 M 192,32 C 192,14.33 177.67,0 160,0 H 32 C 14.33,0 0,14.33 0,32 v 128 c 0,17.67 14.33,32 32,32 h 95.72 l 73.16,128.04 C 211.98,300.98 232.4,288 256,288 h 0.28 L 192,175.51 V 128 H 416 V 64 H 192 Z M 608,0 H 480 c -17.67,0 -32,14.33 -32,32 v 128 c 0,17.67 14.33,32 32,32 h 128 c 17.67,0 32,-14.33 32,-32 V 32 C 640,14.33 625.67,0 608,0"
     id="path1" />
</svg>`,"galaxies/disarm-actortypes":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-95.9909 0.0000 639.9818 511.9854"
   version="1.1"
   id="svg1"
   sodipodi:docname="disarm-actortypes.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 383.9,308.28542 23.9,-62.6 c 4,-10.5 -3.7,-21.7 -15,-21.7 h -58.5 c 11,-18.9 17.8,-40.6 17.8,-64 v -0.3 c 39.2,-7.8 64,-19.1 64,-31.7 0,-13.3 -27.3,-25.1 -70.1,-32.999997 -9.2,-32.8 -27,-65.8 -40.6,-82.8 C 295.9,0.28542306 279.5,-3.4145769 265.9,3.3854231 L 238.3,17.185423 c -9,4.5 -19.6,4.5 -28.6,0 L 182.1,3.3854231 c -13.6,-6.8 -30,-3.10000004 -39.5,8.7999999 -13.5,17 -31.4,50 -40.6,82.8 -42.7,7.899997 -70,19.699997 -70,32.999997 0,12.6 24.8,23.9 64,31.7 v 0.3 c 0,23.4 6.8,45.1 17.8,64 H 56.3 c -11.5,0 -19.2,11.7 -14.7,22.3 l 25.8,60.2 c -40.1,23.3 -67.4,66.2 -67.4,115.9 v 44.8 c 0,24.7 20.1,44.8 44.8,44.8 h 358.4 c 24.7,0 44.8,-20.1 44.8,-44.8 v -44.8 c 0,-48.4 -25.8,-90.4 -64.1,-114.1 m -207.9,171.7 -41.6,-192 49.6,32 24,40 z m 96,0 -32,-120 24,-40 49.6,-32 z m 41.7,-298.5 c -3.9,11.9 -7,24.6 -16.5,33.4 -10.1,9.3 -48,22.4 -64,-25 -2.8,-8.4 -15.4,-8.4 -18.3,0 -17,50.2 -56,32.4 -64,25 -9.5,-8.8 -12.7,-21.5 -16.5,-33.4 -0.8,-2.5 -6.3,-5.7 -6.3,-5.8 v -10.8 c 28.3,3.6 61,5.8 96,5.8 35,0 67.7,-2.1 96,-5.8 v 10.8 c -0.1,0.1 -5.6,3.2 -6.4,5.8"
     id="path1" />
</svg>`,"galaxies/disarm-countermeasures":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-79.9688 0.0000 639.9376 511.9501"
   version="1.1"
   id="svg1"
   sodipodi:docname="disarm-countermeasures.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 450.5,83.675063 258.5,3.6750632 a 48.15,48.15 0 0 0 -36.9,0 L 29.6,83.675063 C 11.7,91.075063 0,108.57506 0,127.97506 c 0,198.5 114.5,335.7 221.5,380.3 11.8,4.9 25.1,4.9 36.9,0 85.7,-35.7 221.6,-159 221.6,-380.3 0,-19.4 -11.7,-36.899997 -29.5,-44.299997 M 240.1,446.27506 240,65.275063 415.9,138.57506 c -3.3,151.4 -82.1,261.1 -175.8,307.7"
     id="path1" />
</svg>`,"galaxies/disarm-detections":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-95.9993 0.0000 640.0000 512.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="disarm-detections.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 224.00069,512 c 35.32,0 63.97,-28.65 63.97,-64 h -127.94 c 0,35.35 28.65,64 63.97,64 m 215.39,-149.71 c -19.32,-20.76 -55.47,-51.99 -55.47,-154.29 0,-77.7 -54.48,-139.9 -127.94,-155.16 V 32 c 0,-17.67 -14.32,-32 -31.98,-32 -17.66,0 -31.98,14.33 -31.98,32 V 52.84 C 118.56069,68.1 64.080691,130.3 64.080691,208 c 0,102.3 -36.15,133.53 -55.4699996,154.29 -6,6.45 -8.66000001,14.16 -8.61000001189,21.71 C 0.11069139,400.4 12.980691,416 32.100691,416 H 415.90069 c 19.12,0 32,-15.6 32.1,-32 0.05,-7.55 -2.61,-15.27 -8.61,-21.71"
     id="path1" />
</svg>`,"galaxies/disarm-techniques":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="0.0000 0.0000 576.0000 448.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="disarm-techniques.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 0,85.66 v 346.32 c 0,11.32 11.43,19.06 21.94,14.86 L 160,384 V 0 L 20.12,55.95 A 32.01,32.01 0 0 0 0,85.66 M 192,384 384,448 V 64 L 192,0 Z M 554.06,1.16 416,64 V 448 L 555.88,392.05 A 32,32 0 0 0 576,362.34 V 16.02 C 576,4.7 564.57,-3.04 554.06,1.16"
     id="path1" />
</svg>`,"galaxies/election-guidelines":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="0.0000 0.0000 576.0000 448.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="election-guidelines.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 0,85.66 v 346.32 c 0,11.32 11.43,19.06 21.94,14.86 L 160,384 V 0 L 20.12,55.95 A 32.01,32.01 0 0 0 0,85.66 M 192,384 384,448 V 64 L 192,0 Z M 554.06,1.16 416,64 V 448 L 555.88,392.05 A 32,32 0 0 0 576,362.34 V 16.02 C 576,4.7 564.57,-3.04 554.06,1.16"
     id="path1" />
</svg>`,"galaxies/entity":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-96.0000 0.0000 640.0000 512.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="entity.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 224,256 C 294.7,256 352,198.7 352,128 352,57.3 294.7,0 224,0 153.3,0 96,57.3 96,128 c 0,70.7 57.3,128 128,128 m 89.6,32 h -16.7 c -22.2,10.2 -46.9,16 -72.9,16 -26,0 -50.6,-5.8 -72.9,-16 H 134.4 C 60.2,288 0,348.2 0,422.4 V 464 c 0,26.5 21.5,48 48,48 h 352 c 26.5,0 48,-21.5 48,-48 V 422.4 C 448,348.2 387.8,288 313.6,288"
     id="path1" />
</svg>`,"galaxies/exercise-world":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-62.0500 0.0000 620.0000 496.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="exercise-world.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 336.5,152 C 322,62.7 287.8,0 248,0 208.2,0 174,62.7 159.5,152 Z M 152,248 c 0,22.2 1.2,43.5 3.3,64 h 185.3 c 2.1,-20.5 3.3,-41.8 3.3,-64 0,-22.2 -1.2,-43.5 -3.3,-64 H 155.3 c -2.1,20.5 -3.3,41.8 -3.3,64 M 476.7,152 C 448.1,84.1 390.2,31.6 318.7,10.4 c 24.4,33.8 41.2,84.7 50,141.6 z M 177.2,10.4 C 105.8,31.6 47.8,84.1 19.3,152 h 108 C 136,95.1 152.8,44.2 177.2,10.4 M 487.4,184 H 372.7 c 2.1,21 3.3,42.5 3.3,64 0,21.5 -1.2,43 -3.3,64 h 114.6 c 5.5,-20.5 8.6,-41.8 8.6,-64 0,-22.2 -3.1,-43.5 -8.5,-64 M 120,248 c 0,-21.5 1.2,-43 3.3,-64 H 8.6 C 3.2,204.5 0,225.8 0,248 c 0,22.2 3.2,43.5 8.6,64 h 114.6 c -2,-21 -3.2,-42.5 -3.2,-64 m 39.5,96 c 14.5,89.3 48.7,152 88.5,152 39.8,0 74,-62.7 88.5,-152 z m 159.3,141.6 c 71.4,-21.2 129.4,-73.7 158,-141.6 h -108 c -8.8,56.9 -25.6,107.8 -50,141.6 M 19.3,344 c 28.6,67.9 86.5,120.4 158,141.6 -24.4,-33.8 -41.2,-84.7 -50,-141.6 z"
     id="path1" />
</svg>`,"galaxies/exploit-kit":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-64.0001 0.0000 640.0000 512.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="exploit-kit.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 483.049,159.70637 c 10.855,-24.575 21.424,-60.438002 21.424,-87.871002 0,-72.72200002 -79.641,-98.371 -209.673,-38.577 -107.632,-7.181 -211.221,73.670002 -237.098,186.457002 30.852,-34.862 78.271,-82.298 121.977,-101.158 -54.275,48.293 -100.551,109.445 -135.687,173.168 C 23.246,329.65137 0,390.94037 0,436.74737 c 0,98.575 92.854,86.5 180.251,42.006 31.423,15.43 66.559,15.573 101.695,15.573 97.124,0 184.249,-54.294 216.814,-146.022 H 377.927 c -52.509,88.593 -196.819,52.996 -196.819,-47.436 H 509.9 c 6.407,-43.581 -1.655,-95.715 -26.851,-141.162 m -418.49,187.171 c 17.711,51.15 53.703,95.871 100.266,123.304 -88.741,48.94 -173.267,29.096 -100.266,-123.304 m 115.977,-108.873 c 2,-55.151 50.276,-94.871 103.98,-94.871 53.418,0 101.981,39.72 103.981,94.871 z M 365.072,50.404368 c 21.425,-10.287 48.563,-22.003 72.558,-22.003 31.422,0 54.274,21.717 54.274,53.722 0,20.003002 -7.427,49.007002 -14.569,67.867002 -26.28,-42.292 -65.986,-81.584002 -112.263,-99.586002"
     id="path1" />
</svg>`,"galaxies/firearms":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-128.0004 0.0000 640.0008 512.0006"
   version="1.1"
   id="svg1"
   sodipodi:docname="firearms.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 216,23.860635 C 216,0.06063523 185.35,-8.9093648 171.85,10.820635 48,191.85064 224,200.00064 224,288.00064 c 0,35.63 -29.11,64.46 -64.85,63.99 -35.17,-0.45 -63.15,-29.77 -63.15,-64.94 v -85.51 c 0,-21.7 -26.47,-32.23 -41.43,-16.5 -26.77,28.12 -54.57,76.29 -54.57,134.96 0,105.87 86.13,192 192,192 105.87,0 192,-86.13 192,-192 0,-170.29 -168,-193 -168,-296.140005"
     id="path1" />
</svg>`,"galaxies/first-csirt-services-framework":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-96.0000 0.0000 640.0000 512.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="first-csirt-services-framework.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 224,256 C 294.7,256 352,198.7 352,128 352,57.3 294.7,0 224,0 153.3,0 96,57.3 96,128 c 0,70.7 57.3,128 128,128 m 89.6,32 h -16.7 c -22.2,10.2 -46.9,16 -72.9,16 -26,0 -50.6,-5.8 -72.9,-16 H 134.4 C 60.2,288 0,348.2 0,422.4 V 464 c 0,26.5 21.5,48 48,48 h 352 c 26.5,0 48,-21.5 48,-48 V 422.4 C 448,348.2 387.8,288 313.6,288"
     id="path1" />
</svg>`,"galaxies/first-dns":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-96.0000 0.0000 640.0000 512.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="first-dns.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 448,73.143 v 45.714 C 448,159.143 347.667,192 224,192 100.333,192 0,159.143 0,118.857 V 73.143 C 0,32.857 100.333,0 224,0 347.667,0 448,32.857 448,73.143 M 448,176 V 278.857 C 448,319.143 347.667,352 224,352 100.333,352 0,319.143 0,278.857 V 176 c 48.125,33.143 136.208,48.572 224,48.572 87.792,0 175.874,-15.429 224,-48.572 m 0,160 V 438.857 C 448,479.143 347.667,512 224,512 100.333,512 0,479.143 0,438.857 V 336 c 48.125,33.143 136.208,48.572 224,48.572 87.792,0 175.874,-15.429 224,-48.572"
     id="path1" />
</svg>`,"galaxies/gsma-motif":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="0.0000 0.0000 640.0000 512.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="gsma-motif.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 622.3,271.1 -115.2,-45 c -4.1,-1.6 -12.6,-3.7 -22.2,0 l -115.2,45 c -10.7,4.2 -17.7,14 -17.7,24.9 0,111.6 68.7,188.8 132.9,213.9 9.6,3.7 18,1.6 22.2,0 51.3,-20 132.9,-89.4 132.9,-213.9 0,-10.9 -7,-20.7 -17.7,-24.9 M 496,462.4 V 273.3 l 95.5,37.3 C 585.9,397.7 530.6,446 496,462.4 M 224,256 C 294.7,256 352,198.7 352,128 352,57.3 294.7,0 224,0 153.3,0 96,57.3 96,128 c 0,70.7 57.3,128 128,128 m 96,40 c 0,-2.5 0.8,-4.8 1.1,-7.2 -2.5,-0.1 -4.9,-0.8 -7.5,-0.8 h -16.7 c -22.2,10.2 -46.9,16 -72.9,16 -26,0 -50.6,-5.8 -72.9,-16 H 134.4 C 60.2,288 0,348.2 0,422.4 V 464 c 0,26.5 21.5,48 48,48 h 352 c 6.8,0 13.3,-1.5 19.2,-4 C 365.2,465.1 320,391.3 320,296"
     id="path1" />
</svg>`,"galaxies/handicap":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-64.0000 0.0000 640.0000 512.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="handicap.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 496.101,385.66896 14.227,28.663 c 3.929,7.915 0.697,17.516 -7.218,21.445 l -65.465,32.886 c -16.049,7.967 -35.556,1.194 -43.189,-15.055 l -62.777,-133.608 H 192 c -15.925,0 -29.426,-11.71 -31.679,-27.475 C 126.433,55.307959 128.38,70.043959 128,63.999959 128,27.641959 158.318,-1.6350407 195.052,0.07095931 228.323,1.6159593 255.1,28.975959 255.977,62.271959 c 0.868,32.933 -23.152,60.423001 -54.608,65.039001 l 4.67,32.69 H 336 c 8.837,0 16,7.163 16,16 v 32 c 0,8.837 -7.163,16 -16,16 H 215.182 l 4.572,32 H 352 a 32,32 0 0 1 28.962,18.392 l 57.515,122.407 36.178,-18.349 c 7.915,-3.929 17.517,-0.697 21.446,7.218 m -184.743,-33.669 h -24.506 c -7.788,54.204 -54.528,96 -110.852,96 -61.757,0 -112,-50.243 -112,-112 0,-41.505 22.694,-77.809 56.324,-97.156 -3.712,-25.965 -6.844,-47.86 -9.488,-66.333 C 45.956,198.46396 0,261.96296 0,335.99996 c 0,97.047 78.953,176 176,176 71.87,0 133.806,-43.308 161.11,-105.192 z"
     id="path1" />
</svg>`,"galaxies/human-kill-chain":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-32.0000 0.0000 640.0000 512.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="human-kill-chain.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 96,128 A 64,64 0 1 0 32,64 64,64 0 0 0 96,128 m 0,176.08 a 44.1,44.1 0 0 1 13.64,-32 L 181.77,204 c 1.65,-1.55 3.77,-2.31 5.61,-3.57 A 63.91,63.91 0 0 0 128,160 H 64 A 64,64 0 0 0 0,224 v 96 a 32,32 0 0 0 32,32 v 128 a 32,32 0 0 0 32,32 h 64 a 32,32 0 0 0 32,-32 V 383.61 L 109.64,336.08 A 44.08,44.08 0 0 1 96,304.08 M 480,128 a 64,64 0 1 0 -64,-64 64,64 0 0 0 64,64 m 32,32 h -64 a 63.91,63.91 0 0 0 -59.38,40.42 c 1.84,1.27 4,2 5.62,3.59 l 72.12,68.06 a 44.37,44.37 0 0 1 0,64 L 416,383.62 V 480 a 32,32 0 0 0 32,32 h 64 a 32,32 0 0 0 32,-32 V 352 a 32,32 0 0 0 32,-32 V 224 A 64,64 0 0 0 512,160 M 444.4,295.34 372.28,227.28 A 12,12 0 0 0 352,236 v 36 H 224 v -36 a 12,12 0 0 0 -20.28,-8.73 l -72.12,68.07 a 12.4,12.4 0 0 0 0,17.47 l 72.12,68.07 A 12,12 0 0 0 224,372.14 V 336 h 128 v 36.14 a 12,12 0 0 0 20.28,8.74 l 72.12,-68.07 a 12.4,12.4 0 0 0 0,-17.47"
     id="path1" />
</svg>`,"galaxies/intelligence-agencies":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-96.0000 0.0000 640.0000 512.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="intelligence-agencies.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 325.4,289.2 224,390.6 122.6,289.2 C 54,295.3 0,352.2 0,422.4 V 464 c 0,26.5 21.5,48 48,48 h 352 c 26.5,0 48,-21.5 48,-48 V 422.4 C 448,352.2 394,295.3 325.4,289.2 M 32,192 c 27.3,0 51.8,-11.5 69.2,-29.7 15.1,53.9 64,93.7 122.8,93.7 70.7,0 128,-57.3 128,-128 C 352,57.3 294.7,0 224,0 173.6,0 130.4,29.4 109.5,71.8 92.1,47.8 64,32 32,32 32,65.4 49.1,94.8 75.1,112 49.1,129.2 32,158.6 32,192 M 176,96 h 96 c 17.7,0 32,14.3 32,32 H 144 c 0,-17.7 14.3,-32 32,-32"
     id="path1" />
</svg>`,"galaxies/interpol-dwva":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-95.9909 0.0000 639.9818 511.9854"
   version="1.1"
   id="svg1"
   sodipodi:docname="interpol-dwva.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 383.9,308.28542 23.9,-62.6 c 4,-10.5 -3.7,-21.7 -15,-21.7 h -58.5 c 11,-18.9 17.8,-40.6 17.8,-64 v -0.3 c 39.2,-7.8 64,-19.1 64,-31.7 0,-13.3 -27.3,-25.1 -70.1,-32.999997 -9.2,-32.8 -27,-65.8 -40.6,-82.8 C 295.9,0.28542306 279.5,-3.4145769 265.9,3.3854231 L 238.3,17.185423 c -9,4.5 -19.6,4.5 -28.6,0 L 182.1,3.3854231 c -13.6,-6.8 -30,-3.10000004 -39.5,8.7999999 -13.5,17 -31.4,50 -40.6,82.8 -42.7,7.899997 -70,19.699997 -70,32.999997 0,12.6 24.8,23.9 64,31.7 v 0.3 c 0,23.4 6.8,45.1 17.8,64 H 56.3 c -11.5,0 -19.2,11.7 -14.7,22.3 l 25.8,60.2 c -40.1,23.3 -67.4,66.2 -67.4,115.9 v 44.8 c 0,24.7 20.1,44.8 44.8,44.8 h 358.4 c 24.7,0 44.8,-20.1 44.8,-44.8 v -44.8 c 0,-48.4 -25.8,-90.4 -64.1,-114.1 m -207.9,171.7 -41.6,-192 49.6,32 24,40 z m 96,0 -32,-120 24,-40 49.6,-32 z m 41.7,-298.5 c -3.9,11.9 -7,24.6 -16.5,33.4 -10.1,9.3 -48,22.4 -64,-25 -2.8,-8.4 -15.4,-8.4 -18.3,0 -17,50.2 -56,32.4 -64,25 -9.5,-8.8 -12.7,-21.5 -16.5,-33.4 -0.8,-2.5 -6.3,-5.7 -6.3,-5.8 v -10.8 c 28.3,3.6 61,5.8 96,5.8 35,0 67.7,-2.1 96,-5.8 v 10.8 c -0.1,0.1 -5.6,3.2 -6.4,5.8"
     id="path1" />
</svg>`,"galaxies/it-infrastructure-equipment":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-24.0000 0.0000 560.0000 448.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="it-infrastructure-equipment.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 480,128 H 32 C 14.327,128 0,113.673 0,96 V 32 C 0,14.327 14.327,0 32,0 h 448 c 17.673,0 32,14.327 32,32 v 64 c 0,17.673 -14.327,32 -32,32 M 432,40 c -13.255,0 -24,10.745 -24,24 0,13.255 10.745,24 24,24 13.255,0 24,-10.745 24,-24 0,-13.255 -10.745,-24 -24,-24 m -64,0 c -13.255,0 -24,10.745 -24,24 0,13.255 10.745,24 24,24 13.255,0 24,-10.745 24,-24 0,-13.255 -10.745,-24 -24,-24 M 480,288 H 32 C 14.327,288 0,273.673 0,256 v -64 c 0,-17.673 14.327,-32 32,-32 h 448 c 17.673,0 32,14.327 32,32 v 64 c 0,17.673 -14.327,32 -32,32 m -48,-88 c -13.255,0 -24,10.745 -24,24 0,13.255 10.745,24 24,24 13.255,0 24,-10.745 24,-24 0,-13.255 -10.745,-24 -24,-24 m -64,0 c -13.255,0 -24,10.745 -24,24 0,13.255 10.745,24 24,24 13.255,0 24,-10.745 24,-24 0,-13.255 -10.745,-24 -24,-24 M 480,448 H 32 C 14.327,448 0,433.673 0,416 v -64 c 0,-17.673 14.327,-32 32,-32 h 448 c 17.673,0 32,14.327 32,32 v 64 c 0,17.673 -14.327,32 -32,32 m -48,-88 c -13.255,0 -24,10.745 -24,24 0,13.255 10.745,24 24,24 13.255,0 24,-10.745 24,-24 0,-13.255 -10.745,-24 -24,-24 m -64,0 c -13.255,0 -24,10.745 -24,24 0,13.255 10.745,24 24,24 13.255,0 24,-10.745 24,-24 0,-13.255 -10.745,-24 -24,-24"
     id="path1" />
</svg>`,"galaxies/malpedia":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-80.0008 0.0000 640.0016 512.0013"
   version="1.1"
   id="svg1"
   sodipodi:docname="malpedia.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 208.00002,192 a 16,16 0 1 0 16,16 16,16 0 0 0 -16,-16 m 242.5,-108.32 -192,-80 a 57.4,57.4 0 0 0 -18.45,-3.68 57.4,57.4 0 0 0 -18.46,3.67 l -191.999996,80 A 47.93,47.93 0 0 0 2.3644917e-5,128 C 2.3644917e-5,326.5 114.50002,463.72 221.50002,508.32 a 48.1,48.1 0 0 0 36.91,0 c 85.68,-35.71 221.59,-159.02 221.59,-380.32 a 48,48 0 0 0 -29.5,-44.32 m -82.5,172.32 h -12.12 c -28.51,0 -42.79,34.47 -22.63,54.63 l 8.58,8.57 a 16.001826,16.001826 0 1 1 -22.63,22.63 l -8.57,-8.58 c -20.16,-20.16 -54.63,-5.88 -54.63,22.63 V 368 a 16,16 0 0 1 -32,0 v -12.12 c 0,-28.51 -34.47,-42.79 -54.63,-22.63 l -8.57,8.58 a 16.001826,16.001826 0 0 1 -22.63,-22.63 l 8.58,-8.57 c 20.16,-20.16 5.88,-54.63 -22.63,-54.63 h -12.12 a 16,16 0 0 1 0,-32 h 12.12 c 28.51,0 42.79,-34.47 22.63,-54.63 l -8.58,-8.57 a 16.001826,16.001826 0 0 1 22.63,-22.63 l 8.57,8.58 c 20.16,20.16 54.63,5.88 54.63,-22.63 V 112 a 16,16 0 0 1 32,0 v 12.12 c 0,28.51 34.47,42.79 54.63,22.63 l 8.57,-8.58 a 16.001826,16.001826 0 0 1 22.63,22.63 l -8.58,8.57 c -20.16,20.16 -5.88,54.63 22.63,54.63 h 12.12 a 16,16 0 0 1 0,32 m -96,0 a 16,16 0 1 0 16,16 16,16 0 0 0 -16,-16"
     id="path1" />
</svg>`,"galaxies/microsoft-activity-group":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-95.9909 0.0000 639.9818 511.9854"
   version="1.1"
   id="svg1"
   sodipodi:docname="microsoft-activity-group.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 383.9,308.28542 23.9,-62.6 c 4,-10.5 -3.7,-21.7 -15,-21.7 h -58.5 c 11,-18.9 17.8,-40.6 17.8,-64 v -0.3 c 39.2,-7.8 64,-19.1 64,-31.7 0,-13.3 -27.3,-25.1 -70.1,-32.999997 -9.2,-32.8 -27,-65.8 -40.6,-82.8 C 295.9,0.28542306 279.5,-3.4145769 265.9,3.3854231 L 238.3,17.185423 c -9,4.5 -19.6,4.5 -28.6,0 L 182.1,3.3854231 c -13.6,-6.8 -30,-3.10000004 -39.5,8.7999999 -13.5,17 -31.4,50 -40.6,82.8 -42.7,7.899997 -70,19.699997 -70,32.999997 0,12.6 24.8,23.9 64,31.7 v 0.3 c 0,23.4 6.8,45.1 17.8,64 H 56.3 c -11.5,0 -19.2,11.7 -14.7,22.3 l 25.8,60.2 c -40.1,23.3 -67.4,66.2 -67.4,115.9 v 44.8 c 0,24.7 20.1,44.8 44.8,44.8 h 358.4 c 24.7,0 44.8,-20.1 44.8,-44.8 v -44.8 c 0,-48.4 -25.8,-90.4 -64.1,-114.1 m -207.9,171.7 -41.6,-192 49.6,32 24,40 z m 96,0 -32,-120 24,-40 49.6,-32 z m 41.7,-298.5 c -3.9,11.9 -7,24.6 -16.5,33.4 -10.1,9.3 -48,22.4 -64,-25 -2.8,-8.4 -15.4,-8.4 -18.3,0 -17,50.2 -56,32.4 -64,25 -9.5,-8.8 -12.7,-21.5 -16.5,-33.4 -0.8,-2.5 -6.3,-5.7 -6.3,-5.8 v -10.8 c 28.3,3.6 61,5.8 96,5.8 35,0 67.7,-2.1 96,-5.8 v 10.8 c -0.1,0.1 -5.6,3.2 -6.4,5.8"
     id="path1" />
</svg>`,"galaxies/misinfosec-amitt-misinformation-pattern":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="0.0000 0.0000 576.0000 448.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="misinfosec-amitt-misinformation-pattern.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 0,85.66 v 346.32 c 0,11.32 11.43,19.06 21.94,14.86 L 160,384 V 0 L 20.12,55.95 A 32.01,32.01 0 0 0 0,85.66 M 192,384 384,448 V 64 L 192,0 Z M 554.06,1.16 416,64 V 448 L 555.88,392.05 A 32,32 0 0 0 576,362.34 V 16.02 C 576,4.7 564.57,-3.04 554.06,1.16"
     id="path1" />
</svg>`,"galaxies/mitre-analytic":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-79.9688 0.0000 639.9376 511.9501"
   version="1.1"
   id="svg1"
   sodipodi:docname="mitre-analytic.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 450.5,83.675063 258.5,3.6750632 a 48.15,48.15 0 0 0 -36.9,0 L 29.6,83.675063 C 11.7,91.075063 0,108.57506 0,127.97506 c 0,198.5 114.5,335.7 221.5,380.3 11.8,4.9 25.1,4.9 36.9,0 85.7,-35.7 221.6,-159 221.6,-380.3 0,-19.4 -11.7,-36.899997 -29.5,-44.299997 M 240.1,446.27506 240,65.275063 415.9,138.57506 c -3.3,151.4 -82.1,261.1 -175.8,307.7"
     id="path1" />
</svg>`,"galaxies/mitre-atlas-attack-pattern":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="0.0000 0.0000 576.0000 448.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="mitre-atlas-attack-pattern.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 0,85.66 v 346.32 c 0,11.32 11.43,19.06 21.94,14.86 L 160,384 V 0 L 20.12,55.95 A 32.01,32.01 0 0 0 0,85.66 M 192,384 384,448 V 64 L 192,0 Z M 554.06,1.16 416,64 V 448 L 555.88,392.05 A 32,32 0 0 0 576,362.34 V 16.02 C 576,4.7 564.57,-3.04 554.06,1.16"
     id="path1" />
</svg>`,"galaxies/mitre-atlas-course-of-action":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-64.0007 0.0000 640.0012 512.0010"
   version="1.1"
   id="svg1"
   sodipodi:docname="mitre-atlas-course-of-action.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 326.6125,185.3915 c 59.747,59.809 58.927,155.698 0.36,214.59 -0.11,0.12 -0.24,0.25 -0.36,0.37 l -67.2,67.2 c -59.27,59.27 -155.699,59.262 -214.96,0 -59.27,-59.26 -59.27,-155.7 0,-214.96 l 37.106,-37.106 c 9.84,-9.84 26.786,-3.3 27.294,10.606 0.648,17.722 3.826,35.527 9.69,52.721 1.986,5.822 0.567,12.262 -3.783,16.612 l -13.087,13.087 c -28.026,28.026 -28.905,73.66 -1.155,101.96 28.024,28.579 74.086,28.749 102.325,0.51 l 67.2,-67.19 c 28.191,-28.191 28.073,-73.757 0,-101.83 -3.701,-3.694 -7.429,-6.564 -10.341,-8.569 a 16.04,16.04 0 0 1 -6.947,-12.606 c -0.396,-10.567 3.348,-21.456 11.698,-29.806 l 21.054,-21.055 c 5.521,-5.521 14.182,-6.199 20.584,-1.731 a 152.5,152.5 0 0 1 20.522,17.197 m 140.935,-140.942 c -59.261,-59.262 -155.69,-59.27 -214.96,0 l -67.2,67.2 c -0.12,0.12 -0.25,0.25 -0.36,0.37 -58.566,58.892 -59.387,154.781 0.36,214.59 a 152.5,152.5 0 0 0 20.521,17.196 c 6.402,4.468 15.064,3.789 20.584,-1.731 l 21.054,-21.055 c 8.35,-8.35 12.094,-19.239 11.698,-29.806 a 16.04,16.04 0 0 0 -6.947,-12.606 c -2.912,-2.005 -6.64,-4.875 -10.341,-8.569 -28.073,-28.073 -28.191,-73.639 0,-101.83 l 67.2,-67.19 c 28.239,-28.239 74.3,-28.069 102.325,0.51 27.75,28.3 26.872,73.934 -1.155,101.96 l -13.087,13.087 c -4.35,4.35 -5.769,10.79 -3.783,16.612 5.864,17.194 9.042,34.999 9.69,52.721 0.509,13.906 17.454,20.446 27.294,10.606 l 37.106,-37.106 c 59.271,-59.259 59.271,-155.699 0.001,-214.959"
     id="path1" />
</svg>`,"galaxies/mitre-attack-pattern":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="0.0000 0.0000 576.0000 448.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="mitre-attack-pattern.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 0,85.66 v 346.32 c 0,11.32 11.43,19.06 21.94,14.86 L 160,384 V 0 L 20.12,55.95 A 32.01,32.01 0 0 0 0,85.66 M 192,384 384,448 V 64 L 192,0 Z M 554.06,1.16 416,64 V 448 L 555.88,392.05 A 32,32 0 0 0 576,362.34 V 16.02 C 576,4.7 564.57,-3.04 554.06,1.16"
     id="path1" />
</svg>`,"galaxies/mitre-course-of-action":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-64.0007 0.0000 640.0012 512.0010"
   version="1.1"
   id="svg1"
   sodipodi:docname="mitre-course-of-action.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 326.6125,185.3915 c 59.747,59.809 58.927,155.698 0.36,214.59 -0.11,0.12 -0.24,0.25 -0.36,0.37 l -67.2,67.2 c -59.27,59.27 -155.699,59.262 -214.96,0 -59.27,-59.26 -59.27,-155.7 0,-214.96 l 37.106,-37.106 c 9.84,-9.84 26.786,-3.3 27.294,10.606 0.648,17.722 3.826,35.527 9.69,52.721 1.986,5.822 0.567,12.262 -3.783,16.612 l -13.087,13.087 c -28.026,28.026 -28.905,73.66 -1.155,101.96 28.024,28.579 74.086,28.749 102.325,0.51 l 67.2,-67.19 c 28.191,-28.191 28.073,-73.757 0,-101.83 -3.701,-3.694 -7.429,-6.564 -10.341,-8.569 a 16.04,16.04 0 0 1 -6.947,-12.606 c -0.396,-10.567 3.348,-21.456 11.698,-29.806 l 21.054,-21.055 c 5.521,-5.521 14.182,-6.199 20.584,-1.731 a 152.5,152.5 0 0 1 20.522,17.197 m 140.935,-140.942 c -59.261,-59.262 -155.69,-59.27 -214.96,0 l -67.2,67.2 c -0.12,0.12 -0.25,0.25 -0.36,0.37 -58.566,58.892 -59.387,154.781 0.36,214.59 a 152.5,152.5 0 0 0 20.521,17.196 c 6.402,4.468 15.064,3.789 20.584,-1.731 l 21.054,-21.055 c 8.35,-8.35 12.094,-19.239 11.698,-29.806 a 16.04,16.04 0 0 0 -6.947,-12.606 c -2.912,-2.005 -6.64,-4.875 -10.341,-8.569 -28.073,-28.073 -28.191,-73.639 0,-101.83 l 67.2,-67.19 c 28.239,-28.239 74.3,-28.069 102.325,0.51 27.75,28.3 26.872,73.934 -1.155,101.96 l -13.087,13.087 c -4.35,4.35 -5.769,10.79 -3.783,16.612 5.864,17.194 9.042,34.999 9.69,52.721 0.509,13.906 17.454,20.446 27.294,10.606 l 37.106,-37.106 c 59.271,-59.259 59.271,-155.699 0.001,-214.959"
     id="path1" />
</svg>`,"galaxies/mitre-d3fend":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="0.0000 0.0000 640.0000 512.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="mitre-d3fend.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 622.3,271.1 -115.2,-45 c -4.1,-1.6 -12.6,-3.7 -22.2,0 l -115.2,45 c -10.7,4.2 -17.7,14 -17.7,24.9 0,111.6 68.7,188.8 132.9,213.9 9.6,3.7 18,1.6 22.2,0 51.3,-20 132.9,-89.4 132.9,-213.9 0,-10.9 -7,-20.7 -17.7,-24.9 M 496,462.4 V 273.3 l 95.5,37.3 C 585.9,397.7 530.6,446 496,462.4 M 224,256 C 294.7,256 352,198.7 352,128 352,57.3 294.7,0 224,0 153.3,0 96,57.3 96,128 c 0,70.7 57.3,128 128,128 m 96,40 c 0,-2.5 0.8,-4.8 1.1,-7.2 -2.5,-0.1 -4.9,-0.8 -7.5,-0.8 h -16.7 c -22.2,10.2 -46.9,16 -72.9,16 -26,0 -50.6,-5.8 -72.9,-16 H 134.4 C 60.2,288 0,348.2 0,422.4 V 464 c 0,26.5 21.5,48 48,48 h 352 c 6.8,0 13.3,-1.5 19.2,-4 C 365.2,465.1 320,391.3 320,296"
     id="path1" />
</svg>`,"galaxies/mitre-data-component":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="0.0000 0.0000 640.0000 512.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="mitre-data-component.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 128,352 H 32 C 14.33,352 0,366.33 0,384 v 96 c 0,17.67 14.33,32 32,32 h 96 c 17.67,0 32,-14.33 32,-32 v -96 c 0,-17.67 -14.33,-32 -32,-32 m -24,-80 h 192 v 48 h 48 v -48 h 192 v 48 h 48 V 262.41 C 584,241.24 566.77,224 545.59,224 H 344 v -64 h 40 c 17.67,0 32,-14.33 32,-32 V 32 C 416,14.33 401.67,0 384,0 H 256 c -17.67,0 -32,14.33 -32,32 v 96 c 0,17.67 14.33,32 32,32 h 40 v 64 H 94.41 C 73.23,224 56,241.23 56,262.41 V 320 h 48 z m 264,80 h -96 c -17.67,0 -32,14.33 -32,32 v 96 c 0,17.67 14.33,32 32,32 h 96 c 17.67,0 32,-14.33 32,-32 v -96 c 0,-17.67 -14.33,-32 -32,-32 m 240,0 h -96 c -17.67,0 -32,14.33 -32,32 v 96 c 0,17.67 14.33,32 32,32 h 96 c 17.67,0 32,-14.33 32,-32 v -96 c 0,-17.67 -14.33,-32 -32,-32"
     id="path1" />
</svg>`,"galaxies/mitre-data-source":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="0.0000 0.0000 640.0000 512.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="mitre-data-source.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 128,352 H 32 C 14.33,352 0,366.33 0,384 v 96 c 0,17.67 14.33,32 32,32 h 96 c 17.67,0 32,-14.33 32,-32 v -96 c 0,-17.67 -14.33,-32 -32,-32 m -24,-80 h 192 v 48 h 48 v -48 h 192 v 48 h 48 V 262.41 C 584,241.24 566.77,224 545.59,224 H 344 v -64 h 40 c 17.67,0 32,-14.33 32,-32 V 32 C 416,14.33 401.67,0 384,0 H 256 c -17.67,0 -32,14.33 -32,32 v 96 c 0,17.67 14.33,32 32,32 h 40 v 64 H 94.41 C 73.23,224 56,241.23 56,262.41 V 320 h 48 z m 264,80 h -96 c -17.67,0 -32,14.33 -32,32 v 96 c 0,17.67 14.33,32 32,32 h 96 c 17.67,0 32,-14.33 32,-32 v -96 c 0,-17.67 -14.33,-32 -32,-32 m 240,0 h -96 c -17.67,0 -32,14.33 -32,32 v 96 c 0,17.67 14.33,32 32,32 h 96 c 17.67,0 32,-14.33 32,-32 v -96 c 0,-17.67 -14.33,-32 -32,-32"
     id="path1" />
</svg>`,"galaxies/mitre-detection-strategy":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-79.9688 0.0000 639.9376 511.9501"
   version="1.1"
   id="svg1"
   sodipodi:docname="mitre-detection-strategy.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 450.5,83.675063 258.5,3.6750632 a 48.15,48.15 0 0 0 -36.9,0 L 29.6,83.675063 C 11.7,91.075063 0,108.57506 0,127.97506 c 0,198.5 114.5,335.7 221.5,380.3 11.8,4.9 25.1,4.9 36.9,0 85.7,-35.7 221.6,-159 221.6,-380.3 0,-19.4 -11.7,-36.899997 -29.5,-44.299997 M 240.1,446.27506 240,65.275063 415.9,138.57506 c -3.3,151.4 -82.1,261.1 -175.8,307.7"
     id="path1" />
</svg>`,"galaxies/mitre-engage-framework":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-95.9909 0.0000 639.9818 511.9854"
   version="1.1"
   id="svg1"
   sodipodi:docname="mitre-engage-framework.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 383.9,308.28542 23.9,-62.6 c 4,-10.5 -3.7,-21.7 -15,-21.7 h -58.5 c 11,-18.9 17.8,-40.6 17.8,-64 v -0.3 c 39.2,-7.8 64,-19.1 64,-31.7 0,-13.3 -27.3,-25.1 -70.1,-32.999997 -9.2,-32.8 -27,-65.8 -40.6,-82.8 C 295.9,0.28542306 279.5,-3.4145769 265.9,3.3854231 L 238.3,17.185423 c -9,4.5 -19.6,4.5 -28.6,0 L 182.1,3.3854231 c -13.6,-6.8 -30,-3.10000004 -39.5,8.7999999 -13.5,17 -31.4,50 -40.6,82.8 -42.7,7.899997 -70,19.699997 -70,32.999997 0,12.6 24.8,23.9 64,31.7 v 0.3 c 0,23.4 6.8,45.1 17.8,64 H 56.3 c -11.5,0 -19.2,11.7 -14.7,22.3 l 25.8,60.2 c -40.1,23.3 -67.4,66.2 -67.4,115.9 v 44.8 c 0,24.7 20.1,44.8 44.8,44.8 h 358.4 c 24.7,0 44.8,-20.1 44.8,-44.8 v -44.8 c 0,-48.4 -25.8,-90.4 -64.1,-114.1 m -207.9,171.7 -41.6,-192 49.6,32 24,40 z m 96,0 -32,-120 24,-40 49.6,-32 z m 41.7,-298.5 c -3.9,11.9 -7,24.6 -16.5,33.4 -10.1,9.3 -48,22.4 -64,-25 -2.8,-8.4 -15.4,-8.4 -18.3,0 -17,50.2 -56,32.4 -64,25 -9.5,-8.8 -12.7,-21.5 -16.5,-33.4 -0.8,-2.5 -6.3,-5.7 -6.3,-5.8 v -10.8 c 28.3,3.6 61,5.8 96,5.8 35,0 67.7,-2.1 96,-5.8 v 10.8 c -0.1,0.1 -5.6,3.2 -6.4,5.8"
     id="path1" />
</svg>`,"galaxies/mitre-enterprise-attack-attack-pattern":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="0.0000 0.0000 576.0000 448.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="mitre-enterprise-attack-attack-pattern.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 0,85.66 v 346.32 c 0,11.32 11.43,19.06 21.94,14.86 L 160,384 V 0 L 20.12,55.95 A 32.01,32.01 0 0 0 0,85.66 M 192,384 384,448 V 64 L 192,0 Z M 554.06,1.16 416,64 V 448 L 555.88,392.05 A 32,32 0 0 0 576,362.34 V 16.02 C 576,4.7 564.57,-3.04 554.06,1.16"
     id="path1" />
</svg>`,"galaxies/mitre-enterprise-attack-course-of-action":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-64.0007 0.0000 640.0012 512.0010"
   version="1.1"
   id="svg1"
   sodipodi:docname="mitre-enterprise-attack-course-of-action.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 326.6125,185.3915 c 59.747,59.809 58.927,155.698 0.36,214.59 -0.11,0.12 -0.24,0.25 -0.36,0.37 l -67.2,67.2 c -59.27,59.27 -155.699,59.262 -214.96,0 -59.27,-59.26 -59.27,-155.7 0,-214.96 l 37.106,-37.106 c 9.84,-9.84 26.786,-3.3 27.294,10.606 0.648,17.722 3.826,35.527 9.69,52.721 1.986,5.822 0.567,12.262 -3.783,16.612 l -13.087,13.087 c -28.026,28.026 -28.905,73.66 -1.155,101.96 28.024,28.579 74.086,28.749 102.325,0.51 l 67.2,-67.19 c 28.191,-28.191 28.073,-73.757 0,-101.83 -3.701,-3.694 -7.429,-6.564 -10.341,-8.569 a 16.04,16.04 0 0 1 -6.947,-12.606 c -0.396,-10.567 3.348,-21.456 11.698,-29.806 l 21.054,-21.055 c 5.521,-5.521 14.182,-6.199 20.584,-1.731 a 152.5,152.5 0 0 1 20.522,17.197 m 140.935,-140.942 c -59.261,-59.262 -155.69,-59.27 -214.96,0 l -67.2,67.2 c -0.12,0.12 -0.25,0.25 -0.36,0.37 -58.566,58.892 -59.387,154.781 0.36,214.59 a 152.5,152.5 0 0 0 20.521,17.196 c 6.402,4.468 15.064,3.789 20.584,-1.731 l 21.054,-21.055 c 8.35,-8.35 12.094,-19.239 11.698,-29.806 a 16.04,16.04 0 0 0 -6.947,-12.606 c -2.912,-2.005 -6.64,-4.875 -10.341,-8.569 -28.073,-28.073 -28.191,-73.639 0,-101.83 l 67.2,-67.19 c 28.239,-28.239 74.3,-28.069 102.325,0.51 27.75,28.3 26.872,73.934 -1.155,101.96 l -13.087,13.087 c -4.35,4.35 -5.769,10.79 -3.783,16.612 5.864,17.194 9.042,34.999 9.69,52.721 0.509,13.906 17.454,20.446 27.294,10.606 l 37.106,-37.106 c 59.271,-59.259 59.271,-155.699 0.001,-214.959"
     id="path1" />
</svg>`,"galaxies/mitre-enterprise-attack-intrusion-set":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-95.9909 0.0000 639.9818 511.9854"
   version="1.1"
   id="svg1"
   sodipodi:docname="mitre-enterprise-attack-intrusion-set.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 383.9,308.28542 23.9,-62.6 c 4,-10.5 -3.7,-21.7 -15,-21.7 h -58.5 c 11,-18.9 17.8,-40.6 17.8,-64 v -0.3 c 39.2,-7.8 64,-19.1 64,-31.7 0,-13.3 -27.3,-25.1 -70.1,-32.999997 -9.2,-32.8 -27,-65.8 -40.6,-82.8 C 295.9,0.28542306 279.5,-3.4145769 265.9,3.3854231 L 238.3,17.185423 c -9,4.5 -19.6,4.5 -28.6,0 L 182.1,3.3854231 c -13.6,-6.8 -30,-3.10000004 -39.5,8.7999999 -13.5,17 -31.4,50 -40.6,82.8 -42.7,7.899997 -70,19.699997 -70,32.999997 0,12.6 24.8,23.9 64,31.7 v 0.3 c 0,23.4 6.8,45.1 17.8,64 H 56.3 c -11.5,0 -19.2,11.7 -14.7,22.3 l 25.8,60.2 c -40.1,23.3 -67.4,66.2 -67.4,115.9 v 44.8 c 0,24.7 20.1,44.8 44.8,44.8 h 358.4 c 24.7,0 44.8,-20.1 44.8,-44.8 v -44.8 c 0,-48.4 -25.8,-90.4 -64.1,-114.1 m -207.9,171.7 -41.6,-192 49.6,32 24,40 z m 96,0 -32,-120 24,-40 49.6,-32 z m 41.7,-298.5 c -3.9,11.9 -7,24.6 -16.5,33.4 -10.1,9.3 -48,22.4 -64,-25 -2.8,-8.4 -15.4,-8.4 -18.3,0 -17,50.2 -56,32.4 -64,25 -9.5,-8.8 -12.7,-21.5 -16.5,-33.4 -0.8,-2.5 -6.3,-5.7 -6.3,-5.8 v -10.8 c 28.3,3.6 61,5.8 96,5.8 35,0 67.7,-2.1 96,-5.8 v 10.8 c -0.1,0.1 -5.6,3.2 -6.4,5.8"
     id="path1" />
</svg>`,"galaxies/mitre-enterprise-attack-malware":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-13.5444 0.0000 603.2721 482.6177"
   version="1.1"
   id="svg1"
   sodipodi:docname="mitre-enterprise-attack-malware.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 572.756,406.76941 c 5.6,-9.5 4.7,-15.2 -5.4,-11.6 -3,-4.9 -7,-9.5 -11.1,-13.8 2.9,-9.7 -0.7,-14.2 -10.8,-9.2 -4.6,-3.2 -10.3,-6.5 -15.9,-9.2 0,-15.1 -11.6,-11.6 -17.6,-5.7 -10.4,-1.5 -18.7,-0.3 -26.8,5.7 0.3,-6.5 0.3,-13 0.3,-19.7 12.6,0 40.2,-11 45.9,-36.2 1.4,-6.8 1.6,-13.8 -0.3,-21.9 -3,-13.5 -14.3,-21.3 -25.1,-25.7 -0.8,-5.9 -7.6,-14.3 -14.9,-15.9 -7.3,-1.6 -12.4,4.9 -14.1,10.3 -8.5,0 -19.2,2.8 -21.1,8.4 -5.4,-0.5 -11.1,-1.4 -16.8,-1.9 2.7,-1.9 5.4,-3.5 8.4,-4.6 5.4,-9.2 14.6,-11.4 25.7,-11.6 v -2.8 c 19.5,-0.5 43,-5.9 53.8,-18.1 12.7,-13.8 14.6,-37.3 12.4,-55.1 -2.4,-17.3 -9.7,-37.6 -24.6,-48.1 -8.4,-5.9 -21.6,-0.8 -22.7,9.5 -2.2,19.6 1.2,30 -38.6,25.1 -10.3,-23.8 -24.6,-44.6 -42.7,-60.000005 -69.6,-59.7 -167.7,-53.8 -244.2,-37.6 19.7,4.6 41.1,8.6 59.7,16.5 -26.2,2.4 -52.7,11.3 -76.2,23.2 -32.8,17.000005 -44,29.900005 -56.7,42.400005 14.9,-2.2 28.9,-5.1 43.8,-3.8 -9.7,5.4 -18.4,12.2 -26.5,20 -25.8,0.9 -23.8,-5.3 -26.2,-25.9 -1.1,-10.5 -14.3,-15.4 -22.7,-9.7 -28.1,19.9 -33.5,79.9 -12.2,103.5 10.8,12.2 35.1,17.3 54.9,17.8 -0.3,1.1 -0.3,1.9 -0.3,2.7 10.8,0.5 19.5,2.7 24.6,11.6 3,1.1 5.7,2.7 8.1,4.6 -5.4,0.5 -11.1,1.4 -16.5,1.9 -3.3,-6.6 -13.7,-8.1 -21.1,-8.1 -1.6,-5.7 -6.5,-12.2 -14.1,-10.3 -6.8,1.9 -14.1,10 -14.9,15.9 -22.5,9.5 -30.1,26.8 -25.1,47.6 5.3,24.8 33,36.2 45.9,36.2 v 19.7 c -6.6,-5 -14.3,-7.5 -26.8,-5.7 -5.5,-5.5 -17.3,-10.1 -17.3,5.7 -5.9,2.7 -11.4,5.9 -15.9,9.2 -9.8,-4.9 -13.6,-1.7 -11.1,9.2 -4.1,4.3 -7.8,8.6 -11.1,13.8 -10.2,-3.7 -11,2.2 -5.4,11.6 -1.1,3.5 -1.6,7 -1.9,10.8 -0.5,31.6 44.6,64 73.5,65.1 17.3,0.5 34.6,-8.4 43,-23.5 113.2,4.9 226.7,4.1 340.2,0 8.1,15.1 25.4,24.3 42.7,23.5 29.2,-1.1 74.3,-33.5 73.5,-65.1 0.2,-3.7 -0.7,-7.2 -1.7,-10.7 m -73.8,-254 c 1.1,-3 2.4,-8.4 2.4,-14.6 0,-5.9 6.8,-8.1 14.1,-0.8 11.1,11.6 14.9,40.5 13.8,51.1 -4.1,-13.6 -13,-29 -30.3,-35.7 m -4.6,6.7 c 19.5,6.2 28.6,27.6 29.7,48.9 -1.1,2.7 -3,5.4 -4.9,7.6 -5.7,5.9 -15.4,10 -26.2,12.2 4.3,-21.3 0.3,-47.3 -12.7,-63 4.9,-0.8 10.9,-2.4 14.1,-5.7 m -24.1,6.8 c 13.8,11.9 20,39.2 14.1,63.5 -4.1,0.5 -8.1,0.8 -11.6,0.8 -1.9,-21.9 -6.8,-44 -14.3,-64.6 3.7,0.3 8.1,0.3 11.8,0.3 m -422.6,22.1 c -1.1,-10.5 2.4,-39.5 13.8,-51.1 7,-7.3 14.1,-5.1 14.1,0.8 0,6.2 1.4,11.6 2.4,14.6 -17.3,6.8 -26.2,22.2 -30.3,35.7 m 9.7,27.6 c -1.9,-2.2 -3.5,-4.9 -4.9,-7.6 1.4,-21.3 10.3,-42.7 29.7,-48.9 3.2,3.2 9.2,4.9 14.1,5.7 -13,15.7 -17,41.6 -12.7,63 -10.8,-2.2 -20.5,-6 -26.2,-12.2 m 47.9,14.6 c -4.1,0 -8.1,-0.3 -12.7,-0.8 -4.6,-18.6 -1.9,-38.9 5.4,-53 v 0.3 l 12.2,-5.1 c 4.9,-1.9 9.7,-3.8 14.9,-4.9 -10.7,19.7 -17.4,41.3 -19.8,63.5 m 184,-162.700005 c 41.9,0 76.2,34.000005 76.2,75.900005 0,42.2 -34.3,76.2 -76.2,76.2 -41.9,0 -76.2,-34 -76.2,-76.2 0,-41.8 34.3,-75.900005 76.2,-75.900005 m 115.6,174.300005 c -0.3,17.8 -7,48.9 -23,57 -13.2,6.6 -6.5,-7.5 -16.5,-58.1 13.3,0.3 26.6,0.3 39.5,1.1 m -54,-1.6 c 0.8,4.9 3.8,40.3 -1.6,41.9 -11.6,3.5 -40,4.3 -51.1,-1.1 -4.1,-3 -4.6,-35.9 -4.3,-41.1 v 0.3 c 18.9,-0.3 38.1,-0.3 57,0 m -72.4,53.8 c -13,3.5 -41.6,4.1 -54.6,-1.6 -6.5,-2.7 -3.8,-42.4 -1.9,-51.6 19.2,-0.5 38.4,-0.5 57.8,-0.8 v 0.3 c 1.1,8.3 3.3,51.2 -1.3,53.7 m -106.5,-51.1 c 12.2,-0.8 24.6,-1.4 36.8,-1.6 -2.4,15.4 -3,43.5 -4.9,52.2 -1.1,6.8 -4.3,6.8 -9.7,4.3 -21.9,-9.8 -27.6,-35.2 -22.2,-54.9 m -35.4,31.3 c 7.8,-1.1 15.7,-1.9 23.5,-2.7 1.6,6.2 3.8,11.9 7,17.6 10,17 44,35.7 45.1,7 6.2,14.9 40.8,12.2 54.9,10.8 15.7,-1.4 23.8,-1.4 26.8,-14.3 12.4,4.3 30.8,4.1 44,3 11.3,-0.8 20.8,-0.5 24.6,-8.9 1.1,5.1 1.9,11.6 4.6,16.8 10.8,21.3 37.3,1.4 46.8,-31.6 8.6,0.8 17.6,1.9 26.5,2.7 -0.4,1.3 -3.8,7.3 7.3,11.6 -47.6,47 -95.7,87.8 -163.2,107 -63.2,-20.8 -112.1,-59.5 -155.9,-106.5 9.6,-3.4 10.4,-8.8 8,-12.5 m -21.6,172.5 c -3.8,17.8 -21.9,29.7 -39.7,28.9 -19.2,-0.8 -46.5,-17 -59.2,-36.5 -2.7,-31.1 43.8,-61.3 66.2,-54.6 14.9,4.3 27.8,30.8 33.5,54 0,3 -0.3,5.7 -0.8,8.2 m -8.7,-66 c -0.5,-13.5 -0.5,-27 -0.3,-40.5 h 0.3 c 2.7,-1.6 5.7,-3.8 7.8,-6.5 6.5,-1.6 13,-5.1 15.1,-9.2 3.3,-7.1 -7,-7.5 -5.4,-12.4 2.7,-1.1 5.7,-2.2 7.8,-3.5 29.2,29.2 58.6,56.5 97.3,77 -36.8,11.3 -72.4,27.6 -105.9,47 -1.2,-18.6 -7.7,-35.9 -16.7,-51.9 m 337.6,64.6 c -103,3.5 -206.2,4.1 -309.4,0 0,0.3 0,0.3 -0.3,0.3 v -0.3 h 0.3 c 35.1,-21.6 72.2,-39.2 112.4,-50.8 11.6,5.1 23,9.5 34.9,13.2 2.2,0.8 2.2,0.8 4.3,0 14.3,-4.1 28.4,-9.2 42.2,-15.4 41.5,11.7 78.8,31.7 115.6,53 m 10.5,-12.4 c -35.9,-19.5 -73,-35.9 -111.9,-47.6 38.1,-20 71.9,-47.3 103.5,-76.7 2.2,1.4 4.6,2.4 7.6,3.2 0,0.8 0.3,1.9 0.5,2.4 -4.6,2.7 -7.8,6.2 -5.9,10.3 2.2,3.8 8.6,7.6 15.1,8.9 2.4,2.7 5.1,5.1 8.1,6.8 0,13.8 -0.3,27.6 -0.8,41.3 l 0.3,-0.3 c -9.3,15.9 -15.5,37 -16.5,51.7 m 105.9,6.2 c -12.7,19.5 -40,35.7 -59.2,36.5 -19.3,0.9 -40.5,-13.2 -40.5,-37 5.7,-23.2 18.9,-49.7 33.5,-54 22.7,-6.9 69.2,23.4 66.2,54.5 M 373.056,60.569405 c -3.8,-72.1 -100.8,-79.7 -126,-23.5 44.6,-24.3 90.3,-15.7 126,23.5 M 74.956,392.46941 c -15.7,1.6 -49.5,25.4 -49.5,43.2 0,11.6 15.7,19.5 32.2,14.9 12.2,-3.2 31.1,-17.6 35.9,-27.3 6,-11.6 -3.7,-32.7 -18.6,-30.8 m 215.9,-176.2 c 28.6,0 51.9,-21.6 51.9,-48.4 0,-36.1 -40.5,-58.1 -72.2,-44.3 9.5,3 16.5,11.6 16.5,21.6 0,23.3 -33.3,32 -46.5,11.3 -7.3,34.1 19.4,59.8 50.3,59.8 m -222.7,243.2 c 0.5,6.5 12.2,12.7 21.6,9.5 6.8,-2.7 14.6,-10.5 17.3,-16.2 3,-7 -1.1,-20 -9.7,-18.4 -8.9,1.6 -29.7,16.7 -29.2,25.1 m 433.2,-67 c -14.9,-1.9 -24.6,19.2 -18.9,30.8 4.9,9.7 24.1,24.1 36.2,27.3 16.5,4.6 32.2,-3.2 32.2,-14.9 0,-17.8 -33.8,-41.6 -49.5,-43.2 m -22.4,41.9 c -8.4,-1.6 -12.4,11.3 -9.5,18.4 2.4,5.7 10.3,13.5 17.3,16.2 9.2,3.2 21.1,-3 21.3,-9.5 0.9,-8.4 -20.2,-23.5 -29.1,-25.1"
     id="path1" />
</svg>`,"galaxies/mitre-enterprise-attack-tool":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-64.0011 0.0000 640.0019 512.0015"
   version="1.1"
   id="svg1"
   sodipodi:docname="mitre-enterprise-attack-tool.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 504.97075,199.36275 -22.627,-22.627 c -9.373,-9.373 -24.569,-9.373 -33.941,0 l -5.657,5.657 -113.138,-113.137 5.657,-5.657 c 9.373,-9.373 9.373,-24.569 0,-33.941 l -22.627,-22.628 c -9.373,-9.373 -24.569,-9.373 -33.941,0 l -124.451,124.451 c -9.373,9.373 -9.373,24.569 0,33.941 l 22.627,22.627 c 9.373,9.373 24.569,9.373 33.941,0 l 5.657,-5.657 39.598,39.598 -81.04,81.04 -5.657,-5.657 c -12.497,-12.497 -32.758,-12.497 -45.255,0 l -114.744,114.746 c -12.497,12.497 -12.497,32.758 0,45.255 l 45.255,45.255 c 12.497,12.497 32.758,12.497 45.255,0 l 114.745,-114.745 c 12.497,-12.497 12.497,-32.758 0,-45.255 l -5.657,-5.657 81.04,-81.04 39.598,39.598 -5.657,5.657 c -9.373,9.373 -9.373,24.569 0,33.941 l 22.627,22.627 c 9.373,9.373 24.569,9.373 33.941,0 l 124.451,-124.451 c 9.372,-9.372 9.372,-24.568 0,-33.941"
     id="path1" />
</svg>`,"galaxies/mitre-fraud-framework":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="0.0000 0.0000 576.0000 448.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="mitre-fraud-framework.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 0,85.66 v 346.32 c 0,11.32 11.43,19.06 21.94,14.86 L 160,384 V 0 L 20.12,55.95 A 32.01,32.01 0 0 0 0,85.66 M 192,384 384,448 V 64 L 192,0 Z M 554.06,1.16 416,64 V 448 L 555.88,392.05 A 32,32 0 0 0 576,362.34 V 16.02 C 576,4.7 564.57,-3.04 554.06,1.16"
     id="path1" />
</svg>`,"galaxies/mitre-ics-assets":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-64.0009 0.0000 640.0007 512.0005"
   version="1.1"
   id="svg1"
   sodipodi:docname="mitre-ics-assets.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 458.62197,255.92044 45.985,-45.005 c 13.708,-12.977 7.316,-36.039 -10.664,-40.339 l -62.65,-15.99 17.661,-62.014996 c 4.991,-17.838 -11.829,-34.663 -29.661,-29.671 l -61.994,17.667 -15.984,-62.671 c -4.23,-17.69899989 -27.55,-24.1719999 -40.325,-10.6679999 l -44.99,46.3419999 -44.989,-46.3409999 c -12.63,-13.351 -36.047,-7.23399999 -40.325,10.6679999 l -15.984,62.671 -61.995002,-17.667 c -17.837,-4.994 -34.651,11.837 -29.661,29.671 l 17.661,62.014996 -62.65,15.99 c -17.98799964,4.301 -24.3669996,27.367 -10.6649996,40.338 l 45.9849996,45.005 -45.9849996,45.004 c -13.708,12.977 -7.31600004,36.039 10.6639996,40.339 l 62.65,15.99 -17.661,62.015 c -4.991,17.838 11.829,34.663 29.661,29.671 l 61.994002,-17.667 15.984,62.671 c 4.439,18.575 27.696,24.018 40.325,10.668 l 44.991,-46.001 44.989,46.001 c 12.5,13.488 35.987,7.486 40.325,-10.668 l 15.984,-62.671 61.994,17.667 c 17.836,4.994 34.651,-11.837 29.661,-29.671 l -17.661,-62.015 62.65,-15.99 c 17.987,-4.302 24.366,-27.367 10.664,-40.339 z"
     id="path1" />
</svg>`,"galaxies/mitre-ics-groups":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-95.9997 0.0000 640.0084 512.0067"
   version="1.1"
   id="svg1"
   sodipodi:docname="mitre-ics-groups.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 439.15232,453.06 -141.98,-69.06 141.99,-69.06 c 7.9,-3.95 11.11,-13.56 7.15,-21.46 l -14.31,-28.63 c -3.95,-7.9 -13.56,-11.11 -21.47,-7.16 l -186.53,90.72 -186.530002,-90.72 c -7.9,-3.95 -17.51,-0.75 -21.47,7.16 L 1.6923176,293.48 c -3.95,7.9 -0.75000002,17.51 7.15,21.46 L 150.83232,384 8.8523176,453.06 c -7.90000002,3.95 -11.11,13.56 -7.15,21.47 l 14.3100004,28.63 c 3.95,7.9 13.56,11.11 21.47,7.15 l 186.520002,-90.72 186.53,90.72 c 7.9,3.95 17.51,0.75 21.47,-7.15 l 14.31,-28.63 c 3.95,-7.91 0.74,-17.52 -7.16,-21.47 m -289.15,-215.78 -5.48,25.87 c -2.67,12.62 5.42,24.85 16.45,24.85 h 126.08 c 11.03,0 19.12,-12.23 16.45,-24.85 l -5.5,-25.87 c 41.78,-22.41 70,-62.75 70,-109.28 0,-70.69 -64.47,-128 -144,-128 -79.53,0 -144.000002,57.31 -144.000002,128 0,46.53 28.220002,86.87 70.000002,109.28 m 130,-125.28 c 17.65,0 32,14.35 32,32 0,17.65 -14.35,32 -32,32 -17.65,0 -32,-14.35 -32,-32 0,-17.65 14.35,-32 32,-32 m -112,0 c 17.65,0 32,14.35 32,32 0,17.65 -14.35,32 -32,32 -17.65,0 -32,-14.35 -32,-32 0,-17.65 14.35,-32 32,-32"
     id="path1" />
</svg>`,"galaxies/mitre-ics-levels":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-64.0026 0.0000 640.0102 512.0082"
   version="1.1"
   id="svg1"
   sodipodi:docname="mitre-ics-levels.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 12.4125,148.02816 232.94,105.67 c 6.8,3.09 14.49,3.09 21.29,0 l 232.94,-105.67 c 16.55,-7.51 16.55,-32.52 0,-40.03 L 266.6525,2.3181621 a 25.6,25.6 0 0 0 -21.29,0 L 12.4125,107.98816 c -16.55,7.51 -16.55,32.53 0,40.04 m 487.18,88.28 -58.09,-26.33 -161.64,73.27 c -7.56,3.43 -15.59,5.17 -23.86,5.17 -8.27,0 -16.29,-1.74 -23.86,-5.17 l -161.63,-73.27 -58.1,26.33 c -16.55,7.5 -16.55,32.5 0,40 l 232.94,105.59 c 6.8,3.08 14.49,3.08 21.29,0 l 232.95,-105.59 c 16.55,-7.5 16.55,-32.5 0,-40 m 0,127.8 -57.87,-26.23 -161.86,73.37 c -7.56,3.43 -15.59,5.17 -23.86,5.17 -8.27,0 -16.29,-1.74 -23.86,-5.17 l -161.85,-73.37 -57.88,26.23 c -16.55,7.5 -16.55,32.5 0,40 l 232.94,105.59 c 6.8,3.08 14.49,3.08 21.29,0 l 232.95,-105.59 c 16.55,-7.5 16.55,-32.5 0,-40"
     id="path1" />
</svg>`,"galaxies/mitre-ics-software":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-128.0000 0.0000 640.0000 512.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="mitre-ics-software.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 384,121.941 V 128 H 256 V 0 h 6.059 c 6.365,0 12.47,2.529 16.971,7.029 l 97.941,97.941 A 24,24 0 0 1 384,121.941 M 248,160 c -13.2,0 -24,-10.8 -24,-24 V 0 H 24 C 10.745,0 0,10.745 0,24 v 464 c 0,13.255 10.745,24 24,24 h 336 c 13.255,0 24,-10.745 24,-24 V 160 Z M 123.206,400.505 a 5.4,5.4 0 0 1 -7.633,0.246 L 50.707,339.939 a 5.4,5.4 0 0 1 0,-7.879 l 64.866,-60.812 a 5.4,5.4 0 0 1 7.633,0.246 l 19.579,20.885 a 5.4,5.4 0 0 1 -0.372,7.747 L 101.65,336 l 40.763,35.874 a 5.4,5.4 0 0 1 0.372,7.747 z m 51.295,50.479 -27.453,-7.97 a 5.4,5.4 0 0 1 -3.681,-6.692 l 61.44,-211.626 a 5.4,5.4 0 0 1 6.692,-3.681 l 27.452,7.97 a 5.4,5.4 0 0 1 3.68,6.692 l -61.44,211.626 a 5.397,5.397 0 0 1 -6.69,3.681 m 160.792,-111.045 -64.866,60.812 a 5.4,5.4 0 0 1 -7.633,-0.246 l -19.58,-20.885 a 5.4,5.4 0 0 1 0.372,-7.747 L 284.35,336 243.587,300.126 a 5.4,5.4 0 0 1 -0.372,-7.747 l 19.58,-20.885 a 5.4,5.4 0 0 1 7.633,-0.246 l 64.866,60.812 a 5.4,5.4 0 0 1 -10e-4,7.879"
     id="path1" />
</svg>`,"galaxies/mitre-ics-tactics":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-140.0000 0.0000 600.0000 480.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="mitre-ics-tactics.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 105.1,192 H 80 a 16,16 0 0 0 -16,16 v 32 a 16,16 0 0 0 16,16 h 16 v 5.49 c 0,44 -4.14,86.6 -24,122.51 H 248 C 228.11,348.09 224,305.49 224,261.49 V 256 h 16 a 16,16 0 0 0 16,-16 V 208 A 16,16 0 0 0 240,192 H 214.9 C 244.29,173.62 264,141.22 264,104 a 104,104 0 0 0 -208,0 c 0,37.22 19.71,69.62 49.1,88 M 304,416 H 16 A 16,16 0 0 0 0,432 v 32 a 16,16 0 0 0 16,16 h 288 a 16,16 0 0 0 16,-16 v -32 a 16,16 0 0 0 -16,-16"
     id="path1" />
</svg>`,"galaxies/mitre-ics-techniques":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-96.0000 0.0000 640.0000 512.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="mitre-ics-techniques.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 325.4,289.2 224,390.6 122.6,289.2 C 54,295.3 0,352.2 0,422.4 V 464 c 0,26.5 21.5,48 48,48 h 352 c 26.5,0 48,-21.5 48,-48 V 422.4 C 448,352.2 394,295.3 325.4,289.2 M 32,192 c 27.3,0 51.8,-11.5 69.2,-29.7 15.1,53.9 64,93.7 122.8,93.7 70.7,0 128,-57.3 128,-128 C 352,57.3 294.7,0 224,0 173.6,0 130.4,29.4 109.5,71.8 92.1,47.8 64,32 32,32 32,65.4 49.1,94.8 75.1,112 49.1,129.2 32,158.6 32,192 M 176,96 h 96 c 17.7,0 32,14.3 32,32 H 144 c 0,-17.7 14.3,-32 32,-32"
     id="path1" />
</svg>`,"galaxies/mitre-intrusion-set":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-95.9909 0.0000 639.9818 511.9854"
   version="1.1"
   id="svg1"
   sodipodi:docname="mitre-intrusion-set.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 383.9,308.28542 23.9,-62.6 c 4,-10.5 -3.7,-21.7 -15,-21.7 h -58.5 c 11,-18.9 17.8,-40.6 17.8,-64 v -0.3 c 39.2,-7.8 64,-19.1 64,-31.7 0,-13.3 -27.3,-25.1 -70.1,-32.999997 -9.2,-32.8 -27,-65.8 -40.6,-82.8 C 295.9,0.28542306 279.5,-3.4145769 265.9,3.3854231 L 238.3,17.185423 c -9,4.5 -19.6,4.5 -28.6,0 L 182.1,3.3854231 c -13.6,-6.8 -30,-3.10000004 -39.5,8.7999999 -13.5,17 -31.4,50 -40.6,82.8 -42.7,7.899997 -70,19.699997 -70,32.999997 0,12.6 24.8,23.9 64,31.7 v 0.3 c 0,23.4 6.8,45.1 17.8,64 H 56.3 c -11.5,0 -19.2,11.7 -14.7,22.3 l 25.8,60.2 c -40.1,23.3 -67.4,66.2 -67.4,115.9 v 44.8 c 0,24.7 20.1,44.8 44.8,44.8 h 358.4 c 24.7,0 44.8,-20.1 44.8,-44.8 v -44.8 c 0,-48.4 -25.8,-90.4 -64.1,-114.1 m -207.9,171.7 -41.6,-192 49.6,32 24,40 z m 96,0 -32,-120 24,-40 49.6,-32 z m 41.7,-298.5 c -3.9,11.9 -7,24.6 -16.5,33.4 -10.1,9.3 -48,22.4 -64,-25 -2.8,-8.4 -15.4,-8.4 -18.3,0 -17,50.2 -56,32.4 -64,25 -9.5,-8.8 -12.7,-21.5 -16.5,-33.4 -0.8,-2.5 -6.3,-5.7 -6.3,-5.8 v -10.8 c 28.3,3.6 61,5.8 96,5.8 35,0 67.7,-2.1 96,-5.8 v 10.8 c -0.1,0.1 -5.6,3.2 -6.4,5.8"
     id="path1" />
</svg>`,"galaxies/mitre-malware":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-13.5444 0.0000 603.2721 482.6177"
   version="1.1"
   id="svg1"
   sodipodi:docname="mitre-malware.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 572.756,406.76941 c 5.6,-9.5 4.7,-15.2 -5.4,-11.6 -3,-4.9 -7,-9.5 -11.1,-13.8 2.9,-9.7 -0.7,-14.2 -10.8,-9.2 -4.6,-3.2 -10.3,-6.5 -15.9,-9.2 0,-15.1 -11.6,-11.6 -17.6,-5.7 -10.4,-1.5 -18.7,-0.3 -26.8,5.7 0.3,-6.5 0.3,-13 0.3,-19.7 12.6,0 40.2,-11 45.9,-36.2 1.4,-6.8 1.6,-13.8 -0.3,-21.9 -3,-13.5 -14.3,-21.3 -25.1,-25.7 -0.8,-5.9 -7.6,-14.3 -14.9,-15.9 -7.3,-1.6 -12.4,4.9 -14.1,10.3 -8.5,0 -19.2,2.8 -21.1,8.4 -5.4,-0.5 -11.1,-1.4 -16.8,-1.9 2.7,-1.9 5.4,-3.5 8.4,-4.6 5.4,-9.2 14.6,-11.4 25.7,-11.6 v -2.8 c 19.5,-0.5 43,-5.9 53.8,-18.1 12.7,-13.8 14.6,-37.3 12.4,-55.1 -2.4,-17.3 -9.7,-37.6 -24.6,-48.1 -8.4,-5.9 -21.6,-0.8 -22.7,9.5 -2.2,19.6 1.2,30 -38.6,25.1 -10.3,-23.8 -24.6,-44.6 -42.7,-60.000005 -69.6,-59.7 -167.7,-53.8 -244.2,-37.6 19.7,4.6 41.1,8.6 59.7,16.5 -26.2,2.4 -52.7,11.3 -76.2,23.2 -32.8,17.000005 -44,29.900005 -56.7,42.400005 14.9,-2.2 28.9,-5.1 43.8,-3.8 -9.7,5.4 -18.4,12.2 -26.5,20 -25.8,0.9 -23.8,-5.3 -26.2,-25.9 -1.1,-10.5 -14.3,-15.4 -22.7,-9.7 -28.1,19.9 -33.5,79.9 -12.2,103.5 10.8,12.2 35.1,17.3 54.9,17.8 -0.3,1.1 -0.3,1.9 -0.3,2.7 10.8,0.5 19.5,2.7 24.6,11.6 3,1.1 5.7,2.7 8.1,4.6 -5.4,0.5 -11.1,1.4 -16.5,1.9 -3.3,-6.6 -13.7,-8.1 -21.1,-8.1 -1.6,-5.7 -6.5,-12.2 -14.1,-10.3 -6.8,1.9 -14.1,10 -14.9,15.9 -22.5,9.5 -30.1,26.8 -25.1,47.6 5.3,24.8 33,36.2 45.9,36.2 v 19.7 c -6.6,-5 -14.3,-7.5 -26.8,-5.7 -5.5,-5.5 -17.3,-10.1 -17.3,5.7 -5.9,2.7 -11.4,5.9 -15.9,9.2 -9.8,-4.9 -13.6,-1.7 -11.1,9.2 -4.1,4.3 -7.8,8.6 -11.1,13.8 -10.2,-3.7 -11,2.2 -5.4,11.6 -1.1,3.5 -1.6,7 -1.9,10.8 -0.5,31.6 44.6,64 73.5,65.1 17.3,0.5 34.6,-8.4 43,-23.5 113.2,4.9 226.7,4.1 340.2,0 8.1,15.1 25.4,24.3 42.7,23.5 29.2,-1.1 74.3,-33.5 73.5,-65.1 0.2,-3.7 -0.7,-7.2 -1.7,-10.7 m -73.8,-254 c 1.1,-3 2.4,-8.4 2.4,-14.6 0,-5.9 6.8,-8.1 14.1,-0.8 11.1,11.6 14.9,40.5 13.8,51.1 -4.1,-13.6 -13,-29 -30.3,-35.7 m -4.6,6.7 c 19.5,6.2 28.6,27.6 29.7,48.9 -1.1,2.7 -3,5.4 -4.9,7.6 -5.7,5.9 -15.4,10 -26.2,12.2 4.3,-21.3 0.3,-47.3 -12.7,-63 4.9,-0.8 10.9,-2.4 14.1,-5.7 m -24.1,6.8 c 13.8,11.9 20,39.2 14.1,63.5 -4.1,0.5 -8.1,0.8 -11.6,0.8 -1.9,-21.9 -6.8,-44 -14.3,-64.6 3.7,0.3 8.1,0.3 11.8,0.3 m -422.6,22.1 c -1.1,-10.5 2.4,-39.5 13.8,-51.1 7,-7.3 14.1,-5.1 14.1,0.8 0,6.2 1.4,11.6 2.4,14.6 -17.3,6.8 -26.2,22.2 -30.3,35.7 m 9.7,27.6 c -1.9,-2.2 -3.5,-4.9 -4.9,-7.6 1.4,-21.3 10.3,-42.7 29.7,-48.9 3.2,3.2 9.2,4.9 14.1,5.7 -13,15.7 -17,41.6 -12.7,63 -10.8,-2.2 -20.5,-6 -26.2,-12.2 m 47.9,14.6 c -4.1,0 -8.1,-0.3 -12.7,-0.8 -4.6,-18.6 -1.9,-38.9 5.4,-53 v 0.3 l 12.2,-5.1 c 4.9,-1.9 9.7,-3.8 14.9,-4.9 -10.7,19.7 -17.4,41.3 -19.8,63.5 m 184,-162.700005 c 41.9,0 76.2,34.000005 76.2,75.900005 0,42.2 -34.3,76.2 -76.2,76.2 -41.9,0 -76.2,-34 -76.2,-76.2 0,-41.8 34.3,-75.900005 76.2,-75.900005 m 115.6,174.300005 c -0.3,17.8 -7,48.9 -23,57 -13.2,6.6 -6.5,-7.5 -16.5,-58.1 13.3,0.3 26.6,0.3 39.5,1.1 m -54,-1.6 c 0.8,4.9 3.8,40.3 -1.6,41.9 -11.6,3.5 -40,4.3 -51.1,-1.1 -4.1,-3 -4.6,-35.9 -4.3,-41.1 v 0.3 c 18.9,-0.3 38.1,-0.3 57,0 m -72.4,53.8 c -13,3.5 -41.6,4.1 -54.6,-1.6 -6.5,-2.7 -3.8,-42.4 -1.9,-51.6 19.2,-0.5 38.4,-0.5 57.8,-0.8 v 0.3 c 1.1,8.3 3.3,51.2 -1.3,53.7 m -106.5,-51.1 c 12.2,-0.8 24.6,-1.4 36.8,-1.6 -2.4,15.4 -3,43.5 -4.9,52.2 -1.1,6.8 -4.3,6.8 -9.7,4.3 -21.9,-9.8 -27.6,-35.2 -22.2,-54.9 m -35.4,31.3 c 7.8,-1.1 15.7,-1.9 23.5,-2.7 1.6,6.2 3.8,11.9 7,17.6 10,17 44,35.7 45.1,7 6.2,14.9 40.8,12.2 54.9,10.8 15.7,-1.4 23.8,-1.4 26.8,-14.3 12.4,4.3 30.8,4.1 44,3 11.3,-0.8 20.8,-0.5 24.6,-8.9 1.1,5.1 1.9,11.6 4.6,16.8 10.8,21.3 37.3,1.4 46.8,-31.6 8.6,0.8 17.6,1.9 26.5,2.7 -0.4,1.3 -3.8,7.3 7.3,11.6 -47.6,47 -95.7,87.8 -163.2,107 -63.2,-20.8 -112.1,-59.5 -155.9,-106.5 9.6,-3.4 10.4,-8.8 8,-12.5 m -21.6,172.5 c -3.8,17.8 -21.9,29.7 -39.7,28.9 -19.2,-0.8 -46.5,-17 -59.2,-36.5 -2.7,-31.1 43.8,-61.3 66.2,-54.6 14.9,4.3 27.8,30.8 33.5,54 0,3 -0.3,5.7 -0.8,8.2 m -8.7,-66 c -0.5,-13.5 -0.5,-27 -0.3,-40.5 h 0.3 c 2.7,-1.6 5.7,-3.8 7.8,-6.5 6.5,-1.6 13,-5.1 15.1,-9.2 3.3,-7.1 -7,-7.5 -5.4,-12.4 2.7,-1.1 5.7,-2.2 7.8,-3.5 29.2,29.2 58.6,56.5 97.3,77 -36.8,11.3 -72.4,27.6 -105.9,47 -1.2,-18.6 -7.7,-35.9 -16.7,-51.9 m 337.6,64.6 c -103,3.5 -206.2,4.1 -309.4,0 0,0.3 0,0.3 -0.3,0.3 v -0.3 h 0.3 c 35.1,-21.6 72.2,-39.2 112.4,-50.8 11.6,5.1 23,9.5 34.9,13.2 2.2,0.8 2.2,0.8 4.3,0 14.3,-4.1 28.4,-9.2 42.2,-15.4 41.5,11.7 78.8,31.7 115.6,53 m 10.5,-12.4 c -35.9,-19.5 -73,-35.9 -111.9,-47.6 38.1,-20 71.9,-47.3 103.5,-76.7 2.2,1.4 4.6,2.4 7.6,3.2 0,0.8 0.3,1.9 0.5,2.4 -4.6,2.7 -7.8,6.2 -5.9,10.3 2.2,3.8 8.6,7.6 15.1,8.9 2.4,2.7 5.1,5.1 8.1,6.8 0,13.8 -0.3,27.6 -0.8,41.3 l 0.3,-0.3 c -9.3,15.9 -15.5,37 -16.5,51.7 m 105.9,6.2 c -12.7,19.5 -40,35.7 -59.2,36.5 -19.3,0.9 -40.5,-13.2 -40.5,-37 5.7,-23.2 18.9,-49.7 33.5,-54 22.7,-6.9 69.2,23.4 66.2,54.5 M 373.056,60.569405 c -3.8,-72.1 -100.8,-79.7 -126,-23.5 44.6,-24.3 90.3,-15.7 126,23.5 M 74.956,392.46941 c -15.7,1.6 -49.5,25.4 -49.5,43.2 0,11.6 15.7,19.5 32.2,14.9 12.2,-3.2 31.1,-17.6 35.9,-27.3 6,-11.6 -3.7,-32.7 -18.6,-30.8 m 215.9,-176.2 c 28.6,0 51.9,-21.6 51.9,-48.4 0,-36.1 -40.5,-58.1 -72.2,-44.3 9.5,3 16.5,11.6 16.5,21.6 0,23.3 -33.3,32 -46.5,11.3 -7.3,34.1 19.4,59.8 50.3,59.8 m -222.7,243.2 c 0.5,6.5 12.2,12.7 21.6,9.5 6.8,-2.7 14.6,-10.5 17.3,-16.2 3,-7 -1.1,-20 -9.7,-18.4 -8.9,1.6 -29.7,16.7 -29.2,25.1 m 433.2,-67 c -14.9,-1.9 -24.6,19.2 -18.9,30.8 4.9,9.7 24.1,24.1 36.2,27.3 16.5,4.6 32.2,-3.2 32.2,-14.9 0,-17.8 -33.8,-41.6 -49.5,-43.2 m -22.4,41.9 c -8.4,-1.6 -12.4,11.3 -9.5,18.4 2.4,5.7 10.3,13.5 17.3,16.2 9.2,3.2 21.1,-3 21.3,-9.5 0.9,-8.4 -20.2,-23.5 -29.1,-25.1"
     id="path1" />
</svg>`,"galaxies/mitre-mobile-attack-attack-pattern":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="0.0000 0.0000 576.0000 448.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="mitre-mobile-attack-attack-pattern.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 0,85.66 v 346.32 c 0,11.32 11.43,19.06 21.94,14.86 L 160,384 V 0 L 20.12,55.95 A 32.01,32.01 0 0 0 0,85.66 M 192,384 384,448 V 64 L 192,0 Z M 554.06,1.16 416,64 V 448 L 555.88,392.05 A 32,32 0 0 0 576,362.34 V 16.02 C 576,4.7 564.57,-3.04 554.06,1.16"
     id="path1" />
</svg>`,"galaxies/mitre-mobile-attack-course-of-action":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-64.0007 0.0000 640.0012 512.0010"
   version="1.1"
   id="svg1"
   sodipodi:docname="mitre-mobile-attack-course-of-action.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 326.6125,185.3915 c 59.747,59.809 58.927,155.698 0.36,214.59 -0.11,0.12 -0.24,0.25 -0.36,0.37 l -67.2,67.2 c -59.27,59.27 -155.699,59.262 -214.96,0 -59.27,-59.26 -59.27,-155.7 0,-214.96 l 37.106,-37.106 c 9.84,-9.84 26.786,-3.3 27.294,10.606 0.648,17.722 3.826,35.527 9.69,52.721 1.986,5.822 0.567,12.262 -3.783,16.612 l -13.087,13.087 c -28.026,28.026 -28.905,73.66 -1.155,101.96 28.024,28.579 74.086,28.749 102.325,0.51 l 67.2,-67.19 c 28.191,-28.191 28.073,-73.757 0,-101.83 -3.701,-3.694 -7.429,-6.564 -10.341,-8.569 a 16.04,16.04 0 0 1 -6.947,-12.606 c -0.396,-10.567 3.348,-21.456 11.698,-29.806 l 21.054,-21.055 c 5.521,-5.521 14.182,-6.199 20.584,-1.731 a 152.5,152.5 0 0 1 20.522,17.197 m 140.935,-140.942 c -59.261,-59.262 -155.69,-59.27 -214.96,0 l -67.2,67.2 c -0.12,0.12 -0.25,0.25 -0.36,0.37 -58.566,58.892 -59.387,154.781 0.36,214.59 a 152.5,152.5 0 0 0 20.521,17.196 c 6.402,4.468 15.064,3.789 20.584,-1.731 l 21.054,-21.055 c 8.35,-8.35 12.094,-19.239 11.698,-29.806 a 16.04,16.04 0 0 0 -6.947,-12.606 c -2.912,-2.005 -6.64,-4.875 -10.341,-8.569 -28.073,-28.073 -28.191,-73.639 0,-101.83 l 67.2,-67.19 c 28.239,-28.239 74.3,-28.069 102.325,0.51 27.75,28.3 26.872,73.934 -1.155,101.96 l -13.087,13.087 c -4.35,4.35 -5.769,10.79 -3.783,16.612 5.864,17.194 9.042,34.999 9.69,52.721 0.509,13.906 17.454,20.446 27.294,10.606 l 37.106,-37.106 c 59.271,-59.259 59.271,-155.699 0.001,-214.959"
     id="path1" />
</svg>`,"galaxies/mitre-mobile-attack-intrusion-set":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-95.9909 0.0000 639.9818 511.9854"
   version="1.1"
   id="svg1"
   sodipodi:docname="mitre-mobile-attack-intrusion-set.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 383.9,308.28542 23.9,-62.6 c 4,-10.5 -3.7,-21.7 -15,-21.7 h -58.5 c 11,-18.9 17.8,-40.6 17.8,-64 v -0.3 c 39.2,-7.8 64,-19.1 64,-31.7 0,-13.3 -27.3,-25.1 -70.1,-32.999997 -9.2,-32.8 -27,-65.8 -40.6,-82.8 C 295.9,0.28542306 279.5,-3.4145769 265.9,3.3854231 L 238.3,17.185423 c -9,4.5 -19.6,4.5 -28.6,0 L 182.1,3.3854231 c -13.6,-6.8 -30,-3.10000004 -39.5,8.7999999 -13.5,17 -31.4,50 -40.6,82.8 -42.7,7.899997 -70,19.699997 -70,32.999997 0,12.6 24.8,23.9 64,31.7 v 0.3 c 0,23.4 6.8,45.1 17.8,64 H 56.3 c -11.5,0 -19.2,11.7 -14.7,22.3 l 25.8,60.2 c -40.1,23.3 -67.4,66.2 -67.4,115.9 v 44.8 c 0,24.7 20.1,44.8 44.8,44.8 h 358.4 c 24.7,0 44.8,-20.1 44.8,-44.8 v -44.8 c 0,-48.4 -25.8,-90.4 -64.1,-114.1 m -207.9,171.7 -41.6,-192 49.6,32 24,40 z m 96,0 -32,-120 24,-40 49.6,-32 z m 41.7,-298.5 c -3.9,11.9 -7,24.6 -16.5,33.4 -10.1,9.3 -48,22.4 -64,-25 -2.8,-8.4 -15.4,-8.4 -18.3,0 -17,50.2 -56,32.4 -64,25 -9.5,-8.8 -12.7,-21.5 -16.5,-33.4 -0.8,-2.5 -6.3,-5.7 -6.3,-5.8 v -10.8 c 28.3,3.6 61,5.8 96,5.8 35,0 67.7,-2.1 96,-5.8 v 10.8 c -0.1,0.1 -5.6,3.2 -6.4,5.8"
     id="path1" />
</svg>`,"galaxies/mitre-mobile-attack-malware":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-13.5444 0.0000 603.2721 482.6177"
   version="1.1"
   id="svg1"
   sodipodi:docname="mitre-mobile-attack-malware.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 572.756,406.76941 c 5.6,-9.5 4.7,-15.2 -5.4,-11.6 -3,-4.9 -7,-9.5 -11.1,-13.8 2.9,-9.7 -0.7,-14.2 -10.8,-9.2 -4.6,-3.2 -10.3,-6.5 -15.9,-9.2 0,-15.1 -11.6,-11.6 -17.6,-5.7 -10.4,-1.5 -18.7,-0.3 -26.8,5.7 0.3,-6.5 0.3,-13 0.3,-19.7 12.6,0 40.2,-11 45.9,-36.2 1.4,-6.8 1.6,-13.8 -0.3,-21.9 -3,-13.5 -14.3,-21.3 -25.1,-25.7 -0.8,-5.9 -7.6,-14.3 -14.9,-15.9 -7.3,-1.6 -12.4,4.9 -14.1,10.3 -8.5,0 -19.2,2.8 -21.1,8.4 -5.4,-0.5 -11.1,-1.4 -16.8,-1.9 2.7,-1.9 5.4,-3.5 8.4,-4.6 5.4,-9.2 14.6,-11.4 25.7,-11.6 v -2.8 c 19.5,-0.5 43,-5.9 53.8,-18.1 12.7,-13.8 14.6,-37.3 12.4,-55.1 -2.4,-17.3 -9.7,-37.6 -24.6,-48.1 -8.4,-5.9 -21.6,-0.8 -22.7,9.5 -2.2,19.6 1.2,30 -38.6,25.1 -10.3,-23.8 -24.6,-44.6 -42.7,-60.000005 -69.6,-59.7 -167.7,-53.8 -244.2,-37.6 19.7,4.6 41.1,8.6 59.7,16.5 -26.2,2.4 -52.7,11.3 -76.2,23.2 -32.8,17.000005 -44,29.900005 -56.7,42.400005 14.9,-2.2 28.9,-5.1 43.8,-3.8 -9.7,5.4 -18.4,12.2 -26.5,20 -25.8,0.9 -23.8,-5.3 -26.2,-25.9 -1.1,-10.5 -14.3,-15.4 -22.7,-9.7 -28.1,19.9 -33.5,79.9 -12.2,103.5 10.8,12.2 35.1,17.3 54.9,17.8 -0.3,1.1 -0.3,1.9 -0.3,2.7 10.8,0.5 19.5,2.7 24.6,11.6 3,1.1 5.7,2.7 8.1,4.6 -5.4,0.5 -11.1,1.4 -16.5,1.9 -3.3,-6.6 -13.7,-8.1 -21.1,-8.1 -1.6,-5.7 -6.5,-12.2 -14.1,-10.3 -6.8,1.9 -14.1,10 -14.9,15.9 -22.5,9.5 -30.1,26.8 -25.1,47.6 5.3,24.8 33,36.2 45.9,36.2 v 19.7 c -6.6,-5 -14.3,-7.5 -26.8,-5.7 -5.5,-5.5 -17.3,-10.1 -17.3,5.7 -5.9,2.7 -11.4,5.9 -15.9,9.2 -9.8,-4.9 -13.6,-1.7 -11.1,9.2 -4.1,4.3 -7.8,8.6 -11.1,13.8 -10.2,-3.7 -11,2.2 -5.4,11.6 -1.1,3.5 -1.6,7 -1.9,10.8 -0.5,31.6 44.6,64 73.5,65.1 17.3,0.5 34.6,-8.4 43,-23.5 113.2,4.9 226.7,4.1 340.2,0 8.1,15.1 25.4,24.3 42.7,23.5 29.2,-1.1 74.3,-33.5 73.5,-65.1 0.2,-3.7 -0.7,-7.2 -1.7,-10.7 m -73.8,-254 c 1.1,-3 2.4,-8.4 2.4,-14.6 0,-5.9 6.8,-8.1 14.1,-0.8 11.1,11.6 14.9,40.5 13.8,51.1 -4.1,-13.6 -13,-29 -30.3,-35.7 m -4.6,6.7 c 19.5,6.2 28.6,27.6 29.7,48.9 -1.1,2.7 -3,5.4 -4.9,7.6 -5.7,5.9 -15.4,10 -26.2,12.2 4.3,-21.3 0.3,-47.3 -12.7,-63 4.9,-0.8 10.9,-2.4 14.1,-5.7 m -24.1,6.8 c 13.8,11.9 20,39.2 14.1,63.5 -4.1,0.5 -8.1,0.8 -11.6,0.8 -1.9,-21.9 -6.8,-44 -14.3,-64.6 3.7,0.3 8.1,0.3 11.8,0.3 m -422.6,22.1 c -1.1,-10.5 2.4,-39.5 13.8,-51.1 7,-7.3 14.1,-5.1 14.1,0.8 0,6.2 1.4,11.6 2.4,14.6 -17.3,6.8 -26.2,22.2 -30.3,35.7 m 9.7,27.6 c -1.9,-2.2 -3.5,-4.9 -4.9,-7.6 1.4,-21.3 10.3,-42.7 29.7,-48.9 3.2,3.2 9.2,4.9 14.1,5.7 -13,15.7 -17,41.6 -12.7,63 -10.8,-2.2 -20.5,-6 -26.2,-12.2 m 47.9,14.6 c -4.1,0 -8.1,-0.3 -12.7,-0.8 -4.6,-18.6 -1.9,-38.9 5.4,-53 v 0.3 l 12.2,-5.1 c 4.9,-1.9 9.7,-3.8 14.9,-4.9 -10.7,19.7 -17.4,41.3 -19.8,63.5 m 184,-162.700005 c 41.9,0 76.2,34.000005 76.2,75.900005 0,42.2 -34.3,76.2 -76.2,76.2 -41.9,0 -76.2,-34 -76.2,-76.2 0,-41.8 34.3,-75.900005 76.2,-75.900005 m 115.6,174.300005 c -0.3,17.8 -7,48.9 -23,57 -13.2,6.6 -6.5,-7.5 -16.5,-58.1 13.3,0.3 26.6,0.3 39.5,1.1 m -54,-1.6 c 0.8,4.9 3.8,40.3 -1.6,41.9 -11.6,3.5 -40,4.3 -51.1,-1.1 -4.1,-3 -4.6,-35.9 -4.3,-41.1 v 0.3 c 18.9,-0.3 38.1,-0.3 57,0 m -72.4,53.8 c -13,3.5 -41.6,4.1 -54.6,-1.6 -6.5,-2.7 -3.8,-42.4 -1.9,-51.6 19.2,-0.5 38.4,-0.5 57.8,-0.8 v 0.3 c 1.1,8.3 3.3,51.2 -1.3,53.7 m -106.5,-51.1 c 12.2,-0.8 24.6,-1.4 36.8,-1.6 -2.4,15.4 -3,43.5 -4.9,52.2 -1.1,6.8 -4.3,6.8 -9.7,4.3 -21.9,-9.8 -27.6,-35.2 -22.2,-54.9 m -35.4,31.3 c 7.8,-1.1 15.7,-1.9 23.5,-2.7 1.6,6.2 3.8,11.9 7,17.6 10,17 44,35.7 45.1,7 6.2,14.9 40.8,12.2 54.9,10.8 15.7,-1.4 23.8,-1.4 26.8,-14.3 12.4,4.3 30.8,4.1 44,3 11.3,-0.8 20.8,-0.5 24.6,-8.9 1.1,5.1 1.9,11.6 4.6,16.8 10.8,21.3 37.3,1.4 46.8,-31.6 8.6,0.8 17.6,1.9 26.5,2.7 -0.4,1.3 -3.8,7.3 7.3,11.6 -47.6,47 -95.7,87.8 -163.2,107 -63.2,-20.8 -112.1,-59.5 -155.9,-106.5 9.6,-3.4 10.4,-8.8 8,-12.5 m -21.6,172.5 c -3.8,17.8 -21.9,29.7 -39.7,28.9 -19.2,-0.8 -46.5,-17 -59.2,-36.5 -2.7,-31.1 43.8,-61.3 66.2,-54.6 14.9,4.3 27.8,30.8 33.5,54 0,3 -0.3,5.7 -0.8,8.2 m -8.7,-66 c -0.5,-13.5 -0.5,-27 -0.3,-40.5 h 0.3 c 2.7,-1.6 5.7,-3.8 7.8,-6.5 6.5,-1.6 13,-5.1 15.1,-9.2 3.3,-7.1 -7,-7.5 -5.4,-12.4 2.7,-1.1 5.7,-2.2 7.8,-3.5 29.2,29.2 58.6,56.5 97.3,77 -36.8,11.3 -72.4,27.6 -105.9,47 -1.2,-18.6 -7.7,-35.9 -16.7,-51.9 m 337.6,64.6 c -103,3.5 -206.2,4.1 -309.4,0 0,0.3 0,0.3 -0.3,0.3 v -0.3 h 0.3 c 35.1,-21.6 72.2,-39.2 112.4,-50.8 11.6,5.1 23,9.5 34.9,13.2 2.2,0.8 2.2,0.8 4.3,0 14.3,-4.1 28.4,-9.2 42.2,-15.4 41.5,11.7 78.8,31.7 115.6,53 m 10.5,-12.4 c -35.9,-19.5 -73,-35.9 -111.9,-47.6 38.1,-20 71.9,-47.3 103.5,-76.7 2.2,1.4 4.6,2.4 7.6,3.2 0,0.8 0.3,1.9 0.5,2.4 -4.6,2.7 -7.8,6.2 -5.9,10.3 2.2,3.8 8.6,7.6 15.1,8.9 2.4,2.7 5.1,5.1 8.1,6.8 0,13.8 -0.3,27.6 -0.8,41.3 l 0.3,-0.3 c -9.3,15.9 -15.5,37 -16.5,51.7 m 105.9,6.2 c -12.7,19.5 -40,35.7 -59.2,36.5 -19.3,0.9 -40.5,-13.2 -40.5,-37 5.7,-23.2 18.9,-49.7 33.5,-54 22.7,-6.9 69.2,23.4 66.2,54.5 M 373.056,60.569405 c -3.8,-72.1 -100.8,-79.7 -126,-23.5 44.6,-24.3 90.3,-15.7 126,23.5 M 74.956,392.46941 c -15.7,1.6 -49.5,25.4 -49.5,43.2 0,11.6 15.7,19.5 32.2,14.9 12.2,-3.2 31.1,-17.6 35.9,-27.3 6,-11.6 -3.7,-32.7 -18.6,-30.8 m 215.9,-176.2 c 28.6,0 51.9,-21.6 51.9,-48.4 0,-36.1 -40.5,-58.1 -72.2,-44.3 9.5,3 16.5,11.6 16.5,21.6 0,23.3 -33.3,32 -46.5,11.3 -7.3,34.1 19.4,59.8 50.3,59.8 m -222.7,243.2 c 0.5,6.5 12.2,12.7 21.6,9.5 6.8,-2.7 14.6,-10.5 17.3,-16.2 3,-7 -1.1,-20 -9.7,-18.4 -8.9,1.6 -29.7,16.7 -29.2,25.1 m 433.2,-67 c -14.9,-1.9 -24.6,19.2 -18.9,30.8 4.9,9.7 24.1,24.1 36.2,27.3 16.5,4.6 32.2,-3.2 32.2,-14.9 0,-17.8 -33.8,-41.6 -49.5,-43.2 m -22.4,41.9 c -8.4,-1.6 -12.4,11.3 -9.5,18.4 2.4,5.7 10.3,13.5 17.3,16.2 9.2,3.2 21.1,-3 21.3,-9.5 0.9,-8.4 -20.2,-23.5 -29.1,-25.1"
     id="path1" />
</svg>`,"galaxies/mitre-mobile-attack-tool":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-64.0011 0.0000 640.0019 512.0015"
   version="1.1"
   id="svg1"
   sodipodi:docname="mitre-mobile-attack-tool.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 504.97075,199.36275 -22.627,-22.627 c -9.373,-9.373 -24.569,-9.373 -33.941,0 l -5.657,5.657 -113.138,-113.137 5.657,-5.657 c 9.373,-9.373 9.373,-24.569 0,-33.941 l -22.627,-22.628 c -9.373,-9.373 -24.569,-9.373 -33.941,0 l -124.451,124.451 c -9.373,9.373 -9.373,24.569 0,33.941 l 22.627,22.627 c 9.373,9.373 24.569,9.373 33.941,0 l 5.657,-5.657 39.598,39.598 -81.04,81.04 -5.657,-5.657 c -12.497,-12.497 -32.758,-12.497 -45.255,0 l -114.744,114.746 c -12.497,12.497 -12.497,32.758 0,45.255 l 45.255,45.255 c 12.497,12.497 32.758,12.497 45.255,0 l 114.745,-114.745 c 12.497,-12.497 12.497,-32.758 0,-45.255 l -5.657,-5.657 81.04,-81.04 39.598,39.598 -5.657,5.657 c -9.373,9.373 -9.373,24.569 0,33.941 l 22.627,22.627 c 9.373,9.373 24.569,9.373 33.941,0 l 124.451,-124.451 c 9.372,-9.372 9.372,-24.568 0,-33.941"
     id="path1" />
</svg>`,"galaxies/mitre-pre-attack-attack-pattern":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="0.0000 0.0000 576.0000 448.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="mitre-pre-attack-attack-pattern.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 0,85.66 v 346.32 c 0,11.32 11.43,19.06 21.94,14.86 L 160,384 V 0 L 20.12,55.95 A 32.01,32.01 0 0 0 0,85.66 M 192,384 384,448 V 64 L 192,0 Z M 554.06,1.16 416,64 V 448 L 555.88,392.05 A 32,32 0 0 0 576,362.34 V 16.02 C 576,4.7 564.57,-3.04 554.06,1.16"
     id="path1" />
</svg>`,"galaxies/mitre-pre-attack-intrusion-set":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-95.9909 0.0000 639.9818 511.9854"
   version="1.1"
   id="svg1"
   sodipodi:docname="mitre-pre-attack-intrusion-set.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 383.9,308.28542 23.9,-62.6 c 4,-10.5 -3.7,-21.7 -15,-21.7 h -58.5 c 11,-18.9 17.8,-40.6 17.8,-64 v -0.3 c 39.2,-7.8 64,-19.1 64,-31.7 0,-13.3 -27.3,-25.1 -70.1,-32.999997 -9.2,-32.8 -27,-65.8 -40.6,-82.8 C 295.9,0.28542306 279.5,-3.4145769 265.9,3.3854231 L 238.3,17.185423 c -9,4.5 -19.6,4.5 -28.6,0 L 182.1,3.3854231 c -13.6,-6.8 -30,-3.10000004 -39.5,8.7999999 -13.5,17 -31.4,50 -40.6,82.8 -42.7,7.899997 -70,19.699997 -70,32.999997 0,12.6 24.8,23.9 64,31.7 v 0.3 c 0,23.4 6.8,45.1 17.8,64 H 56.3 c -11.5,0 -19.2,11.7 -14.7,22.3 l 25.8,60.2 c -40.1,23.3 -67.4,66.2 -67.4,115.9 v 44.8 c 0,24.7 20.1,44.8 44.8,44.8 h 358.4 c 24.7,0 44.8,-20.1 44.8,-44.8 v -44.8 c 0,-48.4 -25.8,-90.4 -64.1,-114.1 m -207.9,171.7 -41.6,-192 49.6,32 24,40 z m 96,0 -32,-120 24,-40 49.6,-32 z m 41.7,-298.5 c -3.9,11.9 -7,24.6 -16.5,33.4 -10.1,9.3 -48,22.4 -64,-25 -2.8,-8.4 -15.4,-8.4 -18.3,0 -17,50.2 -56,32.4 -64,25 -9.5,-8.8 -12.7,-21.5 -16.5,-33.4 -0.8,-2.5 -6.3,-5.7 -6.3,-5.8 v -10.8 c 28.3,3.6 61,5.8 96,5.8 35,0 67.7,-2.1 96,-5.8 v 10.8 c -0.1,0.1 -5.6,3.2 -6.4,5.8"
     id="path1" />
</svg>`,"galaxies/mitre-tool":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-64.0011 0.0000 640.0019 512.0015"
   version="1.1"
   id="svg1"
   sodipodi:docname="mitre-tool.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 504.97075,199.36275 -22.627,-22.627 c -9.373,-9.373 -24.569,-9.373 -33.941,0 l -5.657,5.657 -113.138,-113.137 5.657,-5.657 c 9.373,-9.373 9.373,-24.569 0,-33.941 l -22.627,-22.628 c -9.373,-9.373 -24.569,-9.373 -33.941,0 l -124.451,124.451 c -9.373,9.373 -9.373,24.569 0,33.941 l 22.627,22.627 c 9.373,9.373 24.569,9.373 33.941,0 l 5.657,-5.657 39.598,39.598 -81.04,81.04 -5.657,-5.657 c -12.497,-12.497 -32.758,-12.497 -45.255,0 l -114.744,114.746 c -12.497,12.497 -12.497,32.758 0,45.255 l 45.255,45.255 c 12.497,12.497 32.758,12.497 45.255,0 l 114.745,-114.745 c 12.497,-12.497 12.497,-32.758 0,-45.255 l -5.657,-5.657 81.04,-81.04 39.598,39.598 -5.657,5.657 c -9.373,9.373 -9.373,24.569 0,33.941 l 22.627,22.627 c 9.373,9.373 24.569,9.373 33.941,0 l 124.451,-124.451 c 9.372,-9.372 9.372,-24.568 0,-33.941"
     id="path1" />
</svg>`,"galaxies/nace":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-24.0000 0.0000 560.0000 448.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="nace.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 475.115,131.781 336,220.309 v -68.28 c 0,-18.916 -20.931,-30.399 -36.885,-20.248 L 160,220.309 V 24 C 160,10.745 149.255,0 136,0 H 24 C 10.745,0 0,10.745 0,24 v 400 c 0,13.255 10.745,24 24,24 h 464 c 13.255,0 24,-10.745 24,-24 V 152.029 c 0,-18.917 -20.931,-30.399 -36.885,-20.248"
     id="path1" />
</svg>`,"galaxies/naics":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-24.0000 0.0000 560.0000 448.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="naics.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 475.115,131.781 336,220.309 v -68.28 c 0,-18.916 -20.931,-30.399 -36.885,-20.248 L 160,220.309 V 24 C 160,10.745 149.255,0 136,0 H 24 C 10.745,0 0,10.745 0,24 v 400 c 0,13.255 10.745,24 24,24 h 464 c 13.255,0 24,-10.745 24,-24 V 152.029 c 0,-18.917 -20.931,-30.399 -36.885,-20.248"
     id="path1" />
</svg>`,"galaxies/nato":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-24.0000 0.0000 560.0000 448.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="nato.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 475.115,131.781 336,220.309 v -68.28 c 0,-18.916 -20.931,-30.399 -36.885,-20.248 L 160,220.309 V 24 C 160,10.745 149.255,0 136,0 H 24 C 10.745,0 0,10.745 0,24 v 400 c 0,13.255 10.745,24 24,24 h 464 c 13.255,0 24,-10.745 24,-24 V 152.029 c 0,-18.917 -20.931,-30.399 -36.885,-20.248"
     id="path1" />
</svg>`,"galaxies/nice-framework-competency-areas":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-96.0000 0.0000 640.0000 512.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="nice-framework-competency-areas.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 224,256 C 294.7,256 352,198.7 352,128 352,57.3 294.7,0 224,0 153.3,0 96,57.3 96,128 c 0,70.7 57.3,128 128,128 m 89.6,32 h -16.7 c -22.2,10.2 -46.9,16 -72.9,16 -26,0 -50.6,-5.8 -72.9,-16 H 134.4 C 60.2,288 0,348.2 0,422.4 V 464 c 0,26.5 21.5,48 48,48 h 352 c 26.5,0 48,-21.5 48,-48 V 422.4 C 448,348.2 387.8,288 313.6,288"
     id="path1" />
</svg>`,"galaxies/nice-framework-knowledges":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-96.0000 0.0000 640.0000 512.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="nice-framework-knowledges.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 224,256 C 294.7,256 352,198.7 352,128 352,57.3 294.7,0 224,0 153.3,0 96,57.3 96,128 c 0,70.7 57.3,128 128,128 m 89.6,32 h -16.7 c -22.2,10.2 -46.9,16 -72.9,16 -26,0 -50.6,-5.8 -72.9,-16 H 134.4 C 60.2,288 0,348.2 0,422.4 V 464 c 0,26.5 21.5,48 48,48 h 352 c 26.5,0 48,-21.5 48,-48 V 422.4 C 448,348.2 387.8,288 313.6,288"
     id="path1" />
</svg>`,"galaxies/nice-framework-opm-codes":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-96.0000 0.0000 640.0000 512.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="nice-framework-opm-codes.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 224,256 C 294.7,256 352,198.7 352,128 352,57.3 294.7,0 224,0 153.3,0 96,57.3 96,128 c 0,70.7 57.3,128 128,128 m 89.6,32 h -16.7 c -22.2,10.2 -46.9,16 -72.9,16 -26,0 -50.6,-5.8 -72.9,-16 H 134.4 C 60.2,288 0,348.2 0,422.4 V 464 c 0,26.5 21.5,48 48,48 h 352 c 26.5,0 48,-21.5 48,-48 V 422.4 C 448,348.2 387.8,288 313.6,288"
     id="path1" />
</svg>`,"galaxies/nice-framework-skills":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-96.0000 0.0000 640.0000 512.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="nice-framework-skills.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 224,256 C 294.7,256 352,198.7 352,128 352,57.3 294.7,0 224,0 153.3,0 96,57.3 96,128 c 0,70.7 57.3,128 128,128 m 89.6,32 h -16.7 c -22.2,10.2 -46.9,16 -72.9,16 -26,0 -50.6,-5.8 -72.9,-16 H 134.4 C 60.2,288 0,348.2 0,422.4 V 464 c 0,26.5 21.5,48 48,48 h 352 c 26.5,0 48,-21.5 48,-48 V 422.4 C 448,348.2 387.8,288 313.6,288"
     id="path1" />
</svg>`,"galaxies/nice-framework-tasks":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-96.0000 0.0000 640.0000 512.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="nice-framework-tasks.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 224,256 C 294.7,256 352,198.7 352,128 352,57.3 294.7,0 224,0 153.3,0 96,57.3 96,128 c 0,70.7 57.3,128 128,128 m 89.6,32 h -16.7 c -22.2,10.2 -46.9,16 -72.9,16 -26,0 -50.6,-5.8 -72.9,-16 H 134.4 C 60.2,288 0,348.2 0,422.4 V 464 c 0,26.5 21.5,48 48,48 h 352 c 26.5,0 48,-21.5 48,-48 V 422.4 C 448,348.2 387.8,288 313.6,288"
     id="path1" />
</svg>`,"galaxies/nice-framework-work-roles":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-96.0000 0.0000 640.0000 512.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="nice-framework-work-roles.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 224,256 C 294.7,256 352,198.7 352,128 352,57.3 294.7,0 224,0 153.3,0 96,57.3 96,128 c 0,70.7 57.3,128 128,128 m 89.6,32 h -16.7 c -22.2,10.2 -46.9,16 -72.9,16 -26,0 -50.6,-5.8 -72.9,-16 H 134.4 C 60.2,288 0,348.2 0,422.4 V 464 c 0,26.5 21.5,48 48,48 h 352 c 26.5,0 48,-21.5 48,-48 V 422.4 C 448,348.2 387.8,288 313.6,288"
     id="path1" />
</svg>`,"galaxies/o365-exchange-techniques":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="0.0000 0.0000 576.0000 448.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="o365-exchange-techniques.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 0,85.66 v 346.32 c 0,11.32 11.43,19.06 21.94,14.86 L 160,384 V 0 L 20.12,55.95 A 32.01,32.01 0 0 0 0,85.66 M 192,384 384,448 V 64 L 192,0 Z M 554.06,1.16 416,64 V 448 L 555.88,392.05 A 32,32 0 0 0 576,362.34 V 16.02 C 576,4.7 564.57,-3.04 554.06,1.16"
     id="path1" />
</svg>`,"galaxies/online-service":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="0.0000 0.0000 640.0000 448.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="online-service.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 537.6,194.6 C 541.7,183.9 544,172.2 544,160 544,107 501,64 448,64 428.3,64 409.9,70 394.7,80.2 367,32.2 315.3,0 256,0 167.6,0 96,71.6 96,160 c 0,2.7 0.1,5.4 0.2,8.1 C 40.2,187.8 0,241.2 0,304 0,383.5 64.5,448 144,448 h 368 c 70.7,0 128,-57.3 128,-128 0,-61.9 -44,-113.6 -102.4,-125.4"
     id="path1" />
</svg>`,"galaxies/operating-system":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="0.0000 0.0000 640.0000 512.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="operating-system.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 624,416 H 381.54 c -0.74,19.81 -14.71,32 -32.74,32 H 288 c -18.69,0 -33.02,-17.47 -32.77,-32 H 16 c -8.8,0 -16,7.2 -16,16 v 16 c 0,35.2 28.8,64 64,64 h 512 c 35.2,0 64,-28.8 64,-64 v -16 c 0,-8.8 -7.2,-16 -16,-16 M 576,48 C 576,21.6 554.4,0 528,0 H 112 C 85.6,0 64,21.6 64,48 V 384 H 576 Z M 512,320 H 128 V 64 h 384 z"
     id="path1" />
</svg>`,"galaxies/plot4ai":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-32.0000 0.0000 640.0000 512.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="plot4ai.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 208,0 c -29.9,0 -54.7,20.5 -61.8,48.2 -0.8,0 -1.4,-0.2 -2.2,-0.2 -35.3,0 -64,28.7 -64,64 0,4.8 0.6,9.5 1.7,14 -29.2,12 -49.7,40.6 -49.7,74 0,12.6 3.2,24.3 8.3,34.9 C 16.3,248.7 0,274.3 0,304 c 0,33.3 20.4,61.9 49.4,73.9 -0.9,4.6 -1.4,9.3 -1.4,14.1 0,39.8 32.2,72 72,72 4.1,0 8.1,-0.5 12,-1.2 9.6,28.5 36.2,49.2 68,49.2 39.8,0 72,-32.2 72,-72 V 64 C 272,28.7 243.3,0 208,0 m 368,304 c 0,-29.7 -16.3,-55.3 -40.3,-69.1 5.2,-10.6 8.3,-22.3 8.3,-34.9 0,-33.4 -20.5,-62 -49.7,-74 1,-4.5 1.7,-9.2 1.7,-14 0,-35.3 -28.7,-64 -64,-64 -0.8,0 -1.5,0.2 -2.2,0.2 C 422.7,20.5 397.9,0 368,0 332.7,0 304,28.6 304,64 v 376 c 0,39.8 32.2,72 72,72 31.8,0 58.4,-20.7 68,-49.2 3.9,0.7 7.9,1.2 12,1.2 39.8,0 72,-32.2 72,-72 0,-4.8 -0.5,-9.5 -1.4,-14.1 29,-12 49.4,-40.6 49.4,-73.9"
     id="path1" />
</svg>`,"galaxies/preventive-measure":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-79.9688 0.0000 639.9376 511.9501"
   version="1.1"
   id="svg1"
   sodipodi:docname="preventive-measure.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 450.5,83.675063 258.5,3.6750632 a 48.15,48.15 0 0 0 -36.9,0 L 29.6,83.675063 C 11.7,91.075063 0,108.57506 0,127.97506 c 0,198.5 114.5,335.7 221.5,380.3 11.8,4.9 25.1,4.9 36.9,0 85.7,-35.7 221.6,-159 221.6,-380.3 0,-19.4 -11.7,-36.899997 -29.5,-44.299997 M 240.1,446.27506 240,65.275063 415.9,138.57506 c -3.3,151.4 -82.1,261.1 -175.8,307.7"
     id="path1" />
</svg>`,"galaxies/producer":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-96.0000 0.0000 640.0000 512.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="producer.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 448,360 V 24 C 448,10.7 437.3,0 424,0 H 96 C 43,0 0,43 0,96 v 320 c 0,53 43,96 96,96 h 328 c 13.3,0 24,-10.7 24,-24 v -16 c 0,-7.5 -3.5,-14.3 -8.9,-18.7 -4.2,-15.4 -4.2,-59.3 0,-74.7 5.4,-4.3 8.9,-11.1 8.9,-18.6 M 128,134 c 0,-3.3 2.7,-6 6,-6 h 212 c 3.3,0 6,2.7 6,6 v 20 c 0,3.3 -2.7,6 -6,6 H 134 c -3.3,0 -6,-2.7 -6,-6 z m 0,64 c 0,-3.3 2.7,-6 6,-6 h 212 c 3.3,0 6,2.7 6,6 v 20 c 0,3.3 -2.7,6 -6,6 H 134 c -3.3,0 -6,-2.7 -6,-6 z M 381.4,448 H 96 c -17.7,0 -32,-14.3 -32,-32 0,-17.6 14.4,-32 32,-32 h 285.4 c -1.9,17.1 -1.9,46.9 0,64"
     id="path1" />
</svg>`,"galaxies/ransomware":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-131.7641 0.0000 640.0000 512.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="ransomware.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 306.44,242.638 c 27.73,-14.18 45.377,-39.39 41.28,-81.3 C 342.362,103.987 295.262,84.765 232.87,79.409 V 0 h -48.528 v 77.203 c -12.605,0 -25.525,0.315 -38.444,0.63 V 0 H 97.37 v 79.409 c -17.842,0.539 -38.622,0.276 -97.37,0 v 51.678 c 38.314,-0.678 58.417,-3.14 63.023,21.427 V 369.943 C 60.098,389.435 44.499,386.628 9.768,386.014 L 10e-4,443.68 c 88.481,0 97.37,0.315 97.37,0.315 V 512 h 48.528 v -67.06 c 13.234,0.315 26.154,0.315 38.444,0.315 V 512 h 48.528 v -68.005 c 81.299,-4.412 135.647,-24.894 142.895,-101.467 5.671,-61.446 -23.32,-88.862 -69.326,-99.89 M 146.844,134.553 c 27.415,0 113.126,-8.507 113.126,48.528 0,54.515 -85.71,48.212 -113.126,48.212 z m 0,251.776 V 279.821 c 32.772,0 133.127,-9.138 133.127,53.255 -10e-4,60.186 -100.355,53.253 -133.127,53.253"
     id="path1" />
</svg>`,"galaxies/rat":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="0.0000 0.0000 575.9989 384.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="rat.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 572.51945,177.4 C 518.28945,71.59 410.92945,0 287.99945,0 165.06945,0 57.679453,71.64 3.4794532,177.41 a 32.35,32.35 0 0 0 0,29.19 C 57.709453,312.41 165.06945,384 287.99945,384 c 122.93,0 230.32,-71.64 284.52,-177.41 a 32.35,32.35 0 0 0 0,-29.19 m -284.52,158.6 a 144,144 0 1 1 144,-144 143.93,143.93 0 0 1 -144,144 m 0,-240 a 95.3,95.3 0 0 0 -25.31,3.79 47.85,47.85 0 0 1 -66.9,66.9 95.78,95.78 0 1 0 92.21,-70.69"
     id="path1" />
</svg>`,"galaxies/region":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-62.0000 0.0000 620.0000 496.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="region.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 248,0 C 111,0 0,111 0,248 0,385 111,496 248,496 385,496 496,385 496,248 496,111 385,0 248,0 m 200,248 c 0,22.5 -3.9,44.2 -10.8,64.4 h -20.3 c -4.3,0 -8.4,-1.7 -11.4,-4.8 l -32,-32.6 c -4.5,-4.6 -4.5,-12.1 0.1,-16.7 l 12.5,-12.5 v -8.7 c 0,-3 -1.2,-5.9 -3.3,-8 l -9.4,-9.4 c -2.1,-2.1 -5,-3.3 -8,-3.3 h -16 c -6.2,0 -11.3,-5.1 -11.3,-11.3 0,-3 1.2,-5.9 3.3,-8 l 9.4,-9.4 c 2.1,-2.1 5,-3.3 8,-3.3 h 32 c 6.2,0 11.3,-5.1 11.3,-11.3 v -9.4 c 0,-6.2 -5.1,-11.3 -11.3,-11.3 h -36.7 c -8.8,0 -16,7.2 -16,16 v 4.5 c 0,6.9 -4.4,13 -10.9,15.2 l -31.6,10.5 c -3.3,1.1 -5.5,4.1 -5.5,7.6 v 2.2 c 0,4.4 -3.6,8 -8,8 h -16 c -4.4,0 -8,-3.6 -8,-8 0,-4.4 -3.6,-8 -8,-8 H 247 c -3,0 -5.8,1.7 -7.2,4.4 l -9.4,18.7 c -2.7,5.4 -8.2,8.8 -14.3,8.8 H 194 c -8.8,0 -16,-7.2 -16,-16 V 191 c 0,-4.2 1.7,-8.3 4.7,-11.3 l 20.1,-20.1 c 4.6,-4.6 7.2,-10.9 7.2,-17.5 0,-3.4 2.2,-6.5 5.5,-7.6 l 40,-13.3 c 1.7,-0.6 3.2,-1.5 4.4,-2.7 l 26.8,-26.8 c 2.1,-2.1 3.3,-5 3.3,-8 0,-6.2 -5.1,-11.3 -11.3,-11.3 H 258 l -16,16 v 8 c 0,4.4 -3.6,8 -8,8 h -16 c -4.4,0 -8,-3.6 -8,-8 v -20 c 0,-2.5 1.2,-4.9 3.2,-6.4 L 242.1,48.3 C 244,48.2 245.9,48 247.8,48 358.3,48 448,137.7 448,248 M 130.1,141.1 c 0,-3 1.2,-5.9 3.3,-8 l 25.4,-25.4 c 2.1,-2.1 5,-3.3 8,-3.3 6.2,0 11.3,5.1 11.3,11.3 v 16 c 0,3 -1.2,5.9 -3.3,8 l -9.4,9.4 c -2.1,2.1 -5,3.3 -8,3.3 h -16 c -6.2,0 -11.3,-5.1 -11.3,-11.3 m 128,306.4 v -7.1 c 0,-8.8 -7.2,-16 -16,-16 h -20.2 c -10.8,0 -26.7,-5.3 -35.4,-11.8 l -22.2,-16.7 c -11.5,-8.6 -18.2,-22.1 -18.2,-36.4 v -23.9 c 0,-16 8.4,-30.8 22.1,-39 l 42.9,-25.7 c 7.1,-4.2 15.2,-6.5 23.4,-6.5 h 31.2 c 10.9,0 21.4,3.9 29.6,10.9 l 43.2,37.1 h 18.3 c 8.5,0 16.6,3.4 22.6,9.4 l 17.3,17.3 c 3.4,3.4 8.1,5.3 12.9,5.3 H 423 c -32.4,58.9 -93.8,99.5 -164.9,103.1"
     id="path1" />
</svg>`,"galaxies/rmm-tool":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-95.9909 0.0000 639.9818 511.9854"
   version="1.1"
   id="svg1"
   sodipodi:docname="rmm-tool.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 383.9,308.28542 23.9,-62.6 c 4,-10.5 -3.7,-21.7 -15,-21.7 h -58.5 c 11,-18.9 17.8,-40.6 17.8,-64 v -0.3 c 39.2,-7.8 64,-19.1 64,-31.7 0,-13.3 -27.3,-25.1 -70.1,-32.999997 -9.2,-32.8 -27,-65.8 -40.6,-82.8 C 295.9,0.28542306 279.5,-3.4145769 265.9,3.3854231 L 238.3,17.185423 c -9,4.5 -19.6,4.5 -28.6,0 L 182.1,3.3854231 c -13.6,-6.8 -30,-3.10000004 -39.5,8.7999999 -13.5,17 -31.4,50 -40.6,82.8 -42.7,7.899997 -70,19.699997 -70,32.999997 0,12.6 24.8,23.9 64,31.7 v 0.3 c 0,23.4 6.8,45.1 17.8,64 H 56.3 c -11.5,0 -19.2,11.7 -14.7,22.3 l 25.8,60.2 c -40.1,23.3 -67.4,66.2 -67.4,115.9 v 44.8 c 0,24.7 20.1,44.8 44.8,44.8 h 358.4 c 24.7,0 44.8,-20.1 44.8,-44.8 v -44.8 c 0,-48.4 -25.8,-90.4 -64.1,-114.1 m -207.9,171.7 -41.6,-192 49.6,32 24,40 z m 96,0 -32,-120 24,-40 49.6,-32 z m 41.7,-298.5 c -3.9,11.9 -7,24.6 -16.5,33.4 -10.1,9.3 -48,22.4 -64,-25 -2.8,-8.4 -15.4,-8.4 -18.3,0 -17,50.2 -56,32.4 -64,25 -9.5,-8.8 -12.7,-21.5 -16.5,-33.4 -0.8,-2.5 -6.3,-5.7 -6.3,-5.8 v -10.8 c 28.3,3.6 61,5.8 96,5.8 35,0 67.7,-2.1 96,-5.8 v 10.8 c -0.1,0.1 -5.6,3.2 -6.4,5.8"
     id="path1" />
</svg>`,"galaxies/rsit":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="0.0000 0.0000 576.0000 448.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="rsit.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 0,85.66 v 346.32 c 0,11.32 11.43,19.06 21.94,14.86 L 160,384 V 0 L 20.12,55.95 A 32.01,32.01 0 0 0 0,85.66 M 192,384 384,448 V 64 L 192,0 Z M 554.06,1.16 416,64 V 448 L 555.88,392.05 A 32,32 0 0 0 576,362.34 V 16.02 C 576,4.7 564.57,-3.04 554.06,1.16"
     id="path1" />
</svg>`,"galaxies/scor-about":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-224.0000 0.0000 640.0000 512.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="scor-about.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 20,424.229 H 40 V 279.771 H 20 c -11.046,0 -20,-8.954 -20,-20 V 212 c 0,-11.046 8.954,-20 20,-20 h 112 c 11.046,0 20,8.954 20,20 v 212.229 h 20 c 11.046,0 20,8.954 20,20 V 492 c 0,11.046 -8.954,20 -20,20 H 20 C 8.954,512 0,503.046 0,492 v -47.771 c 0,-11.046 8.954,-20 20,-20 M 96,0 C 56.235,0 24,32.235 24,72 c 0,39.765 32.235,72 72,72 39.765,0 72,-32.235 72,-72 C 168,32.235 135.764,0 96,0"
     id="path1" />
</svg>`,"galaxies/scor-attack-paths":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="0.0000 0.0000 640.0000 512.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="scor-attack-paths.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 384,320 H 256 c -17.67,0 -32,14.33 -32,32 v 128 c 0,17.67 14.33,32 32,32 h 128 c 17.67,0 32,-14.33 32,-32 V 352 c 0,-17.67 -14.33,-32 -32,-32 M 192,32 C 192,14.33 177.67,0 160,0 H 32 C 14.33,0 0,14.33 0,32 v 128 c 0,17.67 14.33,32 32,32 h 95.72 l 73.16,128.04 C 211.98,300.98 232.4,288 256,288 h 0.28 L 192,175.51 V 128 H 416 V 64 H 192 Z M 608,0 H 480 c -17.67,0 -32,14.33 -32,32 v 128 c 0,17.67 14.33,32 32,32 h 128 c 17.67,0 32,-14.33 32,-32 V 32 C 640,14.33 625.67,0 608,0"
     id="path1" />
</svg>`,"galaxies/scor-detection-signatures":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-64.0500 0.0000 640.0625 512.0500"
   version="1.1"
   id="svg1"
   sodipodi:docname="scor-detection-signatures.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 505,442.7 405.3,343 c -4.5,-4.5 -10.6,-7 -17,-7 H 372 C 399.6,300.7 416,256.3 416,208 416,93.1 322.9,0 208,0 93.1,0 0,93.1 0,208 c 0,114.9 93.1,208 208,208 48.3,0 92.7,-16.4 128,-44 v 16.3 c 0,6.4 2.5,12.5 7,17 l 99.7,99.7 c 9.4,9.4 24.6,9.4 33.9,0 l 28.3,-28.3 c 9.4,-9.4 9.4,-24.6 0.1,-34 M 208,336 C 137.3,336 80,278.8 80,208 80,137.3 137.2,80 208,80 c 70.7,0 128,57.2 128,128 0,70.7 -57.2,128 -128,128"
     id="path1" />
</svg>`,"galaxies/scor-exposure-domain":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-79.9688 0.0000 639.9376 511.9501"
   version="1.1"
   id="svg1"
   sodipodi:docname="scor-exposure-domain.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 450.5,83.675063 258.5,3.6750632 a 48.15,48.15 0 0 0 -36.9,0 L 29.6,83.675063 C 11.7,91.075063 0,108.57506 0,127.97506 c 0,198.5 114.5,335.7 221.5,380.3 11.8,4.9 25.1,4.9 36.9,0 85.7,-35.7 221.6,-159 221.6,-380.3 0,-19.4 -11.7,-36.899997 -29.5,-44.299997 M 240.1,446.27506 240,65.275063 415.9,138.57506 c -3.3,151.4 -82.1,261.1 -175.8,307.7"
     id="path1" />
</svg>`,"galaxies/scor-incidents":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-31.9999 0.0000 640.0000 512.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="scor-incidents.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 569.51729,440.013 c 18.458,31.994 -4.711,71.987 -41.577,71.987 H 48.054287 c -36.937,0 -59.999,-40.055 -41.5770003,-71.987 L 246.42329,23.985005 c 18.467,-32.0090001 64.72,-31.9510001 83.154,0 z M 288.00029,354 c -25.405,0 -46,20.595 -46,46 0,25.405 20.595,46 46,46 25.405,0 46,-20.595 46,-46 0,-25.405 -20.595,-46 -46,-46 m -43.673,-165.346 7.418,136 c 0.347,6.364 5.609,11.346 11.982,11.346 h 48.546 c 6.373,0 11.635,-4.982 11.982,-11.346 l 7.418,-136 c 0.375,-6.874 -5.098,-12.654 -11.982,-12.654 h -63.383 c -6.884,0 -12.356,5.78 -11.981,12.654"
     id="path1" />
</svg>`,"galaxies/scor-resilience-measures":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-80.0008 0.0000 640.0016 512.0013"
   version="1.1"
   id="svg1"
   sodipodi:docname="scor-resilience-measures.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 208.00002,192 a 16,16 0 1 0 16,16 16,16 0 0 0 -16,-16 m 242.5,-108.32 -192,-80 a 57.4,57.4 0 0 0 -18.45,-3.68 57.4,57.4 0 0 0 -18.46,3.67 l -191.999996,80 A 47.93,47.93 0 0 0 2.3644917e-5,128 C 2.3644917e-5,326.5 114.50002,463.72 221.50002,508.32 a 48.1,48.1 0 0 0 36.91,0 c 85.68,-35.71 221.59,-159.02 221.59,-380.32 a 48,48 0 0 0 -29.5,-44.32 m -82.5,172.32 h -12.12 c -28.51,0 -42.79,34.47 -22.63,54.63 l 8.58,8.57 a 16.001826,16.001826 0 1 1 -22.63,22.63 l -8.57,-8.58 c -20.16,-20.16 -54.63,-5.88 -54.63,22.63 V 368 a 16,16 0 0 1 -32,0 v -12.12 c 0,-28.51 -34.47,-42.79 -54.63,-22.63 l -8.57,8.58 a 16.001826,16.001826 0 0 1 -22.63,-22.63 l 8.58,-8.57 c 20.16,-20.16 5.88,-54.63 -22.63,-54.63 h -12.12 a 16,16 0 0 1 0,-32 h 12.12 c 28.51,0 42.79,-34.47 22.63,-54.63 l -8.58,-8.57 a 16.001826,16.001826 0 0 1 22.63,-22.63 l 8.57,8.58 c 20.16,20.16 54.63,5.88 54.63,-22.63 V 112 a 16,16 0 0 1 32,0 v 12.12 c 0,28.51 34.47,42.79 54.63,22.63 l 8.57,-8.58 a 16.001826,16.001826 0 0 1 22.63,22.63 l -8.58,8.57 c -20.16,20.16 -5.88,54.63 22.63,54.63 h 12.12 a 16,16 0 0 1 0,32 m -96,0 a 16,16 0 1 0 16,16 16,16 0 0 0 -16,-16"
     id="path1" />
</svg>`,"galaxies/scor-tens":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-95.9999 0.0000 640.0000 512.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="scor-tens.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 224.00013,224 a 32,32 0 1 0 32.007,32 32.064,32.064 0 0 0 -32.008,-32 m 214.171,-96 c -10.877,-19.5 -40.51,-50.75 -116.275,-41.875 C 300.39213,34.875 267.63413,0 223.99913,0 c -43.635,0 -76.39,34.875 -97.896,86.125 C 50.337126,77.375 20.706126,108.5 9.8291261,128 c -16.379,29.375 -15.004,73.125 25.1289999,128 -40.1329999,54.875 -41.5079999,98.625 -25.1289999,128 29.1299999,52.375 101.6470039,43.625 116.2740039,41.875 21.505,51.25 54.261,86.125 97.896,86.125 43.635,0 76.393,-34.875 97.897,-86.125 14.629,1.75 87.144,10.5 116.275,-41.875 16.379,-29.375 15.004,-73.125 -25.13,-128 40.134,-54.875 41.509,-98.625 25.13,-128 M 63.340126,352 c -4,-7.25 -0.125,-24.75 15.004,-48.25 a 369,369 0 0 0 21.880004,19.125 c 1.626,13.75 4,27.125 6.75,40.125 -24.628004,0.875 -39.882004,-4.375 -43.634004,-11 M 100.22513,189.125 A 369,369 0 0 0 78.344126,208.25 c -15.13,-23.5 -19.004,-41 -15.004,-48.25 3.377,-6.125 16.379,-11.5 37.885004,-11.5 1.75,0 3.875,0.375 5.75,0.375 a 443,443 0 0 0 -6.75,40.25 M 223.99913,64 c 9.502,0 22.256,13.5 33.883,37.25 a 435,435 0 0 0 -33.883,12.875 435,435 0 0 0 -33.883,-12.875 c 11.63,-23.75 24.381,-37.25 33.884,-37.25 m 0,384 c -9.502,0 -22.254,-13.5 -33.883,-37.25 11.254,-3.75 22.506,-8 33.883,-12.875 a 435,435 0 0 0 33.883,12.875 c -11.628,23.75 -24.383,37.25 -33.884,37.25 m 0,-112 a 80,80 0 1 1 80,-80 80,80 0 0 1 -80,80 m 160.66,16 c -3.625,6.625 -19.004,11.875 -43.634,11 2.752,-13 5.127,-26.375 6.752,-40.125 a 368,368 0 0 0 21.878,-19.125 c 15.13,23.5 19.004,41 15.004,48.25 m -15.004,-143.75 a 368,368 0 0 0 -21.879,-19.125 443,443 0 0 0 -6.752,-40.25 c 1.875,0 4.002,-0.375 5.752,-0.375 21.504,0 34.508,5.375 37.883,11.5 4,7.25 0.125,24.75 -15.004,48.25"
     id="path1" />
</svg>`,"galaxies/sector":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-24.0000 0.0000 560.0000 448.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="sector.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 475.115,131.781 336,220.309 v -68.28 c 0,-18.916 -20.931,-30.399 -36.885,-20.248 L 160,220.309 V 24 C 160,10.745 149.255,0 136,0 H 24 C 10.745,0 0,10.745 0,24 v 400 c 0,13.255 10.745,24 24,24 h 464 c 13.255,0 24,-10.745 24,-24 V 152.029 c 0,-18.917 -20.931,-30.399 -36.885,-20.248"
     id="path1" />
</svg>`,"galaxies/sigma-rules":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-64.0007 0.0000 640.0012 512.0010"
   version="1.1"
   id="svg1"
   sodipodi:docname="sigma-rules.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 326.6125,185.3915 c 59.747,59.809 58.927,155.698 0.36,214.59 -0.11,0.12 -0.24,0.25 -0.36,0.37 l -67.2,67.2 c -59.27,59.27 -155.699,59.262 -214.96,0 -59.27,-59.26 -59.27,-155.7 0,-214.96 l 37.106,-37.106 c 9.84,-9.84 26.786,-3.3 27.294,10.606 0.648,17.722 3.826,35.527 9.69,52.721 1.986,5.822 0.567,12.262 -3.783,16.612 l -13.087,13.087 c -28.026,28.026 -28.905,73.66 -1.155,101.96 28.024,28.579 74.086,28.749 102.325,0.51 l 67.2,-67.19 c 28.191,-28.191 28.073,-73.757 0,-101.83 -3.701,-3.694 -7.429,-6.564 -10.341,-8.569 a 16.04,16.04 0 0 1 -6.947,-12.606 c -0.396,-10.567 3.348,-21.456 11.698,-29.806 l 21.054,-21.055 c 5.521,-5.521 14.182,-6.199 20.584,-1.731 a 152.5,152.5 0 0 1 20.522,17.197 m 140.935,-140.942 c -59.261,-59.262 -155.69,-59.27 -214.96,0 l -67.2,67.2 c -0.12,0.12 -0.25,0.25 -0.36,0.37 -58.566,58.892 -59.387,154.781 0.36,214.59 a 152.5,152.5 0 0 0 20.521,17.196 c 6.402,4.468 15.064,3.789 20.584,-1.731 l 21.054,-21.055 c 8.35,-8.35 12.094,-19.239 11.698,-29.806 a 16.04,16.04 0 0 0 -6.947,-12.606 c -2.912,-2.005 -6.64,-4.875 -10.341,-8.569 -28.073,-28.073 -28.191,-73.639 0,-101.83 l 67.2,-67.19 c 28.239,-28.239 74.3,-28.069 102.325,0.51 27.75,28.3 26.872,73.934 -1.155,101.96 l -13.087,13.087 c -4.35,4.35 -5.769,10.79 -3.783,16.612 5.864,17.194 9.042,34.999 9.69,52.721 0.509,13.906 17.454,20.446 27.294,10.606 l 37.106,-37.106 c 59.271,-59.259 59.271,-155.699 0.001,-214.959"
     id="path1" />
</svg>`,"galaxies/social-dark-patterns":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-64.0007 0.0000 640.0012 512.0010"
   version="1.1"
   id="svg1"
   sodipodi:docname="social-dark-patterns.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 326.6125,185.3915 c 59.747,59.809 58.927,155.698 0.36,214.59 -0.11,0.12 -0.24,0.25 -0.36,0.37 l -67.2,67.2 c -59.27,59.27 -155.699,59.262 -214.96,0 -59.27,-59.26 -59.27,-155.7 0,-214.96 l 37.106,-37.106 c 9.84,-9.84 26.786,-3.3 27.294,10.606 0.648,17.722 3.826,35.527 9.69,52.721 1.986,5.822 0.567,12.262 -3.783,16.612 l -13.087,13.087 c -28.026,28.026 -28.905,73.66 -1.155,101.96 28.024,28.579 74.086,28.749 102.325,0.51 l 67.2,-67.19 c 28.191,-28.191 28.073,-73.757 0,-101.83 -3.701,-3.694 -7.429,-6.564 -10.341,-8.569 a 16.04,16.04 0 0 1 -6.947,-12.606 c -0.396,-10.567 3.348,-21.456 11.698,-29.806 l 21.054,-21.055 c 5.521,-5.521 14.182,-6.199 20.584,-1.731 a 152.5,152.5 0 0 1 20.522,17.197 m 140.935,-140.942 c -59.261,-59.262 -155.69,-59.27 -214.96,0 l -67.2,67.2 c -0.12,0.12 -0.25,0.25 -0.36,0.37 -58.566,58.892 -59.387,154.781 0.36,214.59 a 152.5,152.5 0 0 0 20.521,17.196 c 6.402,4.468 15.064,3.789 20.584,-1.731 l 21.054,-21.055 c 8.35,-8.35 12.094,-19.239 11.698,-29.806 a 16.04,16.04 0 0 0 -6.947,-12.606 c -2.912,-2.005 -6.64,-4.875 -10.341,-8.569 -28.073,-28.073 -28.191,-73.639 0,-101.83 l 67.2,-67.19 c 28.239,-28.239 74.3,-28.069 102.325,0.51 27.75,28.3 26.872,73.934 -1.155,101.96 l -13.087,13.087 c -4.35,4.35 -5.769,10.79 -3.783,16.612 5.864,17.194 9.042,34.999 9.69,52.721 0.509,13.906 17.454,20.446 27.294,10.606 l 37.106,-37.106 c 59.271,-59.259 59.271,-155.699 0.001,-214.959"
     id="path1" />
</svg>`,"galaxies/sod-matrix":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="0.0000 0.0000 576.0000 448.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="sod-matrix.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 0,85.66 v 346.32 c 0,11.32 11.43,19.06 21.94,14.86 L 160,384 V 0 L 20.12,55.95 A 32.01,32.01 0 0 0 0,85.66 M 192,384 384,448 V 64 L 192,0 Z M 554.06,1.16 416,64 V 448 L 555.88,392.05 A 32,32 0 0 0 576,362.34 V 16.02 C 576,4.7 564.57,-3.04 554.06,1.16"
     id="path1" />
</svg>`,"galaxies/software-vendor":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-96.0000 0.0000 640.0000 512.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="software-vendor.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 436,480 H 416 V 24 C 416,10.745 405.255,0 392,0 H 56 C 42.745,0 32,10.745 32,24 V 480 H 12 c -6.627,0 -12,5.373 -12,12 v 20 h 448 v -20 c 0,-6.627 -5.373,-12 -12,-12 M 128,76 c 0,-6.627 5.373,-12 12,-12 h 40 c 6.627,0 12,5.373 12,12 v 40 c 0,6.627 -5.373,12 -12,12 h -40 c -6.627,0 -12,-5.373 -12,-12 z m 0,96 c 0,-6.627 5.373,-12 12,-12 h 40 c 6.627,0 12,5.373 12,12 v 40 c 0,6.627 -5.373,12 -12,12 h -40 c -6.627,0 -12,-5.373 -12,-12 z m 52,148 h -40 c -6.627,0 -12,-5.373 -12,-12 v -40 c 0,-6.627 5.373,-12 12,-12 h 40 c 6.627,0 12,5.373 12,12 v 40 c 0,6.627 -5.373,12 -12,12 m 76,160 h -64 v -84 c 0,-6.627 5.373,-12 12,-12 h 40 c 6.627,0 12,5.373 12,12 z m 64,-172 c 0,6.627 -5.373,12 -12,12 h -40 c -6.627,0 -12,-5.373 -12,-12 v -40 c 0,-6.627 5.373,-12 12,-12 h 40 c 6.627,0 12,5.373 12,12 z m 0,-96 c 0,6.627 -5.373,12 -12,12 h -40 c -6.627,0 -12,-5.373 -12,-12 v -40 c 0,-6.627 5.373,-12 12,-12 h 40 c 6.627,0 12,5.373 12,12 z m 0,-96 c 0,6.627 -5.373,12 -12,12 h -40 c -6.627,0 -12,-5.373 -12,-12 V 76 c 0,-6.627 5.373,-12 12,-12 h 40 c 6.627,0 12,5.373 12,12 z"
     id="path1" />
</svg>`,"galaxies/sparta-mitigations":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-79.9688 0.0000 639.9376 511.9501"
   version="1.1"
   id="svg1"
   sodipodi:docname="sparta-mitigations.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 450.5,83.675063 258.5,3.6750632 a 48.15,48.15 0 0 0 -36.9,0 L 29.6,83.675063 C 11.7,91.075063 0,108.57506 0,127.97506 c 0,198.5 114.5,335.7 221.5,380.3 11.8,4.9 25.1,4.9 36.9,0 85.7,-35.7 221.6,-159 221.6,-380.3 0,-19.4 -11.7,-36.899997 -29.5,-44.299997 M 240.1,446.27506 240,65.275063 415.9,138.57506 c -3.3,151.4 -82.1,261.1 -175.8,307.7"
     id="path1" />
</svg>`,"galaxies/sparta-tactics":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="0.0000 0.0000 576.0000 448.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="sparta-tactics.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 0,85.66 v 346.32 c 0,11.32 11.43,19.06 21.94,14.86 L 160,384 V 0 L 20.12,55.95 A 32.01,32.01 0 0 0 0,85.66 M 192,384 384,448 V 64 L 192,0 Z M 554.06,1.16 416,64 V 448 L 555.88,392.05 A 32,32 0 0 0 576,362.34 V 16.02 C 576,4.7 564.57,-3.04 554.06,1.16"
     id="path1" />
</svg>`,"galaxies/sparta-techniques":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="0.0000 0.0000 576.0000 448.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="sparta-techniques.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 0,85.66 v 346.32 c 0,11.32 11.43,19.06 21.94,14.86 L 160,384 V 0 L 20.12,55.95 A 32.01,32.01 0 0 0 0,85.66 M 192,384 384,448 V 64 L 192,0 Z M 554.06,1.16 416,64 V 448 L 555.88,392.05 A 32,32 0 0 0 576,362.34 V 16.02 C 576,4.7 564.57,-3.04 554.06,1.16"
     id="path1" />
</svg>`,"galaxies/stalkerware":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="0.0000 0.0000 575.9989 384.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="stalkerware.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 572.51945,177.4 C 518.28945,71.59 410.92945,0 287.99945,0 165.06945,0 57.679453,71.64 3.4794532,177.41 a 32.35,32.35 0 0 0 0,29.19 C 57.709453,312.41 165.06945,384 287.99945,384 c 122.93,0 230.32,-71.64 284.52,-177.41 a 32.35,32.35 0 0 0 0,-29.19 m -284.52,158.6 a 144,144 0 1 1 144,-144 143.93,143.93 0 0 1 -144,144 m 0,-240 a 95.3,95.3 0 0 0 -25.31,3.79 47.85,47.85 0 0 1 -66.9,66.9 95.78,95.78 0 1 0 92.21,-70.69"
     id="path1" />
</svg>`,"galaxies/stealer":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-64.0000 0.0000 640.0000 512.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="stealer.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 512,176.001 C 512,273.203 433.202,352 336,352 c -11.22,0 -22.19,-1.062 -32.827,-3.069 l -24.012,27.014 A 24,24 0 0 1 261.223,384 H 224 v 40 c 0,13.255 -10.745,24 -24,24 h -40 v 40 c 0,13.255 -10.745,24 -24,24 H 24 C 10.745,512 0,501.255 0,488 v -78.059 c 0,-6.365 2.529,-12.47 7.029,-16.971 L 168.831,231.168 C 163.108,213.814 160,195.271 160,176 160,78.798 238.797,0.00100001 335.999,0 433.488,-9.9999045e-4 512,78.511 512,176.001 M 336,128 c 0,26.51 21.49,48 48,48 26.51,0 48,-21.49 48,-48 0,-26.51 -21.49,-48 -48,-48 -26.51,0 -48,21.49 -48,48"
     id="path1" />
</svg>`,"galaxies/surveillance-vendor":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="0.0000 0.0000 640.0000 512.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="surveillance-vendor.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 622.3,271.1 -115.2,-45 c -4.1,-1.6 -12.6,-3.7 -22.2,0 l -115.2,45 c -10.7,4.2 -17.7,14 -17.7,24.9 0,111.6 68.7,188.8 132.9,213.9 9.6,3.7 18,1.6 22.2,0 51.3,-20 132.9,-89.4 132.9,-213.9 0,-10.9 -7,-20.7 -17.7,-24.9 M 496,462.4 V 273.3 l 95.5,37.3 C 585.9,397.7 530.6,446 496,462.4 M 224,256 C 294.7,256 352,198.7 352,128 352,57.3 294.7,0 224,0 153.3,0 96,57.3 96,128 c 0,70.7 57.3,128 128,128 m 96,40 c 0,-2.5 0.8,-4.8 1.1,-7.2 -2.5,-0.1 -4.9,-0.8 -7.5,-0.8 h -16.7 c -22.2,10.2 -46.9,16 -72.9,16 -26,0 -50.6,-5.8 -72.9,-16 H 134.4 C 60.2,288 0,348.2 0,422.4 V 464 c 0,26.5 21.5,48 48,48 h 352 c 6.8,0 13.3,-1.5 19.2,-4 C 365.2,465.1 320,391.3 320,296"
     id="path1" />
</svg>`,"galaxies/target-information":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-62.0000 0.0000 620.0000 496.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="target-information.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 248,0 C 111.03,0 0,111.03 0,248 0,384.97 111.03,496 248,496 384.97,496 496,384.97 496,248 496,111.03 384.97,0 248,0 m 0,432 C 146.31,432 64,349.71 64,248 64,146.31 146.29,64 248,64 c 101.69,0 184,82.29 184,184 0,101.69 -82.29,184 -184,184 m 0,-312 c -70.69,0 -128,57.31 -128,128 0,70.69 57.31,128 128,128 70.69,0 128,-57.31 128,-128 0,-70.69 -57.31,-128 -128,-128 m 0,192 c -35.29,0 -64,-28.71 -64,-64 0,-35.29 28.71,-64 64,-64 35.29,0 64,28.71 64,64 0,35.29 -28.71,64 -64,64"
     id="path1" />
</svg>`,"galaxies/taxonomy-of-fraud":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="0.0000 0.0000 640.0100 448.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="taxonomy-of-fraud.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 621.16,22.460001 C 582.37,6.1900012 543.55,1.2027583e-6 504.75,1.2027583e-6 381.58,-0.0099988 258.42,62.340001 135.25,62.340001 c -30.89,0 -61.76,-3.92 -92.65,-13.72 -3.47,-1.1 -6.95,-1.62 -10.35,-1.62 -17.21,0 -32.25,13.32 -32.25,31.81 V 396.07 c 0,12.63 7.23,24.6 18.84,29.46 38.79,16.28 77.61,22.47 116.41,22.47 123.17,0 246.34,-62.35 369.51,-62.35 30.89,0 61.76,3.92 92.65,13.72 3.47,1.1 6.95,1.62 10.35,1.62 17.21,0 32.25,-13.32 32.25,-31.81 V 51.930001 c -0.01,-12.64 -7.24,-24.6 -18.85,-29.47 M 48,100.22 c 20.12,5.04 41.12,7.57 62.72,8.93 C 104.84,138.54 79,160.69 48,160.69 Z m 0,285 v -47.78 c 34.37,0 62.18,27.27 63.71,61.4 C 89.18,397.03 68.12,392.53 48,385.22 M 320,320 c -44.19,0 -80,-42.99 -80,-96 0,-53.02 35.82,-96 80,-96 44.18,0 80,42.98 80,96 0,53.03 -35.83,96 -80,96 m 272,27.78 c -17.52,-4.39 -35.71,-6.85 -54.32,-8.44 5.87,-26.08 27.5,-45.88 54.32,-49.28 z m 0,-236.11 c -30.89,-3.91 -54.86,-29.699999 -55.81,-61.549999 19.54,2.17 38.09,6.23 55.81,12.66 z"
     id="path1" />
</svg>`,"galaxies/tds":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-32.0001 0.0000 640.0002 512.0001"
   version="1.1"
   id="svg1"
   sodipodi:docname="tds.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 504.717,320 H 211.572 l 6.545,32 h 268.418 c 15.401,0 26.816,14.301 23.403,29.319 l -5.517,24.276 C 523.112,414.668 536,433.828 536,456 c 0,31.202 -25.519,56.444 -56.824,55.994 -29.823,-0.429 -54.35,-24.631 -55.155,-54.447 -0.44,-16.287 6.085,-31.049 16.803,-41.548 H 231.176 C 241.553,426.165 248,440.326 248,456 c 0,31.813 -26.528,57.431 -58.67,55.938 -28.54,-1.325 -51.751,-24.385 -53.251,-52.917 -1.158,-22.034 10.436,-41.455 28.051,-51.586 L 93.883,64 H 24 C 10.745,64 0,53.255 0,40 V 24 C 0,10.745 10.745,0 24,0 h 102.529 c 11.401,0 21.228,8.021 23.513,19.19 L 159.208,64 H 551.99 c 15.401,0 26.816,14.301 23.403,29.319 l -47.273,208 C 525.637,312.246 515.923,320 504.717,320 M 403.029,192 H 360 v -60 c 0,-6.627 -5.373,-12 -12,-12 h -24 c -6.627,0 -12,5.373 -12,12 v 60 h -43.029 c -10.691,0 -16.045,12.926 -8.485,20.485 l 67.029,67.029 c 4.686,4.686 12.284,4.686 16.971,0 l 67.029,-67.029 C 419.074,204.926 413.72,192 403.029,192"
     id="path1" />
</svg>`,"galaxies/tea-matrix":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="0.0000 0.0000 576.0000 448.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="tea-matrix.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 0,85.66 v 346.32 c 0,11.32 11.43,19.06 21.94,14.86 L 160,384 V 0 L 20.12,55.95 A 32.01,32.01 0 0 0 0,85.66 M 192,384 384,448 V 64 L 192,0 Z M 554.06,1.16 416,64 V 448 L 555.88,392.05 A 32,32 0 0 0 576,362.34 V 16.02 C 576,4.7 564.57,-3.04 554.06,1.16"
     id="path1" />
</svg>`,"galaxies/terrorist-groups":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-95.9909 0.0000 639.9818 511.9854"
   version="1.1"
   id="svg1"
   sodipodi:docname="terrorist-groups.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 383.9,308.28542 23.9,-62.6 c 4,-10.5 -3.7,-21.7 -15,-21.7 h -58.5 c 11,-18.9 17.8,-40.6 17.8,-64 v -0.3 c 39.2,-7.8 64,-19.1 64,-31.7 0,-13.3 -27.3,-25.1 -70.1,-32.999997 -9.2,-32.8 -27,-65.8 -40.6,-82.8 C 295.9,0.28542306 279.5,-3.4145769 265.9,3.3854231 L 238.3,17.185423 c -9,4.5 -19.6,4.5 -28.6,0 L 182.1,3.3854231 c -13.6,-6.8 -30,-3.10000004 -39.5,8.7999999 -13.5,17 -31.4,50 -40.6,82.8 -42.7,7.899997 -70,19.699997 -70,32.999997 0,12.6 24.8,23.9 64,31.7 v 0.3 c 0,23.4 6.8,45.1 17.8,64 H 56.3 c -11.5,0 -19.2,11.7 -14.7,22.3 l 25.8,60.2 c -40.1,23.3 -67.4,66.2 -67.4,115.9 v 44.8 c 0,24.7 20.1,44.8 44.8,44.8 h 358.4 c 24.7,0 44.8,-20.1 44.8,-44.8 v -44.8 c 0,-48.4 -25.8,-90.4 -64.1,-114.1 m -207.9,171.7 -41.6,-192 49.6,32 24,40 z m 96,0 -32,-120 24,-40 49.6,-32 z m 41.7,-298.5 c -3.9,11.9 -7,24.6 -16.5,33.4 -10.1,9.3 -48,22.4 -64,-25 -2.8,-8.4 -15.4,-8.4 -18.3,0 -17,50.2 -56,32.4 -64,25 -9.5,-8.8 -12.7,-21.5 -16.5,-33.4 -0.8,-2.5 -6.3,-5.7 -6.3,-5.8 v -10.8 c 28.3,3.6 61,5.8 96,5.8 35,0 67.7,-2.1 96,-5.8 v 10.8 c -0.1,0.1 -5.6,3.2 -6.4,5.8"
     id="path1" />
</svg>`,"galaxies/threat-actor":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-95.9909 0.0000 639.9818 511.9854"
   version="1.1"
   id="svg1"
   sodipodi:docname="threat-actor.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 383.9,308.28542 23.9,-62.6 c 4,-10.5 -3.7,-21.7 -15,-21.7 h -58.5 c 11,-18.9 17.8,-40.6 17.8,-64 v -0.3 c 39.2,-7.8 64,-19.1 64,-31.7 0,-13.3 -27.3,-25.1 -70.1,-32.999997 -9.2,-32.8 -27,-65.8 -40.6,-82.8 C 295.9,0.28542306 279.5,-3.4145769 265.9,3.3854231 L 238.3,17.185423 c -9,4.5 -19.6,4.5 -28.6,0 L 182.1,3.3854231 c -13.6,-6.8 -30,-3.10000004 -39.5,8.7999999 -13.5,17 -31.4,50 -40.6,82.8 -42.7,7.899997 -70,19.699997 -70,32.999997 0,12.6 24.8,23.9 64,31.7 v 0.3 c 0,23.4 6.8,45.1 17.8,64 H 56.3 c -11.5,0 -19.2,11.7 -14.7,22.3 l 25.8,60.2 c -40.1,23.3 -67.4,66.2 -67.4,115.9 v 44.8 c 0,24.7 20.1,44.8 44.8,44.8 h 358.4 c 24.7,0 44.8,-20.1 44.8,-44.8 v -44.8 c 0,-48.4 -25.8,-90.4 -64.1,-114.1 m -207.9,171.7 -41.6,-192 49.6,32 24,40 z m 96,0 -32,-120 24,-40 49.6,-32 z m 41.7,-298.5 c -3.9,11.9 -7,24.6 -16.5,33.4 -10.1,9.3 -48,22.4 -64,-25 -2.8,-8.4 -15.4,-8.4 -18.3,0 -17,50.2 -56,32.4 -64,25 -9.5,-8.8 -12.7,-21.5 -16.5,-33.4 -0.8,-2.5 -6.3,-5.7 -6.3,-5.8 v -10.8 c 28.3,3.6 61,5.8 96,5.8 35,0 67.7,-2.1 96,-5.8 v 10.8 c -0.1,0.1 -5.6,3.2 -6.4,5.8"
     id="path1" />
</svg>`,"galaxies/tidal-campaigns":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-32.0000 0.0000 640.0000 512.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="tidal-campaigns.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 576,240 c 0,-23.63 -12.95,-44.04 -32,-55.12 V 32.01 C 544,23.26 537.02,0 512,0 504.88,0 497.81,2.38 492.02,7.02 L 406.99,75.05 C 364.28,109.19 310.66,128 256,128 H 64 C 28.65,128 0,156.65 0,192 v 96 c 0,35.35 28.65,64 64,64 h 33.7 c -1.39,10.48 -2.18,21.14 -2.18,32 0,39.77 9.26,77.35 25.56,110.94 5.19,10.69 16.52,17.06 28.4,17.06 h 74.28 c 26.05,0 41.69,-29.84 25.9,-50.56 -16.4,-21.52 -26.15,-48.36 -26.15,-77.44 0,-11.11 1.62,-21.79 4.41,-32 H 256 c 54.66,0 108.28,18.81 150.98,52.95 l 85.03,68.03 a 32.02,32.02 0 0 0 19.98,7.02 c 24.92,0 32,-22.78 32,-32 V 295.13 C 563.05,284.04 576,263.63 576,240 M 480,381.42 446.95,354.98 C 392.95,311.78 325.12,288 256,288 v -96 c 69.12,0 136.95,-23.78 190.95,-66.98 L 480,98.58 Z"
     id="path1" />
</svg>`,"galaxies/tidal-groups":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-95.9909 0.0000 639.9818 511.9854"
   version="1.1"
   id="svg1"
   sodipodi:docname="tidal-groups.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 383.9,308.28542 23.9,-62.6 c 4,-10.5 -3.7,-21.7 -15,-21.7 h -58.5 c 11,-18.9 17.8,-40.6 17.8,-64 v -0.3 c 39.2,-7.8 64,-19.1 64,-31.7 0,-13.3 -27.3,-25.1 -70.1,-32.999997 -9.2,-32.8 -27,-65.8 -40.6,-82.8 C 295.9,0.28542306 279.5,-3.4145769 265.9,3.3854231 L 238.3,17.185423 c -9,4.5 -19.6,4.5 -28.6,0 L 182.1,3.3854231 c -13.6,-6.8 -30,-3.10000004 -39.5,8.7999999 -13.5,17 -31.4,50 -40.6,82.8 -42.7,7.899997 -70,19.699997 -70,32.999997 0,12.6 24.8,23.9 64,31.7 v 0.3 c 0,23.4 6.8,45.1 17.8,64 H 56.3 c -11.5,0 -19.2,11.7 -14.7,22.3 l 25.8,60.2 c -40.1,23.3 -67.4,66.2 -67.4,115.9 v 44.8 c 0,24.7 20.1,44.8 44.8,44.8 h 358.4 c 24.7,0 44.8,-20.1 44.8,-44.8 v -44.8 c 0,-48.4 -25.8,-90.4 -64.1,-114.1 m -207.9,171.7 -41.6,-192 49.6,32 24,40 z m 96,0 -32,-120 24,-40 49.6,-32 z m 41.7,-298.5 c -3.9,11.9 -7,24.6 -16.5,33.4 -10.1,9.3 -48,22.4 -64,-25 -2.8,-8.4 -15.4,-8.4 -18.3,0 -17,50.2 -56,32.4 -64,25 -9.5,-8.8 -12.7,-21.5 -16.5,-33.4 -0.8,-2.5 -6.3,-5.7 -6.3,-5.8 v -10.8 c 28.3,3.6 61,5.8 96,5.8 35,0 67.7,-2.1 96,-5.8 v 10.8 c -0.1,0.1 -5.6,3.2 -6.4,5.8"
     id="path1" />
</svg>`,"galaxies/tidal-references":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-4.0000 0.0000 520.0000 416.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="tidal-references.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 80,320 H 16 A 16,16 0 0 0 0,336 v 64 a 16,16 0 0 0 16,16 H 80 A 16,16 0 0 0 96,400 V 336 A 16,16 0 0 0 80,320 M 80,0 H 16 A 16,16 0 0 0 0,16 V 80 A 16,16 0 0 0 16,96 H 80 A 16,16 0 0 0 96,80 V 16 A 16,16 0 0 0 80,0 m 0,160 H 16 A 16,16 0 0 0 0,176 v 64 a 16,16 0 0 0 16,16 H 80 A 16,16 0 0 0 96,240 V 176 A 16,16 0 0 0 80,160 M 496,336 H 176 a 16,16 0 0 0 -16,16 v 32 a 16,16 0 0 0 16,16 h 320 a 16,16 0 0 0 16,-16 V 352 A 16,16 0 0 0 496,336 M 496,16 H 176 a 16,16 0 0 0 -16,16 v 32 a 16,16 0 0 0 16,16 H 496 A 16,16 0 0 0 512,64 V 32 A 16,16 0 0 0 496,16 m 0,160 H 176 a 16,16 0 0 0 -16,16 v 32 a 16,16 0 0 0 16,16 h 320 a 16,16 0 0 0 16,-16 v -32 a 16,16 0 0 0 -16,-16"
     id="path1" />
</svg>`,"galaxies/tidal-software":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-128.0000 0.0000 640.0000 512.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="tidal-software.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 384,121.941 V 128 H 256 V 0 h 6.059 c 6.365,0 12.47,2.529 16.971,7.029 l 97.941,97.941 A 24,24 0 0 1 384,121.941 M 248,160 c -13.2,0 -24,-10.8 -24,-24 V 0 H 24 C 10.745,0 0,10.745 0,24 v 464 c 0,13.255 10.745,24 24,24 h 336 c 13.255,0 24,-10.745 24,-24 V 160 Z M 123.206,400.505 a 5.4,5.4 0 0 1 -7.633,0.246 L 50.707,339.939 a 5.4,5.4 0 0 1 0,-7.879 l 64.866,-60.812 a 5.4,5.4 0 0 1 7.633,0.246 l 19.579,20.885 a 5.4,5.4 0 0 1 -0.372,7.747 L 101.65,336 l 40.763,35.874 a 5.4,5.4 0 0 1 0.372,7.747 z m 51.295,50.479 -27.453,-7.97 a 5.4,5.4 0 0 1 -3.681,-6.692 l 61.44,-211.626 a 5.4,5.4 0 0 1 6.692,-3.681 l 27.452,7.97 a 5.4,5.4 0 0 1 3.68,6.692 l -61.44,211.626 a 5.397,5.397 0 0 1 -6.69,3.681 m 160.792,-111.045 -64.866,60.812 a 5.4,5.4 0 0 1 -7.633,-0.246 l -19.58,-20.885 a 5.4,5.4 0 0 1 0.372,-7.747 L 284.35,336 243.587,300.126 a 5.4,5.4 0 0 1 -0.372,-7.747 l 19.58,-20.885 a 5.4,5.4 0 0 1 7.633,-0.246 l 64.866,60.812 a 5.4,5.4 0 0 1 -10e-4,7.879"
     id="path1" />
</svg>`,"galaxies/tidal-tactic":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="0.0000 0.0000 576.0000 448.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="tidal-tactic.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 0,85.66 v 346.32 c 0,11.32 11.43,19.06 21.94,14.86 L 160,384 V 0 L 20.12,55.95 A 32.01,32.01 0 0 0 0,85.66 M 192,384 384,448 V 64 L 192,0 Z M 554.06,1.16 416,64 V 448 L 555.88,392.05 A 32,32 0 0 0 576,362.34 V 16.02 C 576,4.7 564.57,-3.04 554.06,1.16"
     id="path1" />
</svg>`,"galaxies/tidal-technique":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-96.0000 0.0000 640.0000 512.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="tidal-technique.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 325.4,289.2 224,390.6 122.6,289.2 C 54,295.3 0,352.2 0,422.4 V 464 c 0,26.5 21.5,48 48,48 h 352 c 26.5,0 48,-21.5 48,-48 V 422.4 C 448,352.2 394,295.3 325.4,289.2 M 32,192 c 27.3,0 51.8,-11.5 69.2,-29.7 15.1,53.9 64,93.7 122.8,93.7 70.7,0 128,-57.3 128,-128 C 352,57.3 294.7,0 224,0 173.6,0 130.4,29.4 109.5,71.8 92.1,47.8 64,32 32,32 32,65.4 49.1,94.8 75.1,112 49.1,129.2 32,158.6 32,192 M 176,96 h 96 c 17.7,0 32,14.3 32,32 H 144 c 0,-17.7 14.3,-32 32,-32"
     id="path1" />
</svg>`,"galaxies/tmss":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="0.0000 0.0000 576.0000 448.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="tmss.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 0,85.66 v 346.32 c 0,11.32 11.43,19.06 21.94,14.86 L 160,384 V 0 L 20.12,55.95 A 32.01,32.01 0 0 0 0,85.66 M 192,384 384,448 V 64 L 192,0 Z M 554.06,1.16 416,64 V 448 L 555.88,392.05 A 32,32 0 0 0 576,362.34 V 16.02 C 576,4.7 564.57,-3.04 554.06,1.16"
     id="path1" />
</svg>`,"galaxies/tool":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-13.5444 0.0000 603.2721 482.6177"
   version="1.1"
   id="svg1"
   sodipodi:docname="tool.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 572.756,406.76941 c 5.6,-9.5 4.7,-15.2 -5.4,-11.6 -3,-4.9 -7,-9.5 -11.1,-13.8 2.9,-9.7 -0.7,-14.2 -10.8,-9.2 -4.6,-3.2 -10.3,-6.5 -15.9,-9.2 0,-15.1 -11.6,-11.6 -17.6,-5.7 -10.4,-1.5 -18.7,-0.3 -26.8,5.7 0.3,-6.5 0.3,-13 0.3,-19.7 12.6,0 40.2,-11 45.9,-36.2 1.4,-6.8 1.6,-13.8 -0.3,-21.9 -3,-13.5 -14.3,-21.3 -25.1,-25.7 -0.8,-5.9 -7.6,-14.3 -14.9,-15.9 -7.3,-1.6 -12.4,4.9 -14.1,10.3 -8.5,0 -19.2,2.8 -21.1,8.4 -5.4,-0.5 -11.1,-1.4 -16.8,-1.9 2.7,-1.9 5.4,-3.5 8.4,-4.6 5.4,-9.2 14.6,-11.4 25.7,-11.6 v -2.8 c 19.5,-0.5 43,-5.9 53.8,-18.1 12.7,-13.8 14.6,-37.3 12.4,-55.1 -2.4,-17.3 -9.7,-37.6 -24.6,-48.1 -8.4,-5.9 -21.6,-0.8 -22.7,9.5 -2.2,19.6 1.2,30 -38.6,25.1 -10.3,-23.8 -24.6,-44.6 -42.7,-60.000005 -69.6,-59.7 -167.7,-53.8 -244.2,-37.6 19.7,4.6 41.1,8.6 59.7,16.5 -26.2,2.4 -52.7,11.3 -76.2,23.2 -32.8,17.000005 -44,29.900005 -56.7,42.400005 14.9,-2.2 28.9,-5.1 43.8,-3.8 -9.7,5.4 -18.4,12.2 -26.5,20 -25.8,0.9 -23.8,-5.3 -26.2,-25.9 -1.1,-10.5 -14.3,-15.4 -22.7,-9.7 -28.1,19.9 -33.5,79.9 -12.2,103.5 10.8,12.2 35.1,17.3 54.9,17.8 -0.3,1.1 -0.3,1.9 -0.3,2.7 10.8,0.5 19.5,2.7 24.6,11.6 3,1.1 5.7,2.7 8.1,4.6 -5.4,0.5 -11.1,1.4 -16.5,1.9 -3.3,-6.6 -13.7,-8.1 -21.1,-8.1 -1.6,-5.7 -6.5,-12.2 -14.1,-10.3 -6.8,1.9 -14.1,10 -14.9,15.9 -22.5,9.5 -30.1,26.8 -25.1,47.6 5.3,24.8 33,36.2 45.9,36.2 v 19.7 c -6.6,-5 -14.3,-7.5 -26.8,-5.7 -5.5,-5.5 -17.3,-10.1 -17.3,5.7 -5.9,2.7 -11.4,5.9 -15.9,9.2 -9.8,-4.9 -13.6,-1.7 -11.1,9.2 -4.1,4.3 -7.8,8.6 -11.1,13.8 -10.2,-3.7 -11,2.2 -5.4,11.6 -1.1,3.5 -1.6,7 -1.9,10.8 -0.5,31.6 44.6,64 73.5,65.1 17.3,0.5 34.6,-8.4 43,-23.5 113.2,4.9 226.7,4.1 340.2,0 8.1,15.1 25.4,24.3 42.7,23.5 29.2,-1.1 74.3,-33.5 73.5,-65.1 0.2,-3.7 -0.7,-7.2 -1.7,-10.7 m -73.8,-254 c 1.1,-3 2.4,-8.4 2.4,-14.6 0,-5.9 6.8,-8.1 14.1,-0.8 11.1,11.6 14.9,40.5 13.8,51.1 -4.1,-13.6 -13,-29 -30.3,-35.7 m -4.6,6.7 c 19.5,6.2 28.6,27.6 29.7,48.9 -1.1,2.7 -3,5.4 -4.9,7.6 -5.7,5.9 -15.4,10 -26.2,12.2 4.3,-21.3 0.3,-47.3 -12.7,-63 4.9,-0.8 10.9,-2.4 14.1,-5.7 m -24.1,6.8 c 13.8,11.9 20,39.2 14.1,63.5 -4.1,0.5 -8.1,0.8 -11.6,0.8 -1.9,-21.9 -6.8,-44 -14.3,-64.6 3.7,0.3 8.1,0.3 11.8,0.3 m -422.6,22.1 c -1.1,-10.5 2.4,-39.5 13.8,-51.1 7,-7.3 14.1,-5.1 14.1,0.8 0,6.2 1.4,11.6 2.4,14.6 -17.3,6.8 -26.2,22.2 -30.3,35.7 m 9.7,27.6 c -1.9,-2.2 -3.5,-4.9 -4.9,-7.6 1.4,-21.3 10.3,-42.7 29.7,-48.9 3.2,3.2 9.2,4.9 14.1,5.7 -13,15.7 -17,41.6 -12.7,63 -10.8,-2.2 -20.5,-6 -26.2,-12.2 m 47.9,14.6 c -4.1,0 -8.1,-0.3 -12.7,-0.8 -4.6,-18.6 -1.9,-38.9 5.4,-53 v 0.3 l 12.2,-5.1 c 4.9,-1.9 9.7,-3.8 14.9,-4.9 -10.7,19.7 -17.4,41.3 -19.8,63.5 m 184,-162.700005 c 41.9,0 76.2,34.000005 76.2,75.900005 0,42.2 -34.3,76.2 -76.2,76.2 -41.9,0 -76.2,-34 -76.2,-76.2 0,-41.8 34.3,-75.900005 76.2,-75.900005 m 115.6,174.300005 c -0.3,17.8 -7,48.9 -23,57 -13.2,6.6 -6.5,-7.5 -16.5,-58.1 13.3,0.3 26.6,0.3 39.5,1.1 m -54,-1.6 c 0.8,4.9 3.8,40.3 -1.6,41.9 -11.6,3.5 -40,4.3 -51.1,-1.1 -4.1,-3 -4.6,-35.9 -4.3,-41.1 v 0.3 c 18.9,-0.3 38.1,-0.3 57,0 m -72.4,53.8 c -13,3.5 -41.6,4.1 -54.6,-1.6 -6.5,-2.7 -3.8,-42.4 -1.9,-51.6 19.2,-0.5 38.4,-0.5 57.8,-0.8 v 0.3 c 1.1,8.3 3.3,51.2 -1.3,53.7 m -106.5,-51.1 c 12.2,-0.8 24.6,-1.4 36.8,-1.6 -2.4,15.4 -3,43.5 -4.9,52.2 -1.1,6.8 -4.3,6.8 -9.7,4.3 -21.9,-9.8 -27.6,-35.2 -22.2,-54.9 m -35.4,31.3 c 7.8,-1.1 15.7,-1.9 23.5,-2.7 1.6,6.2 3.8,11.9 7,17.6 10,17 44,35.7 45.1,7 6.2,14.9 40.8,12.2 54.9,10.8 15.7,-1.4 23.8,-1.4 26.8,-14.3 12.4,4.3 30.8,4.1 44,3 11.3,-0.8 20.8,-0.5 24.6,-8.9 1.1,5.1 1.9,11.6 4.6,16.8 10.8,21.3 37.3,1.4 46.8,-31.6 8.6,0.8 17.6,1.9 26.5,2.7 -0.4,1.3 -3.8,7.3 7.3,11.6 -47.6,47 -95.7,87.8 -163.2,107 -63.2,-20.8 -112.1,-59.5 -155.9,-106.5 9.6,-3.4 10.4,-8.8 8,-12.5 m -21.6,172.5 c -3.8,17.8 -21.9,29.7 -39.7,28.9 -19.2,-0.8 -46.5,-17 -59.2,-36.5 -2.7,-31.1 43.8,-61.3 66.2,-54.6 14.9,4.3 27.8,30.8 33.5,54 0,3 -0.3,5.7 -0.8,8.2 m -8.7,-66 c -0.5,-13.5 -0.5,-27 -0.3,-40.5 h 0.3 c 2.7,-1.6 5.7,-3.8 7.8,-6.5 6.5,-1.6 13,-5.1 15.1,-9.2 3.3,-7.1 -7,-7.5 -5.4,-12.4 2.7,-1.1 5.7,-2.2 7.8,-3.5 29.2,29.2 58.6,56.5 97.3,77 -36.8,11.3 -72.4,27.6 -105.9,47 -1.2,-18.6 -7.7,-35.9 -16.7,-51.9 m 337.6,64.6 c -103,3.5 -206.2,4.1 -309.4,0 0,0.3 0,0.3 -0.3,0.3 v -0.3 h 0.3 c 35.1,-21.6 72.2,-39.2 112.4,-50.8 11.6,5.1 23,9.5 34.9,13.2 2.2,0.8 2.2,0.8 4.3,0 14.3,-4.1 28.4,-9.2 42.2,-15.4 41.5,11.7 78.8,31.7 115.6,53 m 10.5,-12.4 c -35.9,-19.5 -73,-35.9 -111.9,-47.6 38.1,-20 71.9,-47.3 103.5,-76.7 2.2,1.4 4.6,2.4 7.6,3.2 0,0.8 0.3,1.9 0.5,2.4 -4.6,2.7 -7.8,6.2 -5.9,10.3 2.2,3.8 8.6,7.6 15.1,8.9 2.4,2.7 5.1,5.1 8.1,6.8 0,13.8 -0.3,27.6 -0.8,41.3 l 0.3,-0.3 c -9.3,15.9 -15.5,37 -16.5,51.7 m 105.9,6.2 c -12.7,19.5 -40,35.7 -59.2,36.5 -19.3,0.9 -40.5,-13.2 -40.5,-37 5.7,-23.2 18.9,-49.7 33.5,-54 22.7,-6.9 69.2,23.4 66.2,54.5 M 373.056,60.569405 c -3.8,-72.1 -100.8,-79.7 -126,-23.5 44.6,-24.3 90.3,-15.7 126,23.5 M 74.956,392.46941 c -15.7,1.6 -49.5,25.4 -49.5,43.2 0,11.6 15.7,19.5 32.2,14.9 12.2,-3.2 31.1,-17.6 35.9,-27.3 6,-11.6 -3.7,-32.7 -18.6,-30.8 m 215.9,-176.2 c 28.6,0 51.9,-21.6 51.9,-48.4 0,-36.1 -40.5,-58.1 -72.2,-44.3 9.5,3 16.5,11.6 16.5,21.6 0,23.3 -33.3,32 -46.5,11.3 -7.3,34.1 19.4,59.8 50.3,59.8 m -222.7,243.2 c 0.5,6.5 12.2,12.7 21.6,9.5 6.8,-2.7 14.6,-10.5 17.3,-16.2 3,-7 -1.1,-20 -9.7,-18.4 -8.9,1.6 -29.7,16.7 -29.2,25.1 m 433.2,-67 c -14.9,-1.9 -24.6,19.2 -18.9,30.8 4.9,9.7 24.1,24.1 36.2,27.3 16.5,4.6 32.2,-3.2 32.2,-14.9 0,-17.8 -33.8,-41.6 -49.5,-43.2 m -22.4,41.9 c -8.4,-1.6 -12.4,11.3 -9.5,18.4 2.4,5.7 10.3,13.5 17.3,16.2 9.2,3.2 21.1,-3 21.3,-9.5 0.9,-8.4 -20.2,-23.5 -29.1,-25.1"
     id="path1" />
</svg>`,"galaxies/uavs":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-32.0013 0.0000 640.0000 512.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="uavs.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 479.99735,192 h -114.29 L 260.60735,8.0600003 A 16.01,16.01 0 0 0 246.70735,3.4505261e-7 h -65.5 C 170.57735,3.4505261e-7 162.90735,10.17 165.82735,20.39 l 49.03,171.61 h -102.86 L 68.797348,134.4 c -3.02,-4.03 -7.77,-6.4 -12.8,-6.4 h -39.99 C 5.5973484,128 -2.0426516,137.78 0.48734841,147.88 L 31.997348,256 0.48734841,364.12 C -2.0426516,374.22 5.5973484,384 16.007348,384 h 39.99 c 5.04,0 9.78,-2.37 12.8,-6.4 L 111.99735,320 h 102.86 l -49.03,171.6 c -2.92,10.22 4.75,20.4 15.38,20.4 h 65.5 c 5.74,0 11.04,-3.08 13.89,-8.06 L 365.70735,320 h 114.29 c 35.35,0 96,-28.65 96,-64 0,-35.35 -60.65,-64 -96,-64"
     id="path1" />
</svg>`,"galaxies/ukhsa-culture-collections":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-63.4691 0.0000 639.9750 511.9800"
   version="1.1"
   id="svg1"
   sodipodi:docname="ukhsa-culture-collections.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="m 484.08336,227.56 h -21.55 c -50.68,0 -76.07,-61.27 -40.23,-97.11 l 15.23,-15.25 a 28.44,28.44 0 0 0 -40.2,-40.19 l -15.24,15.22 c -35.84,35.83 -97.11,10.45 -97.11,-40.23 V 28.45 a 28.45,28.45 0 0 0 -56.9,0 v 21.56 c 0,50.68 -61.27,76.06 -97.11,40.23 l -15.24,-15.23 A 28.44,28.44 0 0 0 75.533362,115.2 l 15.25,15.25 c 35.839998,35.84 10.449998,97.11 -40.23,97.11 h -21.57 a 28.45,28.45 0 1 0 0,56.89 h 21.55 c 50.679998,0 76.069998,61.28 40.23,97.12 l -15.23,15.24 a 28.45,28.45 0 0 0 40.199998,40.2 l 15.24,-15.25 c 35.84,-35.84 97.11,-10.45 97.11,40.23 v 21.54 a 28.45,28.45 0 0 0 56.9,0 v -21.52 c 0,-50.68 61.27,-76.07 97.11,-40.23 l 15.24,15.23 a 28.45,28.45 0 0 0 40.2,-40.2 l -15.25,-15.24 c -35.84,-35.84 -10.45,-97.12 40.23,-97.12 h 21.54 a 28.45,28.45 0 1 0 0,-56.89 z m -259.55,44.45 a 48,48 0 1 1 48,-48 48,48 0 0 1 -48,48 m 80,56 a 24,24 0 1 1 24,-24 24,24 0 0 1 -24,24"
     id="path1" />
</svg>`,"galaxies/veris-framework":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="0.0000 0.0000 640.0000 512.0000"
   version="1.1"
   id="svg1"
   sodipodi:docname="veris-framework.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 128,352 H 32 C 14.33,352 0,366.33 0,384 v 96 c 0,17.67 14.33,32 32,32 h 96 c 17.67,0 32,-14.33 32,-32 v -96 c 0,-17.67 -14.33,-32 -32,-32 m -24,-80 h 192 v 48 h 48 v -48 h 192 v 48 h 48 V 262.41 C 584,241.24 566.77,224 545.59,224 H 344 v -64 h 40 c 17.67,0 32,-14.33 32,-32 V 32 C 416,14.33 401.67,0 384,0 H 256 c -17.67,0 -32,14.33 -32,32 v 96 c 0,17.67 14.33,32 32,32 h 40 v 64 H 94.41 C 73.23,224 56,241.23 56,262.41 V 320 h 48 z m 264,80 h -96 c -17.67,0 -32,14.33 -32,32 v 96 c 0,17.67 14.33,32 32,32 h 96 c 17.67,0 32,-14.33 32,-32 v -96 c 0,-17.67 -14.33,-32 -32,-32 m 240,0 h -96 c -17.67,0 -32,14.33 -32,32 v 96 c 0,17.67 14.33,32 32,32 h 96 c 17.67,0 32,-14.33 32,-32 v -96 c 0,-17.67 -14.33,-32 -32,-32"
     id="path1" />
</svg>`,"galaxies/wiper":`<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   viewBox="-96.0001 0.0000 640.0002 512.0002"
   version="1.1"
   id="svg1"
   sodipodi:docname="wiper.svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
  <defs
     id="defs1" />
  <path
     fill="currentColor"
     d="M 432,32.000175 H 312 l -9.4,-18.7 A 24,24 0 0 0 281.1,1.7526341e-4 H 166.8 A 23.72,23.72 0 0 0 145.4,13.300175 l -9.4,18.7 H 16 a 16,16 0 0 0 -16,16 v 32 a 16,16 0 0 0 16,16 h 416 a 16,16 0 0 0 16,-16 v -32 a 16,16 0 0 0 -16,-16 M 53.2,467.00018 a 48,48 0 0 0 47.9,45 h 245.8 a 48,48 0 0 0 47.9,-45 l 21.2,-339 H 32 Z"
     id="path1" />
</svg>`};var X={shape:"none",icon:"object",accentColor:"#524948",fontSize:14,iconSize:26};var Y=[{key:"id"},{key:"uuid"},{key:"category",source:"meta-category"},{key:"description"},{key:"comment"},{key:"timestamp",format:"date"},{key:"first_seen"},{key:"last_seen"},{key:"distribution",format:"distribution"},{key:"sharing_group_id",format:"sharing-group"}];function K(g,t,n){switch(g){case"date":return C(t);case"distribution":return M(t);case"sharing-group":return T(t,n);default:return t}}var J="#428BCA";var n0={shape:"none",icon:"sighting",accentColor:"#890096",fontSize:12,iconSize:22},e0={shape:"none",icon:"sighting",accentColor:"#890096",fontSize:10,iconSize:18};var i0='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="currentColor" d="M2 22 2 10 8 10 8 3 11 3 11 8 14 10 14 22 Z"/></svg>',t0='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="currentColor" d="M2 2 2 14 8 14 8 21 11 21 11 16 14 14 14 2 Z"/></svg>';function E(g){let t=g.map(i=>Number(i.date_sighting)).filter(Number.isFinite),n=i=>new Date(i*1e3).toLocaleDateString(),d=[...new Set(g.map(i=>i.Organisation?.name).filter(i=>!!i))].join(", ");return{count:g.length,firstSeen:t.length?n(Math.min(...t)):void 0,lastSeen:t.length?n(Math.max(...t)):void 0,organisations:d}}function d0(g){return{total:g.length,positive:E(g.filter(t=>t.type==="0")),falsePositive:E(g.filter(t=>t.type==="1")),expired:E(g.filter(t=>t.type==="2"))}}var o0={shape:"none",icon:"tag",accentColor:"#DB6A47",fontSize:12,iconSize:22};var s0=[{key:"id"},{key:"local_only"},{key:"local"},{key:"exportable"}];var y="#9CA3AF",f0="#F59E0B",x0={shape:"none",icon:"attribute",accentColor:"#F59E0B",fontSize:11,iconSize:20},r0={"misp-event":q,"misp-attribute":_,"misp-attribute-group":O,"misp-object":X,"misp-tag-group":o0,"misp-galaxy-group":P,"misp-galaxy":$,"misp-sighting-summary":n0,"misp-sighting-type":e0,"misp-correlation":x0},L=class extends F{constructor(){super(...arguments);b(this,"format","misp");b(this,"variant",{id:"event-root",name:"Event as root node",description:"The MISP Event is the root node; Attributes and Objects are its children, Object References become edges between Objects.",default:!0})}detect(n){if(typeof n!="object"||n===null)return!1;let d=n.Event;return typeof d!="object"||d===null?!1:"uuid"in d&&"info"in d}convert(n,d){let{Event:i}=n,e=[],o=[],r={tagIds:new Set,galaxyTypeIds:new Set,galaxyClusterIds:new Set,galaxyClusterEdgeIds:new Set},a={};for(let c of j){let f=i[c.source??c.key];a[c.key]=S(c.format,f,i)}let{data:l,style:p}=k({...a,label:i.info,type:"misp-event"},this.defaultStyle("misp-event",i.info,{theme:d?.theme}),d?.styleRules),w=d?.viewMode==="relations";w||(e.push({id:i.uuid,data:l,style:p,expanded:!1}),this.addTagsAndGalaxies(e,o,i.uuid,i.Tag??[],i.Galaxy??[],r,d));let v=w?this.computeConnectivity(i):void 0,h=(i.Attribute??[]).filter(c=>!v||v.referencedAttrUuids.has(c.uuid));if(w)for(let c of h)this.addAttribute(e,o,void 0,c,r,d);else{let c=this.maybeGroup(e,o,i.uuid,"misp-attribute-group","Attributes","has-attributes",h.length,d);for(let f of h)this.addAttribute(c,o,i.uuid,f,r,d)}let s=(i.Object??[]).filter(c=>!v||v.connectedObjUuids.has(c.uuid));for(let c of s)this.addObject(e,o,w?void 0:i.uuid,c,r,d);for(let c of s)for(let f of c.ObjectReference??[]){if(w&&this.isDeleted(f))continue;let u=f.relationship_type||void 0;o.push({id:`${c.uuid}-${f.referenced_uuid}`,from:c.uuid,to:f.referenced_uuid,data:{label:u,type:"misp-object-reference"},style:{edge:{strokeColor:u?J:y}}})}let m=e.length===0?[{content:"Nothing to display",surface:"terminal",width:260,height:90}]:void 0;return{nodes:e,edges:o,notes:m}}correlateEvents(n,d){let i=[],e=[],o=new Set,r=new Map(n.map(h=>[h.uuid,h])),a=h=>{if(o.has(h.uuid))return;o.add(h.uuid);let s={};for(let f of j){let u=h[f.source??f.key];s[f.key]=S(f.format,u,h)}let{data:m,style:c}=k({...s,label:h.info,type:"misp-event"},this.defaultStyle("misp-event",h.info,{theme:d?.theme}),d?.styleRules);i.push({id:h.uuid,data:m,style:c,expanded:!1})},l=new Set;for(let h of n)for(let s of h.RelatedEvent??[]){let m=r.get(s.Event.uuid)??s.Event,c=[h.uuid,m.uuid].sort().join("|");l.has(c)||(l.add(c),a(h),a(m),e.push({id:`related-${c}`,from:h.uuid,to:m.uuid,data:{type:"related-event"},style:{edge:{strokeColor:f0}}}))}let p=new Map,w=(h,s)=>{if(this.isDeleted(s)||s.disable_correlation)return;let m=`${s.type}:${s.value}`,c=p.get(m);c?c.eventUuids.add(h):p.set(m,{eventUuids:new Set([h]),sample:s})};for(let h of n){for(let s of h.Attribute??[])w(h.uuid,s);for(let s of h.Object??[])for(let m of s.Attribute??[])w(h.uuid,m)}let v=0;for(let{eventUuids:h,sample:s}of p.values()){if(h.size<2)continue;for(let H of h)a(r.get(H));let m=`correlation-${v++}`,c=D[`attributes/${s.type}`]?`attributes/${s.type}`:void 0,f=`${s.type} \xB7 ${h.size} events`,{data:u,style:U}=k({label:s.value,type:"misp-correlation",attributeType:s.type,eventCount:h.size},this.defaultStyle("misp-correlation",s.value,{theme:d?.theme,iconOverride:c,badge:f}),d?.styleRules);i.push({id:m,data:u,style:U,expanded:!1});for(let H of h)e.push({id:`${H}-${m}`,from:H,to:m,data:{type:"correlates-with"},style:{edge:{strokeColor:y}}})}return i.length===0?{nodes:[],edges:[],notes:[{content:n.length>1?`No correlated attributes across these ${n.length} events`:"Nothing to correlate \u2014 only one event",surface:"terminal",width:300,height:90}]}:{nodes:i,edges:e}}isDeleted(n){return n.deleted===!0||n.deleted===1||n.deleted==="1"}computeConnectivity(n){let d=new Set,i=new Set,e=new Map;for(let o of n.Object??[])for(let r of o.Attribute??[])e.set(r.uuid,o.uuid);for(let o of n.Object??[])for(let r of o.ObjectReference??[])if(!this.isDeleted(r))if(i.add(o.uuid),String(r.referenced_type)==="1")i.add(r.referenced_uuid);else{d.add(r.referenced_uuid);let a=e.get(r.referenced_uuid);a&&i.add(a)}return{referencedAttrUuids:d,connectedObjUuids:i}}addAttribute(n,d,i,e,o,r){let a=e.value,l={};for(let h of N){let s=e[h.source??h.key];l[h.key]=G(h.format,s,e)}let p=D[`attributes/${e.type}`]?`attributes/${e.type}`:void 0,{data:w,style:v}=k({...l,label:a,type:"misp-attribute"},this.defaultStyle("misp-attribute",a,{theme:r?.theme,iconOverride:p,badge:e.type}),r?.styleRules);n.push({id:e.uuid,data:w,style:v,expanded:!1}),i!==void 0&&d.push({id:`${i}-${e.uuid}`,from:i,to:e.uuid,data:{type:"has-attribute"},style:{edge:{strokeColor:y}}}),r?.viewMode!=="relations"&&(this.addTagsAndGalaxies(n,d,e.uuid,e.Tag??[],e.Galaxy??[],o,r),e.Sighting?.length&&this.addSightingSummary(n,d,e.uuid,e.Sighting,r))}addObject(n,d,i,e,o,r){let a={};for(let c of Y){let f=e[c.source??c.key];a[c.key]=K(c.format,f,e)}let l=D[`objects/${e.name}`]?`objects/${e.name}`:void 0,p=r?.viewMode==="relations",w=[];if(p)for(let c of e.Attribute??[])this.isDeleted(c)||this.addAttribute(w,d,void 0,c,o,r);let{data:v,style:h}=k({...a,label:e.name,type:"misp-object"},{...this.defaultStyle("misp-object",e.name,{theme:r?.theme,iconOverride:l,badge:e["meta-category"]}),...w.length>0?{badges:[{text:String(w.length),title:`${w.length} hidden attribute${w.length===1?"":"s"}`}]}:{}},r?.styleRules);if(p){n.push({id:e.uuid,data:v,style:h,expanded:!1,children:w});return}n.push({id:e.uuid,data:v,style:h,expanded:!1}),d.push({id:`${i}-${e.uuid}`,from:i,to:e.uuid,data:{type:"has-object"},style:{edge:{strokeColor:y}}}),this.addTagsAndGalaxies(n,d,e.uuid,e.Tag??[],e.Galaxy??[],o,r);let s=e.Attribute??[],m=this.maybeGroup(n,d,e.uuid,"misp-attribute-group","Attributes","has-attributes",s.length,r);for(let c of s)this.addAttribute(m,d,e.uuid,c,o,r)}addTag(n,d,i,e,o,r){let a=e.id||e.name,l=r?.viewMode==="grouped",p=l?`${i}:${a}`:a,w=l?`tag-${i}-${a}`:`tag-${a}`;if(!o.has(p)){o.add(p);let v={};for(let c of s0)v[c.key]=e[c.source??c.key];let h=e.colour??"#888888",{data:s,style:m}=k({...v,label:e.name,type:"misp-tag"},{shape:"none",size:B(e.name,{hasIcon:!1,fontSize:11,padding:14}),html:()=>A(e.name,{background:h})},r?.styleRules);n.push({id:w,data:s,style:m,expanded:!1})}d.push({id:`${i}-${w}`,from:i,to:w,data:{type:"has-tag"},style:{edge:{strokeColor:y}}})}addTagsAndGalaxies(n,d,i,e,o,r,a){if(e.length>0){let c=this.maybeGroup(n,d,i,"misp-tag-group","Tags","has-tags",e.length,a);for(let f of e)this.addTag(c,d,i,f,r.tagIds,a)}if(o.length===0)return;let l=a?.viewMode==="grouped",p=`galaxy-clusters-${i}`,w="Galaxy clusters",{data:v,style:h}=k({label:w,type:"misp-galaxy-group"},this.defaultStyle("misp-galaxy-group",w,{theme:a?.theme}),a?.styleRules),s=[],m=l?s:n;n.push({id:p,data:v,style:h,expanded:!1,...l?{children:s}:{}}),d.push({id:`${i}-${p}`,from:i,to:p,data:{type:"has-galaxy-clusters"},style:{edge:{strokeColor:y}}});for(let c of o){let{children:f,nodeId:u}=this.addGalaxyType(m,d,p,c,r,a);for(let U of c.GalaxyCluster??[])this.addGalaxyCluster(f,d,u,c.name,U,r,a)}}maybeGroup(n,d,i,e,o,r,a,l){if(l?.viewMode!=="grouped"||a===0)return n;let p=`${e}-${i}`,{data:w,style:v}=k({label:o,type:e,count:a},{...this.defaultStyle(e,o,{theme:l?.theme,badge:`${a} ${o.toLowerCase()}`}),badges:[{text:String(a),title:`${a} hidden ${o.toLowerCase()}`}]},l?.styleRules),h=[];return n.push({id:p,data:w,style:v,expanded:!1,children:h}),d.push({id:`${i}-${p}`,from:i,to:p,data:{type:r},style:{edge:{strokeColor:y}}}),h}addSightingSummary(n,d,i,e,o){let r=`sighting-summary-${i}`,a="Sightings",l=d0(e),p=`${l.total} sighting${l.total===1?"":"s"}`,{data:w,style:v}=k({label:a,type:"misp-sighting-summary",count:l.total},this.defaultStyle("misp-sighting-summary",a,{theme:o?.theme,badge:p}),o?.styleRules);n.push({id:r,data:w,style:v,expanded:!1}),d.push({id:`${i}-${r}`,from:i,to:r,data:{type:"has-sightings"},style:{edge:{strokeColor:y}}}),this.addSightingType(n,d,r,"Positive","#16A34A",i0,l.positive,o),this.addSightingType(n,d,r,"False positive","#DC2626",t0,l.falsePositive,o),this.addSightingType(n,d,r,"Expired","#F59E0B",void 0,l.expired,o)}addSightingType(n,d,i,e,o,r,a,l){if(a.count===0)return;let p=`${i}-${e.toLowerCase().replace(/\s+/g,"-")}`,{data:w,style:v}=k({label:e,type:"misp-sighting-type",count:a.count,first_seen:a.firstSeen,last_seen:a.lastSeen,organisations:a.organisations||void 0},this.defaultStyle("misp-sighting-type",e,{theme:l?.theme,accentColorOverride:o,iconSvgOverride:r,badge:String(a.count)}),l?.styleRules);n.push({id:p,data:w,style:v,expanded:!1}),d.push({id:`${i}-${p}`,from:i,to:p,data:{type:"has-sighting-type"},style:{edge:{strokeColor:y}}})}addGalaxyType(n,d,i,e,o,r){let a=r?.viewMode==="grouped",l=a?`${i}:${e.type}`:e.type,p=a?`galaxy-type-${i}-${e.type}`:`galaxy-type-${e.type}`;if(a||d.push({id:`${i}-${p}`,from:i,to:p,data:{type:"has-galaxy"},style:{edge:{strokeColor:y}}}),o.galaxyTypeIds.has(l))return{children:n,nodeId:p};o.galaxyTypeIds.add(l);let w=Z(e.name),v=D[`galaxies/${e.type}`]?`galaxies/${e.type}`:void 0,h={};for(let c of Q)h[c.key]=e[c.key];let{data:s,style:m}=k({...h,label:e.name,type:"misp-galaxy"},this.defaultStyle("misp-galaxy",e.name,{theme:r?.theme,iconOverride:v,accentColorOverride:w.headerText}),r?.styleRules);if(a){let c=[];return n.push({id:p,data:s,style:m,expanded:!1,children:c}),{children:c,nodeId:p}}return n.push({id:p,data:s,style:m,expanded:!1}),{children:n,nodeId:p}}addGalaxyCluster(n,d,i,e,o,r,a){let l=a?.viewMode==="grouped",p=l?`${i}:${o.id}`:o.id,w=l?`galaxy-cluster-${i}-${o.id}`:`galaxy-cluster-${o.id}`;if(!l){let c=`${i}-${w}`;r.galaxyClusterEdgeIds.has(c)||(r.galaxyClusterEdgeIds.add(c),d.push({id:c,from:i,to:w,data:{type:"has-cluster"},style:{edge:{strokeColor:y}}}))}if(r.galaxyClusterIds.has(p))return;r.galaxyClusterIds.add(p);let v=Z(e),h={};for(let c of W)h[c.key]=c.key==="external_id"?o.meta?.external_id?.join(", "):o[c.key];let{data:s,style:m}=k({...h,label:o.value,type:"misp-galaxy-cluster"},{shape:"none",size:B(o.value,{hasIcon:!1,fontSize:11,padding:14}),html:()=>A(o.value,{background:v.badgeBg,textColor:v.badgeText,borderColor:v.badgeBorder,backgroundImage:R})},a?.styleRules);n.push({id:w,data:s,style:m,expanded:!1})}defaultStyle(n,d,i){let{icon:e,accentColor:o,fontSize:r,iconSize:a,...l}=r0[n]??{},p=i?.iconOverride??e,w=i?.iconSvgOverride??(p?D[p]:void 0),v=i?.accentColorOverride??o;if(w){let h=i?.theme==="light"?"#FFFFFF":"#33373C",s=i?.badge;return{...l,size:B(d,{hasIcon:!0,fontSize:r,iconSize:a,extraLines:s?1:0,secondaryText:s}),html:()=>I(w,d,{textColor:v,borderColor:v,background:h,badge:s,fontSize:r,iconSize:a})}}return{...l,text:d}}};V.registerImporter(new L);export{V as GraphRegistry,L as MispEventImporter,r0 as NODE_DEFAULTS,g0 as PIVOTICK_STYLE_OVERRIDES,p0 as RECOMMENDED_PIVOTICK_SIMULATION_OPTIONS};
