/*
  chart-treemap.js — Treemap renderer.
  categories = cell names, series[0].values = cell sizes.
*/

import { mk_title, mk_tooltip_item } from './chart-utils.js';

export function build_option(data, theme) {
    const s    = (data.series && data.series[0]) || {};
    const cats = data.categories || [];
    const vals = s.values || [];

    const items = cats.map((c, i) => ({
        name:      c,
        value:     vals[i] || 0,
        itemStyle: { color: theme.palette[i % theme.palette.length] },
    }));

    return {
        ...mk_title(data, theme),
        ...mk_tooltip_item(theme),
        series: [{
            type:             'treemap',
            top:              data.title ? 44 : 16,
            bottom:           8,
            left:             8,
            right:            8,
            visibleMin:       0,
            data:             items,
            roam:             false,
            nodeClick:        false,
            breadcrumb:       { show: false },
            label: {
                show:      true,
                formatter: '{b}\n{c}',
                color:     '#fff',
                fontSize:  11,
            },
            itemStyle: {
                borderColor:  theme.bg_surface,
                borderWidth:  3,
                gapWidth:     3,
            },
        }],
    };
}
