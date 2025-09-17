'use client';

import React, { useEffect, useRef } from 'react';
import {
  createChart,
  type IChartApi,
  type ISeriesApi,
  type LineData,
  type Time,
  type LineSeriesPartialOptions,
} from 'lightweight-charts';
import { useGWVReplay } from '@/hooks/useGWVReplay';

type TracePoint = {
  timestamp: number | string;
  collapse: number;
  decoherence: number;
};

export function WaveScopePanel({ containerId }: { containerId: string }) {
  const { traceData, isLoading } = useGWVReplay(containerId);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const collapseSeriesRef = useRef<ISeriesApi<'Line'> | null>(null);
  const decoSeriesRef = useRef<ISeriesApi<'Line'> | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { color: 'transparent' },
        textColor: '#ffffff',
      },
      rightPriceScale: { borderVisible: false },
      timeScale: {
        borderVisible: false,
        timeVisible: true,
        secondsVisible: true,
      },
      grid: {
        vertLines: { color: 'rgba(255,255,255,0.06)' },
        horzLines: { color: 'rgba(255,255,255,0.06)' },
      },
    });

    // Size to container immediately
    const { clientWidth, clientHeight } = containerRef.current;
    chart.applyOptions({ width: clientWidth, height: clientHeight });

    const collapseOptions: LineSeriesPartialOptions = {
      color: '#00eaff',
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: false,
    };

    const decoOptions: LineSeriesPartialOptions = {
      color: '#ff6363',
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: false,
    };

    // ✅ Use concrete helpers so the series type is 'Line'
    const collapseSeries = chart.addLineSeries(collapseOptions);
    const decoSeries = chart.addLineSeries(decoOptions);

    chartRef.current = chart;
    collapseSeriesRef.current = collapseSeries;
    decoSeriesRef.current = decoSeries;

    const ro = new ResizeObserver(() => {
      if (!containerRef.current) return;
      const { clientWidth: w, clientHeight: h } = containerRef.current;
      chart.applyOptions({ width: w, height: h });
      chart.timeScale().fitContent();
    });

    ro.observe(containerRef.current);

    return () => {
      ro.disconnect();
      chart.remove();
      chartRef.current = null;
      collapseSeriesRef.current = null;
      decoSeriesRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!chartRef.current || !collapseSeriesRef.current || !decoSeriesRef.current) return;
    if (!traceData || traceData.length === 0) return;

    // Convert number or ISO string to lightweight-charts Time
    const toTime = (t: number | string): Time =>
      typeof t === 'number'
        ? (t as unknown as Time) // UTCTimestamp
        : (Math.floor(new Date(t).getTime() / 1000) as unknown as Time); // seconds -> UTCTimestamp

    const collapse: LineData[] = traceData.map((d: TracePoint) => ({
      time: toTime(d.timestamp),
      value: d.collapse,
    }));

    const deco: LineData[] = traceData.map((d: TracePoint) => ({
      time: toTime(d.timestamp),
      value: d.decoherence,
    }));

    collapseSeriesRef.current.setData(collapse);
    decoSeriesRef.current.setData(deco);
    chartRef.current.timeScale().fitContent();
  }, [traceData]);

  if (isLoading) {
    return <div className="p-4 text-sm text-blue-300">📡 Loading WaveScope...</div>;
  }

  if (!traceData || traceData.length === 0) {
    return <div className="p-4 text-sm text-yellow-300">⚠️ No trace data found.</div>;
  }

  return (
    <div className="bg-black/70 text-white p-4 rounded-xl shadow-xl border border-blue-400/30">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-semibold">🌀 WaveScope Replay</h2>
        <div className="flex items-center gap-4 text-xs">
          <span className="flex items-center gap-1">
            <span className="inline-block h-2 w-4" style={{ borderTop: '2px solid #00eaff' }} />
            Collapse
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block h-2 w-4" style={{ borderTop: '2px solid #ff6363' }} />
            Decoherence
          </span>
        </div>
      </div>

      {/* Chart container */}
      <div ref={containerRef} className="w-full" style={{ height: 280 }} />
    </div>
  );
}