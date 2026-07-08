# API-контракт Aid Platform

## 1. Назначение

REST API обслуживает дипломный MVP адресной помощи: регистрацию, заявки,
модерацию, внутреннюю верификацию, fraud-контроль и демонстрационный fulfillment.
Интеграций с платежами, магазинами, Госуслугами и реальными документами нет.

## 2. Базовый URL и формат

Пути начинаются с `/api/`. Request и response используют JSON; даты передаются
в ISO 8601, денежные значения — decimal-строками.

## 3. JWT-аутентификация

Токен получается через `POST /api/auth/token/` и передаётся как
`Authorization: Bearer <token>`. Обновление — `/api/auth/token/refresh/`.

## 4. Роли

- `applicant` — создаёт заявки, управляет своим минимальным профилем,
  отправляет verification и подтверждает получение помощи.
- `helper` — видит опубликованные заявки, принимает одну и формирует/передаёт
  демонстрационный сертификат.
- `moderator` — модерирует заявки и verification, читает fraud/fulfillment.
- `admin` — обладает служебными правами moderator и разрешёнными существующими
  административными правами отдельных endpoints.

## 5. Приватность

Helper не получает identity applicant, fraud/verification internals и полный
certificate code. Applicant не получает identity helper/moderator и fraud
internals. Полный certificate code доступен applicant только после delivery и
moderator/admin в служебном read-only контракте.

## 6. Ошибки

Обычная ошибка: `{"detail": "..."}`. Доменные конфликты могут возвращать
`{"code": "stable_code", "detail": "..."}`. Основные статусы: 400 —
валидация/lifecycle, 401 — нет JWT, 403 — роль, 404 — объект или скрытый чужой
объект, 409 — конфликт fraud/verification/fulfillment state.

## 7. Endpoints

Обозначения body/response указывают ключевые поля; точная машиночитаемая схема —
`backend/docs/openapi.yaml`.

### Authentication

| Method | Path | Назначение | Роли | Request | Success | Ошибки | Статус |
|---|---|---|---|---|---|---|---|
| POST | `/api/auth/register/` | Регистрация | public | username, password, role?, region?, email? | User | 400 | active |
| POST | `/api/auth/token/` | Login | public | username, password | access, refresh | 401 | active |
| POST | `/api/auth/token/refresh/` | Обновить access | public | refresh | access | 401 | active |
| GET | `/api/auth/me/` | Текущий user | authenticated | — | id, username, email, role, region | 401 | active |

### Applicant profile

| Method | Path | Назначение | Роли | Request | Success | Ошибки | Статус |
|---|---|---|---|---|---|---|---|
| GET | `/api/applicant/profile/` | Собственный профиль | applicant | — | household, dependents, consent, region, verification | 403 | active |
| PATCH | `/api/applicant/profile/` | Обновить профиль | applicant | household_size?, dependents_count?, consent? | Profile | 400, 403 | active |

### Applicant requests

| Method | Path | Назначение | Роли | Request | Success | Ошибки | Статус |
|---|---|---|---|---|---|---|---|
| POST | `/api/requests/applicant/create/` | Создать заявку | applicant | category, title, description, region, amount?, urgency | ApplicantAidRequest | 400, 403 | active |
| GET | `/api/requests/applicant/my/` | Свои заявки | applicant | — | ApplicantAidRequest[] | 403 | active |
| GET | `/api/requests/{request_id}/history/` | История по роли/ownership | applicant/helper/moderator/admin | — | role-specific history[] | 403, 404 | active |
| GET | `/api/applicant/requests/{request_id}/fulfillment/` | Свой fulfillment | applicant owner | — | prepared или delivered fulfillment | 403, 404 | active |
| POST | `/api/applicant/requests/{request_id}/confirm-receipt/` | Подтвердить получение | applicant owner | — | request_status, fulfillment_status | 403, 404, 409 | active |

### Applicant verification

| Method | Path | Назначение | Роли | Request | Success | Ошибки | Статус |
|---|---|---|---|---|---|---|---|
| POST | `/api/applicant/verification/submit/` | Отправить verification | applicant | — | VerificationSummary | 400, 403, 409 | active |
| GET | `/api/applicant/verification/history/` | Своя история | applicant | — | VerificationSummary[] | 403 | active |

### Helper requests

| Method | Path | Назначение | Роли | Request | Success | Ошибки | Статус |
|---|---|---|---|---|---|---|---|
| GET | `/api/requests/published/` | Privacy-safe feed | helper/admin | filters | HelperAidRequest[] | 403 | active |
| POST | `/api/requests/helper/take/{request_id}/` | Принять заявку | helper/admin | method, note? | HelperAidRequest | 400, 403, 404 | active |
| GET | `/api/helper/my-help/` | Собственные взятые заявки и safe fulfillment summary | helper | page?, page_size? | HelperOwnedRequest[] | 401, 403 | active |

### Fulfillment

