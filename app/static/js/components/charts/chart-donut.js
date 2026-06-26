/*
  chart-donut.js — Donut (pie with hole) chart renderer.
*/

import { mk_title, mk_tooltip_item } from './chart-utils.js';

export function build_option(data, theme) {
    const s     = (data.series && data.series[0]) || {};
    const cats  = data.categories || [];
    const vals  = s.values || [];
    const items = cats.map((c, i) => ({
        name:      c,
        value:     vals[i] || 0,
        itemStyle: { color: theme.palette[i % theme.palette.length] },
    }));

    return {
        ...mk_title(data, theme),
        ...mk_tooltip_item(theme),
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
            name:   s.name || 'Value',
            type:   'pie',
            radius: ['42%', '68%'],
            center: ['50%', '58%'],
            data:   items,
            label: {
                color:     theme.text_muted,
                fontSize:  11,
                formatter: '{b}\n{d}%',
            },
            labelLine: { lineStyle: { color: theme.border } },
            emphasis: {
                itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,.25)' },
            },
        }],
    };
}
