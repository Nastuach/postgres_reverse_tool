from typing import Dict, List, Tuple, Optional
from models import Table, Column, Constraint, Index, Trigger, Function, ConstraintType


class DatabaseExtractor:
    """Извлечение данных из pg_catalog PostgreSQL"""

    def __init__(self):
        pass

    def extract_tables(self, cursor) -> Dict[str, Table]:
        """Извлечение таблиц из pg_catalog"""
        tables = {}

        cursor.execute("""
            SELECT 
                c.relname AS table_name,
                n.nspname AS schema_name,
                obj_description(c.oid, 'pg_class') AS description
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relkind = 'r'
                AND n.nspname = 'public'
            ORDER BY c.relname
        """)

        for row in cursor.fetchall():
            table = Table(
                name=row[0],
                schema_name=row[1],
                description=row[2]
            )
            tables[table.name] = table

            try:
                cursor.execute(f'SELECT COUNT(*) FROM "{table.name}"')
                table.row_count = cursor.fetchone()[0]
            except:
                table.row_count = 0

        return tables

    def extract_columns(self, cursor, tables: Dict[str, Table]):
        """Извлечение колонок из pg_catalog"""
        cursor.execute("""
            SELECT 
                c.relname AS table_name,
                a.attname AS column_name,
                pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type,
                NOT a.attnotnull AS is_nullable,
                pg_get_expr(ad.adbin, ad.adrelid) AS default_value,
                a.attidentity != '' AS is_identity,
                col_description(a.attrelid, a.attnum) AS description,
                a.attgenerated != '' AS is_computed,
                CASE WHEN a.attgenerated != '' THEN pg_get_expr(ad.adbin, ad.adrelid) ELSE NULL END AS computed_expr
            FROM pg_attribute a
            JOIN pg_class c ON c.oid = a.attrelid
            LEFT JOIN pg_attrdef ad ON ad.adrelid = a.attrelid AND ad.adnum = a.attnum
            WHERE c.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
                AND a.attnum > 0
                AND NOT a.attisdropped
            ORDER BY c.relname, a.attnum
        """)

        for row in cursor.fetchall():
            table_name = row[0]
            if table_name in tables:
                col = Column(
                    name=row[1],
                    data_type=row[2],
                    is_nullable=row[3],
                    default_value=row[4],
                    is_identity=row[5],
                    description=row[6],
                    is_computed=row[7],
                    computed_expression=row[8]
                )
                tables[table_name].columns.append(col)

    def extract_constraints(self, cursor, tables: Dict[str, Table]):
        """Извлечение ограничений из pg_catalog"""
        cursor.execute("""
            SELECT 
                conname AS constraint_name,
                conrelid::regclass::text AS table_name,
                contype,
                pg_get_constraintdef(oid) AS definition,
                condeferrable,
                condeferred
            FROM pg_constraint
            WHERE connamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
            ORDER BY conname
        """)

        for row in cursor.fetchall():
            table_name = row[1].split('.')[-1] if '.' in row[1] else row[1]
            if table_name in tables:
                columns = self._get_constraint_columns(cursor, row[0])

                constraint_type = {
                    'p': ConstraintType.PRIMARY_KEY,
                    'f': ConstraintType.FOREIGN_KEY,
                    'u': ConstraintType.UNIQUE,
                    'c': ConstraintType.CHECK,
                    'x': ConstraintType.EXCLUSION
                }.get(row[2], ConstraintType.CHECK)

                constraint = Constraint(
                    name=row[0],
                    type=constraint_type,
                    table_name=table_name,
                    columns=columns,
                    definition=row[3],
                    is_deferrable=row[4],
                    is_deferred=row[5]
                )

                if row[2] == 'f':
                    ref_info = self._get_foreign_key_refs(cursor, row[0])
                    if ref_info:
                        constraint.referenced_table = ref_info[0]
                        constraint.referenced_columns = ref_info[1]

                tables[table_name].constraints.append(constraint)

    def _get_constraint_columns(self, cursor, constraint_name: str) -> List[str]:
        """Получение колонок ограничения"""
        try:
            cursor.execute("""
                SELECT 
                    a.attname
                FROM pg_constraint c
                JOIN pg_class ct ON ct.oid = c.conrelid
                JOIN pg_attribute a ON a.attrelid = ct.oid
                WHERE c.conname = %s
                    AND a.attnum = ANY(c.conkey)
                    AND a.attnum > 0
                ORDER BY array_position(c.conkey, a.attnum)
            """, (constraint_name,))
            return [row[0] for row in cursor.fetchall()]
        except:
            try:
                cursor.execute("""
                    SELECT 
                        a.attname
                    FROM pg_constraint c
                    JOIN pg_class ct ON ct.oid = c.conrelid
                    JOIN pg_attribute a ON a.attrelid = ct.oid
                    WHERE c.conname = %s
                        AND a.attnum = ANY(c.conkey)
                    ORDER BY a.attnum
                """, (constraint_name,))
                return [row[0] for row in cursor.fetchall()]
            except:
                return []

    def _get_foreign_key_refs(self, cursor, constraint_name: str) -> Tuple[Optional[str], List[str]]:
        """Получение ссылок внешнего ключа"""
        try:
            cursor.execute("""
                SELECT 
                    c.confrelid::regclass::text AS ref_table,
                    array_agg(a.attname ORDER BY array_position(c.confkey, a.attnum)) AS ref_columns
                FROM pg_constraint c
                JOIN pg_attribute a ON a.attrelid = c.confrelid
                WHERE c.conname = %s
                    AND a.attnum = ANY(c.confkey)
                    AND a.attnum > 0
                GROUP BY c.confrelid
            """, (constraint_name,))
            row = cursor.fetchone()
            if row:
                ref_table = row[0].split('.')[-1] if '.' in row[0] else row[0]
                return (ref_table, row[1] if row[1] else [])
        except:
            pass
        return (None, [])

    def extract_indexes(self, cursor, tables: Dict[str, Table]):
        """Извлечение индексов из pg_catalog"""
        cursor.execute("""
            SELECT 
                i.indexrelid::regclass::text AS index_name,
                c.relname AS table_name,
                i.indisunique AS is_unique,
                i.indisprimary AS is_primary,
                am.amname AS index_type,
                pg_get_indexdef(i.indexrelid) AS definition
            FROM pg_index i
            JOIN pg_class c ON c.oid = i.indrelid
            JOIN pg_class i_rel ON i_rel.oid = i.indexrelid
            JOIN pg_am am ON am.oid = i_rel.relam
            WHERE c.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
                AND c.relkind = 'r'
            ORDER BY c.relname, i.indexrelid::regclass::text
        """)

        for row in cursor.fetchall():
            index_name = row[0]
            table_name = row[1]
            if table_name in tables:
                columns = self._get_index_columns(cursor, index_name)

                index = Index(
                    name=index_name,
                    table_name=table_name,
                    columns=columns,
                    is_unique=row[2],
                    is_primary=row[3],
                    index_type=row[4],
                    definition=row[5]
                )
                tables[table_name].indexes.append(index)

    def _get_index_columns(self, cursor, index_name: str) -> List[str]:
        """Получение колонок индекса"""
        try:
            cursor.execute("""
                SELECT 
                    pg_get_indexdef(%s::regclass, k, true) AS column_name
                FROM generate_subscripts(
                    (SELECT indkey FROM pg_index WHERE indexrelid = %s::regclass), 1
                ) AS s(k)
                WHERE k IS NOT NULL
            """, (index_name, index_name))

            columns = [row[0] for row in cursor.fetchall() if row[0]]

            if not columns:
                cursor.execute("""
                    SELECT 
                        a.attname
                    FROM pg_index i
                    JOIN pg_class c ON c.oid = i.indrelid
                    JOIN pg_attribute a ON a.attrelid = c.oid
                    WHERE i.indexrelid = %s::regclass
                        AND a.attnum = ANY(i.indkey)
                        AND a.attnum > 0
                    ORDER BY array_position(i.indkey, a.attnum)
                """, (index_name,))
                columns = [row[0] for row in cursor.fetchall()]

            return columns
        except Exception as e:
            print(f"Error getting index columns for {index_name}: {e}")
            return []

    def extract_triggers(self, cursor, tables: Dict[str, Table]) -> List[Trigger]:
        """Извлечение триггеров из pg_catalog"""
        from models import TriggerEvent, TriggerTiming
        triggers = []

        cursor.execute("""
            SELECT 
                t.tgname AS trigger_name,
                c.relname AS table_name,
                p.proname AS function_name,
                t.tgenabled AS enabled_state,
                pg_get_triggerdef(t.oid) AS definition,
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
                AND c.relkind = 'r'
            ORDER BY c.relname, t.tgname
        """)

        for row in cursor.fetchall():
            table_name = row[1]

            timing = TriggerTiming.BEFORE if row[5] == 'BEFORE' else \
                     TriggerTiming.AFTER if row[5] == 'AFTER' else TriggerTiming.INSTEAD_OF

            trigger = Trigger(
                name=row[0],
                table_name=table_name,
                function_name=row[2],
                event=TriggerEvent.INSERT,
                timing=timing,
                is_enabled=row[3] != 'D',
                definition=row[4]
            )

            events_str = row[6]
            if 'INSERT' in events_str:
                trigger.event = TriggerEvent.INSERT
            if 'UPDATE' in events_str:
                trigger.event = TriggerEvent.UPDATE
            if 'DELETE' in events_str:
                trigger.event = TriggerEvent.DELETE
            if 'TRUNCATE' in events_str:
                trigger.event = TriggerEvent.TRUNCATE

            triggers.append(trigger)

            if table_name in tables:
                tables[table_name].triggers.append(trigger)

        return triggers

    def extract_functions(self, cursor) -> List[Function]:
        """Извлечение функций из pg_catalog"""
        functions = []

        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        is_postgres_11_or_higher = any(v in version for v in 
            ['PostgreSQL 11', 'PostgreSQL 12', 'PostgreSQL 13', 
             'PostgreSQL 14', 'PostgreSQL 15', 'PostgreSQL 16', 'PostgreSQL 17'])

        if is_postgres_11_or_higher:
            cursor.execute("""
                SELECT 
                    p.proname AS function_name,
                    n.nspname AS schema_name,
                    l.lanname AS language,
                    pg_get_function_result(p.oid) AS return_type,
                    CASE WHEN p.prokind = 'a' THEN true ELSE false END AS is_aggregate,
                    CASE WHEN p.prokind = 'w' THEN true ELSE false END AS is_window,
                    p.proisstrict AS isstrict,
                    CASE p.provolatile
                        WHEN 'i' THEN 'immutable'
                        WHEN 's' THEN 'stable'
                        WHEN 'v' THEN 'volatile'
                    END AS volatility,
                    pg_get_functiondef(p.oid) AS definition,
                    obj_description(p.oid, 'pg_proc') AS description,
                    pg_get_function_arguments(p.oid) AS arguments
                FROM pg_proc p
                JOIN pg_namespace n ON n.oid = p.pronamespace
                JOIN pg_language l ON l.oid = p.prolang
                WHERE n.nspname = 'public'
                    AND p.prokind IN ('f', 'a', 'w')
                    AND l.lanname IN ('plpgsql', 'sql', 'c')
                ORDER BY p.proname
            """)
        else:
            cursor.execute("""
                SELECT 
                    p.proname AS function_name,
                    n.nspname AS schema_name,
                    l.lanname AS language,
                    pg_get_function_result(p.oid) AS return_type,
                    p.proisagg AS is_aggregate,
                    p.proiswindow AS is_window,
                    p.proisstrict AS is_strict,
                    CASE p.provolatile
                        WHEN 'i' THEN 'immutable'
                        WHEN 's' THEN 'stable'
                        WHEN 'v' THEN 'volatile'
                    END AS volatility,
                    pg_get_functiondef(p.oid) AS definition,
                    obj_description(p.oid, 'pg_proc') AS description,
                    pg_get_function_arguments(p.oid) AS arguments
                FROM pg_proc p
                JOIN pg_namespace n ON n.oid = p.pronamespace
                JOIN pg_language l ON l.oid = p.prolang
                WHERE n.nspname = 'public'
                    AND l.lanname IN ('plpgsql', 'sql', 'c')
                ORDER BY p.proname
            """)

        for row in cursor.fetchall():
            arguments = self._parse_function_arguments(row[10])

            function = Function(
                name=row[0],
                schema_name=row[1],
                language=row[2],
                return_type=row[3] if row[3] else 'void',
                is_aggregate=row[4] if len(row) > 4 and row[4] else False,
                is_window=row[5] if len(row) > 5 and row[5] else False,
                is_strict=row[6] if len(row) > 6 and row[6] else False,
                is_volatile=row[7] == 'volatile' if len(row) > 7 else True,
                arguments=arguments,
                definition=row[8] if len(row) > 8 else None,
                description=row[9] if len(row) > 9 else None,
                source_code=row[8] if len(row) > 8 else None
            )

            if function.definition and function.language == 'plpgsql':
                function.business_rules = self._analyze_function_rules(function.definition)

            functions.append(function)

        return functions

    def _parse_function_arguments(self, args_str: str) -> List[Dict[str, str]]:
        """Парсинг строки аргументов функции"""
        arguments = []
        if args_str:
            parts = args_str.split(',')
            for part in parts:
                part = part.strip()
                if part:
                    if ' ' in part:
                        name, typ = part.rsplit(' ', 1)
                        arguments.append({'name': name, 'type': typ})
                    else:
                        arguments.append({'name': f'arg{len(arguments)+1}', 'type': part})
        return arguments

    def _analyze_function_rules(self, source_code: str) -> List[str]:
        """Анализ бизнес-правил в функции"""
        import re
        rules = []

        if not source_code:
            return rules

        patterns = [
            (r'IF\s+(.*?)\s+THEN', 'Условное правило'),
            (r'RAISE\s+EXCEPTION\s+[\'"](.*?)[\'"]', 'Проверка с исключением'),
            (r'PERFORM\s+(.*?);', 'Выполнение проверки'),
            (r'ASSERT\s+(.*?);', 'Утверждение'),
        ]

        for pattern, rule_type in patterns:
            matches = re.findall(pattern, source_code, re.IGNORECASE | re.DOTALL)
            for match in matches:
                if match:
                    rule_text = str(match)[:150]
                    rules.append(f"{rule_type}: {rule_text}")

        return list(set(rules))

    def extract_comments(self, cursor) -> Dict[str, str]:
        """Извлечение всех комментариев"""
        comments = {}

        cursor.execute("""
            SELECT 
                c.relname AS object_name,
                'TABLE' AS object_type,
                obj_description(c.oid, 'pg_class') AS comment
            FROM pg_class c
            WHERE c.relkind = 'r'
                AND c.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
                AND obj_description(c.oid, 'pg_class') IS NOT NULL
        """)

        for row in cursor.fetchall():
            key = f"{row[1]}: {row[0]}"
            comments[key] = row[2]

        cursor.execute("""
            SELECT 
                c.relname AS table_name,
                a.attname AS column_name,
                col_description(a.attrelid, a.attnum) AS comment
            FROM pg_attribute a
            JOIN pg_class c ON c.oid = a.attrelid
            WHERE a.attnum > 0
                AND NOT a.attisdropped
                AND c.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
                AND col_description(a.attrelid, a.attnum) IS NOT NULL
            ORDER BY c.relname, a.attnum
        """)

        for row in cursor.fetchall():
            key = f"COLUMN: {row[0]}.{row[1]}"
            comments[key] = row[2]

        cursor.execute("""
            SELECT 
                p.proname AS function_name,
                obj_description(p.oid, 'pg_proc') AS comment
            FROM pg_proc p
            JOIN pg_namespace n ON n.oid = p.pronamespace
            WHERE n.nspname = 'public'
                AND obj_description(p.oid, 'pg_proc') IS NOT NULL
        """)

        for row in cursor.fetchall():
            key = f"FUNCTION: {row[0]}"
            comments[key] = row[1]

        return comments