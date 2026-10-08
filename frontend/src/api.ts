export interface ScriptScene { t: number; text: string; visual: string }
export interface ScriptResult {
  title: string
  hook: string
  scenes: ScriptScene[]
  cta: string
  duration_sec: number
}
export interface ContentResult { description: string; hashtags: string[]; captions: string[] }
export interface MontageShot { t: number; scene: string; asset: string; transition: string }
export interface MontageResult { timeline: MontageShot[]; music: string; captions: boolean; export: string }
export interface QAIssue { severity: string; message: string; fix: string }
export interface QAReport { passed: boolean; score: number; issues: QAIssue[] }
export interface PublishResult { platform: string; status: string; post_id: string | null; url: string | null }
export interface AnalyticsResult { views: number; likes: number; comments: number; ctr: number; summary: string }

export interface Run {
  id: number
  created_at: string
  topic: string
  brand: string
  status: string
  review_status: string | null
  error: string | null
  iteration: number
  score: number | null
  video?: string | null
  script?: ScriptResult
  content?: ContentResult
  montage?: MontageResult
  qa?: QAReport
  publish?: PublishResult[]
  analytics?: AnalyticsResult
}

const base = '/api'

async function json<T>(r: Response): Promise<T> {
  if (!r.ok) throw new Error(await r.text())
  return r.json() as Promise<T>
}

export const api = {
  list: () => fetch(`${base}/runs`).then(json<Run[]>),
  get: (id: number) => fetch(`${base}/runs/${id}`).then(json<Run>),
  create: (topic: string, brand: string) =>
    fetch(`${base}/runs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic, brand }),
    }).then(json<Run>),
  approve: (id: number) => fetch(`${base}/runs/${id}/approve`, { method: 'POST' }).then(json<Run>),
  reject: (id: number) => fetch(`${base}/runs/${id}/reject`, { method: 'POST' }).then(json<Run>),
  updateScript: (id: number, script: ScriptResult) =>
    fetch(`${base}/runs/${id}/script`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(script),
    }).then(json<Run>),
  updateContent: (id: number, content: ContentResult) =>
    fetch(`${base}/runs/${id}/content`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(content),
    }).then(json<Run>),
  updateMontage: (id: number, montage: MontageResult) =>
    fetch(`${base}/runs/${id}/montage`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(montage),
    }).then(json<Run>),
  publishRun: (id: number) => fetch(`${base}/runs/${id}/publish`, { method: 'POST' }).then(json<Run>),
  renderRun: (id: number) => fetch(`${base}/runs/${id}/render`, { method: 'POST' }).then(json<Run>),
  getPlatforms: () => fetch(`${base}/settings/platforms`).then(json<{ platforms: string[] }>),
  setPlatforms: (platforms: string[]) =>
    fetch(`${base}/settings/platforms`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ platforms }),
    }).then(json<{ platforms: string[] }>),
}
