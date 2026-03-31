import tkinter as tk
from tkinter import ttk, scrolledtext
from typing import Dict


class UIComponents:
    """Компоненты пользовательского интерфейса"""

    def __init__(self, app):
        self.app = app
        self.colors = app.colors

    def create_input_fields(self, parent):
        """Создание полей ввода подключения"""
        fields = [
            ('🌐 Хост:', 'localhost'),
            ('🔌 Порт:', '5432'),
            ('💾 База данных:', ''),
            ('👤 Пользователь:', 'postgres'),
            ('🔒 Пароль:', '')
        ]

        self.app.entries = {}
        for i, (label, default) in enumerate(fields):
            row_frame = tk.Frame(parent, bg=self.colors['card'])
            row_frame.pack(fill='x', pady=5)

            lbl = tk.Label(row_frame, text=label, width=15, anchor='w',
                           font=('Segoe UI', 10), bg=self.colors['card'], 
                           fg=self.colors['text_secondary'])
            lbl.pack(side='left')

            entry = tk.Entry(row_frame, font=('Segoe UI', 10), bg='#3a3a5e',
                            fg=self.colors['text'], insertbackground='white',
                            relief='flat', highlightthickness=1, 
                            highlightcolor=self.colors['accent'])
            entry.pack(side='left', fill='x', expand=True, padx=(10, 0))
            entry.insert(0, default)

            if 'Пароль' in label:
                entry.config(show='•')

            self.app.entries[label] = entry

        return self.app.entries

    def create_info_tab(self):
        """Создание вкладки общей информации"""
        stats_frame = tk.Frame(self.app.info_tab, bg=self.colors['card'], relief='flat')
        stats_frame.pack(fill='x', padx=20, pady=20)

        stats_title = tk.Label(stats_frame, text="📈 Статистика базы данных",
                               font=('Segoe UI', 14, 'bold'), bg=self.colors['card'], 
                               fg=self.colors['text'])
        stats_title.pack(pady=(15, 10), padx=15, anchor='w')

        stats_grid = tk.Frame(stats_frame, bg=self.colors['card'])
        stats_grid.pack(padx=15, pady=(0, 15), fill='both')

        self.app.stats_labels = {}
        stats_items = [
            ('📊 Таблиц', '0', '#7c3aed'),
            ('📝 Колонок', '0', '#10b981'),
            ('🔗 Связей FK', '0', '#f59e0b'),
            ('🔑 Первичных ключей', '0', '#ef4444'),
            ('✅ CHECK-правил', '0', '#06b6d4'),
            ('⚡ Триггеров', '0', '#ec4899'),
            ('🔧 Функций', '0', '#8b5cf6'),
            ('📇 Индексов', '0', '#14b8a6')
        ]

        for i, (name, value, color) in enumerate(stats_items):
            item_frame = tk.Frame(stats_grid, bg=self.colors['card'])
            item_frame.grid(row=i//2, column=i%2, padx=10, pady=10, sticky='nsew')

            name_label = tk.Label(item_frame, text=name, font=('Segoe UI', 10),
                                 bg=self.colors['card'], fg=self.colors['text_secondary'])
            name_label.pack()

            value_label = tk.Label(item_frame, text=value, font=('Segoe UI', 24, 'bold'),
                                  bg=self.colors['card'], fg=color)
            value_label.pack()

            self.app.stats_labels[name] = value_label

        stats_grid.grid_columnconfigure(0, weight=1)
        stats_grid.grid_columnconfigure(1, weight=1)

        self._create_conn_info_section()
        self._create_comments_section()

    def _create_conn_info_section(self):
        """Создание секции информации о подключении"""
        conn_frame = tk.Frame(self.app.info_tab, bg=self.colors['card'], relief='flat')
        conn_frame.pack(fill='x', padx=20, pady=(0, 20))

        conn_title = tk.Label(conn_frame, text="🔌 Информация о подключении",
                              font=('Segoe UI', 14, 'bold'), bg=self.colors['card'], 
                              fg=self.colors['text'])
        conn_title.pack(pady=(15, 10), padx=15, anchor='w')

        self.app.conn_info_text = scrolledtext.ScrolledText(conn_frame, height=6,
                                                            bg='#3a3a5e', fg=self.colors['text'],
                                                            font=('Consolas', 10), relief='flat',
                                                            wrap=tk.WORD)
        self.app.conn_info_text.pack(padx=15, pady=(0, 15), fill='both', expand=True)

    def _create_comments_section(self):
        """Создание секции комментариев"""
        comments_frame = tk.Frame(self.app.info_tab, bg=self.colors['card'], relief='flat')
        comments_frame.pack(fill='x', padx=20, pady=(0, 20))

        comments_title = tk.Label(comments_frame, text="💬 Комментарии к объектам",
                                  font=('Segoe UI', 14, 'bold'), bg=self.colors['card'], 
                                  fg=self.colors['text'])
        comments_title.pack(pady=(15, 10), padx=15, anchor='w')

        self.app.comments_text = scrolledtext.ScrolledText(comments_frame, height=8,
                                                           bg='#3a3a5e', fg=self.colors['text'],
                                                           font=('Consolas', 10), relief='flat')
        self.app.comments_text.pack(padx=15, pady=(0, 15), fill='both', expand=True)

    def create_tables_tab(self):
        """Создание вкладки таблиц"""
        self.app.tree_frame = tk.Frame(self.app.tables_tab, bg=self.colors['card'])
        self.app.tree_frame.pack(fill='both', expand=True, padx=20, pady=20)

        search_frame = tk.Frame(self.app.tree_frame, bg=self.colors['card'])
        search_frame.pack(fill='x', pady=(0, 10))

        tk.Label(search_frame, text="🔍 Поиск: ", bg=self.colors['card'], 
                fg=self.colors['text']).pack(side='left', padx=(0, 10))

        self.app.search_entry = tk.Entry(search_frame, font=('Segoe UI', 10),
                                         bg='#3a3a5e', fg=self.colors['text'],
                                         relief='flat')
        self.app.search_entry.pack(side='left', fill='x', expand=True)
        self.app.search_entry.bind('<KeyRelease>', self.app.search_tables)

        self.app.tree = ttk.Treeview(self.app.tree_frame, 
                                     columns=('columns', 'rows', 'pk', 'description'), 
                                     show='tree headings')
        self.app.tree.heading('#0', text='Таблица')
        self.app.tree.heading('columns', text='Колонки')
        self.app.tree.heading('rows', text='Строки')
        self.app.tree.heading('pk', text='PK')
        self.app.tree.heading('description', text='Описание')

        self.app.tree.column('#0', width=250)
        self.app.tree.column('columns', width=80)
        self.app.tree.column('rows', width=80)
        self.app.tree.column('pk', width=150)
        self.app.tree.column('description', width=200)

        tree_scroll = ttk.Scrollbar(self.app.tree_frame, orient='vertical', 
                                    command=self.app.tree.yview)
        self.app.tree.configure(yscrollcommand=tree_scroll.set)

        self.app.tree.pack(side='left', fill='both', expand=True)
        tree_scroll.pack(side='right', fill='y')

        self.app.table_details = scrolledtext.ScrolledText(self.app.tree_frame, height=8,
                                                           bg='#3a3a5e', fg=self.colors['text'],
                                                           font=('Consolas', 9), relief='flat')
        self.app.table_details.pack(fill='x', pady=(10, 0))

        self.app.tree.bind('<<TreeviewSelect>>', self.app.on_table_select)

    def create_columns_tab(self):
        """Создание вкладки колонок"""
        columns_frame = tk.Frame(self.app.columns_tab, bg=self.colors['card'])
        columns_frame.pack(fill='both', expand=True, padx=20, pady=20)

        self.app.columns_tree = ttk.Treeview(columns_frame, 
            columns=('table', 'type', 'nullable', 'default', 'computed', 'description'), 
            show='tree headings')
        self.app.columns_tree.heading('#0', text='Колонка')
        self.app.columns_tree.heading('table', text='Таблица')
        self.app.columns_tree.heading('type', text='Тип')
        self.app.columns_tree.heading('nullable', text='Nullable')
        self.app.columns_tree.heading('default', text='Default')
        self.app.columns_tree.heading('computed', text='Вычисляемое')
        self.app.columns_tree.heading('description', text='Описание')

        self.app.columns_tree.column('#0', width=200)
        self.app.columns_tree.column('table', width=150)
        self.app.columns_tree.column('type', width=120)
        self.app.columns_tree.column('nullable', width=80)
        self.app.columns_tree.column('default', width=150)
        self.app.columns_tree.column('computed', width=100)
        self.app.columns_tree.column('description', width=200)

        scroll = ttk.Scrollbar(columns_frame, orient='vertical', 
                               command=self.app.columns_tree.yview)
        self.app.columns_tree.configure(yscrollcommand=scroll.set)

        self.app.columns_tree.pack(side='left', fill='both', expand=True)
        scroll.pack(side='right', fill='y')

    def create_constraints_tab(self):
        """Создание вкладки ограничений"""
        constraints_frame = tk.Frame(self.app.constraints_tab, bg=self.colors['card'])
        constraints_frame.pack(fill='both', expand=True, padx=20, pady=20)

        self.app.constraints_tree = ttk.Treeview(constraints_frame, 
            columns=('type', 'table', 'columns', 'reference'), show='tree headings')
        self.app.constraints_tree.heading('#0', text='Ограничение')
        self.app.constraints_tree.heading('type', text='Тип')
        self.app.constraints_tree.heading('table', text='Таблица')
        self.app.constraints_tree.heading('columns', text='Колонки')
        self.app.constraints_tree.heading('reference', text='Ссылка')

        self.app.constraints_tree.column('#0', width=200)
        self.app.constraints_tree.column('type', width=120)
        self.app.constraints_tree.column('table', width=150)
        self.app.constraints_tree.column('columns', width=200)
        self.app.constraints_tree.column('reference', width=200)

        scroll = ttk.Scrollbar(constraints_frame, orient='vertical', 
                               command=self.app.constraints_tree.yview)
        self.app.constraints_tree.configure(yscrollcommand=scroll.set)

        self.app.constraints_tree.pack(side='left', fill='both', expand=True)
        scroll.pack(side='right', fill='y')

    def create_indexes_tab(self):
        """Создание вкладки индексов"""
        indexes_frame = tk.Frame(self.app.indexes_tab, bg=self.colors['card'])
        indexes_frame.pack(fill='both', expand=True, padx=20, pady=20)

        self.app.indexes_tree = ttk.Treeview(indexes_frame, 
            columns=('table', 'columns', 'unique', 'type'), show='tree headings')
        self.app.indexes_tree.heading('#0', text='Индекс')
        self.app.indexes_tree.heading('table', text='Таблица')
        self.app.indexes_tree.heading('columns', text='Колонки')
        self.app.indexes_tree.heading('unique', text='Уникальный')
        self.app.indexes_tree.heading('type', text='Тип')

        self.app.indexes_tree.column('#0', width=200)
        self.app.indexes_tree.column('table', width=150)
        self.app.indexes_tree.column('columns', width=250)
        self.app.indexes_tree.column('unique', width=80)
        self.app.indexes_tree.column('type', width=100)

        scroll = ttk.Scrollbar(indexes_frame, orient='vertical', 
                               command=self.app.indexes_tree.yview)
        self.app.indexes_tree.configure(yscrollcommand=scroll.set)

        self.app.indexes_tree.pack(side='left', fill='both', expand=True)
        scroll.pack(side='right', fill='y')

    def create_triggers_tab(self):
        """Создание вкладки триггеров"""
        triggers_frame = tk.Frame(self.app.triggers_tab, bg=self.colors['card'])
        triggers_frame.pack(fill='both', expand=True, padx=20, pady=20)

        self.app.triggers_tree = ttk.Treeview(triggers_frame, 
            columns=('table', 'event', 'timing', 'function', 'enabled'), show='tree headings')
        self.app.triggers_tree.heading('#0', text='Триггер')
        self.app.triggers_tree.heading('table', text='Таблица')
        self.app.triggers_tree.heading('event', text='Событие')
        self.app.triggers_tree.heading('timing', text='Время')
        self.app.triggers_tree.heading('function', text='Функция')
        self.app.triggers_tree.heading('enabled', text='Включен')

        self.app.triggers_tree.column('#0', width=200)
        self.app.triggers_tree.column('table', width=150)
        self.app.triggers_tree.column('event', width=100)
        self.app.triggers_tree.column('timing', width=100)
        self.app.triggers_tree.column('function', width=200)
        self.app.triggers_tree.column('enabled', width=80)

        scroll = ttk.Scrollbar(triggers_frame, orient='vertical', 
                               command=self.app.triggers_tree.yview)
        self.app.triggers_tree.configure(yscrollcommand=scroll.set)

        self.app.triggers_tree.pack(side='left', fill='both', expand=True)
        scroll.pack(side='right', fill='y')

        self.app.trigger_code = scrolledtext.ScrolledText(triggers_frame, height=6,
                                                          bg='#3a3a5e', fg=self.colors['text'],
                                                          font=('Consolas', 9), relief='flat')
        self.app.trigger_code.pack(fill='x', pady=(10, 0))

        self.app.triggers_tree.bind('<<TreeviewSelect>>', self.app.on_trigger_select)

    def create_functions_tab(self):
        """Создание вкладки функций"""
        functions_frame = tk.Frame(self.app.functions_tab, bg=self.colors['card'])
        functions_frame.pack(fill='both', expand=True, padx=20, pady=20)

        self.app.functions_tree = ttk.Treeview(functions_frame, 
            columns=('language', 'returns', 'is_aggregate'), show='tree headings')
        self.app.functions_tree.heading('#0', text='Функция')
        self.app.functions_tree.heading('language', text='Язык')
        self.app.functions_tree.heading('returns', text='Возвращает')
        self.app.functions_tree.heading('is_aggregate', text='Агрегатная')

        self.app.functions_tree.column('#0', width=250)
        self.app.functions_tree.column('language', width=100)
        self.app.functions_tree.column('returns', width=150)
        self.app.functions_tree.column('is_aggregate', width=80)

        scroll = ttk.Scrollbar(functions_frame, orient='vertical', 
                               command=self.app.functions_tree.yview)
        self.app.functions_tree.configure(yscrollcommand=scroll.set)

        self.app.functions_tree.pack(side='left', fill='both', expand=True)
        scroll.pack(side='right', fill='y')

        self.app.function_code = scrolledtext.ScrolledText(functions_frame, height=8,
                                                           bg='#3a3a5e', fg=self.colors['text'],
                                                           font=('Consolas', 9), relief='flat')
        self.app.function_code.pack(fill='x', pady=(10, 0))

        self.app.functions_tree.bind('<<TreeviewSelect>>', self.app.on_function_select)

    def create_business_rules_tab(self):
        """Создание вкладки бизнес-правил"""
        rules_frame = tk.Frame(self.app.business_rules_tab, bg=self.colors['card'])
        rules_frame.pack(fill='both', expand=True, padx=20, pady=20)

        self.app.rules_tree = ttk.Treeview(rules_frame, 
            columns=('type', 'table', 'active'), show='tree headings')
        self.app.rules_tree.heading('#0', text='Правило')
        self.app.rules_tree.heading('type', text='Тип')
        self.app.rules_tree.heading('table', text='Таблица')
        self.app.rules_tree.heading('active', text='Активно')

        self.app.rules_tree.column('#0', width=250)
        self.app.rules_tree.column('type', width=120)
        self.app.rules_tree.column('table', width=150)
        self.app.rules_tree.column('active', width=80)

        scroll = ttk.Scrollbar(rules_frame, orient='vertical', 
                               command=self.app.rules_tree.yview)
        self.app.rules_tree.configure(yscrollcommand=scroll.set)

        self.app.rules_tree.pack(side='left', fill='both', expand=True)
        scroll.pack(side='right', fill='y')

        self.app.rule_details = scrolledtext.ScrolledText(rules_frame, height=8,
                                                          bg='#3a3a5e', fg=self.colors['text'],
                                                          font=('Consolas', 9), relief='flat')
        self.app.rule_details.pack(fill='x', pady=(10, 0))

        self.app.rules_tree.bind('<<TreeviewSelect>>', self.app.on_rule_select)

    def create_schema_image_tab(self):
        """Создание вкладки ER-диаграммы"""
        self.app.image_frame = tk.Frame(self.app.schema_tab, bg=self.colors['card'])
        self.app.image_frame.pack(fill='both', expand=True, padx=20, pady=20)

        controls_frame = tk.Frame(self.app.image_frame, bg=self.colors['card'])
        controls_frame.pack(fill='x', pady=(0, 10))

        tk.Button(controls_frame, text="🔄 Обновить диаграмму",
                 font=('Segoe UI', 9), bg=self.colors['accent'], fg='white',
                 relief='flat', cursor='hand2',
                 command=self.app.load_diagram_image).pack(side='left', padx=5)

        tk.Button(controls_frame, text="🔍 Увеличить",
                 font=('Segoe UI', 9), bg=self.colors['accent'], fg='white',
                 relief='flat', cursor='hand2',
                 command=self.app.zoom_in).pack(side='left', padx=5)

        tk.Button(controls_frame, text="🔍 Уменьшить",
                 font=('Segoe UI', 9), bg=self.colors['accent'], fg='white',
                 relief='flat', cursor='hand2',
                 command=self.app.zoom_out).pack(side='left', padx=5)

        tk.Button(controls_frame, text="↺ Сбросить масштаб",
                 font=('Segoe UI', 9), bg=self.colors['accent'], fg='white',
                 relief='flat', cursor='hand2',
                 command=self.app.reset_zoom).pack(side='left', padx=5)

        canvas_frame = tk.Frame(self.app.image_frame, bg=self.colors['card'])
        canvas_frame.pack(fill='both', expand=True)

        self.app.canvas = tk.Canvas(canvas_frame, bg=self.colors['card'], highlightthickness=0)
        h_scrollbar = ttk.Scrollbar(canvas_frame, orient='horizontal', command=self.app.canvas.xview)
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient='vertical', command=self.app.canvas.yview)
        self.app.canvas.configure(xscrollcommand=h_scrollbar.set, yscrollcommand=v_scrollbar.set)

        self.app.canvas.grid(row=0, column=0, sticky='nsew')
        h_scrollbar.grid(row=1, column=0, sticky='ew')
        v_scrollbar.grid(row=0, column=1, sticky='ns')

        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)

        self.app.image_container = tk.Frame(self.app.canvas, bg=self.colors['card'])
        self.app.canvas_window = self.app.canvas.create_window((0, 0), 
                                                                window=self.app.image_container, 
                                                                anchor='nw')

        self.app.image_label = tk.Label(self.app.image_container, bg=self.colors['card'])
        self.app.image_label.pack()

        self.app.zoom_level = 1.0

        self.app.canvas.bind('<Configure>', self.app.on_canvas_configure)
        self.app.image_container.bind('<Configure>', self.app.on_container_configure)