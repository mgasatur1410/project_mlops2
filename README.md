# Система обнаружения мошенничества с использованием Kafka и CatBoost

## Обзор проекта
Система предназначена для обнаружения мошеннических транзакций в режиме реального времени с использованием модели машинного обучения CatBoost. Архитектура системы построена на микросервисах, взаимодействующих через Kafka, с хранением результатов в PostgreSQL и визуализацией через веб-интерфейс.


### Основные компоненты:
1. **CSV Loader**: Загружает транзакции из CSV-файлов в Kafka
2. **Scoring Service**: Обрабатывает транзакции, применяет модель CatBoost и оценивает вероятность мошенничества
3. **DB Service**: Сохраняет результаты скоринга в базу данных PostgreSQL
4. **Web App**: Предоставляет веб-интерфейс для мониторинга результатов и визуализации метрик

### Потоки данных:
- Транзакции → Kafka (topic: transactions) → Scoring Service → Kafka (topic: scores) → DB Service → PostgreSQL
- Web App → PostgreSQL для получения результатов и отображения в пользовательском интерфейсе


## Быстрый старт

### 1. Подготовка проекта
```bash
git clone https://github.com/mgasatur1410/project_mlops2.git
```

### 2. Подготовка данных и модели
- Разместите предобученную модель CatBoost в `model/catboost_model.cbm`
- Поместите файл с тестовыми транзакциями в `input/test.csv`

## Где взять test_processed.csv и модель
- **test_processed.csv**: https://drive.google.com/file/d/1JojlNmhOaKfnaAezB1fxUclDFnmsogH0/view?usp=sharing
- **catboost_model.cbm**: https://drive.google.com/file/d/12ByZn00cUYWrQXP03ffjHk0L1z6EGl8C/view?usp=sharing

### 3. Запуск системы
```bash
docker-compose up -d
```

### 4. Мониторинг системы
- Веб-интерфейс: http://localhost:5000
- Логи сервисов можно просмотреть командой:
```bash
docker logs scoring-service  # логи сервиса скоринга
docker logs db-service       # логи сервиса базы данных
```

### 5. Запросы к базе данных
```bash
docker exec -it postgres psql -U postgres -d frauddb -c "SELECT COUNT(*) FROM transaction_scores;"
docker exec -it postgres psql -U postgres -d frauddb -c "SELECT COUNT(*), CASE WHEN score > 0.9 THEN 'High Risk' WHEN score > 0.5 THEN 'Medium Risk' ELSE 'Low Risk' END AS risk_category FROM transaction_scores GROUP BY risk_category;"
```

### 6. Остановка системы
```bash
docker-compose down
```

## Структура проекта
```
project_mlops/
├── input/                  # данные транзакций (CSV)
├── output/                 # результаты обработки
├── model/                  # предобученная модель CatBoost
├── scripts/
│   ├── preprocess.py       # препроцессинг данных
│   ├── kafka_consumer.py   # потребитель Kafka
│   ├── kafka_producer.py   # производитель Kafka
│   ├── kafka_scoring_service.py # сервис скоринга
│   ├── db_service.py       # сервис работы с PostgreSQL
│   ├── web_app.py          # веб-интерфейс
│   ├── csv_to_kafka.py     # загрузка CSV в Kafka
│   └── templates/          # HTML шаблоны
└── docker-compose.yml      # конфигурация сервисов
```

## Детальное описание сервисов

### CSV Loader
Сервис загружает транзакции из CSV-файла в топик Kafka `transactions`. Поддерживает настройку темпа отправки данных через параметр `--delay`.

### Scoring Service
Основной компонент скоринга:
- Загружает модель CatBoost
- Получает транзакции из Kafka
- Выполняет предсказание вероятности мошенничества
- Отправляет результаты в топик Kafka `scores`
- Маркирует транзакции как мошеннические при скоре > 0.9

### DB Service
Сервис хранения данных:
- Получает результаты скоринга из Kafka
- Сохраняет в PostgreSQL
- Обеспечивает доступ к историческим данным для аналитики

### Web App
Веб-интерфейс для мониторинга:
- Отображает последние обнаруженные мошеннические транзакции
- Показывает распределение скоров для визуальной оценки
- Предоставляет интерактивные графики и таблицы

## Настройка параметров
Все параметры системы настраиваются через переменные окружения в файле `docker-compose.yml`:

```yaml
environment:
  KAFKA_BOOTSTRAP_SERVERS: kafka:9092
  KAFKA_INPUT_TOPIC: transactions
  KAFKA_OUTPUT_TOPIC: scores
  DB_HOST: postgres
  DB_PORT: 5432
  DB_NAME: frauddb
  DB_USER: postgres
  DB_PASSWORD: postgres
```

## Масштабирование
Система поддерживает горизонтальное масштабирование:
- Увеличение числа экземпляров Scoring Service для обработки большего объема транзакций
- Масштабирование Kafka с увеличением числа партиций и брокеров
- Репликация базы данных PostgreSQL для высокой доступности

## Расширение системы
Возможные направления расширения:
- Добавление алертинга при обнаружении подозрительных транзакций
- Интеграция с системами мониторинга (Prometheus, Grafana)
- Реализация A/B тестирования моделей
- Добавление API для интеграции с внешними системами
