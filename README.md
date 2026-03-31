# 🐘 PostgreSQL Reverse Engineering Tool

Инструмент для автоматического анализа структуры базы данных PostgreSQL и выявления бизнес-правил.
Приложение позволяет автоматически анализировать структуру базы данных PostgreSQL, извлекать метаданные из системных каталогов pg_catalog и выявлять бизнес-правила, реализованные через триггеры, функции и ограничения.

## ✨ Возможности

| Функция | Описание |
|---------|----------|
| 🔍 Анализ таблиц | Извлечение всей информации о таблицах схемы public |
| 📝 Анализ колонок | Типы данных, nullable, default значения, вычисляемые поля |
| 🔗 Ограничения | PK, FK, UNIQUE, CHECK ограничения с определениями |
| 📇 Индексы | Все индексы с типами, колонками и условиями |
| ⚡ Триггеры | Триггеры с исходным кодом функций |
| 🔧 Функции | Хранимые функции и процедуры PL/pgSQL |
| 📜 Бизнес-правила | Автоматическое выявление из кода триггеров и функций |
| 📊 ER-диаграмма | Визуальная схема связей между таблицами |
| 📄 Экспорт в PDF | Генерация отчёта в формате PDF |
| 📊 Экспорт в Excel | Генерация отчёта в формате XLSX |
| 💬 Комментарии | Извлечение комментариев ко всем объектам БД |

## 🚀 Быстрый старт

### 1. Установка Python

Убедитесь, что установлен Python 3.8 или выше:

```bash
python --version
```

[Скачать Python](https://www.python.org/downloads/)

> ⚠️ При установке отметьте галочку **"Add Python to PATH"** и **"Install tcl/tk and IDLE"**

### 2. Клонирование репозитория

```bash
git clone https://github.com/ВАШ_НИК/postgres_reverse_tool.git
cd postgres_reverse_tool
```

### 3. Создание виртуального окружения

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Установка зависимостей

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Установка Graphviz

**Windows:**
1. Скачайте установщик с [graphviz.org](https://graphviz.org/download/)
2. Установите и добавьте в PATH (отметьте галочку при установке)
3. Перезапустите терминал

**Linux:**
```bash
sudo apt-get install graphviz
```

**Mac:**
```bash
brew install graphviz
```

### 6. Запуск приложения

```bash
python main.py
```

## 📸 Скриншоты

### Главное окно
![Главное окно](screenshots/main.png)

### ER-диаграмма
![ER-диаграмма](screenshots/er_diagram.png)

### Бизнес-правила
![Бизнес-правила](screenshots/rules.png)

## 📁 Структура проекта

```
postgres_reverse_tool/
├── main.py              # Точка входа в приложение
├── app.py               # Основной класс приложения
├── models.py            # Модели данных (Table, Column, Constraint...)
├── analyzer.py          # Анализатор бизнес-правил
├── extractor.py         # Извлечение данных из pg_catalog
├── ui.py                # UI компоненты Tkinter
├── export.py            # Экспорт в PDF/Excel
├── requirements.txt     # Python зависимости
├── README.md            # Документация
└── .gitignore           # Git игнор
```

## 🔧 Требования к БД

- PostgreSQL 10 или выше
- Права на чтение системных каталогов pg_catalog
- Доступ к схеме public
- Пользователь с правами SELECT на системные таблицы

## 📊 Пример использования

1. Запустите приложение: `python main.py`
2. Введите параметры подключения:
   - **Хост:** `localhost`
   - **Порт:** `5432`
   - **База данных:** `your_database`
   - **Пользователь:** `postgres`
   - **Пароль:** `your_password`
3. Нажмите **"🚀 Начать анализ"**
4. Дождитесь завершения анализа
5. Просмотрите результаты по вкладкам:
   - 📊 Общая информация
   - 📋 Структура таблиц
   - 🔍 Детали колонок
   - 🔗 Ограничения
   - 📇 Индексы
   - ⚡ Триггеры
   - 🔧 Функции
   - 📜 Бизнес-правила
   - 📊 ER-диаграмма
6. Экспортируйте отчёт (PDF или Excel)

## 🎯 Горячие клавиши

| Клавиша | Действие |
|---------|----------|
| `Ctrl+A` | Начать анализ |
| `Ctrl+R` | Сбросить масштаб диаграммы |
| `F5` | Обновить диаграмму |
| `Ctrl+C` | Очистить результаты |
| `Ctrl+E` | Экспорт в Excel |
| `Ctrl+P` | Экспорт в PDF |

## 📦 Зависимости

```
psycopg2-binary>=2.9.0    # Драйвер PostgreSQL
Pillow>=9.0.0             # Работа с изображениями
reportlab>=3.6.0          # Генерация PDF
openpyxl>=3.0.0           # Генерация Excel
graphviz>=0.20.0          # Построение ER-диаграмм
```

## 🐛 Решение проблем

### Ошибка: `No module named 'tkinter'`

**Windows:** Переустановите Python с опцией **tcl/tk**

**Linux:**
```bash
sudo apt-get install python3-tk
```

**Mac:**
```bash
brew install python-tk
```

### Ошибка: `graphviz not found`

```bash
# Установите Graphviz и добавьте в PATH
# Проверка установки:
dot -V
```

### Ошибка подключения к БД

- Проверьте, что PostgreSQL запущен
- Проверьте настройки `pg_hba.conf`
- Убедитесь в правильности учётных данных
- Проверьте права пользователя на чтение pg_catalog

### Ошибка: `psycopg2` не устанавливается

```bash
# Попробуйте установить предварительно скомпилированную версию
pip install psycopg2-binary
```

## 📝 Лицензия

MIT License

## 👤 Автор

Ваше Имя
- GitHub: [@ваш_ник](https://github.com/ваш_ник)
- Email: your.email@example.com

## 🤝 Вклад в проект

1. Fork репозиторий
2. Создайте ветку (`git checkout -b feature/AmazingFeature`)
3. Закоммитьте изменения (`git commit -m 'Add some AmazingFeature'`)
4. Push в ветку (`git push origin feature/AmazingFeature`)
5. Откройте Pull Request

## 📅 Дата обновления

Последнее обновление: 2025
