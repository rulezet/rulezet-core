/*
  chart-area.js — Area (filled line) chart renderer.
*/

import { mk_title, mk_tooltip, mk_legend, mk_grid, mk_x_axis, mk_y_axis } from './chart-utils.js';

export function build_option(data, theme) {
    const series = (data.series || []).map((s, i) => {
        const color = theme.palette[i % theme.palette.length];
        return {
            name:      s.name || ('Series ' + (i + 1)),
            type:      'line',
            data:      s.values || [],
            smooth:    true,
            symbol:    'circle',
            symbolSize: 4,
            lineStyle: { width: 2, color },
            itemStyle: { color },
            areaStyle: {
                color: {
                    type:       'linear',
                    x: 0, y: 0, x2: 0, y2: 1,
                    colorStops: [
                        { offset: 0,   color: color + 'CC' },
                        { offset: 1,   color: color + '0A' },
                    ],
                },
            },
        };
    });

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
