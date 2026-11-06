import React from 'react';
import { AegisState } from '../live/types';

const Section: React.FC<{ title: string; sub?: string; children: React.ReactNode }> = ({ title, sub, children }) => (
  <div className="bg-deep rounded-md p-4 sm:p-6 space-y-4">
    <div>
      <h2 className="font-display text-2xl text-fog">{title}</h2>
      {sub && <p className="text-sm text-mist mt-1">{sub}</p>}
    </div>
    {children}
  </div>
);

const Empty: React.FC<{ text: string }> = ({ text }) => <p className="text-sm text-mist py-8">{text}</p>;

const diffColor = (line: string) =>
  line.startsWith('+') && !line.startsWith('+++') ? 'text-ok' : line.startsWith('-') && !line.startsWith('---') ? 'text-attack' : 'text-mist';

export const RepairView: React.FC<{ state: AegisState }> = ({ state }) => {
  const r = state.repair;
  return (
    <Section
      title="Code repair"
      sub={
        r
          ? `Written by ${r.model}${r.latencyMs ? ` in ${(r.latencyMs / 1000).toFixed(1)} s` : ''}, file ${r.file}`
          : 'The repair model gets the attacked file, the exploit and what leaked.'
      }
    >
      {!r && <Empty text="No repair yet. Attack the service from the command center." />}
      {r && (
        <>
          {r.rootCause && (
            <p className="text-sm text-fog leading-relaxed">
              <span className="font-semibold">Root cause, {r.cwe}:</span> <span className="text-mist">{r.rootCause}</span>
            </p>
          )}
          {r.attempts.length > 0 && (
            <div className="space-y-1">
              {r.attempts.map((a) => (
                <div key={a.attempt} className={`text-sm ${a.ok ? 'text-ok' : 'text-attack'}`}>
                  Candidate {a.attempt}: {a.ok ? 'verified' : `rejected, ${a.reason}`}
                </div>
              ))}
            </div>
          )}
          {r.diff ? (
            <pre className="p-4 bg-ink rounded-sm font-mono text-sm overflow-x-auto max-h-[460px] leading-relaxed">
              {r.diff.split('\n').map((line, i) => (
                <div key={i} className={diffColor(line)}>
                  {line || ' '}
                </div>
              ))}
            </pre>
          ) : (
            <pre className="p-4 bg-ink text-fog rounded-sm font-mono text-sm overflow-x-auto max-h-[460px]">{r.before}</pre>
          )}
          {r.testCode && (
            <div>
              <div className="text-sm font-semibold text-fog mb-2">Test written by the model (advisory only)</div>
              <pre className="p-4 bg-ink text-mist rounded-sm font-mono text-sm overflow-x-auto max-h-[320px]">{r.testCode}</pre>
            </div>
          )}
        </>
      )}
    </Section>
  );
};

const Check: React.FC<{ ok: boolean; title: string; body: React.ReactNode }> = ({ ok, title, body }) => (
  <div className="bg-raise rounded-sm px-4 py-3">
    <div className="text-sm font-semibold text-fog">{title}</div>
    <div className={`text-sm mt-1 ${ok ? 'text-ok' : 'text-attack'}`}>{body}</div>
  </div>
);

export const SandboxView: React.FC<{ state: AegisState }> = ({ state }) => {
  const s = state.sandbox;
  return (
    <Section title="Sandbox proof" sub="Every candidate fix runs in a throwaway container with no network before it can reach production.">
      {!s && <Empty text="No sandbox run yet." />}
      {s && (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
            <Check ok={!!s.reproducesOnV1} title="The real exploit works on the old code" body={s.reproducesOnV1 ? 'Yes, reproduced' : 'No, nothing to prove'} />
            <Check
              ok={!!s.v2?.passed}
              title="Everything is safe on the new code"
              body={s.v2 ? `${s.v2.counts.passed} passed, ${s.v2.counts.failed} failed` : 'not run'}
            />
            <Check
              ok={!!s.ok}
              title="Verdict"
              body={
                <>
                  {s.ok ? 'Cleared to ship' : s.reason}
                  {s.modelTestPassed != null && (
                    <span className="block text-mist">The model's own test {s.modelTestPassed ? 'passed' : 'failed'} (advisory)</span>
                  )}
                </>
              }
            />
          </div>
          {s.v2 && (
            <div className="bg-ink rounded-sm py-2">
              {s.v2.per_test.map((t) => (
                <div key={t.name} className="px-4 py-1 text-sm font-mono flex justify-between gap-4">
                  <span className="truncate text-fog">{t.name}</span>
                  <span className={t.outcome === 'passed' ? 'text-ok' : t.outcome === 'failed' ? 'text-attack' : 'text-mist'}>{t.outcome}</span>
                </div>
              ))}
            </div>
          )}
          <p className="text-sm text-mist leading-relaxed max-w-3xl">
            The agent writes this gate, not the model: the exploit seen in production, every red-team variant (each must come
            back safe within 2.5 s), the service's own tests, and recorded legitimate requests, which must return exactly what
            the old code returned. The model's own test runs too, but it cannot approve a fix.
          </p>
        </>
      )}
    </Section>
  );
};

export const RolloutView: React.FC<{ state: AegisState }> = ({ state }) => (
  <Section title="Zero-downtime rollout" sub="Weighted Nginx upstreams move real traffic to the new container in steps, with probes between steps.">
    <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm">
      <div className="bg-raise rounded-sm px-4 py-3">
        <div className="font-semibold text-fog">Previous release</div>
        <div className="font-mono mt-1 text-mist">{state.container.previous ?? 'aegis_app_blue'}</div>
        <div className="mt-2 text-fog">Traffic {state.trafficSplit.old}%</div>
      </div>
      <div className="bg-raise rounded-sm px-4 py-3">
        <div className="font-semibold text-ok">Active release {state.container.version}</div>
        <div className="font-mono mt-1 text-mist">{state.container.active}</div>
        <div className="mt-2 text-fog">
          Canary {state.canary.status.replace(/_/g, ' ')}, {state.canary.probesOk} probes ok, {state.canary.probesFailed} failed
        </div>
      </div>
    </div>
    {state.history.length > 0 ? (
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-mist">
            <th className="py-2 font-normal">Incident</th>
            <th className="font-normal">Attack</th>
            <th className="font-normal">Contained</th>
            <th className="font-normal">Healed</th>
            <th className="font-normal">Release</th>
          </tr>
        </thead>
        <tbody className="text-fog">
          {state.history.map((h) => (
            <tr key={h.incident}>
              <td className="py-1 font-mono">{h.incident}</td>
              <td>{h.scenario.replace('_', ' ')}</td>
              <td>{h.containS != null ? `${h.containS} s` : 'none'}</td>
              <td>{h.healedS} s</td>
              <td className="font-mono">
                {h.from} to {h.to}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    ) : (
      <Empty text="No release shipped yet." />
    )}
  </Section>
);
