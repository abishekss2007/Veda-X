/**
 * AyurCTMS — Clinical Analytics Chart Engine & Precision Tooltip
 * Implements subtle, clinical-grade hover interactions:
 * "Highlight the data being inspected, not the entire visualization."
 * 
 * Line chart: Inspect one point -> point enlarges, subtle guide line appears, compact value bubble attaches.
 * Stacked bar: Inspect one segment -> only that segment highlights, other segments remain stable.
 * Bar chart: Inspect one bar -> only that bar highlights, attached value bubble appears.
 * Donut chart: Inspect one slice -> only that slice highlights, percentage bubble appears.
 */

class ChartTooltip {
  static el = null;

  static init() {
    if (typeof document === 'undefined' || ChartTooltip.el) return;
    let portal = document.getElementById('chart-global-tooltip');
    if (!portal) {
      portal = document.createElement('div');
      portal.id = 'chart-global-tooltip';
      portal.className = 'chart-tooltip-portal';
      document.body.appendChild(portal);
    }
    ChartTooltip.el = portal;
  }

  static show(target, clientX, clientY) {
    ChartTooltip.init();
    if (!ChartTooltip.el || !target) return;

    const title = target.getAttribute('data-tt-title') || '';
    const category = target.getAttribute('data-tt-category') || title;
    const value = target.getAttribute('data-tt-val') || '';
    const unit = target.getAttribute('data-tt-unit') || '';
    const targetVal = target.getAttribute('data-tt-target') || '';
    const sub = target.getAttribute('data-tt-sub') || '';
    const color = target.getAttribute('data-tt-color') || '#059669';

    ChartTooltip.el.innerHTML = `
      <div class="tooltip-bubble">
        <div class="tooltip-cat-row">
          <span class="tooltip-indicator-dot" style="background-color: ${color};"></span>
          <span class="tooltip-cat-name">${category}</span>
        </div>
        <div class="tooltip-val-row">
          <span class="tooltip-val-num">${value}</span>
          ${unit ? `<span class="tooltip-val-unit">${unit}</span>` : ''}
          ${targetVal ? `<span class="tooltip-target-sub">/ Target ${targetVal}</span>` : ''}
        </div>
        ${sub ? `<div class="tooltip-sub-line">${sub}</div>` : ''}
      </div>
      <div class="tooltip-arrow"></div>
    `;

    // Position precisely relative to target element
    const dot = target.querySelector ? target.querySelector('.chart-point-dot') : null;
    const rect = (dot || target).getBoundingClientRect();
    const tooltipWidth = ChartTooltip.el.offsetWidth || 140;
    const tooltipHeight = ChartTooltip.el.offsetHeight || 50;

    const isDonut = target.classList.contains('donut-slice');

    // For points and bars, anchor to element's center. For donut, anchor near mouse or slice center
    let anchorX = (isDonut && clientX !== undefined) ? clientX : (rect.left + rect.width / 2);
    let anchorY = (isDonut && clientY !== undefined) ? clientY : rect.top;

    const scrollX = window.pageXOffset || document.documentElement.scrollLeft || 0;
    const scrollY = window.pageYOffset || document.documentElement.scrollTop || 0;

    const pad = 12;
    const halfW = tooltipWidth / 2;

    // Viewport bounds clamping
    let tooltipX = anchorX;
    if (tooltipX - halfW < pad) {
      tooltipX = pad + halfW;
    } else if (tooltipX + halfW > window.innerWidth - pad) {
      tooltipX = window.innerWidth - pad - halfW;
    }

    // Determine placement: above element by default, flip below if too close to viewport top
    const spaceAbove = anchorY - tooltipHeight - 12;
    let placeBottom = spaceAbove < pad;

    let tooltipY;
    if (placeBottom) {
      const bottomEdge = (isDonut && clientY !== undefined) ? clientY + 14 : rect.bottom + 8;
      tooltipY = bottomEdge;
      ChartTooltip.el.className = 'chart-tooltip-portal placement-bottom is-visible';
    } else {
      tooltipY = anchorY - 8;
      ChartTooltip.el.className = 'chart-tooltip-portal placement-top is-visible';
    }

    ChartTooltip.el.style.left = `${tooltipX + scrollX}px`;
    ChartTooltip.el.style.top = `${tooltipY + scrollY}px`;

    // Adjust arrow to point directly to anchorX
    const arrow = ChartTooltip.el.querySelector('.tooltip-arrow');
    if (arrow) {
      const offsetInBubble = anchorX - (tooltipX - halfW);
      const clampedOffset = Math.max(10, Math.min(tooltipWidth - 10, offsetInBubble));
      arrow.style.left = `${clampedOffset}px`;
    }
  }

