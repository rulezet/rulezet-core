/*
  chart-utils.js — Shared helpers for all ECharts renderers.
  Reads CSS vars so colors always match the active theme.
*/

export function get_theme() {
    const s = getComputedStyle(document.documentElement);
    const g = k => s.getPropertyValue(k).trim();
    const is_dark = document.documentElement.getAttribute('data-bs-theme') === 'dark';
    return {
        text_main:  g('--text-main')  || (is_dark ? '#F2EFEA' : '#1A1714'),
        text_muted: g('--text-muted') || (is_dark ? '#6B6663' : '#9A9390'),
        bg_surface: g('--bg-surface') || (is_dark ? '#242129' : '#FFFFFF'),
        bg_body:    g('--bg-body')    || (is_dark ? '#1A171D' : '#F5F1EC'),
        border:     g('--border')     || (is_dark ? 'rgba(255,255,255,.1)' : 'rgba(0,0,0,.1)'),
        brand:      g('--brand')      || '#D4522A',
        is_dark,
        palette: [
            '#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de',
            '#3ba272', '#fc8452', '#9a60b4', '#ea7ccc', '#D4522A',
        ],
    };
}

export function mk_title(data, theme) {
    if (!data.title && !data.subtitle) return {};
    return {
        title: {
            text:        data.title    || '',
            subtext:     data.subtitle || '',
            textStyle:   { color: theme.text_main,  fontSize: 14, fontWeight: 600 },
            subtextStyle:{ color: theme.text_muted, fontSize: 12 },
            left: 'left',
            top: 4,
        },
    };
}

export function mk_tooltip(theme) {
    return {
        tooltip: {
            trigger: 'axis',
            backgroundColor: theme.bg_surface,
            borderColor:     theme.border,
            borderWidth:     1,
            textStyle:       { color: theme.text_main, fontSize: 12 },
            axisPointer:     { lineStyle: { color: theme.border } },
        },
    };
}

export function mk_tooltip_item(theme) {
    return {
        tooltip: {
            trigger: 'item',
            backgroundColor: theme.bg_surface,
            borderColor:     theme.border,
            borderWidth:     1,
            textStyle:       { color: theme.text_main, fontSize: 12 },
        },
    };
}

export function mk_legend(data, theme) {
    if (!data.series || data.series.length <= 1) return {};
    return {
        legend: {
            data:      data.series.map(s => s.name),
            textStyle: { color: theme.text_muted, fontSize: 11 },
            top:       data.title ? 36 : 8,
            left:      'center',
            icon:      'circle',
            itemWidth:  8,
            itemHeight: 8,
            itemGap:   14,
        },
    };
}

export function mk_grid(data) {
    const has_title  = !!(data.title || data.subtitle);
    const has_legend = data.series && data.series.length > 1;
    const top = has_title ? (has_legend ? 72 : 44) : (has_legend ? 36 : 16);
    return {
        grid: { top, right: 16, bottom: 32, left: 48, containLabel: true },
    };
}

export function mk_x_axis(data, theme) {
    return {
        xAxis: {
            type:        'category',
            data:        data.categories || [],
            name:        (data.meta && data.meta.x_label) || '',
            nameTextStyle:{ color: theme.text_muted, fontSize: 11 },
            axisLine:    { lineStyle: { color: theme.border } },
            axisTick:    { show: false },
            axisLabel:   { color: theme.text_muted, fontSize: 11 },
            splitLine:   { show: false },
        },
    };
}

export function mk_y_axis(data, theme) {
    const unit = (data.meta && data.meta.unit) || '';
    return {
        yAxis: {
            type:    'value',
            name:    (data.meta && data.meta.y_label) || '',
            nameTextStyle:{ color: theme.text_muted, fontSize: 11 },
            axisLine:    { show: false },
            axisTick:    { show: false },
            axisLabel:   {
                color:     theme.text_muted,
                fontSize:  11,
                formatter: v => unit ? v + unit : v,
            },
            splitLine:   { lineStyle: { color: theme.border, type: 'dashed' } },
        },
    };
}

export function mk_series_colors(series, palette) {
    return series.map((s, i) => ({
        ...s,
        _color: palette[i % palette.length],
    }));
}
