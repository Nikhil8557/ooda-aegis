import React, { useEffect, useState } from 'react';
import { Scenario } from '../data/scenarios';
import { RequestResult } from '../live/types';
import { Panel, verdictColor } from './ui';

interface Props {
  scenario: Scenario;
  lastResult: RequestResult | null;
  live: boolean;
  virtualPatchActive: boolean;
  version: string;
  onSend: (value: string, malicious: boolean) => Promise<void>;
}

const verdictText: Record<string, string> = {
  exploited: 'Exploited: the service leaked data or stalled',
  blocked_by_edge: 'Blocked at the proxy by the virtual patch',
  sanitized_by_v2: 'Handled safely by the patched code',
  benign: 'Normal response',
};

export const AttackerConsole: React.FC<Props> = ({ scenario, lastResult, live, virtualPatchActive, version, onSend }) => {
  const [index, setIndex] = useState(0);
  const [value, setValue] = useState(scenario.payloads[0].value);
  const [sending, setSending] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    setIndex(0);
    setValue(scenario.payloads[0].value);
  }, [scenario]);

  const preset = scenario.payloads[index];
  const query = new URLSearchParams({ ...scenario.fixedParams, [scenario.param]: value }).toString();

  const send = async (times = 1) => {
    setSending(true);
    try {
      for (let i = 0; i < times; i++) await onSend(value, preset.malicious);
    } finally {
      setSending(false);
    }
  };

  const r = lastResult;

  return (
    <Panel title="Attacker" note={scenario.cwe}>
      <div className="p-4 flex-1 flex flex-col gap-4 overflow-y-auto">
        <div className="space-y-2">
          <div className="text-sm text-mist">Request, sent through the real Nginx proxy</div>
          <div className="rounded-sm bg-ink px-3 py-2 font-mono text-sm text-fog break-all">
            GET {scenario.endpoint}?{query}
          </div>
        </div>

        <div className="space-y-2">
          <div className="text-sm text-mist">Payloads</div>
          <div className="flex flex-col gap-1">
            {scenario.payloads.map((p, i) => (
              <button
                key={p.name}
                onClick={() => {
                  setIndex(i);
                  setValue(p.value);
                }}
                className={`text-left px-3 py-2 rounded-sm text-sm cursor-pointer ${
                  index === i ? 'bg-slate text-fog' : 'bg-raise text-fog hover:bg-slate'
                }`}
              >
                <div className="flex items-baseline justify-between gap-2">
                  <span className="font-semibold">{p.name}</span>
                  <span className={`text-sm ${p.malicious ? 'text-attack' : 'text-mist'}`}>{p.malicious ? 'attack' : 'legitimate'}</span>
                </div>
                <div className="text-sm text-mist mt-1">{p.description}</div>
              </button>
            ))}
          </div>
        </div>

        <div className="space-y-2">
          <label className="text-sm text-mist block">
            Value of <span className="font-mono text-fog">{scenario.param}</span>
          </label>
          <textarea
            value={value}
            onChange={(e) => setValue(e.target.value)}
            rows={2}
            disabled={!live}
            className="w-full px-3 py-2 font-mono text-sm text-fog bg-ink rounded-sm resize-none disabled:text-mist"
          />
        </div>

        <div className="space-y-2">
          <div className="grid grid-cols-2 gap-2">
            <button
              onClick={() => send(1)}
              disabled={sending}
              className="px-4 py-2 text-sm font-semibold text-ink bg-fog hover:bg-mist disabled:bg-slate disabled:text-mist rounded-sm cursor-pointer"
            >
              {live ? (preset.malicious ? 'Fire attack' : 'Send request') : 'Play recorded run'}
            </button>
            <button
              onClick={() => send(5)}
              disabled={sending || !live}
              className="px-4 py-2 text-sm text-fog bg-raise hover:bg-slate disabled:text-mist rounded-sm cursor-pointer disabled:cursor-default"
            >
              Send 5 times
            </button>
          </div>
          <p className="text-sm text-mist">
            {!live
              ? 'Website mode: this replays a recorded live run. Run it yourself with docker compose.'
              : virtualPatchActive
              ? 'A virtual patch is live at the proxy.'
              : version.includes('vulnerable')
              ? 'The service is still vulnerable.'
              : `Serving patched release ${version}.`}
          </p>
        </div>

        <div className="flex flex-col gap-2 pt-2">
          <div className="flex items-baseline justify-between">
            <span className="text-sm font-semibold text-fog">Response</span>
            {r && (
              <span className="flex items-baseline gap-4">
                <span className={`text-sm font-mono ${verdictColor[r.verdict]}`}>
                  HTTP {r.statusCode}, {Math.round(r.durationMs)} ms
                </span>
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(JSON.stringify(r.responseBody, null, 2));
                    setCopied(true);
                    setTimeout(() => setCopied(false), 1500);
                  }}
                  className="text-sm text-mist hover:text-fog cursor-pointer"
                >
                  {copied ? 'Copied' : 'Copy'}
                </button>
              </span>
            )}
          </div>
          {r && <div className={`text-sm font-semibold ${verdictColor[r.verdict]}`}>{verdictText[r.verdict]}</div>}
          <div className="bg-ink text-fog p-3 rounded-sm font-mono text-sm overflow-auto max-h-56 min-h-[96px]">
            {r ? (
              <pre className="whitespace-pre-wrap break-all leading-relaxed">
                {typeof r.responseBody === 'string' ? r.responseBody : JSON.stringify(r.responseBody, null, 2)}
              </pre>
            ) : (
              <div className="text-mist font-sans">No request sent yet.</div>
            )}
          </div>
        </div>
      </div>
    </Panel>
  );
};
