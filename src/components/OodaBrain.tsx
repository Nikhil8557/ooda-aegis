import React, { useEffect, useRef, useState } from 'react';
import { AegisState, TraceStep } from '../live/types';
import { Panel } from './ui';

interface Props {
  state: AegisState;
  live: boolean;
  onChaos: () => void;
}

type Tab = 'trace' | 'edge' | 'fuzz' | 'fleet' | 'canary';

const phaseLabel: Record<string, string> = {
  idle: 'Watching telemetry',
  exploited: 'Attack detected',
  edge_containment: 'Containing at the edge',
  code_repair: 'Writing a fix',
  sandbox_testing: 'Proving the fix',
  hot_swapping: 'Canary rollout',
  immune: 'Healed',
  escalated: 'Escalated to a human',
  rolled_back: 'Rolled back',
  degraded: 'Stopped safely',
};

const phaseColor = (p: string) =>
  p === 'immune' ? 'text-ok' : ['exploited', 'escalated', 'rolled_back', 'degraded'].includes(p) ? 'text-attack' : p === 'idle' ? 'text-mist' : 'text-hold';

const Step: React.FC<{ step: TraceStep }> = ({ step }) => {
  const [open, setOpen] = useState(false);
  const fail = /FAIL|rejected|No verified|stopped|rollback|No safe/i.test(step.summary);
  return (
    <div className="px-3 py-2 rounded-sm bg-raise">
      <div className="flex items-baseline justify-between gap-2 text-sm text-mist">
        <span className="font-mono">{step.timestamp}</span>
        <span>{step.phase}</span>
      </div>
      <div className={`text-sm font-semibold mt-1 ${fail ? 'text-attack' : 'text-fog'}`}>{step.summary}</div>
      <div className="text-sm text-mist mt-1 leading-relaxed">{step.details}</div>
      {step.toolCall && (
        <div className="mt-2">
          <button onClick={() => setOpen(!open)} className="text-sm text-fog hover:text-mist cursor-pointer">
            {open ? 'Hide' : 'Show'} tool call <span className="font-mono">{step.toolCall.name}</span>
          </button>
          {open && (
            <pre className="mt-2 p-2 bg-ink text-fog rounded-sm font-mono text-sm whitespace-pre-wrap break-all">
              {JSON.stringify(step.toolCall.input, null, 1)}
              {'\nresult: '}
              {step.toolCall.output}
            </pre>
          )}
        </div>
      )}
    </div>
  );
};

const Row: React.FC<{ children: React.ReactNode }> = ({ children }) => <div className="px-3 py-2 rounded-sm bg-raise text-sm">{children}</div>;

