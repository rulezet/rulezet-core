/*
  chart-bar-h.js — Horizontal bar chart renderer.
*/

import { mk_title, mk_tooltip, mk_legend, mk_grid } from './chart-utils.js';

export function build_option(data, theme) {
    const series = (data.series || []).map((s, i) => ({
        name:      s.name || ('Series ' + (i + 1)),
        type:      'bar',
        data:      s.values || [],
        barMaxWidth: 36,
        itemStyle: {
            color:        theme.palette[i % theme.palette.length],
            borderRadius: [0, 4, 4, 0],
        },
    }));

    const has_title  = !!(data.title || data.subtitle);
    const has_legend = data.series && data.series.length > 1;
    const top = has_title ? (has_legend ? 72 : 44) : (has_legend ? 36 : 16);

    return {
        ...mk_title(data, theme),
        ...mk_tooltip(theme),
        ...mk_legend(data, theme),
        grid: { top, right: 24, bottom: 16, left: 16, containLabel: true },
        xAxis: {
            type:      'value',
            axisLine:  { show: false },
            axisTick:  { show: false },
            axisLabel: { color: theme.text_muted, fontSize: 11 },
            splitLine: { lineStyle: { color: theme.border, type: 'dashed' } },
        },
        yAxis: {
            type:      'category',
            data:      data.categories || [],
            axisLine:  { lineStyle: { color: theme.border } },
            axisTick:  { show: false },
            axisLabel: { color: theme.text_muted, fontSize: 11 },
            splitLine: { show: false },
        },
        series,
    };
}