| Method | Path | Назначение | Роли | Request | Success | Ошибки | Статус |
|---|---|---|---|---|---|---|---|
| GET | `/api/helper/requests/{request_id}/fulfillment/` | Свой fulfillment | owner helper | — | masked HelperFulfillment | 403, 404 | active |
| POST | `/api/helper/requests/{request_id}/fulfillment/` | Создать mock certificate | owner helper | provider_name, amount | masked HelperFulfillment | 400, 403, 404, 409 | active |
| POST | `/api/helper/requests/{request_id}/fulfillment/deliver/` | Отметить delivery | owner helper | — | masked HelperFulfillment | 403, 404, 409 | active |
| GET | `/api/moderation/requests/{request_id}/fulfillment/` | Служебное чтение | moderator/admin | — | ModeratorFulfillment | 403, 404 | active |

### Moderation

| Method | Path | Назначение | Роли | Request | Success | Ошибки | Статус |
|---|---|---|---|---|---|---|---|
| GET | `/api/requests/moderation/queue/` | Очередь заявок | moderator/admin | filters | ModeratorAidRequest[] | 403 | active |
| POST | `/api/requests/moderation/{request_id}/` | Approve/reject | moderator/admin | action, comment? | id, new_status | 400, 403, 404, 409 | active |
| GET | `/api/moderation/verifications/` | Очередь verification | moderator/admin | status?, region?, ordering? | ModeratorVerification[] | 403 | active |
| GET | `/api/moderation/verifications/{id}/` | Verification detail | moderator/admin | — | ModeratorVerification | 403, 404 | active |
| POST | `/api/moderation/verifications/{id}/decision/` | Решение | moderator/admin | decision, comment? | ModeratorVerification | 400, 403, 404, 409 | active |

### Fraud

| Method | Path | Назначение | Роли | Request | Success | Ошибки | Статус |
|---|---|---|---|---|---|---|---|
| GET | `/api/fraud/requests/{request_id}/decision/` | Fraud decision | moderator/admin | — | FraudDecision | 403, 404 | active |
| GET | `/api/fraud/requests/{request_id}/checks/` | Fraud checks | moderator/admin | — | FraudCheck[] | 403, 404 | active |
| POST | `/api/fraud/requests/{request_id}/recheck/` | Recheck | moderator/admin | — | FraudDecision или safe failure | 403, 404 | active |
| POST | `/api/fraud/requests/{request_id}/override/` | Effective action override | moderator/admin | new_action, comment | FraudOverride | 400, 403, 404 | active |

### Documentation и health

| Method | Path | Назначение | Роли | Request | Success | Ошибки | Статус |
|---|---|---|---|---|---|---|---|
| GET | `/api/health/` | Health check | public | — | status | — | active |
| GET | `/api/schema/` | OpenAPI | public | — | YAML/JSON schema | — | active |
| GET | `/api/docs/swagger/` | Swagger UI | public | — | HTML | — | active |
| GET | `/api/docs/redoc/` | ReDoc | public | — | HTML | — | active |

## 8. Матрица ролей

`own` — только собственный объект; `RO` — read-only.

| Действие | applicant | helper | moderator | admin |
|---|---:|---:|---:|---:|
| register/login | разрешено | разрешено | login | login |
| own profile | own | запрещено | запрещено | запрещено |
| create/own request list | own | запрещено | запрещено | запрещено |
| published feed | запрещено | разрешено | запрещено | разрешено |
| take request | запрещено | разрешено | запрещено | разрешено |
| list own commitments | запрещено | own | запрещено | запрещено |
| create/deliver certificate | запрещено | own | запрещено | запрещено |
| confirm receipt | own | запрещено | запрещено | запрещено |
| verification submit/history | own | запрещено | запрещено | запрещено |
| verification moderation | запрещено | запрещено | разрешено | разрешено |
| request moderation | запрещено | запрещено | разрешено | разрешено |
| fraud decision/checks/recheck/override | запрещено | запрещено | разрешено | разрешено |
| fulfillment moderation | запрещено | запрещено | RO | RO |
| request history | own | own commitment | RO | RO |

## 9. Жизненные циклы

AidRequest: `draft → on_moderation → published → in_progress → closed`, с
терминальным `rejected`. Переходы выполняются только transition service.

Verification: `not_submitted → pending → verified|rejected`; после rejected
возможна новая pending-запись, verified терминален для MVP.

AidFulfillment: `created → delivered → confirmed`; confirmation applicant
атомарно закрывает AidRequest.

## 10. Fraud publication policy

Effective `allow` и `manual_review` допускают ручной approve. `block` возвращает
409 до override. Отсутствующее решение также даёт fail-safe 409. Reject не
блокируется fraud policy.

## 11. Deprecated

`PATCH /api/requests/close/{request_id}/` — deprecated applicant-only alias
receipt confirmation. Helper не может закрыть заявку.

## 12. Намеренно отсутствует

Нет реальных документов, Госуслуг, платежей, магазинов, списания сертификата,
логистики, disputes, уведомлений и frontend-контрактов вне этой схемы.
