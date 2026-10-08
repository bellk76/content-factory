import { useState } from 'react'
import type { ContentResult, MontageResult, Run, ScriptResult } from '../api'

const statusLabel: Record<string, string> = {
  running: 'в работе',
  researched: 'ресёрч',
  revising: 'доработка',
  published: 'очерёдность',
  awaiting_approval: 'ждёт согласования',
  needs_review: 'на проверку',
  approved: 'одобрено',
  rejected: 'отклонено',
  done: 'готово',
  error: 'ошибка',
}

export default function RunCard({
  run,
  onSaveScript,
  onSaveContent,
  onSaveMontage,
}: {
  run: Run
  onSaveScript?: (id: number, script: ScriptResult) => void
  onSaveContent?: (id: number, content: ContentResult) => void
  onSaveMontage?: (id: number, montage: MontageResult) => void
}) {
  const badge = run.review_status ?? run.status
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState<ScriptResult | null>(null)
  const [editingContent, setEditingContent] = useState(false)
  const [draftContent, setDraftContent] = useState<ContentResult | null>(null)
  const [editingMontage, setEditingMontage] = useState(false)
  const [draftMontage, setDraftMontage] = useState<MontageResult | null>(null)

  function startEdit() {
    if (!run.script) return
    setDraft(JSON.parse(JSON.stringify(run.script)) as ScriptResult)
    setEditing(true)
  }

  function save() {
    if (draft && onSaveScript) onSaveScript(run.id, draft)
    setEditing(false)
  }

  function startEditContent() {
    if (!run.content) return
    setDraftContent(JSON.parse(JSON.stringify(run.content)) as ContentResult)
    setEditingContent(true)
  }

  function saveContent() {
    if (draftContent && onSaveContent) onSaveContent(run.id, draftContent)
    setEditingContent(false)
  }

  function startEditMontage() {
    if (!run.montage) return
    setDraftMontage(JSON.parse(JSON.stringify(run.montage)) as MontageResult)
    setEditingMontage(true)
  }

  function saveMontage() {
    if (draftMontage && onSaveMontage) onSaveMontage(run.id, draftMontage)
    setEditingMontage(false)
  }

  return (
    <div className="card">
      <div className="card-head">
        <div>
          <h3>#{run.id} · {run.topic}</h3>
          <span className="muted">{run.brand || 'без бренда'} · {run.created_at}</span>
        </div>
        <span className={`badge status-${badge}`}>{statusLabel[badge] ?? badge}</span>
      </div>
      {run.error && <p className="error">Ошибка: {run.error}</p>}

      {run.script && (
        <section>
          <div className="sec-head">
            <h4>Сценарий</h4>
            {!editing && onSaveScript && (
              <button className="ghost small" onClick={startEdit}>Редактировать</button>
            )}
          </div>

          {editing && draft ? (
            <div className="edit">
              <label>Заголовок
                <input value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })} />
              </label>
              <label>Хук
                <textarea value={draft.hook} onChange={(e) => setDraft({ ...draft, hook: e.target.value })} />
              </label>
              {draft.scenes.map((s, i) => (
                <label key={i}>Сцена {i + 1} <span className="muted">{s.t}s</span>
                  <textarea
                    value={s.text}
                    onChange={(e) => {
                      const scenes = [...draft.scenes]
                      scenes[i] = { ...s, text: e.target.value }
                      setDraft({ ...draft, scenes })
                    }}
                  />
                </label>
              ))}
              <label>CTA
                <input value={draft.cta} onChange={(e) => setDraft({ ...draft, cta: e.target.value })} />
              </label>
              <div className="actions">
                <button onClick={save}>Сохранить</button>
                <button className="ghost" onClick={() => setEditing(false)}>Отмена</button>
              </div>
            </div>
          ) : (
            <>
              <p><b>{run.script.title}</b></p>
              <p className="hook">Хук: {run.script.hook}</p>
              <ol>
                {run.script.scenes.map((s) => (
                  <li key={s.t}>
                    <span className="muted">{s.t.toFixed(0)}s</span> {s.text}
                  </li>
                ))}
              </ol>
              <p className="cta">CTA: {run.script.cta}</p>
            </>
          )}
        </section>
      )}

      {run.content && (
        <section>
          <div className="sec-head">
            <h4>Текст публикации</h4>
            {!editingContent && onSaveContent && (
              <button className="ghost small" onClick={startEditContent}>Редактировать</button>
            )}
          </div>
          {editingContent && draftContent ? (
            <div className="edit">
              <label>Описание
                <textarea
                  value={draftContent.description}
                  onChange={(e) => setDraftContent({ ...draftContent, description: e.target.value })}
                />
              </label>
              <label>Хэштеги (через пробел)
                <input
                  value={draftContent.hashtags.join(' ')}
                  onChange={(e) => setDraftContent({ ...draftContent, hashtags: e.target.value.split(/\s+/).filter(Boolean) })}
                />
              </label>
              {draftContent.captions.map((c, i) => (
                <label key={i}>Вариант заголовка {i + 1}
                  <input
                    value={c}
                    onChange={(e) => {
                      const captions = [...draftContent.captions]
                      captions[i] = e.target.value
                      setDraftContent({ ...draftContent, captions })
                    }}
                  />
                </label>
              ))}
              <div className="actions">
                <button onClick={saveContent}>Сохранить</button>
                <button className="ghost" onClick={() => setEditingContent(false)}>Отмена</button>
              </div>
            </div>
          ) : (
            <>
              <p>{run.content.description}</p>
              <p className="muted">{run.content.hashtags.join(' ')}</p>
            </>
          )}
        </section>
      )}

      {run.montage && (
        <section>
          <div className="sec-head">
            <h4>Монтаж</h4>
            {!editingMontage && onSaveMontage && (
              <button className="ghost small" onClick={startEditMontage}>Редактировать</button>
            )}
          </div>
          {editingMontage && draftMontage ? (
            <div className="edit">
              {draftMontage.timeline.map((m, i) => (
                <div key={i} className="edit-row">
                  <label>t, с
                    <input type="number" value={m.t}
                      onChange={(e) => {
                        const timeline = [...draftMontage.timeline]
                        timeline[i] = { ...m, t: Number(e.target.value) }
                        setDraftMontage({ ...draftMontage, timeline })
                      }} />
                  </label>
                  <label>Сцена
                    <input value={m.scene}
                      onChange={(e) => {
                        const timeline = [...draftMontage.timeline]
                        timeline[i] = { ...m, scene: e.target.value }
                        setDraftMontage({ ...draftMontage, timeline })
                      }} />
                  </label>
                  <label>В кадре
                    <input value={m.asset}
                      onChange={(e) => {
                        const timeline = [...draftMontage.timeline]
                        timeline[i] = { ...m, asset: e.target.value }
                        setDraftMontage({ ...draftMontage, timeline })
                      }} />
                  </label>
                  <label>Переход
                    <input value={m.transition}
                      onChange={(e) => {
                        const timeline = [...draftMontage.timeline]
                        timeline[i] = { ...m, transition: e.target.value }
                        setDraftMontage({ ...draftMontage, timeline })
                      }} />
                  </label>
                </div>
              ))}
              <label>Музыка
                <input value={draftMontage.music} onChange={(e) => setDraftMontage({ ...draftMontage, music: e.target.value })} />
              </label>
              <label>Экспорт
                <input value={draftMontage.export} onChange={(e) => setDraftMontage({ ...draftMontage, export: e.target.value })} />
              </label>
              <label className="row">
                <input type="checkbox" checked={draftMontage.captions}
                  onChange={(e) => setDraftMontage({ ...draftMontage, captions: e.target.checked })} />
                субтитры
              </label>
              <div className="actions">
                <button onClick={saveMontage}>Сохранить</button>
                <button className="ghost" onClick={() => setEditingMontage(false)}>Отмена</button>
              </div>
            </div>
          ) : (
            <>
              <ul>
                {run.montage.timeline.map((m) => (
                  <li key={m.t}>
                    <span className="muted">{m.t.toFixed(0)}s</span> {m.scene} — {m.asset} ({m.transition})
                  </li>
                ))}
              </ul>
              <p className="muted">{run.montage.music} · {run.montage.export} · субтитры: {run.montage.captions ? 'да' : 'нет'}</p>
            </>
          )}
        </section>
      )}

      {run.qa && (
        <section>
          <h4>QA {run.qa.passed ? '✅' : '⚠️'} (score {run.qa.score})</h4>
          {run.qa.issues.length > 0 ? (
            <ul>
              {run.qa.issues.map((i, idx) => (
                <li key={idx}>[{i.severity}] {i.message} → {i.fix}</li>
              ))}
            </ul>
          ) : (
            <p className="muted">Замечаний нет</p>
          )}
        </section>
      )}

      {run.video && (
        <section>
          <h4>Видео</h4>
          <video
            controls
            preload="auto"
            muted
            src={`/api/runs/${run.id}/video`}
            style={{ width: '100%', maxHeight: 460, borderRadius: 12, marginTop: 8, background: '#000' }}
          />
        </section>
      )}

      {run.publish && (
        <section>
          <h4>Публикации площадок</h4>
          <ul>
            {run.publish.map((p) => (
              <li key={p.platform}>{p.platform}: {p.status} {p.post_id ? `(${p.post_id})` : ''}</li>
            ))}
          </ul>
        </section>
      )}

      {run.analytics && (
        <section>
          <h4>Аналитика</h4>
          <p>
            👁 {run.analytics.views} · ❤ {run.analytics.likes} · 💬 {run.analytics.comments} · CTR {run.analytics.ctr}%
          </p>
          <p className="muted">{run.analytics.summary}</p>
        </section>
      )}
    </div>
  )
}
