import React from 'react';
import { AegisState } from '../live/types';
import { Panel, verdictColor } from './ui';

const verdictShort: Record<string, string> = {
  exploited: 'exploited',
  blocked_by_edge: 'blocked at edge',
  sanitized_by_v2: 'handled by patch',
  benign: 'ok',
};

export const ServiceHud: React.FC<{ state: AegisState }> = ({ state }) => {
  const m = state.metrics;
  const vulnerable = state.container.version.includes('vulnerable');
  const stats: [string, string][] = [
    ['Time to contain', m.timeToContainS != null ? `${m.timeToContainS} s` : 'not yet'],
    ['Time to heal', m.timeToHealS != null ? `${m.timeToHealS} s` : 'not yet'],
    ['Blocked at edge', String(m.blocked)],
    ['Exploits landed', String(m.exploited)],
    ['Average latency', `${m.avgLatencyMs} ms`],
    ['CPU and memory', `${m.cpu}%, ${m.memoryMb} MB`],
  ];
  return (
    <Panel title="Production service" note={<span className="font-mono">doc-vault</span>}>
      <div className="px-4 pb-4 space-y-4">
        <div className="bg-raise rounded-sm px-3 py-2">
          <div className={`text-base font-semibold ${vulnerable ? 'text-attack' : 'text-ok'}`}>{state.container.version}</div>
          <div className="text-sm font-mono text-mist truncate">{state.container.active}</div>
        </div>
        <div className="text-sm">
          <span className="text-mist">Virtual patch </span>
          <span className={state.virtualPatch.active ? 'text-hold font-semibold' : 'text-fog'}>
            {state.virtualPatch.active ? state.virtualPatch.ruleId : 'none'}
          </span>
        </div>
        <div>
          <div className="flex justify-between text-sm text-mist mb-2">
            <span>Old release {state.trafficSplit.old}%</span>
            <span>New release {state.trafficSplit.new}%</span>
          </div>
          <div className="h-2 rounded-sm bg-slate overflow-hidden flex">
            <div className="bg-mist transition-[width] duration-700" style={{ width: `${state.trafficSplit.old}%` }} />
            <div className="bg-ok transition-[width] duration-700" style={{ width: `${state.trafficSplit.new}%` }} />
          </div>
        </div>
        <dl className="grid grid-cols-2 gap-x-4 gap-y-2">
          {stats.map(([k, v]) => (
            <div key={k}>
              <dt className="text-sm text-mist">{k}</dt>
              <dd className="text-base font-semibold text-fog tabular-nums">{v}</dd>
            </div>
          ))}
        </dl>
        {state.history.length > 0 && (
          <div className="text-sm text-mist space-y-1">
            {state.history.map((h) => (
              <div key={h.incident}>
                Healed {h.scenario.replace('_', ' ')}: {h.from} to <span className="font-semibold text-ok">{h.to}</span> in {h.healedS} s
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="px-4 pt-2 text-sm font-semibold text-fog">Request log</div>
      <div className="flex-1 overflow-y-auto py-1">
        {state.logs.length === 0 && <div className="text-sm text-mist p-4">No requests yet.</div>}
        {state.logs.map((l) => (
          <div key={l.id} className="px-4 py-1 text-sm font-mono flex items-center gap-2">
            <span className="text-mist shrink-0">{l.timestamp}</span>
            <span className={`shrink-0 font-medium ${verdictColor[l.verdict]}`}>{l.statusCode}</span>
            <span className="truncate text-fog flex-1">{l.payload}</span>
            <span className={`shrink-0 font-sans ${verdictColor[l.verdict]}`}>{verdictShort[l.verdict]}</span>
          </div>
        ))}
      </div>
    </Panel>
  );
};