  static hide() {
    if (ChartTooltip.el) {
      ChartTooltip.el.classList.remove('is-visible');
    }
  }
}

// Global event delegation for charts hover & touch events
if (typeof document !== 'undefined') {
  let activeElement = null;

  document.addEventListener('mouseover', (e) => {
    const target = e.target.closest('[data-tt-val]');
    if (!target) return;
    activeElement = target;
    ChartTooltip.show(target, e.clientX, e.clientY);
  });

  document.addEventListener('mousemove', (e) => {
    if (!activeElement || !ChartTooltip.el || !ChartTooltip.el.classList.contains('is-visible')) return;
    if (activeElement.classList.contains('donut-slice')) {
      ChartTooltip.show(activeElement, e.clientX, e.clientY);
    }
  });

  document.addEventListener('mouseout', (e) => {
    const target = e.target.closest('[data-tt-val]');
    if (target && target === activeElement) {
      activeElement = null;
      ChartTooltip.hide();
    }
  });

  // Keyboard accessibility: tab focus opens tooltip and highlights element
  document.addEventListener('focusin', (e) => {
    const target = e.target.closest('[data-tt-val]');
    if (!target) return;
    activeElement = target;
    ChartTooltip.show(target);
  });

  document.addEventListener('focusout', (e) => {
    const target = e.target.closest('[data-tt-val]');
    if (target && target === activeElement) {
      activeElement = null;
      ChartTooltip.hide();
    }
  });

  // Touch device support: tap shows attached tooltip, tap outside hides
  document.addEventListener('touchstart', (e) => {
    const target = e.target.closest('[data-tt-val]');
    if (target && e.touches.length > 0) {
      activeElement = target;
      ChartTooltip.show(target, e.touches[0].clientX, e.touches[0].clientY);
    } else {
      activeElement = null;
      ChartTooltip.hide();
    }
  }, { passive: true });
}

