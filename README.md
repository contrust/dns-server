# DNS Сервер

DNS сервер на Python, который предоставляет итеративное разрешение DNS-запросов с возможностью кэширования. Сервер поддерживает как TCP, так и UDP протоколы и может обрабатывать множество клиентских подключений одновременно.

## Возможности

- **Поддержка нескольких протоколов**
  - Обработка TCP и UDP запросов
  - Поддержка IPv4 (A-записи) и IPv6 (AAAA-записи)
  - Потокобезопасная реализация

- **Система кэширования**
  - LRU (Least Recently Used) кэш с поддержкой TTL
  - Постоянное хранение кэша
  - Автоматическая очистка устаревших записей
  - Настраиваемый размер кэша

- **Специальные возможности**
  - Настраиваемый прокси-сервер для вышестоящего DNS-разрешения
  - Подробная система логирования

- **Потокобезопасность**
  - Многопоточная обработка запросов
  - Потокобезопасные операции с кэшем
  - Настраиваемый размер пула потоков

## Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/yourusername/dns-server.git
cd dns-server
```

2. Установите зависимости:
```bash
make install
```

## Использование

### Быстрый старт с Makefile

Проект включает Makefile для упрощения основных операций:

```bash
# Генерация конфигурационного файла
make config

# Запуск сервера
make run

# Запуск сервера с подробным логированием
make run-verbose

# Запуск тестов
make test

# Очистка кэш-файлов и логов
make clean

# Показать справку по командам
make help
```

### Примеры использования

#### Прямой DNS-запрос (A-запись)

```bash
# Первый запрос (без кэша)
$ dig @127.0.0.2 google.com

; <<>> DiG 9.20.9 <<>> @127.0.0.2 google.com
; (1 server found)
;; global options: +cmd
;; Got answer:
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 54488
;; flags: qr; QUERY: 1, ANSWER: 6, AUTHORITY: 0, ADDITIONAL: 6

;; QUESTION SECTION:
;google.com.                    IN      A

;; ANSWER SECTION:
google.com.             300     IN      A       64.233.162.139
google.com.             300     IN      A       64.233.162.100
google.com.             300     IN      A       64.233.162.101
google.com.             300     IN      A       64.233.162.102
google.com.             300     IN      A       64.233.162.138
google.com.             300     IN      A       64.233.162.113

;; Query time: 229 msec

# Повторный запрос (из кэша)
$ dig @127.0.0.2 google.com

;; Query time: 1 msec  # Заметно быстрее благодаря кэшированию
```

#### Обратный DNS-запрос (PTR-запись)

```bash
# Первый запрос (без кэша)
$ dig @127.0.0.2 -x 91.201.52.139

; <<>> DiG 9.20.9 <<>> @127.0.0.2 -x 91.201.52.139
; (1 server found)
;; global options: +cmd
;; Got answer:
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 4872
;; flags: qr; QUERY: 1, ANSWER: 1, AUTHORITY: 3, ADDITIONAL: 4

;; QUESTION SECTION:
;139.52.201.91.in-addr.arpa.    IN      PTR

;; ANSWER SECTION:
139.52.201.91.in-addr.arpa. 3600 IN     PTR     be24.netangels.ru.

;; AUTHORITY SECTION:
52.201.91.in-addr.arpa. 14400   IN      NS      ns3.netangels.ru.
52.201.91.in-addr.arpa. 14400   IN      NS      ns1.netangels.ru.
52.201.91.in-addr.arpa. 14400   IN      NS      ns2.netangels.ru.

;; Query time: 534 msec

# Повторный запрос (из кэша)
$ dig @127.0.0.2 -x 91.201.52.139

;; Query time: 2 msec  # Заметно быстрее благодаря кэшированию
```

### Ручная настройка

Сервер можно настроить с помощью JSON-файла конфигурации. Вы можете сгенерировать файл конфигурации по умолчанию с помощью:

```bash
sudo python3 -m server -g config.json
```

Параметры конфигурации по умолчанию:
- `hostname`: '127.0.0.2'
- `port`: 53
- `max_threads`: 5
- `cache_size`: 100
- `log_file`: 'log.txt'
- `cache_file`: 'cache.pkl'
- `proxy_hostname`: "a.root-servers.net"
- `proxy_port`: 53

### Запуск сервера

1. Сгенерируйте конфигурацию (если еще не сделано):
```bash
sudo python3 -m server -g config.json
```

2. Запустите сервер:
```bash
sudo python3 -m server -c config.json
```

Дополнительные опции:
- `-h, --help`: Показать справочное сообщение
- `-v, --verbose`: Запустить сервер в режиме подробного логирования

## Тестирование

Проект включает модульные тесты для системы кэширования. Для запуска тестов:

```bash
make test
```

или

```bash
python -m unittest tests/test_timed_lru_cache.py -v
```

Тестовое покрытие включает:
- Базовые операции с кэшем (добавление, получение)
- Истечение срока действия TTL
- Вытеснение по LRU
- Сохранение в файл
- Потокобезопасность
- Граничные случаи

## Структура проекта

```
dns-server/
├── server/
│   ├── __main__.py      # Точка входа сервера
│   ├── server.py        # Основная реализация сервера
│   ├── config.py        # Управление конфигурацией
│   └── timed_lru_cache.py  # Система кэширования
├── entities/
│   ├── dns_message.py   # Обработка DNS-сообщений
│   ├── flags.py         # DNS-флаги
│   ├── query.py         # Обработка DNS-запросов
│   └── question.py      # Обработка DNS-вопросов
├── tests/
│   └── test_timed_lru_cache.py  # Модульные тесты
├── Makefile            # Скрипты автоматизации
└── README.md
```

## Требования

- Python 3.x
- Права root/администратора (для привязки к порту 53)
- Make (для использования Makefile)

## Автор

**Артём Борисов**

## Лицензия

Этот проект распространяется под лицензией MIT - подробности в файле LICENSE.
