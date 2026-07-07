'use client'
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import L from 'leaflet'

// Fix default marker icons
delete (L.Icon.Default.prototype as any)._getIconUrl
L.Icon.Default.mergeOptions({ iconRetinaUrl: '/marker-icon-2x.png', iconUrl: '/marker-icon.png', shadowUrl: '/marker-shadow.png' })

export default function TenderMapInner({ locations, height }: { locations: any[]; height: number }) {
  const center: [number, number] = locations.length ? [locations[0].lat, locations[0].lng] : [52.0, 19.0]
  return (
    <MapContainer center={center} zoom={6} style={{ height: `${height}px`, width: '100%' }}>
      <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' />
      {locations.map(loc => (
        <Marker key={loc.id} position={[loc.lat, loc.lng]}>
          <Popup><strong>{loc.title}</strong><br />{new Intl.NumberFormat('pl-PL').format(loc.value_pln)} PLN</Popup>
        </Marker>
      ))}
    </MapContainer>
  )
}
