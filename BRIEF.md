# БРИФ: Resume Builder AI

> Читай этот файл целиком перед началом работы. Здесь вся архитектура, задания, промпты и API.

---

## 1. Суть проекта

Веб-сервис, который:
1. Регистрирует пользователя и сохраняет его постоянные данные
2. Принимает ссылку на вакансию или её текстовое описание
3. Запускает AI-чат, который задаёт точечные вопросы для сбора недостающих данных
4. Генерирует резюме через **ChatGPT-5 (ТОЛЬКО эта модель, никакая другая)** в формате JSON
5. Конвертирует JSON → PDF и отдаёт пользователю готовый файл
6. Сохраняет историю всех резюме в аккаунте пользователя

---

## 2. Стек

| Слой | Технология |
|---|---|
| Бэкенд | Python, FastAPI |
| База данных | SQLite (через SQLAlchemy) |
| AI | OpenAI API, модель **`gpt-5`** — СТРОГО эта, никакая другая |
| PDF | WeasyPrint |
| Фронтенд | Next.js + TypeScript + Tailwind + shadcn/ui |
| Чат UI | shadcn-chatbot-kit |
| Авторизация | JWT (access + refresh токены) |
| Деплой | Локально |

---

## 3. Страницы приложения

| Страница | Маршрут | Доступ |
|---|---|---|
| Регистрация | `/register` | Публичная |
| Онбординг (постоянные данные) | `/onboarding` | После регистрации |
| Вход | `/login` | Публичная |
| Главная (чат + вакансия) | `/` | Авторизованные |
| История резюме | `/history` | Авторизованные |
| Настройки | `/settings` | Авторизованные |

---

## 4. Описание страниц

### `/register` — Регистрация
Поля:
- Номер телефона
- Email
- Пароль
- Повтор пароля (валидация совпадения на фронте и бэке)

После успешной регистрации → редирект на `/onboarding`

---

### `/onboarding` — Постоянные данные (после регистрации)
Показывается один раз после регистрации.

Текст: *"Хочешь заполнить базовые данные? Мы будем подставлять их в каждое резюме автоматически."*

Две кнопки: **"Заполнить"** / **"Пропустить"**

Если "Заполнить" — форма со следующими полями:
- Имя и фамилия
- Город
- Телефон (предзаполнен с регистрации)
- Email (предзаполнен с регистрации)
- Ссылка на hh.ru
- Ссылка на GitHub / портфолио
- Вуз
- Факультет
- Специальность
- Год окончания / курс
- Языки (язык + уровень, можно добавлять несколько)

После сохранения или пропуска → редирект на `/`

---

### `/login` — Вход
- Поле: телефон или email (одно поле, определять автоматически по формату)
- Пароль
- Кнопка "Войти"

---

### `/` — Главная страница
Два состояния:

**Состояние 1 — ввод вакансии:**
- Поле для URL вакансии (hh.ru и др.)
- ИЛИ текстовое поле для вставки описания вакансии
- Кнопка "Начать"

**Состояние 2 — чат:**
- После нажатия "Начать" на той же странице появляется чат
- AI задаёт вопросы, собирает данные (постоянные данные пользователя уже известны — AI их НЕ спрашивает)
- Когда `is_complete = true` — показывается лоадер "Генерирую резюме..."
- После генерации → показывается превью резюме + кнопка "Скачать PDF"

---

### `/history` — История резюме
Список всех резюме пользователя. Для каждого:
- Название вакансии
- Краткое описание (первые 100 символов из vacancy_text)
- Дата создания
- Кнопка "Скачать PDF"

---

### `/settings` — Настройки
Два раздела:

**1. Личные данные** — те же поля что и в онбординге, редактируемые. Кнопка "Сохранить".

**2. Безопасность** — три отдельных блока, каждый с подтверждением текущего пароля:
- Смена пароля (старый пароль → новый пароль → повтор нового)
- Смена email (новый email + текущий пароль)
- Смена телефона (новый телефон + текущий пароль)

---

## 5. API эндпоинты

### AUTH

#### POST /auth/register
```json
// Request
{
  "phone": "+79991234567",
  "email": "user@mail.ru",
  "password": "secret123",
  "password_confirm": "secret123"
}
// Response 201
{
  "user_id": "usr_abc",
  "access_token": "...",
  "refresh_token": "..."
}
```