class ChartCard {
  /**
   * Renders a chart card into a target DOM container.
   * @param {Object} props
   * @param {string} props.id - Unique DOM id
   * @param {string} props.title - Card title
   * @param {string} props.insight - Plain-language insight line
   * @param {string} props.type - 'line' | 'bar' | 'stacked-bar' | 'donut'
   * @param {Array|Object} props.data - Chart data payload
   * @param {Object} [props.options] - Custom colors, labels, height
   * @param {boolean} [props.loading] - Whether to show loading skeleton
   * @param {boolean} [props.empty] - Whether data is empty
   * @returns {string} HTML string
   */
  static render({ id, title, insight, type, data, options = {}, loading = false, empty = false }) {
    if (loading) {
      return `
        <div class="dash-card chart-card" id="${id}">
          <div class="chart-header">
            <div class="skeleton-line" style="width: 40%; height: 18px; margin-bottom: 8px;"></div>
            <div class="skeleton-line" style="width: 70%; height: 14px;"></div>
          </div>
          <div class="chart-body skeleton-rect" style="height: 220px; border-radius: 8px; margin-top: 14px;"></div>
        </div>
      `;
    }

    if (empty || !data || (Array.isArray(data) && data.length === 0)) {
      return `
        <div class="dash-card chart-card" id="${id}">
          <div class="chart-header">
            <h4 class="chart-title">${title}</h4>
            ${insight ? `<p class="chart-insight">${insight}</p>` : ''}
          </div>
          <div class="chart-empty-state">
            <span class="empty-icon">🌿</span>
            <p>No clinical trial data points available for this period.</p>
          </div>
        </div>
      `;
    }

    let chartSvg = '';
    const h = options.height || 220;
    const w = options.width || 440;

    switch (type) {
      case 'line':
        chartSvg = ChartCard.renderLineChart(data, w, h, options);
        break;
      case 'bar':
        chartSvg = ChartCard.renderBarChart(data, w, h, options);
        break;
      case 'stacked-bar':
        chartSvg = ChartCard.renderStackedBarChart(data, w, h, options);
        break;
      case 'donut':
        chartSvg = ChartCard.renderDonutChart(data, w, h, options);
        break;
      default:
        chartSvg = `<div class="chart-unsupported">Unsupported chart type: ${type}</div>`;
    }

    return `
      <div class="dash-card chart-card" id="${id}" data-chart-type="${type}">
        <div class="chart-header">
          <div class="chart-title-wrap">
            <h4 class="chart-title">${title}</h4>
            ${options.badge ? `<span class="badge ${options.badgeClass || 'badge-secondary'}">${options.badge}</span>` : ''}
          </div>
          ${insight ? `<p class="chart-insight"><span class="insight-bullet">💡</span> ${insight}</p>` : ''}
        </div>
        <div class="chart-body" style="position: relative; width: 100%; min-height: ${h}px;">
          ${chartSvg}
        </div>
      </div>
    `;
  }