export const OodaBrain: React.FC<Props> = ({ state, live, onChaos }) => {
  const [tab, setTab] = useState<Tab>('trace');
  const scroller = useRef<HTMLDivElement>(null);
  const phases = new Set(state.trace.map((t) => t.phase));
  const vp = state.virtualPatch;

  useEffect(() => {
    if (tab === 'trace' && scroller.current) scroller.current.scrollTop = scroller.current.scrollHeight;
  }, [state.trace.length, tab]);

  const tabs: { id: Tab; label: string }[] = [
    { id: 'trace', label: `Trace ${state.trace.length}` },
    { id: 'edge', label: 'Virtual patch' },
    { id: 'fuzz', label: `Red team ${state.fuzz.length}` },
    { id: 'fleet', label: 'Fleet' },
    { id: 'canary', label: 'Canary' },
  ];

  return (
    <Panel title="Defense agent" note={<span className={`font-semibold ${phaseColor(state.phase)}`}>{phaseLabel[state.phase] ?? state.phase}</span>}>
      <div className="px-4 pb-2 text-sm flex flex-wrap gap-x-4 gap-y-1">
        {['Observe', 'Orient', 'Decide', 'Act'].map((name) => (
          <span key={name} className={phases.has(name as TraceStep['phase']) ? 'text-fog font-semibold' : 'text-slate'}>
            {name}
          </span>
        ))}
      </div>

      <div className="px-4 pb-2 text-sm text-mist space-y-1">
        <div>
          Edge model <span className="text-fog">{state.models.edge.label}</span>
        </div>
        <div>
          Repair model <span className="text-fog">{state.models.repair.label}</span>
        </div>
      </div>

      <div className="flex items-center gap-4 px-4 pt-2 text-sm overflow-x-auto">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`py-1 whitespace-nowrap cursor-pointer ${tab === t.id ? 'text-fog font-semibold shadow-[inset_0_-2px_0_#CCD0CF]' : 'text-mist hover:text-fog'}`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div ref={scroller} className="flex-1 overflow-y-auto p-4 space-y-2 min-h-[380px] max-h-[620px]">
        {tab === 'trace' &&
          (state.trace.length ? (
            <>
              {state.trace.map((s) => (
                <Step key={s.id} step={s} />
              ))}
              {state.busy && <div className="text-sm text-hold px-1">Agent working</div>}
            </>
          ) : (
            <p className="text-sm text-mist leading-relaxed">
              The agent reads every response the service sends. Fire an attack from the left: there is no defend button.
              Detection, containment, repair, testing and rollout happen on their own.
            </p>
          ))}

        {tab === 'edge' && (
          <div className="space-y-2 text-sm">
            <Row>
              <div className={`font-semibold ${vp.active ? 'text-hold' : 'text-fog'}`}>
                {vp.active ? `${vp.ruleId} is active at the proxy` : vp.ruleId ? `${vp.ruleId} retired, the code is fixed` : 'No virtual patch yet'}
              </div>
              {vp.regex && <pre className="mt-2 p-2 bg-ink text-fog rounded-sm font-mono whitespace-pre-wrap break-all">{vp.regex}</pre>}
              {vp.model && (
                <div className="mt-2 text-mist">
                  Written by {vp.model} in {vp.modelLatencyMs} ms. nginx -t and graceful reload took {vp.reloadMs} ms.
                </div>
              )}
            </Row>
            {vp.attempts.map((a) => (
              <Row key={a.attempt}>
                <div className="flex justify-between">
                  <span className="font-semibold text-fog">Attempt {a.attempt}</span>
                  <span className={a.ok ? 'text-ok' : 'text-attack'}>{a.ok ? 'validated' : 'rejected'}</span>
                </div>
                <div className="text-mist mt-1">Rule from the model: {a.rule}</div>
                {!a.ok && <div className="text-attack mt-1">{a.reason}</div>}
              </Row>
            ))}
            <p className="text-mist leading-relaxed">
              The model writes the rule in a small safe language. The agent compiles it, checks that it blocks the attack and
              none of the recorded legitimate requests, then reloads Nginx.
            </p>
          </div>
        )}

        {tab === 'fuzz' && (
          <div className="space-y-1">
            {state.fuzz.length === 0 && <p className="text-sm text-mist">Variants appear once an attack is contained.</p>}
            {state.fuzz.map((f) => (
              <div key={f.id} className="px-3 py-2 rounded-sm bg-raise text-sm flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="font-semibold text-fog">{f.technique}</div>
                  <div className="font-mono text-mist break-all">{f.mutatedPayload}</div>
                </div>
                <div className="text-right shrink-0">
                  <div className={f.edgeCovered ? 'text-hold' : 'text-mist'}>{f.edgeCovered ? 'edge catches' : 'edge misses'}</div>
                  <div className={f.status === 'blocked' ? 'text-ok font-semibold' : f.status === 'bypassed' ? 'text-attack font-semibold' : 'text-mist'}>
                    {f.status === 'blocked' ? 'fix holds' : f.status === 'bypassed' ? 'fix bypassed' : 'untested'}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {tab === 'fleet' && (
          <div className="space-y-1 text-sm">
            {state.fleet.map((n) => (
              <Row key={n.id}>
                <div className="flex justify-between">
                  <div>
                    <div className="font-semibold text-fog">{n.name}</div>
                    <div className="text-mist">{n.zone}</div>
                  </div>
                  <div className="text-right">
                    <div className={n.status === 'immune' ? 'text-ok font-semibold' : 'text-mist'}>{n.status.replace('_', ' ')}</div>
                    {n.syncLatencyMs > 0 && <div className="text-mist">{n.syncLatencyMs} ms</div>}
                  </div>
                </div>
              </Row>
            ))}
            <p className="text-mist pt-2">Each peer is its own container on the Redis bus. It compiles the rule, tests it and replies.</p>
          </div>
        )}

        {tab === 'canary' && (
          <div className="space-y-4 text-sm">
            <dl className="grid grid-cols-2 gap-x-4 gap-y-2">
              {[
                ['Status', state.canary.status.replace(/_/g, ' ')],
                ['Step', state.canary.step ?? 'none'],
                ['Probes ok, failed', `${state.canary.probesOk}, ${state.canary.probesFailed}`],
                ['p99 latency', `${state.canary.p99LatencyMs} ms`],
              ].map(([k, v]) => (
                <div key={k}>
                  <dt className="text-mist">{k}</dt>
                  <dd className="font-semibold text-fog">{v}</dd>
                </div>
              ))}
            </dl>
            {state.canary.circuitBreakerTripped && (
              <Row>
                <span className="text-attack">Circuit breaker tripped: traffic went back to the previous release.</span>
              </Row>
            )}
            <p className="text-mist leading-relaxed">
              Traffic moves to 10%, 50%, then 100% with legitimate probes at each step. A failed or slow probe rolls back.
            </p>
            {live && state.phase === 'hot_swapping' && (
              <button onClick={onChaos} className="px-4 py-2 rounded-sm bg-raise text-attack font-semibold hover:bg-slate cursor-pointer">
                Inject a fault: freeze the new container
              </button>
            )}
          </div>
        )}
      </div>
    </Panel>
  );
};
