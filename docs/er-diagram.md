# ER-диаграмма

Схема БД справочника банкоматов. Источник истины — модели в [backend/app/models](../backend/app/models) и миграции Alembic.

```mermaid
erDiagram
    manufacturer ||--o{ atm_model : "выпускает"
    atm_model ||--o{ atm : "модель"
    branch ||--o{ atm : "обслуживает"
    region ||--o{ branch : ""
    region ||--o{ location : ""

    atm ||--o{ atm_status_history : "смена статуса"
    atm ||--o{ module : "узлы"
    atm ||--o{ software : "ПО"
    atm ||--o{ atm_processing : "Terminal ID / Merchant ID"
    processing ||--o{ atm_processing : ""
    atm }o--o{ currency : "atm_currency"
    atm }o--o{ payment_scheme : "atm_scheme"
    atm }o--o{ dict_item : "atm_service"

    atm ||--o{ placement : "история размещений"
    location ||--o{ placement : ""

    atm ||--o{ service_event : "ремонты, ТО"
    vendor ||--o{ service_event : "исполнитель"
    service_event ||--o{ module_replacement : ""
    module ||--o{ module_replacement : "снят / установлен"

    atm_model ||--o{ certificate : ""
    atm ||--o{ certificate : ""
    module ||--o{ certificate : ""
    payment_scheme ||--o{ certificate : ""

    atm ||--o| contract : "гарантия, договор"
    vendor ||--o{ contract : "поставщик / сервис"

    app_user ||--o{ user_session : ""
    app_user ||--o{ audit_log : "автор изменения"

    atm {
        int id PK
        string atm_code UK "внутренний код — основной идентификатор"
        string serial_number UK
        int model_id FK
        int status_id FK
        int branch_id FK
        date purchase_date
        date commissioning_date
        numeric screen_size_in
        int cassette_count
        bool contactless
    }
    atm_processing {
        int atm_id FK
        int processing_id FK
        string terminal_id "уникален в процессинге"
        string merchant_id "уникален в процессинге"
    }
    placement {
        int atm_id FK
        int location_id FK
        date placed_from
        date placed_to "пусто — стоит сейчас"
    }
    location {
        int id PK
        numeric latitude
        numeric longitude
        string address
        int place_type_id FK
    }
    certificate {
        int atm_model_id FK "ровно одно из трёх"
        int atm_id FK
        int module_id FK
        date valid_until
        bool needs_review "после замены узла"
    }
    dict_item {
        string kind "вид списка"
        string code
        string name
    }
```

## Ограничения, которые держит сама БД

| Правило | Как реализовано |
|---|---|
| Периоды размещения одного банкомата не пересекаются | exclusion constraint `ex_placement_no_overlap` (btree_gist, `daterange`) |
| У банкомата не больше одного текущего размещения | частичный unique-индекс `placed_to is null` |
| Terminal ID и Merchant ID уникальны внутри процессинга | `unique(processing_id, terminal_id)`, `unique(processing_id, merchant_id)` |
| Сертификат привязан ровно к одному объекту | `check num_nonnulls(atm_model_id, atm_id, module_id) = 1` |
| Координаты в пределах Узбекистана | `check latitude between 37 and 46 and longitude between 55 and 74` |
| Логин уникален без учёта регистра | unique-индекс по `lower(login)` |
| У ремонта есть исполнитель | `check vendor_id is not null or by_bank_engineer` |
