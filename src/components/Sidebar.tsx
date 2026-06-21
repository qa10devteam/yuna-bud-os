import { Map, Calculator, Brain, Flag, Shovel } from 'lucide-react';
import Link from 'next/link';

const navItems = [
  { name: 'ZWIAD', href: '/', icon: Map, color: 'text-neutral-600', desc: 'Trzonek' },
  { name: 'KOSZTORYS', href: '/kostorys', icon: Calculator, color: 'text-neutral-500', desc: 'Kij' },
  { name: 'SILNIK', href: '/silnik', icon: Flag, color: 'text-neutral-400', desc: 'Przetwarzanie' },
  { name: 'DECYZJA', href: '/decyzja', icon: Brain, color: 'text-accent-success', desc: 'Łyżka' },
];

export function Sidebar() {
  return (
    <aside className="w-20 md:w-64 bg-neutral-600 text-neutral-100 flex flex-col items-center md:items-start p-4 gap-8 min-h-screen border-r border-neutral-500">
      <div className="flex items-center gap-3">
        <Shovel className="w-8 h-8 text-accent-success" />
        <span className="font-display font-bold text-xl hidden md:block text-accent-success">
          Terra.OS
        </span>
      </div>

      <nav className="flex flex-col gap-2 w-full">
        {navItems.map((item) => (
          <Link
            key={item.name}
            href={item.href}
            className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-neutral-500 transition-colors group"
          >
            <item.icon className={`w-6 h-6 ${item.color} group-hover:text-accent-success transition-colors`} />
            <div className="hidden md:block">
              <div className="font-display font-bold text-sm">{item.name}</div>
              <div className="text-xs text-neutral-300">{item.desc}</div>
            </div>
          </Link>
        ))}
      </nav>

      <div className="mt-auto hidden md:block w-full">
        <div className="bg-neutral-500 rounded-lg p-3 text-xs text-neutral-300">
          <div className="font-display font-bold text-neutral-100 mb-1">Maciek K.</div>
          <div>Firma Robót Ziemnych</div>
          <div className="mt-2 badge-success px-2 py-1 inline-block">Pro Plan</div>
        </div>
      </div>
    </aside>
  );
}