  /**
   * Renders Line Chart with soft gridlines, axes, dots, subtle vertical guide lines, and optional target line.
   */
  static renderLineChart(data, width, height, options) {
    const padL = 45, padR = 25, padT = 20, padB = 40;
    const plotW = width - padL - padR;
    const plotH = height - padT - padB;

    const values = data.flatMap(d => [d.value, d.target].filter(v => v !== undefined));
    const maxVal = Math.max(...values, 10) * 1.15;
    const minVal = 0;

    const getX = i => padL + (i / (data.length - 1 || 1)) * plotW;
    const getY = val => padT + plotH - ((val - minVal) / (maxVal - minVal)) * plotH;

    // Grid lines (3 horizontal)
    const gridLines = [0, 0.5, 1].map(r => {
      const y = padT + plotH * (1 - r);
      const val = Math.round(maxVal * r);
      return `
        <line x1="${padL}" y1="${y}" x2="${width - padR}" y2="${y}" stroke="var(--border, #e2e8f0)" stroke-dasharray="3 3" stroke-width="1"/>
        <text class="chart-axis-label-y" x="${padL - 8}" y="${y + 4}">${val}</text>
      `;
    }).join('');

    // Primary Line Points
    const linePoints = data.map((d, i) => `${getX(i)},${getY(d.value)}`).join(' ');

    // Area Path
    const firstX = getX(0), lastX = getX(data.length - 1);
    const bottomY = padT + plotH;
    const areaPath = `M ${firstX},${bottomY} L ${linePoints} L ${lastX},${bottomY} Z`;

    // Target Line Points (if present)
    let targetPath = '';
    if (data.some(d => d.target !== undefined)) {
      const targetPoints = data.map((d, i) => `${getX(i)},${getY(d.target)}`).join(' ');
      targetPath = `<polyline fill="none" stroke="#94a3b8" stroke-width="2" stroke-dasharray="4 4" points="${targetPoints}" />`;
    }

    // Circles, Vertical Guide Lines, and Precision Data Points
    const seriesLabel = options.seriesLabel || 'Actual';
    const dots = data.map((d, i) => {
      const cx = getX(i), cy = getY(d.value);
      const label = d.label || `Point ${i + 1}`;
      const ttText = d.target !== undefined ? `${label}: ${d.value} (Target: ${d.target})` : `${label}: ${d.value}`;
      return `
        <g class="chart-point" tabindex="0"
           data-tt-title="${label}"
           data-tt-category="${seriesLabel}"
           data-tt-val="${d.value}"
           ${d.target !== undefined ? `data-tt-target="${d.target}"` : ''}
           data-tt-unit="subjects"
           data-tt-color="#059669">
          <!-- Subtle vertical guide line for this specific point only -->
          <line class="chart-guide-line" x1="${cx}" y1="${padT}" x2="${cx}" y2="${padT + plotH}" stroke="#94a3b8" stroke-width="1" stroke-dasharray="3 3" opacity="0" pointer-events="none" />
          <!-- Invisible larger hit area for seamless hovering -->
          <circle cx="${cx}" cy="${cy}" r="14" fill="transparent" class="chart-point-hitarea" />
          <!-- Active point dot -->
          <circle class="chart-point-dot" cx="${cx}" cy="${cy}" r="4.5" fill="#059669" stroke="#ffffff" stroke-width="2" />
          <title>${ttText}</title>
          <text class="chart-axis-label-x" x="${cx}" y="${padT + plotH + 18}">${label}</text>
        </g>
      `;
    }).join('');

    const legendHtml = `
      <div class="chart-legend-row">
        <div class="chart-legend-item">
          <span class="legend-dot" style="background-color: #059669;"></span>
          <span class="legend-text">${options.seriesLabel || 'Actual'}</span>
        </div>
        ${data.some(d => d.target !== undefined) ? `
          <div class="chart-legend-item">
            <span class="legend-dot" style="background-color: #94a3b8;"></span>
            <span class="legend-text">Planned Target</span>
          </div>
        ` : ''}
      </div>
    `;

    return `
      <div style="width: 100%;">
        <svg class="recharts-svg-fluid" viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMid meet" style="width: 100%; height: auto; overflow: visible;">
          <defs>
            <linearGradient id="lineGrad-${width}" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color="#10b981" stop-opacity="0.25"/>
              <stop offset="100%" stop-color="#10b981" stop-opacity="0.0"/>
            </linearGradient>
          </defs>
          ${gridLines}
          <path d="${areaPath}" fill="url(#lineGrad-${width})" />
          ${targetPath}
          <polyline fill="none" stroke="#059669" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" points="${linePoints}" />
          ${dots}
        </svg>
        ${legendHtml}
      </div>
    `;
  }

  /**
   * Renders Standard Bar Chart.
   */
  static renderBarChart(data, width, height, options) {
    const padL = 48, padR = 20, padT = 20, padB = 32;
    const plotW = width - padL - padR;
    const plotH = height - padT - padB;

    const maxVal = Math.max(...data.map(d => d.value), 5) * 1.15;
    const barWidth = Math.min(plotW / (data.length * 1.6), 36);
    const step = plotW / (data.length || 1);

    const gridLines = [0, 0.5, 1].map(r => {
      const y = padT + plotH * (1 - r);
      const val = Math.round(maxVal * r);
      return `
        <line x1="${padL}" y1="${y}" x2="${width - padR}" y2="${y}" stroke="var(--border, #e2e8f0)" stroke-dasharray="3 3" stroke-width="1"/>
        <text class="chart-axis-label-y" x="${padL - 10}" y="${y + 4}">${val}</text>
      `;
    }).join('');

    const bars = data.map((d, i) => {
      const barH = (d.value / maxVal) * plotH;
      const x = padL + i * step + (step - barWidth) / 2;
      const y = padT + plotH - barH;
      const color = d.color || options.defaultColor || '#059669';
      const shortLabel = d.label.length > 14 ? d.label.slice(0, 12) + '…' : d.label;
      return `
        <g class="chart-bar">
          <rect class="chart-bar-seg"
                x="${x}" y="${y}" width="${barWidth}" height="${barH}" rx="4"
                fill="${color}" opacity="0.92" tabindex="0"
                data-tt-title="${d.label}"
                data-tt-category="${d.label}"
                data-tt-val="${d.value}"
                ${d.sublabel ? `data-tt-sub="${d.sublabel}"` : ''}
                data-tt-color="${color}">
            <title>${d.label}: ${d.value} ${d.sublabel ? `(${d.sublabel})` : ''}</title>
          </rect>
          <text class="chart-bar-val" x="${x + barWidth / 2}" y="${y - 6}" font-size="10" font-weight="600" fill="var(--text-main, #0f172a)" text-anchor="middle">${d.value}</text>
          <text class="chart-axis-label-x" x="${x + barWidth / 2}" y="${padT + plotH + 18}">${shortLabel}</text>
        </g>
      `;
    }).join('');

    return `
      <div style="width: 100%;">
        <svg class="recharts-svg-fluid" viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMid meet" style="width: 100%; height: auto; overflow: visible;">
          ${gridLines}
          ${bars}
        </svg>
      </div>
    `;
  }

