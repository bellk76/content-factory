# content-factory

Мультиагентная AI-система для автоматизации производства контента: от идеи и
сценария до публикации на нескольких площадках и анализа результатов.

> Демонстрационный проект: полный цикл **идея → сценарий → генерация → монтаж →
> рендер видео → контроль качества → публикация → аналитика → обратная связь**.
> Работает без ключей (mock-режим) и переключается на реальные модели/сервисы
> переменными окружения. Рендер видео включается `RENDER_VIDEO=true`.

## Демонстрация

- **Обзор и полный цикл** (как работает, какие модели подключаются): [docs/fullcycle.mp4](docs/fullcycle.mp4) · [YouTube](https://youtu.be/deera_mybPs)
- **Ролик, собранный и опубликованный системой**: [docs/reel.mp4](docs/reel.mp4) · [YouTube](https://youtu.be/jVesRSVvi2E)

Полный цикл одной командой (рендер + реальная публикация на YouTube):

```bash
# нужны YOUTUBE_CLIENT_ID / YOUTUBE_CLIENT_SECRET / YOUTUBE_REFRESH_TOKEN
RENDER_VIDEO=true PUBLISH_DRY_RUN=false python -m app.cli run --topic "Двери тест"
# -> data/videos/run_<id>.mp4  и  загрузка на YouTube (см. services/youtube.py)
```

Без ключей всё работает в mock-режиме и dry-run — удобно для демонстрации логики.

## Статус и ограничения

Прототип проходит **весь цикл end-to-end**, но часть звеньев — демонстрационные:

- **Генерация текста** по умолчанию идёт через **mock-режим** (заглушка-шаблон без ключа модели), поэтому контент для разных тем может повторяться. Подключение реальной LLM (`.env`: `LLM_PROVIDER=openai` + `LLM_BASE_URL/LLM_API_KEY/LLM_MODEL`) снимает это ограничение и даёт уникальный текст под каждую идею.
- **Идея** задаётся оператором вручную (автогенерации идей и трендов нет).
- **Генерация визуала** — фото из библиотеки `data/assets`; AI-генерации изображений пока нет.
- **Аналитика метрик** условная (не тянет реальные данные с площадок); обратная связь реализована через запись лучших хуков в базу знаний.
- **Публикация:** YouTube — рабочий адаптер (OAuth2); Telegram — готов, нужен токен; «ферма устройств» — очередь-заглушка.
- **Аутентификация:** по умолчанию API без авторизации (для локального демо). Для сетевого доступа задайте `API_TOKEN` — тогда мутирующие эндпоинты требуют заголовок `x-api-key`; запускайте на `127.0.0.1`.

Что при этом **реально работает**: оркестрация агентов (LangGraph), валидация structured output, цикл контроля качества, рендер видео (ffmpeg: озвучка, субтитры, музыка) и публикация на YouTube.

## Полный цикл: как работает и варианты интеграции

По каждому этапу — как работает сейчас и какие модели/сервисы можно подключить (от дешёвых к дорогим). Цены ориентировочные.

**1. Идея.** Сейчас тему вводит оператор.
- Дёшево/бесплатно: ручной ввод · контент-план (таблица/CSV) · Google Trends, Яндекс Wordstat · генерация идей дешёвой LLM (доли цента).
- Дорого: тренд-сервисы — Brand Analytics, Semrush, Ahrefs, SimilarWeb, TrendHunter ($100–500+/мес).

**2. Сценарий (LLM).** Сейчас — агент `script` через OpenAI-совместимый клиент.
- Дешёвые: DeepSeek-V3 (~$0.14–0.28/1M), GPT-4o-mini (~$0.15/1M), Gemini Flash (~$0.1/1M), Qwen, Mistral.
- Средние: Claude Haiku (~$0.25–1.25/1M), GPT-4.1-mini, Gemini Pro.
- Дорогие: GPT-4o (~$2.5–10/1M), Claude Sonnet (~$3–15/1M), Claude Opus / GPT-5 (до $15–75/1M).
- Сценарий (~3k токенов): от <$0.01 (DeepSeek/mini) до $0.1–0.5 (Opus). Локально (Ollama/vLLM) — бесплатно, нужен GPU.

**3. Генерация (текст + визуал).** Сейчас: текст — LLM, визуал — фото из библиотеки.
- Дешёвые картинки: Flux Schnell (~$0.003/шт), SDXL локально (бесплатно), YandexART (рубли, дёшево), Kandinsky.
- Средние: DALL·E 3 (~$0.04–0.08/шт), Flux Pro (~$0.05/шт), Ideogram; Midjourney (~$10–60/мес).
- Дорого — text-to-video: Runway Gen-3 (~$0.05–0.1/сек), Kling, Luma, Pika, Google Veo, Sora ($0.1–1+/сек); ролик 30 с ≈ $5–30.

**4. Монтаж (сборка + озвучка + музыка).** Сейчас: сборка ffmpeg, озвучка piper (офлайн), музыка процедурная.
- TTS дёшево: piper, SAPI, Silero (бесплатно).
- TTS средне: Yandex SpeechKit (рубли за символы), Google TTS.
- TTS дорого: ElevenLabs ($5–330/мес), PlayHT, OpenAI TTS.
- Сборка: ffmpeg (бесплатно) · Shotstack/Creatomate ($0.1–1/рендер или подписка).
- Музыка: процедурная (бесплатно) · Suno/Udio (~$10–30/мес) · Epidemic Sound (~$15/мес).

**5. Проверка (QA).** Сейчас: агент `qa` (LLM-судья) + цикл доработки; оператор «Одобрить/Отклонить».
- Дёшево: правила (стоп-слова, длина, соответствие ТЗ) — бесплатно; LLM-судья на mini/DeepSeek (<$0.01).
- Дорого: сильная LLM-судья (GPT-4o/Claude Sonnet) — $0.02–0.1 за проверку; платформы эвалов (Langfuse/LangSmith — free tier, платно от ~$40/мес).

**6. Публикация.** Сейчас: адаптеры площадок (YouTube рабочий, Telegram готов, VK/ферма — расширение), кнопка «Опубликовать».
- Бесплатно: YouTube Data API (квота ~6 загрузок/сутки), Telegram Bot API, VK API, Rutube, Дзен.
- Средне: агрегаторы (Buffer, Publer, SMMplanner) — $5–100/мес.
- Дорого: Hootsuite и т.п. (~$99+/мес); «ферма устройств» — железо + обслуживание.

**7. Анализ.** Сейчас: метрики условные; лучшие хуки — в базу знаний.
- Бесплатно: YouTube Analytics API, VK/TG stats, Google Sheets / Looker Studio, Metabase (self-hosted).
- Средне: Power BI (~$10/польз./мес), Amplitude/Mixpanel (free tier → платно).
- Дорого: Roistat/Calltouch (сквозная аналитика) — ~5–30 тыс ₽/мес.

**Стоимость одного ролика:** базовый (наш подход + AI-картинки) ~$0.05–0.1 · средний (сильная LLM + нейро-TTS) ~$0.2–0.5 · text-to-video ~$5–30.

## Архитектура

```
        (оператор задаёт тему)
                 │
                 ▼
  ┌───────────────────────────── мультиагентный граф ────────────────────────────┐
  │                                                                              │
  │   research ─▶ script ─▶ generate ─▶ montage ─▶ qa ──(fail)──▶ script (цикл)   │
  │                                                  │                           │
  │                                            (pass)│                           │
  │                                                  ▼                           │
  │                                            render ─▶ publish ─▶ analytics     │
  │                                                │           │                 │
  └────────────────────────────────────────────────┼───────────┼─────────────────┘
                                                   │           │
                         адаптеры площадок ◀────────┘           └──▶ метрики
                         ├─ YouTube (рабочий, OAuth2)               │
                         ├─ Telegram (готов) / VK (расширение)      ▼
                         └─ Ферма устройств (очередь) ────▶ база знаний (few-shot)
                                                                    │
                                       корректировка промптов ◀──────┘
```

**Агенты (каждый возвращает валидируемый structured output):**

| Агент      | Что делает                                             |
|------------|--------------------------------------------------------|
| research   | ресёрч темы: аудитория, хуки, факты, ракурсы           |
| script     | сценарий: хук, сцены с таймингами, CTA                 |
| generate   | генерация: описание, хэштеги, варианты заголовка       |
| montage    | план монтажа: таймлайн, кадры, переходы, экспорт       |
| qa         | контроль качества (LLM-as-judge): оценка и правки      |
| render     | сборка видео из сценария (ffmpeg: кадры, озвучка, музыка) |
| publish    | публикация через адаптеры площадок                     |
| analytics  | метрики → вывод → запись лучших хуков в базу знаний    |

**Обратная связь:** `analytics` сохраняет метрики и лучшие хуки в базу знаний;
`retrieval` подтягивает их как few-shot при следующем прогоне — система учится
на результатах публикаций.

## Соответствие требованиям вакансии

| Требование (вакансия)                                  | Реализация в проекте                          |
|--------------------------------------------------------|-----------------------------------------------|
| Мультиагентная AI-система для производства контента    | LangGraph-граф из 7 агентов                   |
| Взаимодействие агентов: ресёрч, сценарии, генерация, монтаж, контроль | одноимённые узлы + замыкание QA на доработку |
| Единая база знаний и накопление результатов публикаций | SQLite: runs / metrics / knowledge            |
| Обратная связь: метрики → анализ → корректировка       | analytics → knowledge → few-shot в промптах   |
| Интерфейс оператора: проверка, согласование/доработка  | React + FastAPI (approve/reject)              |
| Публикация на несколько площадок + ферма устройств     | адаптеры YouTube/Telegram/VK + device farm    |
| Архитектура и интеграции (модели, сервисы, БД)         | provider-agnostic LLM-клиент, Store, адаптеры |
| Fullstack (backend + frontend)                         | FastAPI + React/Vite                          |

## Стек

- **Python 3.12**, FastAPI, LangGraph (с fallback-harness), Pydantic (structured output)
- **SQLite** (легко заменить на PostgreSQL — интерфейс `Store`)
- **React 19 + TypeScript + Vite** (интерфейс оператора)
- LLM: любой OpenAI-совместимый шлюз (OpenAI, DeepSeek, OpenRouter, локальный vLLM/ollama)

## Быстрый старт (mock, без ключей)

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows
pip install -r requirements.txt

# CLI: прогнать конвейер
python -m app.cli run --topic "входные двери" --brand "Фабрика Браво"
python -m app.cli list

# API
uvicorn app.api.main:app --reload      # http://localhost:8000/docs

# Тесты и эвалы
pytest -q
python -m evals.run_evals
```

## Реальные модели

Скопируйте `.env.example` в `.env` и укажите:

```
LLM_PROVIDER=openai
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_API_KEY=...
LLM_MODEL=deepseek-chat
```

## Фронтенд оператора

```bash
cd frontend
npm install
npm run dev        # http://localhost:5180 (проксирует /api на :8000)
```

## Структура

```
app/
  config.py                 настройки (env/.env)
  llm/
    client.py               провайдер-агностичный клиент (mock + openai)
    schemas.py              structured output (Pydantic) для каждого агента
  agents/prompts.py         системные промпты
  graph/
    state.py                состояние конвейера
    nodes.py                агенты + QA + публикация + аналитика (harness)
    build.py                сборка LangGraph и запуск (с fallback)
  kb/
    storage.py              SQLite: прогоны, метрики, база знаний, step_logs
    retrieval.py            few-shot из базы знаний
  services/
    publisher.py            адаптеры площадок + ферма устройств (очередь)
    youtube.py              загрузка видео на YouTube (OAuth2, resumable)
    tts.py                  синтез речи: piper | sapi | yandex | elevenlabs
    video.py                рендер mp4: кадры + озвучка + музыка + ffmpeg
    music.py                процедурная фоновая музыка (без авторских прав)
  api/main.py               FastAPI
  cli.py                    CLI
evals/                      датасет + раннер мини-эвала
scripts/video_proof.py      сборка демо-ролика (Pillow + pyttsx3 + ffmpeg)
tests/                      pytest
frontend/                   React + Vite (интерфейс оператора)
.github/workflows/ci.yml    CI: тесты + эвалы
```

## Как из сценария получается видео

Цикл «сценарий → видео» реализован так:

1. Агент **`script`** возвращает сцены с текстом и таймингами (хук, 3–4 сцены, CTA).
2. Агент **`montage`** формирует план монтажа (кадры, переходы, параметры экспорта).
3. Узел **`render`** (сервис `app/services/video.py`) собирает **реальный mp4**:
   - кадры под каждую сцену (Pillow: изображение + текст-субтитр),
   - озвучка (**TTS**: piper / sapi / yandex / elevenlabs),
   - фоновая музыка (процедурная, `music.py`),
   - склейка и микс — **ffmpeg** → вертикальный ролик 1080×1920.
4. Кадры сейчас берутся из библиотеки `data/assets`. Для «настоящей» генерации подключается провайдер:
   - **`ImageProvider`** — по одной AI-картинке на сцену (Flux, SDXL, DALL·E 3, YandexART, Kandinsky) + наш монтаж;
   - **`VideoProvider`** — text-to-video клипы (Runway, Kling, Luma, Pika, Veo) вместо статичных кадров.

Команда:

```bash
RENDER_VIDEO=true python -m app.cli run --topic "Двери тест"   # -> data/videos/run_<id>.mp4
```

## Рендер и публикация

Монтаж реализован в сервисе `app/services/video.py` и встроен в граф узлом
`render` (между `qa` и `publish`). Собирает реальный mp4 1080x1920: кадры
(Pillow, фото-фон «карточкой» + текст) → озвучка (TTS) → фоновая музыка
(процедурная) → микс и склейка (ffmpeg из `imageio-ffmpeg`).

```bash
pip install -r requirements-media.txt   # imageio-ffmpeg, Pillow, numpy, piper-tts, pyttsx3

# включить рендер в пайплайне
RENDER_VIDEO=true python -m app.cli run --topic "Двери тест"   # -> data/videos/run_<id>.mp4

# отдельно, без пайплайна
python scripts/video_proof.py --topic "Двери тест" --out data/reel.mp4
```

Голос: `TTS_PROVIDER=piper` (офлайн нейро, по умолчанию) / `sapi` / `yandex` /
`elevenlabs`. Публикация видео: `youtube.py` (OAuth2 + resumable upload; без
ключей — dry-run), Telegram (`sendVideo`), VK и «ферма устройств» — точки
расширения. Для включения YouTube задайте `YOUTUBE_CLIENT_ID`,
`YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN` и `PUBLISH_DRY_RUN=false`.

## Заметки об инженерных решениях

- **Structured output везде** — каждый шаг возвращает JSON по Pydantic-схеме,
  поэтому результат валидируется, а не «просто текст».
- **QA-цикл** — брак не идёт дальше: при `fail` управление возвращается на
  `script` (ограничено `MAX_QA_ITERATIONS`).
- **Framework vs harness** — граф собирается на LangGraph, но есть встроенный
  fallback, поэтому демо запускается где угодно; это осознанный выбор.
- **Наблюдаемость** — latency и успешность каждого шага пишутся в `step_logs`.
- **Расширяемость** — новая площадка публикации = новый адаптер, пайплайн не меняется.
