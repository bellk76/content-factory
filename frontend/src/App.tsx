import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { api, type ContentResult, type MontageResult, type Run, type ScriptResult } from './api'
import RunCard from './components/RunCard'

const KNOWN_PLATFORMS = ['youtube', 'telegram', 'vk', 'device_farm']

export default function App() {
  const [runs, setRuns] = useState<Run[]>([])
  const [topic, setTopic] = useState('')
  const [brand, setBrand] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [platforms, setPlatforms] = useState<string[]>([])
  const [newPlatform, setNewPlatform] = useState('')

  const load = useCallback(async () => {
    try {
      setRuns(await api.list())
      setError(null)
    } catch (e) {
      setError(String(e))
    }
  }, [])

  useEffect(() => {
    void load()
    api.getPlatforms().then((r) => setPlatforms(r.platforms)).catch(() => {})
  }, [load])

  async function onCreate(e: FormEvent) {
    e.preventDefault()
    if (!topic.trim()) return
    setBusy(true)
    try {
      const run = await api.create(topic.trim(), brand.trim())
      setRuns((prev) => [run, ...prev])
      setTopic('')
      setError(null)
    } catch (e) {
      setError(String(e))
    } finally {
      setBusy(false)
    }
  }

  async function action(id: number, kind: 'approve' | 'reject') {
    try {
      const updated = kind === 'approve' ? await api.approve(id) : await api.reject(id)
      setRuns((prev) => prev.map((r) => (r.id === id ? updated : r)))
    } catch (e) {
      setError(String(e))
    }
  }

  async function saveScript(id: number, script: ScriptResult) {
    try {
      const updated = await api.updateScript(id, script)
      setRuns((prev) => prev.map((r) => (r.id === id ? updated : r)))
    } catch (e) {
      setError(String(e))
    }
  }

  async function saveContent(id: number, content: ContentResult) {
    try {
      const updated = await api.updateContent(id, content)
      setRuns((prev) => prev.map((r) => (r.id === id ? updated : r)))
    } catch (e) {
      setError(String(e))
    }
  }

  async function saveMontage(id: number, montage: MontageResult) {
    try {
      const updated = await api.updateMontage(id, montage)
      setRuns((prev) => prev.map((r) => (r.id === id ? updated : r)))
    } catch (e) {
      setError(String(e))
    }
  }

  function togglePlatform(p: string) {
    setPlatforms((prev) => (prev.includes(p) ? prev.filter((x) => x !== p) : [...prev, p]))
  }

  function addPlatform() {
    const p = newPlatform.trim().toLowerCase()
    if (p && !platforms.includes(p)) setPlatforms([...platforms, p])
    setNewPlatform('')
  }

  async function savePlatforms() {
    try {
      const r = await api.setPlatforms(platforms)
      setPlatforms(r.platforms)
      setError(null)
    } catch (e) {
      setError(String(e))
    }
  }

  async function publish(id: number) {
    try {
      const updated = await api.publishRun(id)
      setRuns((prev) => prev.map((r) => (r.id === id ? updated : r)))
      setError(null)
    } catch (e) {
      setError(String(e))
    }
  }

  async function render(id: number) {
    try {
      const updated = await api.renderRun(id)
      setRuns((prev) => prev.map((r) => (r.id === id ? updated : r)))
      setError(null)
    } catch (e) {
      setError(String(e))
    }
  }

  return (
    <div className="app">
      <header>
        <h1>content-factory</h1>
        <p className="muted">Мультиагентная система производства контента · рабочее место оператора</p>
      </header>

      <section className="settings">
        <h4>Площадки публикации</h4>
        <div className="chips">
          {[...KNOWN_PLATFORMS, ...platforms.filter((p) => !KNOWN_PLATFORMS.includes(p))].map((p) => (
            <label key={p} className={`chip ${platforms.includes(p) ? 'on' : ''}`}>
              <input type="checkbox" checked={platforms.includes(p)} onChange={() => togglePlatform(p)} /> {p}
            </label>
          ))}
        </div>
        <div className="create">
          <input
            placeholder="Добавить площадку (напр. rutube)"
            value={newPlatform}
            onChange={(e) => setNewPlatform(e.target.value)}
          />
          <button type="button" onClick={addPlatform}>Добавить</button>
          <button type="button" onClick={savePlatforms}>Сохранить площадки</button>
        </div>
      </section>

      <form className="create" onSubmit={onCreate}>
        <input
          placeholder="Тема ролика (например: входные двери)"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
        />
        <input placeholder="Бренд" value={brand} onChange={(e) => setBrand(e.target.value)} />
        <button type="submit" disabled={busy}>
          {busy ? 'Генерирую…' : 'Создать прогон'}
        </button>
      </form>

      {error && <div className="error">{error}</div>}

      <div className="list">
        {runs.map((run) => (
          <div key={run.id} className="run">
            <RunCard
              run={run}
              onSaveScript={saveScript}
              onSaveContent={saveContent}
              onSaveMontage={saveMontage}
            />
            {run.content && (
              <div className="actions">
                {(run.review_status === 'awaiting_approval' || run.review_status === 'needs_review') && (
                  <>
                    <button onClick={() => action(run.id, 'approve')}>Одобрить</button>
                    <button className="ghost" onClick={() => action(run.id, 'reject')}>Отклонить</button>
                  </>
                )}
                <button className="ghost" onClick={() => render(run.id)}>Сгенерировать видео</button>
                <button onClick={() => publish(run.id)}>Опубликовать</button>
              </div>
            )}
          </div>
        ))}
        {runs.length === 0 && <p className="muted">Пока нет прогонов — создайте первый.</p>}
      </div>
    </div>
  )
}
