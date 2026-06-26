/*
  chart-line.js — Line chart renderer.
  Uses universal JSON format: { categories, series: [{name, values}], meta, title, subtitle }
*/

import { mk_title, mk_tooltip, mk_legend, mk_grid, mk_x_axis, mk_y_axis } from './chart-utils.js';

export function build_option(data, theme) {
    const series = (data.series || []).map((s, i) => ({
        name:      s.name || ('Series ' + (i + 1)),
        type:      'line',
        data:      s.values || [],
        smooth:    true,
        symbol:    'circle',
        symbolSize: 5,
        lineStyle: { width: 2, color: theme.palette[i % theme.palette.length] },
        itemStyle: { color: theme.palette[i % theme.palette.length] },
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
