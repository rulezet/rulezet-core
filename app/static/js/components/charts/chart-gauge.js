/*
  chart-gauge.js — Gauge chart renderer.
  Uses first value of first series (0-100 range).
*/

import { mk_title } from './chart-utils.js';

export function build_option(data, theme) {
    const s   = (data.series && data.series[0]) || {};
    const val = (s.values && s.values[0]) || 0;
    const unit = (data.meta && data.meta.unit) || '';

    return {
        ...mk_title(data, theme),
        series: [{
            type:     'gauge',
            center:   ['50%', '58%'],
            radius:   '72%',
            startAngle: 210,
            endAngle:   -30,
            min: 0,
            max: 100,
            splitNumber: 10,
            axisLine: {
                lineStyle: {
                    width: 12,
                    color: [
                        [val / 100, theme.brand],
                        [1,         theme.border],
                    ],
                },
            },
            pointer: {
                itemStyle: { color: theme.brand },
                length: '70%',
                width:   6,
            },
            axisTick: {
                distance: -18,
                length:    6,
                lineStyle: { color: theme.text_muted, width: 1 },
            },
            splitLine: {
                distance: -22,
                length:    12,
                lineStyle: { color: theme.text_muted, width: 2 },
            },
            axisLabel: {
                distance: 6,
                color:    theme.text_muted,
                fontSize: 10,
            },
            detail: {
                valueAnimation: true,
                formatter:      v => v + (unit ? ' ' + unit : ''),
                color:          theme.text_main,
                fontSize:       22,
                fontWeight:     700,
                offsetCenter:   [0, '30%'],
            },
            data: [{ value: val, name: s.name || '' }],
            title: {
                color:    theme.text_muted,
                fontSize: 12,
                offsetCenter: [0, '55%'],
            },
        }],
    };
}
