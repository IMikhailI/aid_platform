# Aid Platform — frontend v2

Основа нового интерфейса дипломного MVP на Vue 3 и Vite. Старый `frontend` от проекта не зависит.

## Запуск

```bash
cp .env.example .env
npm install
npm run dev
```

По умолчанию API доступен по `http://localhost:8000/api`. Другой адрес задаётся через `VITE_API_BASE_URL` (без завершающего `/`).

## Команды

- `npm run dev` — локальная разработка;
- `npm run build` — production-сборка;
- `npm run preview` — просмотр собранного приложения.

Токены временно хранятся в `localStorage`; это осознанное MVP-ограничение. Страницы кабинетов пока являются заготовками.

Контент перенесён из исходного статического лендинга без редакторских изменений. Он используется в учебно-демонстрационных целях и будет уточнён позже.

## Кабинет помощника

Реализованы маршруты `/helper/overview`, `/helper/requests`, `/helper/my-help`, `/helper/saved` и `/helper/settings` с доступом только для роли `helper`. Корневой `/helper` перенаправляет на обзор.

Лента `/helper/requests` использует `GET /requests/published/` и `POST /requests/helper/take/{id}/`. Отклик технически означает take request; сертификат или fulfillment при этом не создаётся. Категория, поиск, сортировка и пагинация работают на backend. Регион фильтруется только среди privacy-safe заявок уже загруженной страницы, потому что API не предоставляет отдельный query-параметр `region`.

Раздел «Моя помощь» использует `GET /api/helper/my-help/`: показывает только заявки, взятые текущим helper, и безопасный статус fulfillment. Из раздела можно создать демонстрационный сертификат и отметить его передачу; после подтверждения applicant отображается состояние confirmed/closed. Полный код сертификата и applicant identity helper не получает. Серверной агрегированной статистики пока нет, поэтому «Обзор» не придумывает числовые показатели. Настройки показывают read-only данные из `/auth/me/`.

Сохранённые заявки — локальная функция frontend-v2: в `localStorage` хранятся только ID заявок. Серверной синхронизации favorites пока нет.

## Кабинет получателя помощи

Маршруты `/applicant/overview`, `/applicant/requests`, `/applicant/history` и `/applicant/settings` доступны только роли `applicant`. Корневой `/applicant` перенаправляет на обзор.

Интерфейс использует `GET/PATCH /api/applicant/profile/`, `POST /api/applicant/verification/submit/`, `GET /api/applicant/verification/history/`, `GET /api/requests/applicant/my/`, `POST /api/requests/applicant/create/`, `GET /api/applicant/requests/{id}/fulfillment/` и `POST /api/applicant/requests/{id}/confirm-receipt/`.

Создание заявки отправляет её на модерацию, а подтверждение получения закрывает заявку. Верификация реализована в демонстрационном формате без документов и интеграции с Госуслугами. Личность помощника, внутренние поля модерации и код сертификата до передачи помощи не отображаются.

## Панель модерации

Маршруты `/moderator/pending`, `/moderator/approved` и `/moderator/rejected` доступны ролям `moderator` и `admin`. Корневой `/moderator` перенаправляет в очередь pending.

Очередь использует `GET /api/requests/moderation/queue/` и `POST /api/requests/moderation/{id}/`. Fraud-контекст загружается через decision/checks endpoints; доступны recheck и ручной override с обязательной причиной. Approve может вернуть `409`, если публикация запрещена fraud policy или fraud decision отсутствует.

Компактный блок верификаций использует `/api/moderation/verifications/` и decision endpoint. Текущий backend не предоставляет список уже одобренных и отклонённых заявок, поэтому соответствующие вкладки показывают нейтральное состояние без демонстрационных данных; полноценный архив требует отдельного read-only backend endpoint.
