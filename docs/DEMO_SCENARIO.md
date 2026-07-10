# Демонстрационный стенд aid_platform

## 1. Назначение demo-стенда

Demo-стенд создаёт воспроизводимые локальные данные для защиты диплома:
пользователей разных ролей, верификации заявителей, заявки во всех ключевых
статусах, fraud-сценарии и mock fulfillment. Данные синтетические, не являются
реальными персональными данными и не подключают внешние сервисы.

## 2. Как запустить backend

```bash
docker compose up --build backend
```

Или запустить весь стек:

```bash
docker compose up --build
```

После миграций backend доступен на `http://localhost:8000`.

## 3. Как запустить frontend-v2

```bash
cd frontend-v2
npm ci
npm run dev
```

Локальный адрес: `http://localhost:5173`.

## 4. Как создать demo-данные

В Docker:

```bash
docker compose exec -T backend python manage.py seed_demo_stand
```

Локально из каталога `backend`:

```bash
python manage.py seed_demo_stand
```

Полное пересоздание только demo-записей:

```bash
python manage.py seed_demo_stand --reset-demo-data --reset-demo-passwords
```

`--reset-demo-data` удаляет только заявки с marker `[DEMO_STAND]` и
verification-записи demo-applicant пользователей. Пользовательские данные без
demo-marker не удаляются.

## 5. Demo users и пароли

Эти пароли предназначены только для локального стенда и не должны использоваться
в production.

| Username | Password | Role |
| --- | --- | --- |
| `applicant_demo` | `applicant123` | applicant |
| `helper_demo` | `helper123` | helper |
| `moderator_demo` | `moderator123` | moderator |
| `admin_demo` | `admin123` | admin |
| `applicant_pending_demo` | `applicant123` | applicant |
| `applicant_rejected_demo` | `applicant123` | applicant |

Без флага `--reset-demo-passwords` команда не перезаписывает пароль уже
существующего demo-пользователя.

## 6. Сценарий показа для роли applicant

1. Войти как `applicant_demo`.
2. Открыть список своих заявок.
3. Найти закрытый кейс `[DEMO_STAND] request_closed`.
4. Открыть fulfillment для `[DEMO_STAND] request_fulfillment_delivered`.
5. Подтвердить получение помощи и показать переход заявки в `closed`.
6. Показать историю статусов без внутренних moderator/fraud полей.

## 7. Сценарий показа для роли moderator

1. Войти как `moderator_demo`.
2. Открыть очередь заявок на модерации.
3. Показать low/allow, medium/manual_review и high/block заявки.
4. Попробовать approve для `[DEMO_STAND] request_pending_block` и показать 409
   `fraud_publication_blocked`.
5. Открыть fraud decision/signals для block-заявки.
6. При необходимости выполнить override через fraud API и затем approve.

## 8. Сценарий показа для роли helper

1. Войти как `helper_demo`.
2. Открыть ленту опубликованных заявок и найти `[DEMO_STAND] request_published`.
3. Открыть `/helper/my-help`.
4. Показать заявки без fulfillment, с `created`, с `delivered` и с `confirmed`.
5. Проверить, что helper видит только masked certificate code и не видит личность
   applicant, fraud reasons, verification details и telemetry.

## 9. Полный end-to-end сценарий

1. Applicant создаёт заявку.
2. Anti-fraud создаёт decision, но lifecycle остаётся `on_moderation`.
3. Moderator approve переводит заявку в `published`.
4. Helper берёт заявку в работу.
5. Helper создаёт mock certificate.
6. Helper отмечает certificate как delivered.
7. Applicant подтверждает получение.
8. Fulfillment становится `confirmed`, заявка становится `closed`.

## 10. Что показывать при fraud block

Заявка `[DEMO_STAND] request_pending_block` имеет синтетический
`FraudDecision(action=block)` с demo reasons/signals. Она нужна для показа
защиты approve: публикация возвращает 409, пока moderator/admin не выполнит
явный override. Fraud weights, rules и policy команда не изменяет.

## 11. Что показывать при verification

Команда создаёт три состояния:

- `applicant_demo`: `verified`;
- `applicant_pending_demo`: `pending`;
- `applicant_rejected_demo`: `rejected`.

Профили applicant имеют consent, household size и dependents count. Решения
`verified` и `rejected` приняты от имени `moderator_demo` через service layer.

## 12. Что показывать при fulfillment

Fulfillment полностью mock:

- `[DEMO_STAND] request_in_progress`: fulfillment отсутствует;
- `[DEMO_STAND] request_fulfillment_created`: certificate создан;
- `[DEMO_STAND] request_fulfillment_delivered`: certificate передан, applicant
  может подтвердить получение;
- `[DEMO_STAND] request_closed`: certificate confirmed, заявка closed.

Helper получает только masked code. Applicant получает полный code только после
delivery. Moderator/admin видят служебные сведения.

## 13. Ограничения demo-стенда

- Нет реальных документов, платежей, магазинов и Госуслуг.
- Demo credentials не являются production secrets.
- Команда не удаляет production-данные и не меняет бизнес-логику.
- `block` fraud decision создан синтетически для локального сценария 409/override.
- Повторный запуск без reset переиспользует существующие demo-записи.
