/*
  chart-pie.js — Pie chart renderer.
  Uses first series only. categories = labels, values = sizes.
*/

import { mk_title, mk_tooltip_item, mk_legend } from './chart-utils.js';

export function build_option(data, theme) {
    const s      = (data.series && data.series[0]) || {};
    const cats   = data.categories || [];
    const vals   = s.values || [];
    const items  = cats.map((c, i) => ({
        name:       c,
        value:      vals[i] || 0,
        itemStyle:  { color: theme.palette[i % theme.palette.length] },
    }));

    return {
        ...mk_title(data, theme),
        ...mk_tooltip_item(theme),
        ...mk_legend({ series: [{ name: data.title || '' }, ...cats.map(c => ({ name: c })) ] }, theme),
        legend: {
            data:      cats,
            textStyle: { color: theme.text_muted, fontSize: 11 },
            top:       data.title ? 36 : 8,
            left:      'center',
            icon:      'circle',
            itemWidth:  8,
            itemHeight: 8,
            itemGap:   14,
        },
        series: [{
            name:         s.name || 'Value',
            type:         'pie',
            radius:       ['0%', '65%'],
            center:       ['50%', '58%'],
            data:         items,
            label: {
                color:    theme.text_main,
                fontSize: 11,
            },
            labelLine:    { lineStyle: { color: theme.border } },
            emphasis: {
                itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,.25)' },
            },
        }],
    };
}
