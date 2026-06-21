import { Flag, MapPin, Calendar } from 'lucide-react';
import { Tender } from '@/lib/mockData';

export function TenderCard({ tender }: { tender: Tender }) {
  return (
    <div className="card hover:border-accent-tech transition-colors group">
      <div className="flex justify-between items-start mb-3">
        <span className="badge-tech">{tender.source}</span>
        <div className="flex gap-2">
          {tender.redFlags.length > 0 && (
            <span className="badge-warning flex items-center gap-1">
              <Flag className="w-3 h-3" /> {tender.redFlags.length}
            </span>
          )}
        </div>
      </div>

      <h3 className="font-display font-bold text-lg mb-2 line-clamp-2 group-hover:text-accent-tech transition-colors">
        {tender.title}
      </h3>

      <div className="font-mono text-2xl font-bold text-neutral-600 mb-4">
        {tender.value.toLocaleString('pl-PL')} zł
      </div>

      <div className="flex items-center gap-4 text-sm text-neutral-400 mb-4">
        <span className="flex items-center gap-1">
          <MapPin className="w-4 h-4" /> {tender.location}
        </span>
        <span className="flex items-center gap-1">
          <Calendar className="w-4 h-4" /> {new Date(tender.deadline).toLocaleDateString('pl-PL')}
        </span>
      </div>

      {tender.redFlags.length > 0 && (
        <div className="mb-4 p-2 bg-accent-warning/10 rounded-md">
          <div className="text-xs font-mono text-accent-warning mb-1">
            {tender.redFlags[0].description}
          </div>
          <div className="text-xs font-mono text-accent-warning">
            Strata: {tender.redFlags.reduce((acc, f) => acc + f.impact, 0).toLocaleString('pl-PL')} zł
          </div>
        </div>
      )}

      <button className="w-full btn-primary text-sm">
        ANALIZUJ
      </button>
    </div>
  );
}
