/*
  chart-scatter.js — Scatter chart renderer.
  values can be [[x,y], ...] or simple numbers (auto-indexed on X).
*/

import { mk_title, mk_tooltip, mk_legend, mk_grid } from './chart-utils.js';

export function build_option(data, theme) {
    const series = (data.series || []).map((s, i) => {
        const raw = s.values || [];
        const pts = raw.map((v, idx) => Array.isArray(v) ? v : [idx, v]);
        return {
            name:      s.name || ('Series ' + (i + 1)),
            type:      'scatter',
            data:      pts,
            symbolSize: 8,
            itemStyle: { color: theme.palette[i % theme.palette.length], opacity: .8 },
        };
    });

    const has_title  = !!(data.title || data.subtitle);
    const has_legend = data.series && data.series.length > 1;
    const top = has_title ? (has_legend ? 72 : 44) : (has_legend ? 36 : 16);

    return {
        ...mk_title(data, theme),
        ...mk_tooltip(theme),
        ...mk_legend(data, theme),
        grid: { top, right: 24, bottom: 32, left: 48, containLabel: true },
        xAxis: {
            type:      'value',
            name:      (data.meta && data.meta.x_label) || '',
            nameTextStyle: { color: theme.text_muted, fontSize: 11 },
            axisLine:  { lineStyle: { color: theme.border } },
            axisTick:  { show: false },
            axisLabel: { color: theme.text_muted, fontSize: 11 },
            splitLine: { lineStyle: { color: theme.border, type: 'dashed' } },
        },
        yAxis: {
            type:      'value',
            name:      (data.meta && data.meta.y_label) || '',
            nameTextStyle: { color: theme.text_muted, fontSize: 11 },
            axisLine:  { show: false },
            axisTick:  { show: false },
            axisLabel: { color: theme.text_muted, fontSize: 11 },
            splitLine: { lineStyle: { color: theme.border, type: 'dashed' } },
        },
        series,
    };
}
