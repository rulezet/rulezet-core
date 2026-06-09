import "d3-force";
import { N as C, S as _, E as b, T as k, a as O } from "./index-DiIIpRDH.js";
const I = 1e4, h = 2e4, M = 0.15 * h;
self.onmessage = (g) => {
  var D, S, t, u;
  if (g.data.source !== "simulation-worker-wrapper") return;
  const { nodes: f, edges: i, options: a, canvasBCR: c } = g.data, m = f.map((e) => {
    const y = new C(e.id, e.data, e.style);
    return y.setCircleRadius(e._circleRadius ?? 10), y;
  }), o = new Map(m.map((e) => [e.id, e]));
  (D = a.layout) == null || D.type;
  const { simulation: s, simulationForces: T } = _.initSimulationForces(a, c), d = [];
  for (const e of i) {
    const y = o.get(e.from.id), F = o.get(e.to.id);
    if (y && F) {
      const N = e.style ?? {};
      d.push(new b(e.id, y, F, e.data, N, e.directed));
    }
  }
  s.nodes(m);
  const p = s.force("link");
  p && p.id((e) => e.id).links(d), ((S = a.layout) == null ? void 0 : S.type) === "tree" ? k.registerForcesOnSimulation(
    m,
    d,
    s,
    T,
    a.layout,
    c,
    k
  ) : ((t = a.layout) == null ? void 0 : t.type) === "egoTree" && k.registerForcesOnSimulation(
    m,
    d,
    s,
    T,
    a.layout,
    c,
    O
  );
  let r = a.warmupTicks || h;
  r = r === "auto" ? h : r, r = r - M;
  let l = 0.3;
  s.alphaTarget(l);
  const n = (/* @__PURE__ */ new Date()).getTime();
  let w;
  for (let e = 0; e < r && !((/* @__PURE__ */ new Date()).getTime() - n > I || (/* @__PURE__ */ new Date()).getTime() - n > a.cooldownTime || E(a, s, l) && (/* @__PURE__ */ new Date()).getTime() - n > a.cooldownTime * 0.15); ++e)
    e % 5 === 0 && (w = A(e, (/* @__PURE__ */ new Date()).getTime() - n, a), postMessage({ type: "tick", progress: w, elapsedTime: (/* @__PURE__ */ new Date()).getTime() - n })), s.tick();
  l = 0, s.alphaTarget(l), s.alpha(1);
  for (let e = 0; e < M && !(E(a, s, l) && (/* @__PURE__ */ new Date()).getTime() - n > a.cooldownTime * 0.15); ++e)
    s.tick(), e % 5 === 0 && (w = A(r + e, (/* @__PURE__ */ new Date()).getTime() - n, a), postMessage({ type: "tick", progress: w, elapsedTime: (/* @__PURE__ */ new Date()).getTime() - n }));
  postMessage({ type: "tick", progress: 1, elapsedTime: (/* @__PURE__ */ new Date()).getTime() - n }), ((u = a.layout) == null ? void 0 : u.type) === "tree" && k.simulationDone(
    m,
    d,
    s,
    a.layout
  ), postMessage({
    type: "done",
    nodes: m.map((e) => e.toDict()),
    edges: d.map((e) => e.toDict())
  });
};
function K(g, f, i, a) {
  var n, w, D, S;
  const c = g.map((t) => {
    const u = new C(t.id, t.getData(), t.getStyle());
    return u.weight = t.weight || 1, u.setCircleRadius(t.getCircleRadius()), u;
  }), m = new Map(c.map((t) => [t.id, t]));
  (n = i.layout) == null || n.type;
  const { simulation: o, simulationForces: s } = _.initSimulationForces(i, a), T = [];
  for (const t of f) {
    const u = m.get(t.from.id), e = m.get(t.to.id);
    if (u && e) {
      const y = t.getStyle() ?? {};
      T.push(new b(t.id, u, e, t.getData(), y, t.directed));
    }
  }
  o.nodes(c);
  const d = o.force("link");
  d && d.id((t) => t.id).links(T), (((w = i.layout) == null ? void 0 : w.type) === "tree" || ((D = i.layout) == null ? void 0 : D.type) === "egoTree") && k.registerForcesOnSimulation(
    c,
    T,
    o,
    s,
    i.layout,
    a,
    k
  );
  let p;
  i.warmupTicks === "auto" || i.warmupTicks == null ? p = h : p = i.warmupTicks, p = p - M;
  let r = 0.3;
  o.alphaTarget(r);
  const l = (/* @__PURE__ */ new Date()).getTime();
  for (let t = 0; t < p && !((/* @__PURE__ */ new Date()).getTime() - l > I || (/* @__PURE__ */ new Date()).getTime() - l > i.cooldownTime || E(i, o, r) && (/* @__PURE__ */ new Date()).getTime() - l > i.cooldownTime * 0.15); ++t)
    o.tick();
  r = 0, o.alphaTarget(r), o.alpha(1);
  for (let t = 0; t < M && !(E(i, o, r) && (/* @__PURE__ */ new Date()).getTime() - l > i.cooldownTime * 0.15); ++t)
    o.tick();
  return ((S = i.layout) == null ? void 0 : S.type) === "tree" && k.simulationDone(
    c,
    T,
    o,
    i.layout
  ), {
    nodes: c,
    edges: T
  };
}
function A(g, f, i) {
  return f / i.cooldownTime;
}
function E(g, f, i) {
  return g.d3AlphaMin > 0 && f.alpha() - i < g.d3AlphaMin;
}
export {
  K as runSimulation
};
