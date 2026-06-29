'use client';

import { motion } from 'framer-motion';
import { useStore } from '@/store/useStore';
import {
  TrendingUp,
  Clock,
  FileText,
  AlertTriangle,
} from 'lucide-react';

// Custom SVG Icons
const ShovelIcon = () => <img src="/assets/icons/shovel.svg" alt="Zwiad" className="w-16 h-16" />;
const CalcIcon = () => <img src="/assets/icons/calculator.svg" alt="Kosztorys" className="w-16 h-16" />;
const BrainIcon = () => <img src="/assets/icons/brain.svg" alt="Silnik" className="w-16 h-16" />;
const ClipboardIcon = () => <img src="/assets/icons/clipboard.svg" alt="Decyzja" className="w-16 h-16" />;

const modules = [
  {
    id: 'zwiad' as const,
    name: 'ZWIAD',
    desc: 'Zwiad przetargowy',
    status: '3 przetargi',
    color: 'text-accent-success',
    bg: 'bg-accent-success/10',
    border: 'border-accent-success/30',
    icon: <ShovelIcon />,
  },
  {
    id: 'kosztorys' as const,
    name: 'KOSZTORYS',
    desc: 'Kosztorys 2 warianty',
    status: '2 warianty',
    color: 'text-accent-info',
    bg: 'bg-accent-info/10',
    border: 'border-accent-info/30',
    icon: <CalcIcon />,
  },
  {
    id: 'silnik' as const,
    name: 'SILNIK',
    desc: 'Silnik decyzyjny',
    status: '3 warstw',
    color: 'text-accent-warning',
    bg: 'bg-accent-warning/10',
    border: 'border-accent-warning/30',
    icon: <BrainIcon />,
  },
  {
    id: 'decyzja' as const,
    name: 'DECYZJA',
    desc: 'Rekomendacje',
    status: '1 decyzja',
    color: 'text-accent-violet',
    bg: 'bg-accent-violet/10',
    border: 'border-accent-violet/30',
    icon: <ClipboardIcon />,
  },
];

const activities = [
  { time: '14:32', action: 'Analiza przetargu BZP-2026-001', icon: FileText, color: 'text-accent-success' },
  { time: '13:15', action: 'Wygenerowano kosztorys wariant B', icon: TrendingUp, color: 'text-accent-info' },
  { time: '11:45', action: 'Wykryto 2 czerwone flagi', icon: AlertTriangle, color: 'text-accent-danger' },
  { time: '10:20', action: 'Zaimportowano dokumentację z BZP', icon: FileText, color: 'text-earth-400' },
];

export function DashboardPage() {
  const { setCurrentModule } = useStore();
  
  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-earth-100 mb-2">Dashboard</h1>
        <p className="text-earth-400">Panel Macieka — Podsumowanie aktywności</p>
      </div>
      
      {/* Module Cards */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        {modules.map((mod) => (
          <motion.button
            key={mod.id}
            whileHover={{ scale: 1.02, y: -4 }}
            onClick={() => setCurrentModule(mod.id)}
            className={`card p-6 text-left border-l-4 ${mod.border} ${mod.bg} transition-all`}
          >
            <div className="mb-4">{mod.icon}</div>
            <h3 className="text-xl font-bold text-earth-100 mb-1">{mod.name}</h3>
            <p className="text-sm text-earth-400 mb-3">{mod.desc}</p>
            <span className={`text-xs font-medium ${mod.color}`}>{mod.status}</span>
          </motion.button>
        ))}
      </div>
      
      {/* Metrics */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <div className="card p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-earth-400">Aktywne przetargi</span>
            <FileText className="w-4 h-4 text-accent-success" />
          </div>
          <div className="text-2xl font-bold text-earth-100">3</div>
        </div>
        <div className="card p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-earth-400">Kosztorysy</span>
            <TrendingUp className="w-4 h-4 text-accent-info" />
          </div>
          <div className="text-2xl font-bold text-earth-100">2</div>
        </div>
        <div className="card p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-earth-400">Decyzje</span>
            <FileText className="w-4 h-4 text-accent-violet" />
          </div>
          <div className="text-2xl font-bold text-earth-100">1</div>
        </div>
        <div className="card p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-earth-400">Czerwone flagi</span>
            <AlertTriangle className="w-4 h-4 text-accent-danger" />
          </div>
          <div className="text-2xl font-bold text-earth-100">2</div>
        </div>
      </div>
      
      {/* Timeline */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-earth-100 mb-4 flex items-center gap-2">
          <Clock className="w-5 h-5 text-accent-info" />
          Ostatnie aktywności
        </h3>
        <div className="space-y-4">
          {activities.map((act, i) => (
            <div key={i} className="flex items-start gap-3">
              <div className={`p-2 rounded-lg bg-earth-800 ${act.color}`}>
                <act.icon className="w-4 h-4" />
              </div>
              <div className="flex-1">
                <p className="text-sm text-earth-200">{act.action}</p>
                <p className="text-xs text-earth-500">{act.time}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
