'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { LayoutDashboard, Sparkles, Radar, LineChart, Wallet, Settings } from 'lucide-react';

const NAV = [
  { href: '/', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/agents', label: 'Research Copilot', icon: Sparkles },
  { href: '/monitoring', label: 'Live Monitoring', icon: Radar },
  { href: '/paper', label: 'Paper Trading', icon: Wallet },
  { href: '/drift', label: 'Drift Lab', icon: LineChart },
  { href: '/settings', label: 'Settings', icon: Settings },
];

export default function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="w-64 h-screen fixed left-0 top-0 flex flex-col border-r border-slate-800/80 bg-slate-950/60 backdrop-blur">
      <div className="p-6 border-b border-slate-800/80">
        <h1 className="text-2xl font-bold bg-gradient-to-r from-sky-400 to-emerald-400 bg-clip-text text-transparent tracking-tight">
          QUANTORA
        </h1>
        <p className="text-[11px] text-slate-500 mt-1">The Honest Quant Copilot</p>
      </div>

      <nav className="flex-1 p-3 space-y-1">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = href === '/' ? pathname === '/' : pathname.startsWith(href);
          return (
            <Link key={href} href={href}
              className={`flex items-center px-4 py-2.5 rounded-xl text-sm transition-all duration-150 ${
                active
                  ? 'bg-sky-500/10 text-sky-300 border border-sky-500/20'
                  : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-100 border border-transparent'
              }`}>
              <Icon size={17} className="mr-3 shrink-0" />
              {label}
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-slate-800/80">
        <div className="flex items-center">
          <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-sky-500 to-emerald-500 flex items-center justify-center text-xs font-bold text-slate-900">
            PC
          </div>
          <div className="ml-3">
            <p className="text-sm font-medium text-slate-200">Piyush Chandra</p>
            <p className="text-xs text-slate-500">Quant Researcher</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
