import React from 'react';
import { Connection } from '../live/useAegis';

export type View = 'console' | 'repair' | 'sandbox' | 'rollout';

interface Props {
  view: View;
  setView: (v: View) => void;
  connection: Connection;
  onReset: () => void;
  onAbout: () => void;
}

const views: [View, string][] = [
  ['console', 'Command center'],
  ['repair', 'Code repair'],
  ['sandbox', 'Sandbox proof'],
  ['rollout', 'Rollout'],
];

const connectionText: Record<Connection, string> = {
  live: 'Live agent',
  replay: 'Recorded run',
  connecting: 'Connecting',
  offline: 'Offline',
};

export const Navbar: React.FC<Props> = ({ view, setView, connection, onReset, onAbout }) => (
  <header className="sticky top-0 z-40 bg-ink px-4 sm:px-6 py-4">
    <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-4">
      <div className="flex items-baseline gap-4 shrink-0">
        <span className="font-display text-xl text-fog">ooda-aegis</span>
        <span className="text-sm text-mist hidden sm:inline">by Nikhil Kumar</span>
      </div>

      <nav className="flex items-center gap-6 text-sm overflow-x-auto order-3 lg:order-none w-full lg:w-auto">
        {views.map(([id, label]) => (
          <button
            key={id}
            onClick={() => setView(id)}
            className={`whitespace-nowrap py-1 cursor-pointer ${
              view === id ? 'text-fog font-semibold shadow-[inset_0_-2px_0_#CCD0CF]' : 'text-mist hover:text-fog'
            }`}
          >
            {label}
          </button>
        ))}
      </nav>

      <div className="flex items-center gap-2 shrink-0 text-sm">
        <span className={`mr-2 ${connection === 'live' ? 'text-ok' : 'text-mist'}`}>{connectionText[connection]}</span>
        <button onClick={onReset} className="px-4 py-1.5 rounded-sm bg-raise text-fog hover:bg-slate cursor-pointer">
          Reset
        </button>
        <button onClick={onAbout} className="px-4 py-1.5 rounded-sm bg-fog text-ink font-semibold hover:bg-mist cursor-pointer">
          How it works
        </button>
      </div>
    </div>
  </header>
);
