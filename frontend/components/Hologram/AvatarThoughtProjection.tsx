import React, { useEffect, useRef } from "react"
import { Canvas, useFrame } from "@react-three/fiber"
import { Float, Text } from "@react-three/drei"
import * as THREE from "three"

type ThoughtGlyph = {
  symbol: string
  id: string
  color?: string
  pulse?: boolean
  label?: string
}

type Props = {
  thoughts: ThoughtGlyph[]
  orbitRadius?: number
  avatarPosition?: [number, number, number]
}

const OrbitingGlyph: React.FC<{ glyph: ThoughtGlyph; index: number; total: number; radius: number }> = ({
  glyph,
  index,
  total,
  radius,
}) => {
  const ref = useRef<THREE.Group>(null!)
  const angleOffset = (index / total) * Math.PI * 2

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime()
    const angle = angleOffset + t * 0.3
    const x = Math.cos(angle) * radius
    const z = Math.sin(angle) * radius
    ref.current.position.set(x, 1.5, z)
    ref.current.rotation.y = -angle
  })

  return (
    <group ref={ref}>
      <Float speed={glyph.pulse ? 2 : 0} floatIntensity={glyph.pulse ? 1.5 : 0.2}>
        <Text fontSize={0.3} color={glyph.color || "#ffffff"} anchorX="center" anchorY="middle">
          {glyph.symbol}
        </Text>
      </Float>
    </group>
  )
}

const AvatarThoughtProjection: React.FC<Props> = ({
  thoughts,
  orbitRadius = 2.5,
  avatarPosition = [0, 0, 0],
}) => {
  return (
    <group position={avatarPosition}>
      {thoughts.map((glyph, idx) => (
        <OrbitingGlyph key={glyph.id} glyph={glyph} index={idx} total={thoughts.length} radius={orbitRadius} />
      ))}
    </group>
  )
}

export default AvatarThoughtProjection