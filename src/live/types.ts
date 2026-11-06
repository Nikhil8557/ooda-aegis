// Shape of the state the OODA-Aegis agent streams (see infrastructure/agent/aegis/engine.py).

export type Verdict = 'benign' | 'exploited' | 'blocked_by_edge' | 'sanitized_by_v2';

export interface TraceStep {
  id: string;
  timestamp: string;
  horizon: string;
  phase: 'Observe' | 'Orient' | 'Decide' | 'Act';
  summary: string;
  details: string;
  toolCall?: { name: string; input: Record<string, unknown>; output: string };
}

export interface LogEntry {
  id: string;
  timestamp: string;
  method: string;
  endpoint: string;
  payload: string;
  statusCode: number;
  durationMs: number;
  statusText: string;
  verdict: Verdict;
  containerVersion: string;
}

export interface RequestResult {
  statusCode: number;
  durationMs: number;
  statusText: string;
  responseBody: unknown;
  verdict: Verdict;
  containerVersion: string;
  uri: string;
}

export interface FuzzCase {
  id: string;
  technique: string;
  mutatedPayload: string;
  status: 'pending' | 'blocked' | 'bypassed';
  edgeCovered: boolean;
}

export interface FleetNode {
  id: string;
  name: string;
  zone: string;
  status: 'vulnerable' | 'vaccine_received' | 'immune';
  syncLatencyMs: number;
}

export interface TestCase {
  name: string;
  outcome: 'passed' | 'failed' | 'skipped';
  message: string;
  seconds: number;
}

export interface SandboxPhase {
  passed: boolean;
  output: string;
  counts: { passed: number; failed: number; skipped: number };
  per_test: TestCase[];
}

export interface ModelInfo {
  role: string;
  label: string;
  model: string;
  endpoint: string;
}

export interface AegisState {
  mode: 'live' | 'replay';
  models: { edge: ModelInfo; repair: ModelInfo };
  phase: string;
  busy: boolean;
  scenario: string | null;
  incident: { id: string; scenario: string; startedAt: string; uri: string } | null;
  virtualPatch: {
    active: boolean;
    regex: string | null;
    ruleId: string | null;
    model: string | null;
    modelLatencyMs: number | null;
    reloadMs: number | null;
    attempts: { attempt: number; rule?: string; regex: string | null; ok: boolean; reason: string; latencyMs: number }[];
  };
  container: { active: string; version: string; previous: string | null };
  trafficSplit: { old: number; new: number };
  trace: TraceStep[];
  logs: LogEntry[];
  lastResult: RequestResult | null;
  fuzz: FuzzCase[];
  fleet: FleetNode[];
  canary: {
    status: 'idle' | 'probation_monitoring' | 'healthy_promoted' | 'rollback_executed';
    probesOk: number;
    probesFailed: number;
    step: string | null;
    p99LatencyMs: number;
    circuitBreakerTripped: boolean;
  };
  repair: {
    file: string;
    before: string;
    after: string | null;
    diff: string | null;
    rootCause: string | null;
    cwe: string | null;
    testCode: string | null;
    attempts: { attempt: number; ok: boolean; reason: string }[];
    model: string;
    latencyMs: number | null;
  } | null;
  sandbox: {
    ok: boolean;
    reason: string;
    reproducesOnV1: boolean | null;
    modelTestPassed?: boolean | null;
    v1: SandboxPhase | null;
    v2: SandboxPhase | null;
  } | null;
  metrics: {
    requests: number;
    blocked: number;
    exploited: number;
    remediated: number;
    avgLatencyMs: number;
    errorRatePercent: number;
    cpu: number;
    memoryMb: number;
    fuzzPassRate: number | null;
    fleetImmune: number;
    timeToContainS: number | null;
    timeToHealS: number | null;
  };
  history: { incident: string; scenario: string; from: string; to: string; healedS: number; containS: number | null }[];
}

export interface ReplayFrame {
  t: number;
  state: AegisState;
}
