'use client';

import { ArrowUpRight, ArrowDownRight, ShieldAlert, CheckCircle } from 'lucide-react';
import dynamic from 'next/dynamic';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

// Dynamic import to avoid SSR issues with motion
const MotionDiv = dynamic(() => import('motion/react').then((m) => m.motion.div), { ssr: false });

const data = [
  { name: 'Sty', zysk: 4000 },
  { name: 'Lut', zysk: 3000 },
  { name: 'Mar', zysk: 2000 },
  { name: 'Kwi', zysk: 2780 },
  { name: 'Maj', zysk: 1890 },
  { name: 'Cze', zysk: 2390 },
];

// Chart wrapper component
function RechartsChart() {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data}>
        <XAxis dataKey="name" />
        <YAxis />
        <Tooltip />
        <Bar dataKey="zysk" fill="#00FF94" />
      </BarChart>
    </ResponsiveContainer>
  );
}

const DynamicChart = dynamic(() => Promise.resolve(RechartsChart), { ssr: false });

const stats = [
  {
    title: 'Zaoszczędzono',
    value: '47 500 zł',
    change: '+12%',
    icon: CheckCircle,
    color: 'text-accent-success',
    bg: 'bg-accent-success/20',
  },
  {
    title: 'Ryzyka wykryte',
    value: '14',
    change: '-3',
    icon: ShieldAlert,
    color: 'text-accent-warning',
    bg: 'bg-accent-warning/20',
  },
  {
    title: 'Zysk brutto',
    value: '28%',
    change: '+5%',
    icon: ArrowUpRight,
    color: 'text-accent-tech',
    bg: 'bg-accent-tech/20',
  },
];

export function Dashboard() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
      {stats.map((stat) => (
        <MotionDiv
          key={stat.title}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="card"
        >
          <div className="flex items-center justify-between mb-4">
            <span className="text-neutral-400 text-sm">{stat.title}</span>
            <div className={`p-2 rounded-lg ${stat.bg} ${stat.color}`}>
              <stat.icon className="w-5 h-5" />
            </div>
          </div>
          <div className="flex items-end gap-2">
            <span className="text-3xl font-display font-bold text-neutral-600">{stat.value}</span>
            <span className={`text-sm mb-1 ${stat.color}`}>
              {stat.change}
            </span>
          </div>
        </MotionDiv>
      ))}
      
      {/* Chart section */}
      <div className="col-span-1 md:col-span-3 mt-6">
        <div className="card">
          <h3 className="font-display font-bold text-lg mb-4">Zysk miesięczny</h3>
          <div className="h-80">
            <DynamicChart />
          </div>
        </div>
      </div>
    </div>
  );
}
