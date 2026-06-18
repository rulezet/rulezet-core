/*
  chart-bar.js — Vertical bar chart renderer.
*/

import { mk_title, mk_tooltip, mk_legend, mk_grid, mk_x_axis, mk_y_axis } from './chart-utils.js';

export function build_option(data, theme) {
    const series = (data.series || []).map((s, i) => ({
        name:      s.name || ('Series ' + (i + 1)),
        type:      'bar',
        data:      s.values || [],
        barMaxWidth: 48,
        itemStyle: {
            color:        theme.palette[i % theme.palette.length],
            borderRadius: [4, 4, 0, 0],
        },
    }));

    return {
        ...mk_title(data, theme),
        ...mk_tooltip(theme),
        ...mk_legend(data, theme),
        ...mk_grid(data),
        ...mk_x_axis(data, theme),
        ...mk_y_axis(data, theme),
        series,
    };
}
