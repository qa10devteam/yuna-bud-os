'use client'
import dynamic from 'next/dynamic'

// Dynamic import — Leaflet requires browser (no SSR)
const Map = dynamic(() => import('./_TenderMapInner'), { ssr: false, loading: () => <div className="h-64 bg-gray-100 animate-pulse rounded-lg" /> })

interface TenderLocation { id: string; title: string; lat: number; lng: number; value_pln: number }
interface TenderMapProps { locations: TenderLocation[]; height?: number }

export function TenderMap({ locations, height = 400 }: TenderMapProps) {
  return <Map locations={locations} height={height} />
}
