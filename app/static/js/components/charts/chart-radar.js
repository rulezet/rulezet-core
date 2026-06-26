/*
  chart-radar.js — Radar / spider chart renderer.
  categories = axis names, series[i].values = polygon per serie.
*/

import { mk_title, mk_tooltip_item, mk_legend } from './chart-utils.js';

export function build_option(data, theme) {
    const cats = data.categories || [];
    const indicator = cats.map(c => ({ name: c, color: theme.text_muted }));

    const series_data = (data.series || []).map((s, i) => ({
        name:  s.name || ('Series ' + (i + 1)),
        value: s.values || [],
        areaStyle: { color: theme.palette[i % theme.palette.length] + '40' },
        lineStyle: { color: theme.palette[i % theme.palette.length], width: 2 },
        itemStyle: { color: theme.palette[i % theme.palette.length] },
    }));

    return {
        ...mk_title(data, theme),
        ...mk_tooltip_item(theme),
        ...mk_legend(data, theme),
        radar: {
            indicator,
            shape:      'polygon',
            splitNumber: 4,
            axisName:    { color: theme.text_muted, fontSize: 11 },
            splitLine:   { lineStyle: { color: theme.border } },
            splitArea:   { areaStyle: { color: ['transparent'] } },
            axisLine:    { lineStyle: { color: theme.border } },
        },
        series: [{
            type: 'radar',
            data: series_data,
        }],
    };
}
