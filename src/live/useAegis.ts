import { useCallback, useEffect, useRef, useState } from 'react';
import { AegisState, ReplayFrame, RequestResult } from './types';

// Live: the dashboard is served next to the agent (docker compose) and talks to /api.
// Replay: the public website has no agent, so it plays back a recorded live run.
const API = (import.meta as any).env?.VITE_AGENT_URL ?? '';

export type Connection = 'connecting' | 'live' | 'replay' | 'offline';

export interface Replay {
  name: string;
  title: string;
  file: string;
  frames: ReplayFrame[];
  index: number;
  playing: boolean;
  speed: number;
}

export function useAegis() {
  const [state, setState] = useState<AegisState | null>(null);
  const [connection, setConnection] = useState<Connection>('connecting');
  const [replay, setReplay] = useState<Replay | null>(null);
  const [catalog, setCatalog] = useState<{ name: string; title: string; file: string }[]>([]);
  const [error, setError] = useState<string | null>(null);
  const timer = useRef<number | null>(null);

  // Try the live agent first; fall back to recorded runs.
  useEffect(() => {
    const forceReplay = new URLSearchParams(window.location.search).has('replay');
    let source: EventSource | null = null;
    let settled = false;
    const goReplay = async () => {
      if (settled) return;
      settled = true;
      source?.close();
      setConnection('replay');
      try {
        const list = await fetch(`${import.meta.env.BASE_URL}replays/index.json`).then((r) => r.json());
        setCatalog(list);
        if (list.length) await loadReplay(list[0].file, list[0].name, list[0].title);
      } catch {
        setConnection('offline');
      }
    };
    if (forceReplay) {
      goReplay();
      return;
    }
    source = new EventSource(`${API}/api/events`);
    source.onmessage = (event) => {
      settled = true;
      setConnection('live');
      setState(JSON.parse(event.data));
    };
    source.onerror = () => {
      if (!settled) goReplay();
    };
    const fallback = window.setTimeout(goReplay, 2500);
    return () => {
      window.clearTimeout(fallback);
      source?.close();
    };
  }, []);

  const loadReplay = useCallback(async (file: string, name: string, title: string) => {
    const text = await fetch(`${import.meta.env.BASE_URL}replays/${file}`).then((r) => r.text());
    const frames: ReplayFrame[] = text
      .split('\n')
      .filter(Boolean)
      .map((line) => JSON.parse(line));
    setReplay({ name, title, file, frames, index: 0, playing: false, speed: 1 });
    setState({ ...frames[0].state, mode: 'replay' });
  }, []);

  // Replay clock: advance frames using their recorded timestamps.
  useEffect(() => {
    if (!replay || !replay.playing) return;
    const { frames, index, speed } = replay;
    if (index >= frames.length - 1) {
      setReplay((r) => (r ? { ...r, playing: false } : r));
      return;
    }
    const gap = Math.max(0, (frames[index + 1].t - frames[index].t) * 1000) / speed;
    timer.current = window.setTimeout(() => {
      setReplay((r) => {
        if (!r) return r;
        const next = Math.min(r.index + 1, r.frames.length - 1);
        setState({ ...r.frames[next].state, mode: 'replay' });
        return { ...r, index: next };
      });
    }, Math.min(gap, 4000 / speed));
    return () => {
      if (timer.current) window.clearTimeout(timer.current);
    };
  }, [replay]);

  const replayControls = {
    play: () => setReplay((r) => (r ? { ...r, playing: true, index: r.index >= r.frames.length - 1 ? 0 : r.index } : r)),
    pause: () => setReplay((r) => (r ? { ...r, playing: false } : r)),
    seek: (index: number) =>
      setReplay((r) => {
        if (!r) return r;
        const i = Math.max(0, Math.min(index, r.frames.length - 1));
        setState({ ...r.frames[i].state, mode: 'replay' });
        return { ...r, index: i };
      }),
    speed: (speed: number) => setReplay((r) => (r ? { ...r, speed } : r)),
    load: (file: string) => {
      const item = catalog.find((c) => c.file === file);
      if (item) loadReplay(item.file, item.name, item.title);
    },
  };

  const post = useCallback(async (path: string, body?: unknown) => {
    setError(null);
    const r = await fetch(`${API}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!r.ok) {
      const detail = await r.json().catch(() => ({ detail: r.statusText }));
      setError(detail.detail || 'Request failed');
      throw new Error(detail.detail);
    }
    return r.json();
  }, []);

  const attack = useCallback(
    async (scenario: string, value: string, malicious: boolean): Promise<RequestResult | null> => {
      if (connection !== 'live') {
        // In replay mode the console starts the recording instead of sending traffic.
        replayControls.play();
        return null;
      }
      return post('/api/attack', { scenario, value, malicious });
    },
    [connection, post],
  );

  const reset = useCallback(async () => {
    if (connection === 'live') await post('/api/reset').catch(() => undefined);
    else replayControls.seek(0);
  }, [connection, post]);

  const chaos = useCallback(async () => post('/api/chaos').catch(() => undefined), [post]);

  return { state, connection, replay, catalog, replayControls, attack, reset, chaos, error };
}