#### POST /auth/login
```json
// Request
{
  "login": "+79991234567",
  "password": "secret123"
}
// Response 200
{
  "access_token": "...",
  "refresh_token": "..."
}
```

#### POST /auth/refresh
```json
// Request
{ "refresh_token": "..." }
// Response 200
{ "access_token": "..." }
```

#### POST /auth/change-password
```json
// Request (авторизован, Bearer токен)
{
  "old_password": "...",
  "new_password": "...",
  "new_password_confirm": "..."
}
```

#### POST /auth/change-email
```json
// Request (авторизован)
{ "new_email": "new@mail.ru", "password": "..." }
```

#### POST /auth/change-phone
```json
// Request (авторизован)
{ "new_phone": "+79990000000", "password": "..." }
```

---

### PROFILE

#### GET /profile
Вернуть постоянные данные текущего пользователя.

#### PUT /profile
```json
// Request (авторизован)
{
  "name": "Богдан Верстов",
  "city": "Москва",
  "phone": "+79991234567",
  "email": "user@mail.ru",
  "link_hh": "https://hh.ru/resume/...",
  "link_portfolio": "https://github.com/...",
  "university": "Центральный университет",
  "faculty": "Бизнес и Аналитика",
  "speciality": "Бизнес-информатика",
  "graduation_year": "2027",
  "languages": [
    { "language": "Английский", "level": "B1" }
  ]
}
```

---

### SESSION

#### POST /session
```json
// Request (авторизован)
{
  "vacancy_url": "https://hh.ru/vacancy/123456"
  // ИЛИ
  "vacancy_text": "Ищем бизнес-аналитика..."
}
// Response 201
{
  "session_id": "sess_abc123",
  "vacancy_summary": "Краткое резюме вакансии",
  "created_at": "2025-01-01T00:00:00Z"
}
```

#### POST /session/{session_id}/message
```json
// Request
{ "text": "У меня есть опыт работы с Python 2 года" }
// Response
{
  "reply": "Отлично! Расскажи подробнее — над какими задачами работал?",
  "is_complete": false
}
```

#### POST /session/{session_id}/generate
```json
// Response 200
{
  "resume_id": "res_abc123",
  "session_id": "sess_abc123",
  "data": { /* ResumeData — раздел 6 */ },
  "pdf_url": "/resume/res_abc123/pdf",
  "created_at": "2025-01-01T00:00:00Z"
}
```

---

### RESUME

#### GET /resume — список всех резюме пользователя
```json
[
  {
    "resume_id": "res_abc123",
    "vacancy_title": "Бизнес-аналитик, Сбер",
    "vacancy_preview": "Ищем бизнес-аналитика со знанием...",
    "pdf_url": "/resume/res_abc123/pdf",
    "created_at": "2025-01-01T00:00:00Z"
  }
]
```

#### GET /resume/{resume_id} — одно резюме (JSON)
#### GET /resume/{resume_id}/pdf — скачать PDF (application/pdf)

---

## 6. Структура JSON резюме (ResumeData)

```json
{
  "personal": {
    "name": "Иван Иванов",
    "city": "Москва",
    "phone": "+7 999 000 00 00",
    "email": "ivan@mail.ru",
    "links": ["https://hh.ru/resume/...", "https://github.com/..."],
    "about": "2-3 предложения о себе"
  },
  "education": [
    {
      "university": "МГУ",
      "faculty": "ВМК",
      "speciality": "Прикладная математика",
      "year": "2026",
      "achievements": "Научная статья, победитель олимпиады"
    }
  ],
  "experience": [
    {
      "title": "Кейс-чемпионат ПАО Росгосстрах",
      "role": "Аналитик команды",
      "description": "Разработал модель оценки рисков на основе данных клиентской базы",
      "result": "1 место из 40 команд"
    }
  ],
  "skills": {
    "hard": ["Python", "Excel", "SQL", "SWOT-анализ"],
    "soft": ["Работа в команде", "Аналитическое мышление"]
  },
  "languages": [
    { "language": "Английский", "level": "B1" }
  ],
  "extra": {
    "projects": ["https://waytooffer.vercel.app/"],
    "hobbies": "Баскетбол, музыка (4 инструмента)"
  }
}
```

---

## 7. Системный промпт для AI-чата (интервьюер)

