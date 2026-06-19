/*
  chart-utils.js — Shared helpers for all ECharts renderers.
  Reads CSS vars so colors always match the active theme.
*/

export function get_theme() {
    const s = getComputedStyle(document.documentElement);
    const g = k => s.getPropertyValue(k).trim();
    const is_dark = document.documentElement.classList.contains('dark-mode');
    return {
        text_main:  g('--text-color')        || (is_dark ? '#e2e8f0' : '#1e1e1e'),
        text_muted: g('--subtle-text-color') || (is_dark ? '#94a3b8' : '#6c757d'),
        bg_surface: g('--card-bg-color')     || (is_dark ? '#1e2433' : '#ffffff'),
        bg_body:    g('--light-bg-color')    || (is_dark ? '#151922' : '#f8f9fa'),
        border:     g('--border-color')      || (is_dark ? 'rgba(255,255,255,.1)' : 'rgba(0,0,0,.1)'),
        brand:      '#0d6efd',
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
