# RUN.md — как запускать проект aid_platform

## 1) Требования
- Docker + Docker Compose
- (опционально) `curl`, `python3` для тестов API

---

## 2) Первый запуск (или после `git clone`)

```bash
cd ~/aid_platform
docker compose up --build
```

После запуска:

- Backend: http://localhost:8000
- Health-check: http://localhost:8000/api/health/
- Admin: http://localhost:8000/admin/
- Frontend: http://localhost:5173

---

## 3) Запуск в фоне

```bash
cd ~/aid_platform
docker compose up -d --build
```

Логи:

```bash
docker compose logs -f
```

Остановить:

```bash
docker compose down
```

---

## 4) Миграции

```bash
cd ~/aid_platform
docker compose run --rm backend python manage.py makemigrations
docker compose run --rm backend python manage.py migrate
```

---

## 5) Создать суперпользователя (admin)

```bash
cd ~/aid_platform
docker compose run --rm backend python manage.py createsuperuser
```

---

## 6) Полный сброс БД (ОСТОРОЖНО: удалит данные)

```bash
cd ~/aid_platform
docker compose down -v
docker compose up --build
```

---

## 7) Получить JWT токены для тестов

```bash
APPLICANT_TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"applicant1","password":"StrongPass123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access'])")

MODERATOR_TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"moderator1","password":"StrongPass123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access'])")

HELPER_TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"helper1","password":"StrongPass123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access'])")
```

Проверка, что токены получены:

```bash
echo ${#APPLICANT_TOKEN} ${#MODERATOR_TOKEN} ${#HELPER_TOKEN}
```

---

## 8) Быстрый API flow (демо)

### 8.1 Applicant создаёт заявку
```bash
curl -X POST http://localhost:8000/api/requests/applicant/create/ \
  -H "Authorization: Bearer $APPLICANT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "category":"food",
    "title":"Продуктовая помощь на неделю",
    "description":"Семья с ребенком, нужна базовая корзина",
    "region":"Moscow",
    "requested_amount":"4500.00",
    "urgency":4
  }'
```

### 8.2 Moderator смотрит очередь
```bash
curl http://localhost:8000/api/requests/moderation/queue/ \
  -H "Authorization: Bearer $MODERATOR_TOKEN"
```

### 8.3 Moderator approve заявку #1
```bash
curl -X POST http://localhost:8000/api/requests/moderation/1/ \
  -H "Authorization: Bearer $MODERATOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"action":"approve","comment":"Проверено"}'
```

### 8.4 Helper берёт заявку #1 в работу
```bash
curl -X POST http://localhost:8000/api/requests/helper/take/1/ \
  -H "Authorization: Bearer $HELPER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"method":"certificate","note":"Сертификат на продукты"}'
```

### 8.5 Helper закрывает заявку #1
```bash
curl -X POST http://localhost:8000/api/requests/close/1/ \
  -H "Authorization: Bearer $HELPER_TOKEN"
```

### 8.6 История статусов заявки #1
```bash
curl http://localhost:8000/api/requests/1/history/ \
  -H "Authorization: Bearer $MODERATOR_TOKEN"
```

---

## 9) Полезные команды

Статус контейнеров:
```bash
docker compose ps
```

Перезапуск только backend:
```bash
docker compose restart backend
```

Перезапуск только frontend:
```bash
docker compose restart frontend
```

---

## 10) Частые проблемы

### Проблема: `token_not_valid`
- Токен просрочен или из другого терминала.
- Получи новый `access` токен (см. раздел 7).

### Проблема: `Couldn't connect to localhost:8000`
- Backend не запущен:
```bash
docker compose up -d
docker compose ps
```

### Проблема: правки не подхватываются
- Перезапусти сервис:
```bash
docker compose restart backend
docker compose restart frontend
```

### Проблема: короткий SECRET_KEY warning
- В `.env` поставь длинный `DJANGO_SECRET_KEY` (32+ байт), затем:
```bash
docker compose restart backend
```
