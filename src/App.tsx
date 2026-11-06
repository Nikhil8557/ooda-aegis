import React, { useEffect, useState } from 'react';
import { SCENARIOS, ScenarioId } from './data/scenarios';
import { useAegis } from './live/useAegis';
import { Navbar, View } from './components/Navbar';
import { ScenarioHeader } from './components/ScenarioHeader';
import { AttackerConsole } from './components/AttackerConsole';
import { OodaBrain } from './components/OodaBrain';
import { ServiceHud } from './components/ServiceHud';
import { HackathonModal } from './components/HackathonModal';
import { RepairView, RolloutView, SandboxView } from './components/DetailViews';

export default function App() {
  const { state, connection, replay, catalog, replayControls, attack, reset, chaos, error } = useAegis();
  const [scenarioId, setScenarioId] = useState<ScenarioId>('path_traversal');
  const [view, setView] = useState<View>('console');
  const [about, setAbout] = useState(false);
  const live = connection === 'live';

  // Follow the scenario the agent is actually handling.
  useEffect(() => {
    if (state?.scenario && state.scenario in SCENARIOS) setScenarioId(state.scenario as ScenarioId);
  }, [state?.scenario]);

  const scenario = SCENARIOS[scenarioId];

  // ?autoplay: used when the home page embeds the dashboard. Plays the recorded run and loops it.
  const autoplay = new URLSearchParams(window.location.search).has('autoplay');
  useEffect(() => {
    if (!autoplay || !replay) return;
    if (!replay.playing) {
      const atEnd = replay.index >= replay.frames.length - 1;
      const id = window.setTimeout(() => {
        if (atEnd) replayControls.seek(0);
        replayControls.speed(2);
        replayControls.play();
      }, atEnd ? 4000 : 800);
      return () => window.clearTimeout(id);
    }
  }, [autoplay, replay?.playing, replay?.index === (replay?.frames.length ?? 0) - 1, replay?.file]);

  // Hooks for the demo-film recorder: jump to a frame, switch view.
  useEffect(() => {
    (window as any).__aegis = {
      frames: replay?.frames.map((f) => f.t) ?? [],
      seek: (i: number) => replayControls.seek(i),
      view: (v: View) => setView(v),
      load: (file: string) => replayControls.load(file),
      file: replay?.file,
    };
  });

  return (
    <div className="min-h-screen bg-ink text-fog flex flex-col">
      <Navbar view={view} setView={setView} connection={connection} onReset={reset} onAbout={() => setAbout(true)} />
      <ScenarioHeader current={scenario} onSelect={setScenarioId} />

      {replay && (
        <div data-film-hide className="bg-deep px-4 sm:px-6 py-2">
          <div className="max-w-7xl mx-auto flex flex-wrap items-center gap-4 text-sm text-mist">
            <button
              onClick={replay.playing ? replayControls.pause : replayControls.play}
              className="px-4 py-1 rounded-sm bg-fog text-ink font-semibold hover:bg-mist cursor-pointer"
            >
              {replay.playing ? 'Pause' : 'Play'}
            </button>
            <select
              value={replay.file}
              onChange={(e) => replayControls.load(e.target.value)}
              className="bg-raise text-fog rounded-sm px-2 py-1"
            >
              {catalog.map((c) => (
                <option key={c.file} value={c.file}>
                  {c.title}
                </option>
              ))}
            </select>
            <input
              type="range"
              min={0}
              max={replay.frames.length - 1}
              value={replay.index}
              onChange={(e) => replayControls.seek(Number(e.target.value))}
              className="flex-1 min-w-[120px] accent-[#CCD0CF]"
            />
            <span className="tabular-nums">
              {Math.round(replay.frames[replay.index].t)} s of {Math.round(replay.frames[replay.frames.length - 1].t)} s
            </span>
            <span className="flex gap-1">
              {[1, 2, 4].map((s) => (
                <button
                  key={s}
                  onClick={() => replayControls.speed(s)}
                  className={`px-2 py-0.5 rounded-sm cursor-pointer ${replay.speed === s ? 'bg-fog text-ink' : 'bg-raise text-fog hover:bg-slate'}`}
                >
                  {s}x
                </button>
              ))}
            </span>
            <span className="w-full sm:w-auto">A recorded live run from a laptop. Clone the repo to run it yourself.</span>
          </div>
        </div>
      )}

      {error && <div className="bg-raise text-attack text-sm px-6 py-2 text-center">{error}</div>}

      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 flex flex-col gap-4">
        {!state && (
          <div className="text-sm text-mist text-center py-24">
            {connection === 'offline' ? 'No live agent and no recorded run found.' : 'Connecting to the agent'}
          </div>
        )}
        {state && view === 'console' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 lg:min-h-[680px]">
            <div className="lg:col-span-4">
              <AttackerConsole
                scenario={scenario}
                lastResult={state.lastResult}
                live={live}
                virtualPatchActive={state.virtualPatch.active}
                version={state.container.version}
                onSend={async (value, malicious) => {
                  await attack(scenario.id, value, malicious);
                }}
              />
            </div>
            <div className="lg:col-span-4">
              <OodaBrain state={state} live={live} onChaos={chaos} />
            </div>
            <div className="lg:col-span-4">
              <ServiceHud state={state} />
            </div>
          </div>
        )}
        {state && view === 'repair' && <RepairView state={state} />}
        {state && view === 'sandbox' && <SandboxView state={state} />}
        {state && view === 'rollout' && <RolloutView state={state} />}
      </main>

      <HackathonModal isOpen={about} onClose={() => setAbout(false)} />

      <footer data-film-hide className="bg-deep px-6 py-4 mt-8">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2 text-sm text-mist">
          <span>
            <span className="font-semibold text-fog">OODA-Aegis</span> by Nikhil Kumar, Meta Global AI Developer Hackathon 2026
          </span>
          <span>Runs on Meta open-weight models: Llama 3.2, Llama 3.1, Muse Glimmer</span>
        </div>
      </footer>
    </div>
  );
}