Вставляется в `system` при каждом вызове OpenAI API в `/message`.
**МОДЕЛЬ: `gpt-5` — строго, никакая другая.**

```
Ты — карьерный консультант. Твоя задача — собрать данные кандидата для составления резюме под конкретную вакансию.

Вакансия: {vacancy_text}
Ключевые требования вакансии: {vacancy_requirements}

Постоянные данные кандидата (уже известны, НЕ спрашивай их повторно):
{user_profile}

АЛГОРИТМ:
1. Поздоровайся и кратко объясни процесс (1 сообщение).
2. Задавай строго по ОДНОМУ вопросу за раз.
3. Порядок сбора данных:
   - Опыт: проекты, хакатоны, чемпионаты, стажировки — всё что не указано в профиле
   - Навыки — только те, что важны для ЭТОЙ вакансии
   - Уточняй цифры: "Какое место заняли?", "Что именно делал?", "Какой результат?"
   - Хобби, дополнительные ссылки — в конце
4. Когда все данные собраны — скажи пользователю что готов генерировать.
   Верни JSON: {"status": "complete", "data": {<все собранные данные>}}

СТИЛЬ: дружелюбный, конкретный, без воды. Не задавай несколько вопросов сразу.
ВАЖНО: не выдумывай данные. Если кандидат чего-то не знает — пропускай.
```

---

## 8. Промпт для генерации резюме

Вызывается в `/generate`.
**МОДЕЛЬ: `gpt-5` — строго, никакая другая.**

```
Ты — профессиональный HR-консультант и карьерный коуч. Составь идеальное резюме для стажировки.

ВХОДНЫЕ ДАННЫЕ:
- Описание вакансии: {vacancy_text}
- Постоянные данные кандидата: {user_profile}
- Дополнительные данные из диалога: {candidate_data}

ИНСТРУКЦИИ:
1. Проанализируй вакансию: выдели ключевые требования, hard skills, soft skills.
2. Составь резюме строго по JSON-структуре (раздел 6 брифа).
3. Используй глаголы действия: "разработал", "оптимизировал", "реализовал", "повысил".
4. Добавляй цифры и результаты везде, где они есть.
5. Если данных не хватает — используй учебные проекты или ставь "—".
6. Hard skills — только те, что релевантны вакансии.
7. Раздел "about" — кто кандидат, что умеет, какую пользу принесёт компании.
8. Опыт — от самого релевантного к наименее.
9. IT-вакансия → акцент на технических навыках. Бизнес → акцент на софт-скиллах.

ФОРМАТ: верни ТОЛЬКО валидный JSON без markdown-обёртки и пояснений.
```

---

## 9. Задания для агентов Cowork

---

### 🔧 Агент: Backend (FastAPI)

```
Реализуй FastAPI-сервер по брифу BRIEF.md.

ЗАДАЧИ:
1. Реализуй все эндпоинты из раздела 5:
   /auth/register, /auth/login, /auth/refresh,
   /auth/change-password, /auth/change-email, /auth/change-phone,
   /profile (GET, PUT),
   /session (POST, /{id}/message, /{id}/generate),
   /resume (GET список, GET одно, GET pdf)

2. БД — SQLite через SQLAlchemy.
   Таблицы: users, profiles, sessions, messages, resumes

3. Авторизация — JWT.
   Access токен: 30 минут. Refresh токен: 30 дней.
   Все эндпоинты кроме /auth/register и /auth/login требуют Bearer токен.

4. Валидация:
   - password == password_confirm, минимум 8 символов
   - Смена email/телефона/пароля — проверять текущий пароль

5. В /session — если передан vacancy_url: парсить текст вакансии через requests + BeautifulSoup

6. В /session/{id}/message:
   - Хранить историю сообщений в БД
   - Передавать всю историю в OpenAI как messages[]
   - Системный промпт из раздела 7 брифа с подстановкой user_profile
   - МОДЕЛЬ: gpt-5 — строго, никакая другая

7. В /session/{id}/generate:
   - Промпт из раздела 8 брифа
   - МОДЕЛЬ: gpt-5 — строго, никакая другая
   - Сохранить JSON резюме в таблицу resumes

8. PDF — конвертировать ResumeData JSON → HTML-шаблон → PDF через WeasyPrint

9. CORS — разрешить localhost:3000

ФАЙЛОВАЯ СТРУКТУРА:
/app
  main.py       # FastAPI app, роуты
  models.py     # SQLAlchemy модели
  schemas.py    # Pydantic схемы
  auth.py       # JWT логика
  ai.py         # Работа с OpenAI (gpt-5)
  pdf.py        # Генерация PDF
  database.py   # Подключение к SQLite
  parser.py     # Парсинг вакансий по URL
.env            # OPENAI_API_KEY=..., JWT_SECRET=...
requirements.txt
```

