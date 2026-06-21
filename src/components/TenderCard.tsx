'use client';

import { Calendar, CheckCircle, AlertTriangle } from 'lucide-react';
import { Tender } from '@/lib/mockData';
import dynamic from 'next/dynamic';

// Dynamic import to avoid SSR issues with motion
const MotionDiv = dynamic(() => import('motion/react').then((m) => m.motion.div), { ssr: false });

interface TenderCardProps {
  tender: Tender;
}

export function TenderCard({ tender }: TenderCardProps) {
  return (
    <MotionDiv
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ scale: 1.02 }}
      className="card group"
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-display font-bold text-lg group-hover:text-[#00FF94] transition-colors">
          {tender.title}
        </h3>
        <span className="badge-tech">{tender.source}</span>
      </div>

      <div className="flex items-center gap-4 text-sm text-neutral-400 mb-4">
        <span className="flex items-center gap-1">
          <Calendar className="w-4 h-4" />
          {new Date(tender.deadline).toLocaleDateString('pl-PL')}
        </span>
        <span className="font-mono text-[#F4F4F0]">{tender.value.toLocaleString('pl-PL')} zł</span>
      </div>

      <div className="flex items-center gap-2 mb-4">
        {tender.redFlags.length > 0 ? (
          <>
            <AlertTriangle className="w-4 h-4 text-[#FF3300]" />
            <span className="badge-warning">{tender.redFlags.length} czerwone flagi</span>
          </>
        ) : (
          <>
            <CheckCircle className="w-4 h-4 text-[#00FF94]" />
            <span className="badge-success">Brak zagrożeń</span>
          </>
        )}
      </div>

      <div className="flex gap-2">
        <button className="btn-primary text-sm flex-1">
          Analizuj
        </button>
        <button className="btn-secondary text-sm flex-1">
          Szczegóły
        </button>
      </div>
    </MotionDiv>
  );
}
