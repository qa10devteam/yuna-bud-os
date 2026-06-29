'use client';

import { equipment, employees } from '@/lib/mockData';
import {
  Truck,
  Users,
  Calendar,
  MapPin,
  Check,
  X,
  Clock,
  Wrench,
  Navigation,
  FileText,
  Send,
  Smartphone,
  Camera,
  AlertTriangle,
  ChevronRight,
} from 'lucide-react';
import dynamic from 'next/dynamic';

export function LogistykaPage() {
  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <h1 className="text-3xl font-bold text-earth-100">MÓZG</h1>
          <span className="badge-info">Logistyka i zasoby</span>
        </div>
        <p className="text-earth-400">
          Zarządzanie budową — zasoby, kalendarz, logistyka, plany dnia dla zespołu
        </p>
      </div>
      
      {/* Stats */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="card p-4">
          <div className="text-sm text-earth-400 mb-1">Aktywny sprzęt</div>
          <div className="text-2xl font-bold text-earth-100">
            {equipment.filter(e => e.availability).length} / {equipment.length}
          </div>
        </div>
        <div className="card p-4">
          <div className="text-sm text-earth-400 mb-1">Dostępni pracownicy</div>
          <div className="text-2xl font-bold text-earth-100">
            {employees.filter(e => e.available).length} / {employees.length}
          </div>
        </div>
        <div className="card p-4">
          <div className="text-sm text-earth-400 mb-1">Aktywne kontrakty</div>
          <div className="text-2xl font-bold text-earth-100">2</div>
        </div>
        <div className="card p-4">
          <div className="text-sm text-earth-400 mb-1">Plany wysłane dziś</div>
          <div className="text-2xl font-bold text-earth-100">1</div>
        </div>
      </div>
      
      {/* Equipment */}
      <div className="card p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-earth-100 flex items-center gap-2">
            <Truck className="w-5 h-5 text-accent-info" />
            Sprzęt
          </h2>
          <button className="btn-primary text-sm">+ Dodaj sprzęt</button>
        </div>
        <div className="grid grid-cols-5 gap-4">
          {equipment.map((eq) => (
            <div key={eq.id} className="p-4 bg-earth-800 rounded-lg border border-earth-700">
              <div className="flex items-center justify-between mb-2">
                <span className={`w-2 h-2 rounded-full ${eq.availability ? 'bg-accent-success' : 'bg-accent-danger'}`} />
                <span className="text-xs text-earth-400">{eq.type}</span>
              </div>
              <h3 className="font-semibold text-earth-100 text-sm mb-1">{eq.name}</h3>
              <div className="text-xs text-earth-400">{eq.capacity}</div>
              <div className="text-xs text-earth-400 mt-1 flex items-center gap-1">
                <MapPin className="w-3 h-3" />
                {eq.location}
              </div>
            </div>
          ))}
        </div>
      </div>
      
      {/* Employees */}
      <div className="card p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-earth-100 flex items-center gap-2">
            <Users className="w-5 h-5 text-accent-success" />
            Zespół
          </h2>
          <button className="btn-primary text-sm">+ Dodaj pracownika</button>
        </div>
        <div className="space-y-3">
          {employees.map((emp) => (
            <div key={emp.id} className="flex items-center justify-between p-3 bg-earth-800 rounded-lg border border-earth-700">
              <div className="flex items-center gap-3">
                <div className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold ${
                  emp.available ? 'bg-accent-success/20 text-accent-success' : 'bg-accent-danger/20 text-accent-danger'
                }`}>
                  {emp.nameShort}
                </div>
                <div>
                  <div className="text-sm font-medium text-earth-100">{emp.name}</div>
                  <div className="text-xs text-earth-400">
                    {emp.competencies.join(', ')}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {emp.available ? (
                  <span className="badge-success">Dostępny</span>
                ) : (
                  <span className="badge-danger">Zajęty</span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
      
      {/* Daily Plan */}
      <div className="card p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-earth-100 flex items-center gap-2">
            <Calendar className="w-5 h-5 text-accent-warning" />
            Plan na jutro — Budowa drogi gminnej
          </h2>
          <div className="flex gap-2">
            <button className="btn-secondary flex items-center gap-2 text-sm">
              <Smartphone className="w-4 h-4" />
              Wyślij na telefon
            </button>
            <button className="btn-primary flex items-center gap-2 text-sm">
              <Send className="w-4 h-4" />
              Wyślij na komunikator
            </button>
          </div>
        </div>
        
        <div className="space-y-4">
          <div className="p-4 bg-earth-800 rounded-lg border-l-4 border-accent-success">
            <div className="flex items-start justify-between mb-2">
              <div>
                <h3 className="font-semibold text-earth-100">08:00 — 12:00</h3>
                <p className="text-sm text-earth-400">Wykop ziemny — odcinek A (0-500m)</p>
              </div>
              <span className="badge-info">Koparka + Wywrotka</span>
            </div>
            <div className="flex items-center gap-4 text-xs text-earth-400">
              <span className="flex items-center gap-1">
                <Users className="w-3 h-3" />
                MK, PZ
              </span>
              <span className="flex items-center gap-1">
                <Truck className="w-3 h-3" />
                CAT 320, Scania P320
              </span>
              <span className="flex items-center gap-1">
                <MapPin className="w-3 h-3" />
                Dzierżoniów, ul. Budowlana
              </span>
            </div>
          </div>
          
          <div className="p-4 bg-earth-800 rounded-lg border-l-4 border-accent-warning">
            <div className="flex items-start justify-between mb-2">
              <div>
                <h3 className="font-semibold text-earth-100">13:00 — 17:00</h3>
                <p className="text-sm text-earth-400">Nasyp drogowy — zagęszczenie</p>
              </div>
              <span className="badge-warning">Walcowarka</span>
            </div>
            <div className="flex items-center gap-4 text-xs text-earth-400">
              <span className="flex items-center gap-1">
                <Users className="w-3 h-3" />
                TL, AM
              </span>
              <span className="flex items-center gap-1">
                <Truck className="w-3 h-3" />
                Bomag BW 213
              </span>
              <span className="flex items-center gap-1">
                <MapPin className="w-3 h-3" />
                Dzierżoniów, odcinek B
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