---

### 🎨 Агент: Designer (Figma)

```
Создай дизайн всех страниц приложения в Figma. Создай новый файл.

ЭКРАНЫ (раздел 3-4 брифа):
1. /register — Регистрация (телефон, email, пароль × 2)
2. /onboarding — Оффер ("Заполнить" / "Пропустить") + форма с постоянными данными
3. /login — Вход (один инпут телефон/email + пароль)
4. / — Главная:
   - Состояние 1: ввод URL или текста вакансии
   - Состояние 2: чат с AI (пузыри сообщений, инпут внизу)
   - Состояние 3: превью резюме + кнопка "Скачать PDF"
5. /history — Список карточек резюме (название, превью, дата, кнопка PDF)
6. /settings — Два раздела: "Личные данные" и "Безопасность"

СТИЛЬ:
- Минимализм, профессиональный вид
- Белый фон, акцентный цвет — тёмно-синий #1E3A5F или фиолетовый #6C47FF
- Шрифт — Inter
- Компоненты: инпуты, кнопки, карточки, чат-пузыри — единый стиль
- Адаптив: десктоп (1440px), все экраны

РЕЗУЛЬТАТ: Figma-файл со всеми экранами, компонентами, auto-layout.
```

---

### 💻 Агент: Frontend (Next.js)

```
Реализуй фронтенд по брифу BRIEF.md.
СНАЧАЛА сверстай дизайн из Figma, ЗАТЕМ подключи к бэкенду.

СТЕК: Next.js + TypeScript + Tailwind + shadcn/ui + shadcn-chatbot-kit

ШАГ 1 — ВЁРСТКА (Figma → код):
Возьми Figma-файл от дизайнера и сверстай все 6 экранов:
/register, /onboarding, /login, /, /history, /settings
- Используй shadcn/ui компоненты (Input, Button, Card, Form и др.)
- Соблюдай цвета, шрифты, отступы из Figma точно
- Чат-компонент: shadcn-chatbot-kit (https://github.com/Blazity/shadcn-chatbot-kit)

ШАГ 2 — ПОДКЛЮЧЕНИЕ К БЭКЕНДУ:
Base URL: из .env.local (NEXT_PUBLIC_API_URL=http://localhost:8000)
JWT: хранить в localStorage (access + refresh). При 401 — автообновление через /auth/refresh.

Подключения:
- /register → POST /auth/register → редирект /onboarding
- /onboarding → PUT /profile → редирект /
- /login → POST /auth/login → редирект /
- / состояние 1 → POST /session
- / состояние 2 → POST /session/{id}/message (через компонент Chat)
  is_complete=true → POST /session/{id}/generate → показать превью + кнопка PDF
- /history → GET /resume
- /settings личные данные → GET /profile + PUT /profile
- /settings безопасность → POST /auth/change-password / change-email / change-phone

ЗАЩИТА РОУТОВ:
- /, /history, /settings — редирект на /login если нет токена
- /login, /register — редирект на / если токен есть

УСТАНОВКА:
pnpm create next-app@latest resume-builder --typescript --tailwind --app
cd resume-builder
npx shadcn init
pnpm add axios
npx shadcn add https://shadcn-chatbot-kit.vercel.app/r/chat.json
```

---

## 10. Установка зависимостей

### Бэкенд
```bash
pip install fastapi uvicorn sqlalchemy openai python-dotenv \
  requests beautifulsoup4 weasyprint pydantic python-jose passlib bcrypt
```

### Фронтенд
```bash
pnpm create next-app@latest resume-builder --typescript --tailwind --app
cd resume-builder
npx shadcn init
pnpm add axios
npx shadcn add https://shadcn-chatbot-kit.vercel.app/r/chat.json
```

### Запуск
```bash
# Бэкенд
uvicorn app.main:app --reload --port 8000

# Фронтенд
pnpm dev  # localhost:3000
```