  /**
   * Renders Stacked Bar Chart (e.g. AEs by severity: Mild, Moderate, Severe).
   * Hovering one segment highlights ONLY that segment; all other segments remain stable.
   */
  static renderStackedBarChart(data, width, height, options) {
    const padL = 48, padR = 20, padT = 20, padB = 32;
    const plotW = width - padL - padR;
    const plotH = height - padT - padB;

    const stackKeys = options.keys || [
      { key: 'mild', label: 'Mild', color: '#10b981' },
      { key: 'moderate', label: 'Moderate', color: '#f59e0b' },
      { key: 'severe', label: 'Severe (SAE)', color: '#ef4444' }
    ];

    const totals = data.map(d => stackKeys.reduce((acc, k) => acc + (d[k.key] || 0), 0));
    const maxVal = Math.max(...totals, 5) * 1.15;
    const barWidth = Math.min(plotW / (data.length * 1.6), 36);
    const step = plotW / (data.length || 1);

    const gridLines = [0, 0.5, 1].map(r => {
      const y = padT + plotH * (1 - r);
      const val = Math.round(maxVal * r);
      return `
        <line x1="${padL}" y1="${y}" x2="${width - padR}" y2="${y}" stroke="var(--border, #e2e8f0)" stroke-dasharray="3 3" stroke-width="1"/>
        <text class="chart-axis-label-y" x="${padL - 10}" y="${y + 4}">${val}</text>
      `;
    }).join('');

    // Stacked segments
    const bars = data.map((d, i) => {
      const x = padL + i * step + (step - barWidth) / 2;
      let curY = padT + plotH;
      const segments = stackKeys.map(k => {
        const val = d[k.key] || 0;
        const segH = (val / maxVal) * plotH;
        curY -= segH;
        if (segH <= 0) return '';
        return `
          <rect class="chart-stack-seg"
                x="${x}" y="${curY}" width="${barWidth}" height="${segH}"
                fill="${k.color}" rx="2" tabindex="0"
                data-tt-title="${d.label}"
                data-tt-category="${d.label} • ${k.label}"
                data-tt-val="${val}"
                data-tt-unit="events"
                data-tt-color="${k.color}">
            <title>${d.label} • ${k.label}: ${val}</title>
          </rect>
        `;
      }).join('');

      const totalVal = totals[i];
      const shortLabel = d.label.length > 14 ? d.label.slice(0, 12) + '…' : d.label;
      return `
        <g class="chart-stack-group">
          ${segments}
          <text class="chart-bar-val" x="${x + barWidth / 2}" y="${curY - 6}" font-size="10" font-weight="600" fill="var(--text-main, #0f172a)" text-anchor="middle">${totalVal}</text>
          <text class="chart-axis-label-x" x="${x + barWidth / 2}" y="${padT + plotH + 18}">${shortLabel}</text>
        </g>
      `;
    }).join('');

    // Centered horizontal legend row below chart with 10px round dots and 16px gap
    const legendHtml = `
      <div class="chart-legend-row">
        ${stackKeys.map(k => `
          <div class="chart-legend-item">
            <span class="legend-dot" style="background-color: ${k.color};"></span>
            <span class="legend-text">${k.label}</span>
          </div>
        `).join('')}
      </div>
    `;

    return `
      <div style="width: 100%;">
        <svg class="recharts-svg-fluid" viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMid meet" style="width: 100%; height: auto; overflow: visible;">
          ${gridLines}
          ${bars}
        </svg>
        ${legendHtml}
      </div>
    `;
  }

