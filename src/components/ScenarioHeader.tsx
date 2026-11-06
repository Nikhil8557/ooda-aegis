import React from 'react';
import { SCENARIOS, Scenario, ScenarioId } from '../data/scenarios';

interface Props {
  current: Scenario;
  onSelect: (id: ScenarioId) => void;
}

export const ScenarioHeader: React.FC<Props> = ({ current, onSelect }) => (
  <section data-film-hide className="bg-deep px-4 sm:px-6 py-6">
    <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-end justify-between gap-4">
      <div className="space-y-2 min-w-0">
        <h1 className="font-display text-2xl text-fog">{current.title}</h1>
        <p className="text-sm text-mist max-w-3xl leading-relaxed">{current.summary}</p>
        <p className="text-sm text-mist">
          Severity {current.severity.toLowerCase()}, in <span className="font-mono text-fog">{current.sourceFile}</span>
        </p>
      </div>
      <div className="flex gap-1 shrink-0 overflow-x-auto">
        {Object.values(SCENARIOS).map((s) => (
          <button
            key={s.id}
            onClick={() => onSelect(s.id)}
            className={`px-4 py-2 text-sm rounded-sm whitespace-nowrap cursor-pointer ${
              s.id === current.id ? 'bg-fog text-ink font-semibold' : 'bg-raise text-fog hover:bg-slate'
            }`}
          >
            {s.short}
          </button>
        ))}
      </div>
    </div>
  </section>
);
