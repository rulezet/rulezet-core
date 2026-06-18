/*
  chart-heatmap.js — Heatmap renderer.
  series[i].name = Y-label, categories = X-labels, series[i].values = array of numbers.
*/

import { mk_title, mk_tooltip } from './chart-utils.js';

export function build_option(data, theme) {
    const x_cats = data.categories || [];
    const y_cats = (data.series || []).map(s => s.name || '');

    const raw = [];
    (data.series || []).forEach((s, yi) => {
        (s.values || []).forEach((v, xi) => {
            raw.push([xi, yi, v || 0]);
        });
    });

    const all_vals = raw.map(p => p[2]);
    const min_v    = Math.min(...all_vals);
    const max_v    = Math.max(...all_vals);

    return {
        ...mk_title(data, theme),
        ...mk_tooltip(theme),
        grid: {
            top:    data.title ? 48 : 20,
            right:  80,
            bottom: 36,
            left:   16,
            containLabel: true,
        },
        xAxis: {
            type:      'category',
            data:      x_cats,
            axisLine:  { lineStyle: { color: theme.border } },
            axisTick:  { show: false },
            axisLabel: { color: theme.text_muted, fontSize: 11 },
            splitArea: { show: true, areaStyle: { color: ['transparent'] } },
        },
        yAxis: {
            type:      'category',
            data:      y_cats,
            axisLine:  { lineStyle: { color: theme.border } },
            axisTick:  { show: false },
            axisLabel: { color: theme.text_muted, fontSize: 11 },
            splitArea: { show: true, areaStyle: { color: [theme.bg_surface + '80', 'transparent'] } },
        },
        visualMap: {
            min:          min_v,
            max:          max_v,
            calculable:   true,
            orient:       'vertical',
            right:        0,
            top:          'center',
            textStyle:    { color: theme.text_muted, fontSize: 10 },
            inRange: {
                color: [theme.bg_body, theme.brand],
            },
        },
        series: [{
            type:      'heatmap',
            data:      raw,
            label:     { show: false },
            emphasis:  { itemStyle: { shadowBlur: 8, shadowColor: 'rgba(0,0,0,.3)' } },
        }],
    };
}
