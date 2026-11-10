/**
 * rulesGrowthChart.js — the story page's "Rules added on Rulezet since its creation" chart
 * (macros/history_logo.html), drawn with ECharts (window.echarts): a smooth curve that draws itself,
 * key moments popping up on it one after the other, their story on hover.
 *
 *   <rules-growth-chart :data="info" view="total|added" />
 *   data = /history_logo/rules_growth → { labels, total, added, events: [{ index, label, text }] }
 */
const { ref, watch, onMounted, onBeforeUnmount, nextTick } = Vue

const BLUE = '#0d6efd'
const css = name => getComputedStyle(document.documentElement).getPropertyValue(name).trim()

function option(data, view) {
    const values = view === 'total' ? data.total : data.added
    const text = css('--subtle-text-color') || '#6c757d'
    const grid = css('--border-color') || '#e5e7eb'
    const events = (data.events || []).map((e, i) => ({
        name: e.label, coord: [e.index, values[e.index]], value: e.label, story: e.text,
        symbolSize: 1, label: { show: true },
        itemStyle: { color: BLUE }, _i: i,
    }))
    return {
        animationDuration: 2600,
        animationEasing: 'cubicOut',
        grid: { left: 12, right: 24, top: 78, bottom: 8, containLabel: true },
        tooltip: {
            trigger: 'axis', backgroundColor: 'rgba(11,18,32,.92)', borderWidth: 0, textStyle: { color: '#fff' },
            formatter: params => {
                const p = params[0]
                const ev = (data.events || []).find(e => e.index === p.dataIndex)
                const n = p.value.toLocaleString('en-US')
                return `<b>${p.axisValue}</b><br>${view === 'total' ? 'Rules on Rulezet' : 'Rules added'}: <b>${n}</b>`
                    + (ev ? `<br><span style="color:#8fb8ff">★ ${ev.label}</span><br><span style="opacity:.8">${ev.text}</span>` : '')
            },
        },
        xAxis: {
            type: 'category', data: data.labels, boundaryGap: view !== 'total',
            axisLine: { lineStyle: { color: grid } }, axisTick: { show: false },
            axisLabel: { color: text, fontSize: 11, hideOverlap: true },
        },
        yAxis: {
            type: 'value', splitLine: { lineStyle: { color: grid, type: 'dashed' } },
            axisLabel: { color: text, fontSize: 11, formatter: v => v >= 1000 ? `${Math.round(v / 1000)}k` : v },
        },
        series: [view === 'total' ? {
            type: 'line', data: values, smooth: .45, symbol: 'circle', symbolSize: 6, showSymbol: false,
            lineStyle: { width: 3, color: BLUE, shadowColor: 'rgba(13,110,253,.35)', shadowBlur: 12 },
            itemStyle: { color: BLUE },
            areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: 'rgba(13,110,253,.35)' }, { offset: 1, color: 'rgba(13,110,253,0)' }]) },
            emphasis: { focus: 'series' },
            // pins with the event's name above, one name in two higher so neighbours never overlap
            // (no automatic label hiding: that is what made names blink during the animation)
            markPoint: {
                symbol: 'pin', symbolSize: 40, animationDuration: 500,
                animationDelay: i => 1500 + i * 220,
                labelLayout: { hideOverlap: false, moveOverlap: null },
                itemStyle: { color: BLUE, shadowColor: 'rgba(13,110,253,.45)', shadowBlur: 8 },
                data: events.map((e, i) => ({
                    coord: e.coord, name: e.name,
                    label: {
                        show: true, formatter: '{b}', position: 'top', distance: i % 2 ? 30 : 6,
                        color: text, fontSize: 11, fontWeight: 600,
                        backgroundColor: css('--card-bg-color') || '#fff', borderColor: 'rgba(13,110,253,.35)', borderWidth: 1,
                        borderRadius: 999, padding: [3, 8],
                    },
                })),
            },
            markLine: {
                symbol: 'none', silent: true, animation: false,
                lineStyle: { color: 'rgba(13,110,253,.25)', type: 'dashed' },
                label: { show: false },
                data: events.map(e => ({ xAxis: e.coord[0] })),
            },
        } : {
            type: 'bar', data: values, barMaxWidth: 26,
            itemStyle: {
                borderRadius: [6, 6, 0, 0],
                color: p => (data.events || []).some(e => e.index === p.dataIndex) ? BLUE : 'rgba(13,110,253,.45)',
            },
            animationDelay: i => i * 70,
            markPoint: {
                symbol: 'pin', symbolSize: 40, animationDelay: i => 900 + i * 200,
                label: { color: '#fff', fontSize: 9, formatter: '★' }, itemStyle: { color: BLUE },
                data: events.map(e => ({ coord: e.coord, name: e.name })),
            },
        }],
    }
}

export default {
    name: 'RulesGrowthChart',
    props: { data: { type: Object, required: true }, view: { type: String, default: 'total' } },
    template: `<div ref="el" style="width:100%;height:340px;"></div>`,
    setup(props) {
        const el = ref(null)
        let chart = null, observer = null
        const draw = () => { if (chart) { chart.clear(); chart.setOption(option(props.data, props.view)) } }
        onMounted(async () => {
            await nextTick()
            if (!window.echarts) return
            chart = echarts.init(el.value, null, { renderer: 'canvas' })
            // draw when the chart scrolls into view, so the animation is seen
            observer = new IntersectionObserver(entries => {
                if (entries.some(e => e.isIntersecting)) { draw(); observer.disconnect() }
            }, { threshold: .3 })
            observer.observe(el.value)
            window.addEventListener('resize', onResize)
        })
        const onResize = () => chart?.resize()
        watch(() => props.view, draw)
        onBeforeUnmount(() => { observer?.disconnect(); window.removeEventListener('resize', onResize); chart?.dispose() })
        return { el }
    },
}