  /**
   * Renders Donut Chart with center total and centered bottom legend.
   */
  static renderDonutChart(data, width, height, options) {
    const cx = width * 0.5;
    const cy = height * 0.48;
    const r = Math.min(width, height) * 0.40;
    const innerR = r * 0.65;

    const total = data.reduce((acc, d) => acc + (d.value || 0), 0);
    let cumulativeAngle = -Math.PI / 2;

    const slices = data.map((d, i) => {
      const sliceAngle = total > 0 ? (d.value / total) * 2 * Math.PI : 0;
      const startAngle = cumulativeAngle;
      const endAngle = cumulativeAngle + sliceAngle;
      cumulativeAngle += sliceAngle;

      const x1 = cx + r * Math.cos(startAngle);
      const y1 = cy + r * Math.sin(startAngle);
      const x2 = cx + r * Math.cos(endAngle);
      const y2 = cy + r * Math.sin(endAngle);

      const ix1 = cx + innerR * Math.cos(endAngle);
      const iy1 = cy + innerR * Math.sin(endAngle);
      const ix2 = cx + innerR * Math.cos(startAngle);
      const iy2 = cy + innerR * Math.sin(startAngle);

      const largeArc = sliceAngle > Math.PI ? 1 : 0;
      const pathData = `
        M ${x1} ${y1}
        A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2}
        L ${ix1} ${iy1}
        A ${innerR} ${innerR} 0 ${largeArc} 0 ${ix2} ${iy2}
        Z
      `;

      const pct = total > 0 ? Math.round((d.value / total) * 100) : 0;
      return `
        <path d="${pathData}" fill="${d.color}" class="donut-slice" tabindex="0"
              data-tt-title="${d.label}"
              data-tt-category="${d.label}"
              data-tt-val="${d.value}"
              data-tt-unit="(${pct}%)"
              data-tt-color="${d.color}">
          <title>${d.label}: ${d.value} (${pct}%)</title>
        </path>
      `;
    }).join('');

    // Centered horizontal legend row below chart with 10px round dots and 16px gap
    const legendHtml = `
      <div class="chart-legend-row">
        ${data.map(d => `
          <div class="chart-legend-item">
            <span class="legend-dot" style="background-color: ${d.color};"></span>
            <span class="legend-text">${d.label}</span>
          </div>
        `).join('')}
      </div>
    `;

    return `
      <div style="width: 100%;">
        <svg class="recharts-svg-fluid" viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMid meet" style="width: 100%; height: auto; overflow: visible;">
          <g class="donut-slices">${slices}</g>
          <circle cx="${cx}" cy="${cy}" r="${innerR - 1}" fill="var(--card-bg, #ffffff)"/>
          <text class="donut-center-total" x="${cx}" y="${cy - 3}" font-size="20" font-weight="700" fill="var(--text-main, #0f172a)" text-anchor="middle">${total}</text>
          <text class="donut-center-sub" x="${cx}" y="${cy + 14}" font-size="9" font-weight="600" fill="var(--text-dim, #64748b)" text-anchor="middle">TOTAL</text>
        </svg>
        ${legendHtml}
      </div>
    `;
  }
}

// Attach globally for browser usage
if (typeof window !== 'undefined') {
  window.ChartCard = ChartCard;
}
