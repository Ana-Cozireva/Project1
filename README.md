# ArtGallery

Веб-платформа продажи предметов искусства (по ТЗ ArtGallery).

- **Backend:** Python 3.11, FastAPI, SQLAlchemy, Pydantic, JWT, bcrypt, PostgreSQL 16
- **Frontend:** Next.js 14 (JavaScript, App Router), обычный CSS
- **Запуск:** Docker + docker-compose

## Запуск одной командой

```bash
docker-compose up --build
```

| Что | Адрес |
|---|---|
| Сайт | http://localhost:3000 |
| API + Swagger | http://localhost:8000/docs |

При первом запуске создаётся демо-каталог (24 произведения, брони, сообщения).

| Роль | Email | Пароль |
|---|---|---|
| Администратор | admin@artgallery.md | admin12345 |
| Продавец | gallery@artgallery.md | seller12345 |
| Покупатель | buyer@artgallery.md | buyer12345 |

## Запуск без Docker (SQLite, для разработки)

```bash
# backend
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
DATABASE_URL=sqlite:///./dev.db uvicorn app.main:app --reload     # Windows PowerShell: $env:DATABASE_URL="sqlite:///./dev.db"

# frontend (в другом терминале)
cd frontend
npm install
npm run dev
```

Тесты backend: `cd backend && pytest` (26 тестов).

## Что реализовано (соответствие ТЗ)

| Требование ТЗ | Где |
|---|---|
| Роли: гость, покупатель, продавец, администратор | `app/deps.py`, JWT |
| CRUD объявлений, фото, поиск, фильтры (художник, стиль, техника, город, цена, размер), сортировка, пагинация | `routers/artworks.py` |
| Избранное | `routers/favorites.py` |
| Обращения покупателя к продавцу | `routers/conversations.py` |
| Бронирование: резервирование → подтверждение / отмена, `SELECT ... FOR UPDATE` | `routers/reservations.py` |
| Аналитика: по художнику, стилю, технике, городу, месяцу | `routers/analytics.py` |
| JWT, bcrypt, OpenAPI/Swagger | `core/security.py`, `/docs` |
| Повторные попытки подключения к БД при старте | `core/database.py` |
| Docker: БД + backend + frontend одной командой | `docker-compose.yml` |
| Схема БД (13 таблиц) | `app/models/` |

## Отличия от ТЗ

- Frontend на **Next.js (JavaScript)** вместо React + Vite — по вашему запросу. Tailwind, Axios и nginx не используются (упрощение).
- В схему добавлены два ограничения: уникальность диалога `(artwork_id, buyer_id)` и частичный уникальный индекс «не более одной активной брони на произведение» (защита от двойного бронирования на уровне БД).
- Значения enum в схеме не были видны, приняты такие: `user_role` — buyer / seller / admin; `artwork_condition` — excellent / good / fair / restored; `artwork_status` — available / reserved / sold; `reservation_status` — pending / confirmed / cancelled.
- Таблицы создаются автоматически при старте (`create_all`), миграции Alembic не подключены.
