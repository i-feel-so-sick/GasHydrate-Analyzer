import { memo, useMemo } from "react";
import Plot from "react-plotly.js";
import type { ChartSpec } from "../lib/types";
import { plotlyThemes, type Theme } from "../lib/theme";

type Props = {
  chart: ChartSpec;
  theme: Theme;
};

const plotConfig = {
  responsive: true,
  scrollZoom: true,
  displaylogo: false,
  doubleClick: "reset+autosize" as const,
  modeBarButtonsToRemove: ["select2d", "lasso2d", "autoScale2d"] as any,
  toImageButtonOptions: {
    format: "png" as const,
    filename: "thermoviz-chart",
    scale: 2,
  },
};

/** Merge server layout with current theme tokens. */
function buildThemedLayout(chart: ChartSpec, theme: Theme): Record<string, any> {
  const tokens = plotlyThemes[theme];
  const serverLayout = chart.layout ?? {};
  const { title: _ignored, ...restLayout } = serverLayout;

  const shapes = (restLayout.shapes ?? []).map((shape: any) => {
    const isDotted = shape?.line?.dash === "dot";
    return isDotted
      ? { ...shape, line: { ...shape.line, color: tokens.injectionLine } }
      : shape;
  });

  return {
    ...restLayout,
    paper_bgcolor: tokens.paper,
    plot_bgcolor: tokens.plot,
    font: { color: tokens.textMuted, family: "Inter, system-ui, sans-serif", size: 12 },
    hovermode: "x unified",
    dragmode: "pan",
    margin: { t: 24, r: 24, b: 52, l: 64 },
    hoverlabel: {
      bgcolor: tokens.hoverBg,
      bordercolor: tokens.hoverBorder,
      font: { color: tokens.hoverText, family: "Inter, system-ui, sans-serif", size: 12 },
    },
    xaxis: {
      ...(restLayout.xaxis ?? {}),
      gridcolor: tokens.grid,
      linecolor: tokens.axis,
      tickcolor: tokens.axis,
      zerolinecolor: tokens.axis,
      color: tokens.textMuted,
      title: {
        ...(restLayout.xaxis?.title ?? {}),
        font: { color: tokens.textMuted, size: 12 },
      },
      showspikes: true,
      spikemode: "across",
      spikecolor: tokens.spike,
      spikethickness: 1,
      spikedash: "dot",
    },
    yaxis: {
      ...(restLayout.yaxis ?? {}),
      gridcolor: tokens.grid,
      linecolor: tokens.axis,
      tickcolor: tokens.axis,
      zerolinecolor: tokens.axis,
      color: tokens.textMuted,
      title: {
        ...(restLayout.yaxis?.title ?? {}),
        font: { color: tokens.textMuted, size: 12 },
      },
    },
    legend: {
      ...(restLayout.legend ?? {}),
      bgcolor: tokens.legendBg,
      bordercolor: tokens.legendBorder,
      borderwidth: 1,
      font: { color: tokens.text, size: 11 },
    },
    shapes,
    autosize: true,
  };
}

/** Apply theme colours to each trace. */
function buildThemedTraces(chart: ChartSpec, theme: Theme): any[] {
  const tokens = plotlyThemes[theme];

  return chart.traces.map((trace, index) => {
    const t: any = { ...trace };
    const paletteColor = tokens.palette[index % tokens.palette.length];
    let effectiveColor = paletteColor;

    if (chart.id === "pressure" && trace.mode?.includes("markers") && !trace.mode?.includes("lines")) {
      t.marker = {
        ...t.marker,
        color: tokens.injectionMarker,
        line: { ...t.marker?.line, color: tokens.injectionMarkerEdge, width: 1.5 },
      };
      return t;
    }

    if (chart.id === "pressure") {
      effectiveColor = tokens.accumulationLine;
    } else if (chart.id === "accumulation") {
      effectiveColor = tokens.accumulationLine;
      t.fillcolor = tokens.accumulationFill;
    } else if (chart.id === "saturation") {
      const isRef = trace.line?.dash === "dash";
      effectiveColor = isRef ? tokens.saturationRef : tokens.saturationLine;
      if (!isRef) t.fillcolor = tokens.saturationFill;
    }

    if (t.line || trace.mode?.includes("lines") || !trace.mode) {
      t.line = { ...t.line, color: effectiveColor };
    }
    if (trace.mode?.includes("markers") && t.marker) {
      t.marker = { ...t.marker, color: effectiveColor };
    }

    return t;
  });
}

function ChartPanelImpl({ chart, theme }: Props) {
  const layout = useMemo(() => buildThemedLayout(chart, theme), [chart, theme]);
  const traces = useMemo(() => buildThemedTraces(chart, theme), [chart, theme]);

  return (
    <div className="chart-panel">
      <div className="chart-panel__inner">
        <Plot
          data={traces}
          layout={layout}
          config={plotConfig}
          style={{ width: "100%", height: "100%" }}
          useResizeHandler
        />
      </div>
    </div>
  );
}

export const ChartPanel = memo(ChartPanelImpl);
