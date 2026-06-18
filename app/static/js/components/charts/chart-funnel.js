/*
  chart-funnel.js — Funnel chart renderer.
  Uses first series. categories = stage names, values = sizes (sorted desc).
*/

import { mk_title, mk_tooltip_item } from './chart-utils.js';

export function build_option(data, theme) {
    const s    = (data.series && data.series[0]) || {};
    const cats = data.categories || [];
    const vals = s.values || [];

    const items = cats
        .map((c, i) => ({ name: c, value: vals[i] || 0 }))
        .sort((a, b) => b.value - a.value)
        .map((item, i) => ({
            ...item,
            itemStyle: { color: theme.palette[i % theme.palette.length] },
        }));

    return {
        ...mk_title(data, theme),
        ...mk_tooltip_item(theme),
        series: [{
            name:      s.name || 'Funnel',
            type:      'funnel',
            top:       data.title ? 44 : 16,
            bottom:    16,
            left:      '10%',
            width:     '80%',
            sort:      'descending',
            data:      items,
            label: {
                color:    theme.text_main,
                fontSize: 12,
            },
            labelLine: { lineStyle: { color: theme.border } },
            itemStyle: { borderColor: theme.bg_surface, borderWidth: 2 },
        }],
    };
}
