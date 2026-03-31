import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import threading
import os
import graphviz
import tempfile
from PIL import Image, ImageTk
import psycopg2
from typing import Dict, List

from models import Table, Constraint, ConstraintType
from analyzer import BusinessRuleAnalyzer
from extractor import DatabaseExtractor
from ui import UIComponents
from export import ExportManager


class ModernPostgresReverseApp:
    """Основное приложение для reverse engineering PostgreSQL"""

    def __init__(self, root):
        self.root = root
        self.root.title("PostgreSQL Reverse Engineering Tool v3.0")
        self.root.geometry("1400x900")
        self.root.configure(bg='#1e1e2f')

        self.diagram_path = None
        self.current_image = None
        self.current_data = None
        self.tables_data: Dict[str, Table] = {}
        self.business_rules: Dict[str, List] = {}
        self.entries = {}
        self.stats_labels = {}

        self.colors = {
            'bg': '#1e1e2f',
            'card': '#2a2a3e',
            'accent': '#7c3aed',
            'accent_hover': '#8b5cf6',
            'text': '#e2e8f0',
            'text_secondary': '#94a3b8',
            'success': '#10b981',
            'error': '#ef4444',
            'warning': '#f59e0b',
            'info': '#3b82f6'
        }

        self.extractor = DatabaseExtractor()
        self.ui = UIComponents(self)
        self.export_manager = ExportManager(self)

        self.setup_styles()
        self.create_widgets()
        self.center_window()
        self.setup_hotkeys()

    def center_window(self):
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')

        style.configure('TFrame', background=self.colors['bg'])
        style.configure('TLabel', background=self.colors['bg'], foreground=self.colors['text'])
        style.configure('TEntry', fieldbackground=self.colors['card'], foreground=self.colors['text'])
        style.configure('TButton', background=self.colors['accent'], foreground='white')
        style.configure('TLabelframe', background=self.colors['bg'], foreground=self.colors['text'])
        style.configure('TLabelframe.Label', background=self.colors['bg'], foreground=self.colors['text'])
        style.configure('TNotebook', background=self.colors['bg'], borderwidth=0)
        style.configure('TNotebook.Tab', background=self.colors['card'], foreground=self.colors['text'], padding=[20, 10])
        style.map('TNotebook.Tab', background=[('selected', self.colors['accent'])])
        style.configure('Treeview', background=self.colors['card'], foreground=self.colors['text'],
                        fieldbackground=self.colors['card'], rowheight=25)
        style.configure('Treeview.Heading', background=self.colors['accent'], foreground='white')

    def setup_hotkeys(self):
        self.root.bind('<Control-a>', lambda e: self.analyze())
        self.root.bind('<Control-r>', lambda e: self.reset_zoom())
        self.root.bind('<F5>', lambda e: self.load_diagram_image())
        self.root.bind('<Control-c>', lambda e: self.clear_results())
        self.root.bind('<Control-e>', lambda e: self.export_to_excel())
        self.root.bind('<Control-p>', lambda e: self.export_to_pdf())

    def create_widgets(self):
        header_frame = tk.Frame(self.root, bg=self.colors['accent'], height=80)
        header_frame.pack(fill='x')
        header_frame.pack_propagate(False)

        title_label = tk.Label(header_frame, text="🐘 PostgreSQL Reverse Engineering v3.0",
                               font=('Segoe UI', 18, 'bold'), bg=self.colors['accent'], fg='white')
        title_label.pack(pady=20)

        subtitle_label = tk.Label(header_frame, text="Полный анализ структуры и бизнес-правил базы данных",
                                  font=('Segoe UI', 10), bg=self.colors['accent'], fg='#c7d2fe')
        subtitle_label.pack()

        main_container = tk.Frame(self.root, bg=self.colors['bg'])
        main_container.pack(fill='both', expand=True, padx=20, pady=20)

        left_panel = tk.Frame(main_container, bg=self.colors['bg'], width=380)
        left_panel.pack(side='left', fill='both', expand=False, padx=(0, 10))
        left_panel.pack_propagate(False)

        right_panel = tk.Frame(main_container, bg=self.colors['bg'])
        right_panel.pack(side='right', fill='both', expand=True, padx=(10, 0))

        settings_frame = tk.Frame(left_panel, bg=self.colors['card'], relief='flat', bd=0)
        settings_frame.pack(fill='x', pady=(0, 20))

        settings_title = tk.Label(settings_frame, text="🔧 Настройки подключения",
                                  font=('Segoe UI', 12, 'bold'), bg=self.colors['card'], fg=self.colors['text'])
        settings_title.pack(pady=(15, 10), padx=15, anchor='w')

        fields_frame = tk.Frame(settings_frame, bg=self.colors['card'])
        fields_frame.pack(padx=15, pady=(0, 15), fill='x')

        self.ui.create_input_fields(fields_frame)

        button_frame = tk.Frame(settings_frame, bg=self.colors['card'])
        button_frame.pack(pady=(10, 15), padx=15, fill='x')

        self.analyze_btn = tk.Button(button_frame, text="🚀 Начать анализ",
                                     font=('Segoe UI', 11, 'bold'),
                                     bg=self.colors['accent'], fg='white',
                                     activebackground=self.colors['accent_hover'],
                                     activeforeground='white',
                                     relief='flat', cursor='hand2',
                                     command=self.analyze)
        self.analyze_btn.pack(side='left', padx=5, expand=True, fill='x')

        self.clear_btn = tk.Button(button_frame, text="🗑️ Очистить результаты",
                                   font=('Segoe UI', 11, 'bold'),
                                   bg=self.colors['error'], fg='white',
                                   activebackground='#dc2626',
                                   activeforeground='white',
                                   relief='flat', cursor='hand2',
                                   command=self.clear_results)
        self.clear_btn.pack(side='left', padx=5, expand=True, fill='x')

        export_frame = tk.Frame(settings_frame, bg=self.colors['card'])
        export_frame.pack(pady=(0, 15), padx=15, fill='x')

        self.pdf_btn = tk.Button(export_frame, text="📄 Экспорт в PDF",
                                 font=('Segoe UI', 10),
                                 bg=self.colors['success'], fg='white',
                                 activebackground='#059669',
                                 activeforeground='white',
                                 relief='flat', cursor='hand2',
                                 command=self.export_to_pdf)
        self.pdf_btn.pack(side='left', padx=5, expand=True, fill='x')

        self.excel_btn = tk.Button(export_frame, text="📊 Экспорт в Excel",
                                   font=('Segoe UI', 10),
                                   bg=self.colors['warning'], fg='white',
                                   activebackground='#d97706',
                                   activeforeground='white',
                                   relief='flat', cursor='hand2',
                                   command=self.export_to_excel)
        self.excel_btn.pack(side='left', padx=5, expand=True, fill='x')

        self.progress = ttk.Progressbar(settings_frame, mode='indeterminate')
        self.progress.pack(padx=15, pady=(0, 15), fill='x')

        self.status_frame = tk.Frame(settings_frame, bg=self.colors['card'])
        self.status_frame.pack(padx=15, pady=(0, 15), fill='x')

        self.status_icon = tk.Label(self.status_frame, text="●",
                                    font=('Segoe UI', 12), bg=self.colors['card'])
        self.status_icon.pack(side='left', padx=(0, 5))

        self.status_label = tk.Label(self.status_frame, text="Готов к работе",
                                     font=('Segoe UI', 9), bg=self.colors['card'],
                                     fg=self.colors['text_secondary'])
        self.status_label.pack(side='left')

        self.notebook = ttk.Notebook(right_panel)
        self.notebook.pack(fill='both', expand=True)

        self.info_tab = tk.Frame(self.notebook, bg=self.colors['bg'])
        self.notebook.add(self.info_tab, text="📊 Общая информация")
        self.ui.create_info_tab()

        self.tables_tab = tk.Frame(self.notebook, bg=self.colors['bg'])
        self.notebook.add(self.tables_tab, text="📋 Структура таблиц")
        self.ui.create_tables_tab()

        self.columns_tab = tk.Frame(self.notebook, bg=self.colors['bg'])
        self.notebook.add(self.columns_tab, text="🔍 Детали колонок")
        self.ui.create_columns_tab()

        self.constraints_tab = tk.Frame(self.notebook, bg=self.colors['bg'])
        self.notebook.add(self.constraints_tab, text="🔗 Ограничения")
        self.ui.create_constraints_tab()

        self.indexes_tab = tk.Frame(self.notebook, bg=self.colors['bg'])
        self.notebook.add(self.indexes_tab, text="📇 Индексы")
        self.ui.create_indexes_tab()

        self.triggers_tab = tk.Frame(self.notebook, bg=self.colors['bg'])
        self.notebook.add(self.triggers_tab, text="⚡ Триггеры")
        self.ui.create_triggers_tab()

        self.functions_tab = tk.Frame(self.notebook, bg=self.colors['bg'])
        self.notebook.add(self.functions_tab, text="🔧 Функции")
        self.ui.create_functions_tab()

        self.business_rules_tab = tk.Frame(self.notebook, bg=self.colors['bg'])
        self.notebook.add(self.business_rules_tab, text="📜 Бизнес-правила")
        self.ui.create_business_rules_tab()

        self.schema_tab = tk.Frame(self.notebook, bg=self.colors['bg'])
        self.notebook.add(self.schema_tab, text="📊 ER-диаграмма")
        self.ui.create_schema_image_tab()

    # Методы анализа и обработки данных
    def run_analysis(self, config):
        """Основной метод анализа"""
        try:
            conn = psycopg2.connect(**config)
            cursor = conn.cursor()

            self.update_status("Извлечение структуры таблиц...", 'info')
            tables = self.extractor.extract_tables(cursor)

            self.update_status("Извлечение колонок...", 'info')
            self.extractor.extract_columns(cursor, tables)

            self.update_status("Извлечение ограничений...", 'info')
            self.extractor.extract_constraints(cursor, tables)

            self.update_status("Извлечение индексов...", 'info')
            self.extractor.extract_indexes(cursor, tables)

            self.update_status("Извлечение триггеров...", 'info')
            triggers = self.extractor.extract_triggers(cursor, tables)

            self.update_status("Извлечение функций...", 'info')
            functions = self.extractor.extract_functions(cursor)

            self.update_status("Извлечение комментариев...", 'info')
            comments = self.extractor.extract_comments(cursor)

            self.update_status("Анализ бизнес-правил...", 'info')
            business_rules = self.analyze_business_rules(conn)

            self.update_status("Генерация ER-диаграммы...", 'info')
            self.generate_er_diagram(tables)

            cursor.close()
            conn.close()

            total_columns = sum(len(t.columns) for t in tables.values())
            total_pk = sum(1 for t in tables.values() if t.get_primary_key())
            total_fk = sum(len(t.get_foreign_keys()) for t in tables.values())
            total_indexes = sum(len(t.indexes) for t in tables.values())
            total_triggers = len(triggers)
            total_functions = len(functions)
            total_check = len(business_rules.get('check_constraints', []))

            self.tables_data = tables
            self.business_rules = business_rules

            self.current_data = {
                'tables': tables,
                'triggers': triggers,
                'functions': functions,
                'comments': comments,
                'business_rules': business_rules,
                'config': config,
                'stats': {
                    'tables': len(tables),
                    'columns': total_columns,
                    'primary_keys': total_pk,
                    'foreign_keys': total_fk,
                    'indexes': total_indexes,
                    'triggers': total_triggers,
                    'functions': total_functions,
                    'checks': total_check
                }
            }

            self.root.after(0, self.show_results, self.current_data)

        except Exception as e:
            self.root.after(0, self.show_error, str(e))

    def analyze_business_rules(self, conn) -> Dict[str, List]:
        """Анализ бизнес-правил"""
        analyzer = BusinessRuleAnalyzer(conn)
        return analyzer.analyze_all_rules()

    def generate_er_diagram(self, tables: Dict[str, Table]):
        """Генерация ER-диаграммы с помощью Graphviz"""
        try:
            with tempfile.NamedTemporaryFile(suffix='.dot', delete=False, mode='w') as f:
                dot_path = f.name

            dot = graphviz.Digraph('ER_Diagram', format='png')
            dot.attr(rankdir='TB', splines='ortho', nodesep='0.5', ranksep='0.8')
            dot.attr('node', shape='record', style='filled', fillcolor='#2a2a3e',
                     fontcolor='#e2e8f0', fontname='Segoe UI')

            for table_name, table in tables.items():
                columns_html = []
                for col in table.columns:
                    pk_mark = ''
                    pk = table.get_primary_key()
                    if pk and col.name in pk.columns:
                        pk_mark = '🔑 '

                    nullable_mark = '' if col.is_nullable else ' NOT NULL'
                    computed_mark = ' [Вычисл]' if col.is_computed else ''

                    columns_html.append(f"{pk_mark}{col.name} : {col.data_type}{nullable_mark}{computed_mark}")

                label = f"{{ {table_name} | {'|'.join(columns_html)} }}"
                dot.node(table_name, label)

            for table in tables.values():
                for fk in table.get_foreign_keys():
                    if fk.referenced_table:
                        dot.edge(fk.referenced_table, table.name,
                                label=fk.name, arrowhead='crow', arrowtail='none')

            output_path = os.path.join(tempfile.gettempdir(), 'er_diagram')
            dot.render(output_path, cleanup=True)
            self.diagram_path = f"{output_path}.png"

        except Exception as e:
            print(f"Error generating ER diagram: {e}")
            self.diagram_path = None

    def show_results(self, data):
        """Отображение результатов анализа"""
        stats = data['stats']

        self.stats_labels['📊 Таблиц'].config(text=str(stats['tables']))
        self.stats_labels['📝 Колонок'].config(text=str(stats['columns']))
        self.stats_labels['🔗 Связей FK'].config(text=str(stats['foreign_keys']))
        self.stats_labels['🔑 Первичных ключей'].config(text=str(stats['primary_keys']))
        self.stats_labels['✅ CHECK-правил'].config(text=str(stats['checks']))
        self.stats_labels['⚡ Триггеров'].config(text=str(stats['triggers']))
        self.stats_labels['🔧 Функций'].config(text=str(stats['functions']))
        self.stats_labels['📇 Индексов'].config(text=str(stats['indexes']))

        self.conn_info_text.delete(1.0, tk.END)
        conn_info = f"""
Хост: {data['config']['host']}:{data['config']['port']}
База данных: {data['config']['database']}
Пользователь: {data['config']['user']}
Дата анализа: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        self.conn_info_text.insert(tk.END, conn_info)

        self.comments_text.delete(1.0, tk.END)
        for obj, comment in data['comments'].items():
            self.comments_text.insert(tk.END, f"{obj}: {comment}\n")

        for item in self.tree.get_children():
            self.tree.delete(item)

        for table_name, table in data['tables'].items():
            pk_name = table.get_primary_key()
            pk_text = ', '.join(pk_name.columns) if pk_name else '-'
            self.tree.insert('', 'end', text=table_name,
                            values=(len(table.columns), table.row_count or 0, pk_text, table.description or ''))

        # Заполнение остальных деревьев...
        self.load_diagram_image()

        self.progress.stop()
        self.analyze_btn.config(state='normal', text="🚀 Начать анализ")
        self.update_status("Анализ завершен успешно!", 'success')
        messagebox.showinfo("Успех", f"Анализ базы данных завершен!\nНайдено {stats['tables']} таблиц, {stats['columns']} колонок")

    def update_status(self, message, status_type='info'):
        """Обновление статуса"""
        colors = {
            'info': '#94a3b8',
            'success': '#10b981',
            'warning': '#f59e0b',
            'error': '#ef4444'
        }
        self.status_label.config(text=message, fg=colors.get(status_type, '#94a3b8'))
        self.status_icon.config(fg=colors.get(status_type, '#94a3b8'))
        self.root.update_idletasks()

    def show_error(self, error):
        """Отображение ошибки"""
        self.progress.stop()
        self.analyze_btn.config(state='normal', text="🚀 Начать анализ")
        self.update_status(f"Ошибка: {error}", 'error')
        messagebox.showerror("Ошибка", f"Не удалось подключиться к БД:\n{error}")

    def clear_results(self):
        """Очистка результатов"""
        if messagebox.askyesno("Подтверждение", "Очистить все результаты анализа?"):
            for tree in [self.tree, self.columns_tree, self.constraints_tree,
                         self.indexes_tree, self.triggers_tree, self.functions_tree,
                         self.rules_tree]:
                for item in tree.get_children():
                    tree.delete(item)

            for text in [self.table_details, self.trigger_code, self.function_code,
                         self.rule_details, self.conn_info_text, self.comments_text]:
                text.delete(1.0, tk.END)

            for label in self.stats_labels:
                self.stats_labels[label].config(text='0')

            self.image_label.config(image='', text="Диаграмма не загружена")
            self.current_data = None
            self.tables_data = {}
            self.business_rules = {}

            self.update_status("Результаты очищены", 'info')
            messagebox.showinfo("Успех", "Все результаты очищены!")

    def analyze(self):
        """Запуск анализа"""
        config = {
            'host': self.entries['🌐 Хост:'].get(),
            'port': int(self.entries['🔌 Порт:'].get()),
            'database': self.entries['💾 База данных:'].get(),
            'user': self.entries['👤 Пользователь:'].get(),
            'password': self.entries['🔒 Пароль:'].get()
        }

        if not config['database']:
            messagebox.showerror("Ошибка", "Введите имя базы данных!")
            return

        self.analyze_btn.config(state='disabled', text="⏳ Анализ...")
        self.progress.start()
        self.update_status("Подключение к базе данных...", 'warning')

        thread = threading.Thread(target=self.run_analysis, args=(config,))
        thread.start()

    def export_to_pdf(self):
        """Экспорт в PDF"""
        self.export_manager.export_to_pdf()

    def export_to_excel(self):
        """Экспорт в Excel"""
        self.export_manager.export_to_excel()

    def load_diagram_image(self):
        """Загрузка ER-диаграммы"""
        if self.diagram_path and os.path.exists(self.diagram_path):
            try:
                pil_image = Image.open(self.diagram_path)
                self.original_size = pil_image.size
                new_size = (int(self.original_size[0] * self.zoom_level),
                           int(self.original_size[1] * self.zoom_level))
                resized_image = pil_image.resize(new_size, Image.Resampling.LANCZOS)
                self.current_image = ImageTk.PhotoImage(resized_image)
                self.image_label.config(image=self.current_image)
                self.image_label.update_idletasks()
                self.canvas.configure(scrollregion=self.canvas.bbox('all'))
                self.update_status("Диаграмма загружена", 'success')
            except Exception as e:
                self.image_label.config(text=f"Ошибка загрузки диаграммы: {e}",
                                       fg=self.colors['error'], bg=self.colors['card'])
                self.update_status(f"Ошибка загрузки: {e}", 'error')
        else:
            self.image_label.config(text="Диаграмма не найдена. Выполните анализ для генерации диаграммы.",
                                   fg=self.colors['warning'], bg=self.colors['card'])
            self.update_status("Диаграмма не найдена", 'warning')

    def zoom_in(self):
        self.zoom_level *= 1.2
        self.load_diagram_image()

    def zoom_out(self):
        self.zoom_level /= 1.2
        if self.zoom_level < 0.1:
            self.zoom_level = 0.1
        self.load_diagram_image()

    def reset_zoom(self):
        self.zoom_level = 1.0
        self.load_diagram_image()

    def on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def on_container_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    def search_tables(self, event):
        """Поиск таблиц"""
        search_term = self.search_entry.get().lower()
        for item in self.tree.get_children():
            if search_term in self.tree.item(item, 'text').lower():
                self.tree.reattach(item, '', 'end')
            else:
                self.tree.detach(item)

    def on_table_select(self, event):
        """Обработка выбора таблицы"""
        selection = self.tree.selection()
        if not selection:
            return
        table_name = self.tree.item(selection[0], 'text')
        if table_name in self.tables_data:
            table = self.tables_data[table_name]
            details = f"""
