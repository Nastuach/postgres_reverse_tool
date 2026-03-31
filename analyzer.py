import re
from typing import List, Dict, Optional
from models import BusinessRule, Column


class BusinessRuleAnalyzer:
    """Анализатор бизнес-правил в PostgreSQL"""

    def __init__(self, connection):
        self.conn = connection
        self.cursor = connection.cursor()

    def extract_computed_columns(self, table_name: str) -> List[Column]:
        """Извлечение вычисляемых полей"""
        computed_columns = []

        query = """
            SELECT 
                a.attname AS column_name,
                pg_get_expr(ad.adbin, ad.adrelid) AS generated_expr,
                a.atttypid::regtype::text AS data_type
            FROM pg_attribute a
            LEFT JOIN pg_attrdef ad ON ad.adrelid = a.attrelid AND ad.adnum = a.attnum
            JOIN pg_class c ON c.oid = a.attrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public'
                AND c.relname = %s
                AND a.attgenerated != ''
        """

        try:
            self.cursor.execute(query, (table_name,))
            for row in self.cursor.fetchall():
                col = Column(
                    name=row[0],
                    data_type=row[2],
                    is_computed=True,
                    computed_expression=row[1]
                )
                computed_columns.append(col)
        except Exception as e:
            print(f"Error extracting computed columns: {e}")

        return computed_columns

    def extract_trigger_rules(self, table_name: str = None) -> List[BusinessRule]:
        """Извлечение правил из триггеров"""
        rules = []

        query = """
            SELECT 
                t.tgname AS trigger_name,
                c.relname AS table_name,
                p.proname AS function_name,
                t.tgenabled AS is_enabled,
                pg_get_triggerdef(t.oid) AS trigger_definition,
                CASE 
                    WHEN t.tgtype & 2 = 2 THEN 'BEFORE'
                    WHEN t.tgtype & 64 = 64 THEN 'INSTEAD OF'
                    ELSE 'AFTER'
                END AS timing,
                array_to_string(ARRAY(
                    SELECT CASE 
                        WHEN (t.tgtype & 4) = 4 THEN 'INSERT'
                        WHEN (t.tgtype & 8) = 8 THEN 'DELETE'
                        WHEN (t.tgtype & 16) = 16 THEN 'UPDATE'
                        WHEN (t.tgtype & 32) = 32 THEN 'TRUNCATE'
                    END
                    FROM generate_series(0, 5) s(bit)
                    WHERE (t.tgtype >> bit) & 1 = 1
                ), ', ') AS events
            FROM pg_trigger t
            JOIN pg_class c ON c.oid = t.tgrelid
            JOIN pg_proc p ON p.oid = t.tgfoid
            WHERE NOT t.tgisinternal
                AND c.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
        """

        if table_name:
            query += f" AND c.relname = '{table_name}'"

        try:
            self.cursor.execute(query)
            for row in self.cursor.fetchall():
                rule = BusinessRule(
                    name=row[0],
                    rule_type="TRIGGER",
                    table_name=row[1],
                    expression=row[4],
                    source_code=self._get_function_source(row[2]),
                    metadata={
                        'function_name': row[2],
                        'timing': row[5],
                        'event': row[6],
                        'is_enabled': row[3] != 'D'
                    }
                )
                rules.append(rule)
        except Exception as e:
            print(f"Error extracting trigger rules: {e}")

        return rules

    def _get_function_source(self, function_name: str) -> Optional[str]:
        """Получение исходного кода функции"""
        try:
            self.cursor.execute("""
                SELECT pg_get_functiondef(oid)
                FROM pg_proc
                WHERE proname = %s
            """, (function_name,))
            row = self.cursor.fetchone()
            return row[0] if row else None
        except:
            return None

    def extract_function_rules(self) -> List[BusinessRule]:
        """Извлечение бизнес-правил из функций PL/pgSQL"""
        rules = []

        query = """
            SELECT 
                p.proname AS function_name,
                n.nspname AS schema_name,
                pg_get_functiondef(p.oid) AS function_def,
                l.lanname AS language,
                p.prosrc AS source_code
            FROM pg_proc p
            JOIN pg_namespace n ON n.oid = p.pronamespace
            JOIN pg_language l ON l.oid = p.prolang
            WHERE n.nspname = 'public'
                AND l.lanname IN ('plpgsql', 'sql')
                AND p.prokind IN ('f', 'a', 'w')
        """

        try:
            self.cursor.execute(query)
            for row in self.cursor.fetchall():
                source = row[4] if row[4] else row[3]
                extracted_rules = self._analyze_plpgsql_code(source, row[0])

                rule = BusinessRule(
                    name=row[0],
                    rule_type="FUNCTION",
                    expression=row[3],
                    source_code=source,
                    metadata={
                        'schema': row[1],
                        'language': row[3],
                        'full_definition': row[2]
                    }
                )
                rule.description = "\n".join(extracted_rules) if extracted_rules else None
                rules.append(rule)
        except Exception as e:
            print(f"Error extracting function rules: {e}")

        return rules

    def _analyze_plpgsql_code(self, code: str, function_name: str) -> List[str]:
        """Статический анализ кода PL/pgSQL для выявления бизнес-правил"""
        rules = []

        if not code:
            return rules

        patterns = [
            (r'IF\s+(.*?)\s+THEN', 'Условное правило'),
            (r'RAISE\s+EXCEPTION\s+[\'"](.*?)[\'"]', 'Проверка с исключением'),
            (r'PERFORM\s+(.*?);', 'Выполнение проверки'),
            (r'ASSERT\s+(.*?);', 'Утверждение'),
            (r'CHECK\s*\((.*?)\)', 'Проверка условия'),
            (r'NOT\s+NULL', 'Проверка на NULL'),
            (r'UNIQUE\s+VIOLATION', 'Обработка уникальности'),
            (r'FOREIGN\s+KEY', 'Проверка внешнего ключа'),
            (r'CASE\s+WHEN\s+(.*?)\s+THEN', 'Условная логика'),
            (r'WHILE\s+(.*?)\s+LOOP', 'Циклическая проверка'),
            (r'FOR\s+(.*?)\s+IN\s+(.*?)\s+LOOP', 'Цикл по данным'),
            (r'NEW\s*\.\s*(\w+)', 'Доступ к новому значению'),
            (r'OLD\s*\.\s*(\w+)', 'Доступ к старому значению'),
            (r'TG_OP\s*=\s*[\'"](\w+)[\'"]', 'Операция триггера'),
        ]

        for pattern, rule_type in patterns:
            matches = re.findall(pattern, code, re.IGNORECASE | re.DOTALL)
            for match in matches:
                if match:
                    rule_text = str(match)[:150]
                    rules.append(f"{rule_type}: {rule_text}")

        if re.search(r'validate|check|verify|ensure', code, re.IGNORECASE):
            rules.append("Валидационная функция")

        if re.search(r'audit|log|history', code, re.IGNORECASE):
            rules.append("Функция аудита/логирования")

        if re.search(r'TG_OP|NEW\.|OLD\.', code):
            rules.append("Триггерная функция")

        return list(set(rules))

    def extract_check_constraints(self) -> List[BusinessRule]:
        """Извлечение CHECK-ограничений"""
        rules = []

        query = """
            SELECT 
                conname AS constraint_name,
                conrelid::regclass::text AS table_name,
                pg_get_constraintdef(oid) AS constraint_def
            FROM pg_constraint
            WHERE contype = 'c'
                AND connamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
        """

        try:
            self.cursor.execute(query)
            for row in self.cursor.fetchall():
                table_name = row[1].split('.')[-1] if '.' in row[1] else row[1]
                rule = BusinessRule(
                    name=row[0],
                    rule_type="CHECK",
                    table_name=table_name,
                    expression=row[2]
                )
                rules.append(rule)
        except Exception as e:
            print(f"Error extracting check constraints: {e}")

        return rules

    def analyze_all_rules(self) -> Dict[str, List[BusinessRule]]:
        """Анализ всех бизнес-правил"""
        return {
            'check_constraints': self.extract_check_constraints(),
            'triggers': self.extract_trigger_rules(),
            'functions': self.extract_function_rules()
        }