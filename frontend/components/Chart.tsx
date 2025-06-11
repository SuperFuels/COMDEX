import React from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

/** A single point on the chart */
export interface ChartPoint {
  time: number    // UNIX timestamp in seconds
  value: number
}

interface ChartProps {
  data: ChartPoint[]
  /** height in pixels */
  height?: number
}

export default function Chart({ data, height = 200 }: ChartProps) {
  // format timestamps into human-readable labels
  const formatted = data.map(d => ({
    time: new Date(d.time * 1000).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
    }),
    value: d.value,
  }))

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={formatted}>
        <XAxis dataKey="time" tick={{ fontSize: 12 }} />
        <YAxis tick={{ fontSize: 12 }} />
        <Tooltip
          labelFormatter={label => `Time: ${label}`}
          formatter={(val: number) => val.toFixed(2)}
        />
        <Line
          type="monotone"
          dataKey="value"
          strokeWidth={2}
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}