📁 Таблица: {table.name}
📝 Описание: {table.description or 'Нет'}
📊 Количество строк: {table.row_count or 0}
🔑 Первичный ключ: {', '.join(table.get_primary_key().columns) if table.get_primary_key() else 'Нет'}
📋 Колонки:
{'-' * 50}
"""
            for col in table.columns:
                pk_mark = '🔑 ' if table.get_primary_key() and col.name in table.get_primary_key().columns else '   '
                details += f"{pk_mark}{col.name:25} {col.data_type:20} "
                details += f"{'NULL' if col.is_nullable else 'NOT NULL':10}"
                if col.default_value:
                    details += f" DEFAULT {col.default_value}"
                if col.description:
                    details += f"\n{' ' * 30}💬 {col.description}"
                details += "\n"
            self.table_details.delete(1.0, tk.END)
            self.table_details.insert(tk.END, details)

    def on_trigger_select(self, event):
        """Обработка выбора триггера"""
        selection = self.triggers_tree.selection()
        if not selection:
            return
        trigger_name = self.triggers_tree.item(selection[0], 'text')
        for trigger in self.current_data['triggers']:
            if trigger.name == trigger_name:
                self.trigger_code.delete(1.0, tk.END)
                self.trigger_code.insert(tk.END, trigger.definition or 'Определение не найдено')
                break

    def on_function_select(self, event):
        """Обработка выбора функции"""
        selection = self.functions_tree.selection()
        if not selection:
            return
        func_name = self.functions_tree.item(selection[0], 'text')
        for func in self.current_data['functions']:
            if func.name == func_name:
                self.function_code.delete(1.0, tk.END)
                code = func.definition or 'Исходный код не найден'
                if func.business_rules:
                    code += f"\n\n📜 Выявленные бизнес-правила:\n{'-' * 50}\n"
                    code += "\n".join(func.business_rules)
                self.function_code.insert(tk.END, code)
                break

    def on_rule_select(self, event):
        """Обработка выбора бизнес-правила"""
        selection = self.rules_tree.selection()
        if not selection:
            return
        rule_name = self.rules_tree.item(selection[0], 'text')
        for rule_type, rules in self.business_rules.items():
            for rule in rules:
                if rule.name == rule_name:
                    details = f"""
📋 Правило: {rule.name}
🏷️ Тип: {rule.rule_type}
📁 Таблица: {rule.table_name or 'Не привязано'}
✅ Активно: {'Да' if rule.is_active else 'Нет'}
📝 Выражение/Описание:
{rule.expression or rule.description or 'Нет'}
"""
                    if rule.source_code:
                        details += f"""
💻 Исходный код:
{'-' * 50}
{rule.source_code}
"""
                    self.rule_details.delete(1.0, tk.END)
                    self.rule_details.insert(tk.END, details)
                    break