"""
Модульные тесты для PostgreSQL Reverse Engineering Tool
Запуск: python -m pytest test_unit.py -v
        или: python test_unit.py
"""

import unittest
from unittest.mock import MagicMock

from models import (
    Column, Constraint, Index, Trigger, Function, Table, BusinessRule,
    ConstraintType, TriggerEvent, TriggerTiming,
)
from extractor import DatabaseExtractor
from analyzer import BusinessRuleAnalyzer


# ─── models.py ────────────────────────────────────────────────────────────────

class TestEnums(unittest.TestCase):

    def test_constraint_type_values(self):
        self.assertEqual(ConstraintType.PRIMARY_KEY.value, "PRIMARY KEY")
        self.assertEqual(ConstraintType.FOREIGN_KEY.value, "FOREIGN KEY")
        self.assertEqual(ConstraintType.UNIQUE.value, "UNIQUE")
        self.assertEqual(ConstraintType.CHECK.value, "CHECK")
        self.assertEqual(ConstraintType.NOT_NULL.value, "NOT NULL")
        self.assertEqual(ConstraintType.EXCLUSION.value, "EXCLUSION")

    def test_trigger_event_values(self):
        self.assertEqual(TriggerEvent.INSERT.value, "INSERT")
        self.assertEqual(TriggerEvent.UPDATE.value, "UPDATE")
        self.assertEqual(TriggerEvent.DELETE.value, "DELETE")
        self.assertEqual(TriggerEvent.TRUNCATE.value, "TRUNCATE")

    def test_trigger_timing_values(self):
        self.assertEqual(TriggerTiming.BEFORE.value, "BEFORE")
        self.assertEqual(TriggerTiming.AFTER.value, "AFTER")
        self.assertEqual(TriggerTiming.INSTEAD_OF.value, "INSTEAD OF")


class TestColumn(unittest.TestCase):

    def test_creation_with_defaults(self):
        col = Column(name="id", data_type="integer")
        self.assertEqual(col.name, "id")
        self.assertEqual(col.data_type, "integer")
        self.assertTrue(col.is_nullable)
        self.assertIsNone(col.default_value)
        self.assertFalse(col.is_identity)
        self.assertFalse(col.is_computed)
        self.assertIsNone(col.computed_expression)

    def test_creation_not_nullable(self):
        col = Column(name="email", data_type="varchar(255)", is_nullable=False,
                     description="Email пользователя")
        self.assertFalse(col.is_nullable)
        self.assertEqual(col.description, "Email пользователя")

    def test_to_dict_keys(self):
        col = Column(name="price", data_type="numeric", is_nullable=False,
                     default_value="0.00", description="Цена")
        d = col.to_dict()
        for key in ("name", "data_type", "is_nullable", "default_value",
                    "is_identity", "description", "is_computed"):
            self.assertIn(key, d)

    def test_to_dict_values(self):
        col = Column(name="price", data_type="numeric", is_nullable=False,
                     default_value="0.00")
        d = col.to_dict()
        self.assertEqual(d["name"], "price")
        self.assertEqual(d["data_type"], "numeric")
        self.assertFalse(d["is_nullable"])
        self.assertEqual(d["default_value"], "0.00")

    def test_to_dict_computed_column(self):
        col = Column(name="full_name", data_type="text", is_computed=True,
                     computed_expression="first_name || ' ' || last_name")
        d = col.to_dict()
        self.assertTrue(d["is_computed"])


class TestConstraint(unittest.TestCase):

    def test_primary_key_defaults(self):
        c = Constraint(name="pk_users", type=ConstraintType.PRIMARY_KEY,
                       table_name="users", columns=["id"])
        self.assertFalse(c.is_deferrable)
        self.assertFalse(c.is_deferred)
        self.assertIsNone(c.referenced_table)

    def test_foreign_key_refs(self):
        c = Constraint(
            name="fk_orders_user",
            type=ConstraintType.FOREIGN_KEY,
            table_name="orders",
            columns=["user_id"],
            referenced_table="users",
            referenced_columns=["id"],
        )
        self.assertEqual(c.referenced_table, "users")
        self.assertEqual(c.referenced_columns, ["id"])

    def test_to_dict_type_as_string(self):
        c = Constraint(name="fk_test", type=ConstraintType.FOREIGN_KEY,
                       table_name="orders")
        self.assertEqual(c.to_dict()["type"], "FOREIGN KEY")

    def test_to_dict_check_expression(self):
        c = Constraint(name="chk_age", type=ConstraintType.CHECK,
                       table_name="persons", check_expression="age > 0")
        d = c.to_dict()
        self.assertEqual(d["check_expression"], "age > 0")
        self.assertEqual(d["name"], "chk_age")


class TestIndex(unittest.TestCase):

    def test_creation_with_defaults(self):
        idx = Index(name="idx_email", table_name="users", columns=["email"])
        self.assertFalse(idx.is_unique)
        self.assertFalse(idx.is_primary)
        self.assertEqual(idx.index_type, "btree")

    def test_unique_index(self):
        idx = Index(name="uq_email", table_name="users",
                    columns=["email"], is_unique=True)
        self.assertTrue(idx.is_unique)

    def test_to_dict_structure(self):
        idx = Index(name="idx_test", table_name="orders",
                    columns=["user_id", "status"], is_unique=True, index_type="hash")
        d = idx.to_dict()
        self.assertEqual(d["columns"], ["user_id", "status"])
        self.assertTrue(d["is_unique"])
        self.assertEqual(d["index_type"], "hash")


class TestTrigger(unittest.TestCase):

    def test_creation_enabled_by_default(self):
        t = Trigger(name="trg_audit", table_name="users",
                    function_name="audit_fn",
                    event=TriggerEvent.INSERT, timing=TriggerTiming.AFTER)
        self.assertTrue(t.is_enabled)

    def test_to_dict_enum_values(self):
        t = Trigger(name="trg_upd", table_name="orders",
                    function_name="check_order",
                    event=TriggerEvent.UPDATE, timing=TriggerTiming.BEFORE,
                    is_enabled=False)
        d = t.to_dict()
        self.assertEqual(d["event"], "UPDATE")
        self.assertEqual(d["timing"], "BEFORE")
        self.assertFalse(d["is_enabled"])


class TestFunction(unittest.TestCase):

    def test_creation_with_defaults(self):
        f = Function(name="get_user", schema_name="public", language="plpgsql")
        self.assertFalse(f.is_aggregate)
        self.assertFalse(f.is_window)
        self.assertTrue(f.is_volatile)
        self.assertEqual(f.business_rules, [])
        self.assertEqual(f.arguments, [])

    def test_to_dict_structure(self):
        f = Function(
            name="validate_email",
            schema_name="public",
            language="plpgsql",
            return_type="boolean",
            arguments=[{"name": "p_email", "type": "text"}],
            business_rules=["Проверка формата email"],
        )
        d = f.to_dict()
        self.assertEqual(d["name"], "validate_email")
        self.assertEqual(d["return_type"], "boolean")
        self.assertEqual(len(d["arguments"]), 1)
        self.assertEqual(d["business_rules"], ["Проверка формата email"])


class TestTable(unittest.TestCase):

    def _make_table(self):
        t = Table(name="orders", schema_name="public")
        t.columns = [
            Column(name="id", data_type="integer"),
            Column(name="user_id", data_type="integer"),
            Column(name="status", data_type="varchar(50)"),
        ]
        t.constraints = [
            Constraint(name="pk_orders", type=ConstraintType.PRIMARY_KEY,
                       table_name="orders", columns=["id"]),
            Constraint(name="fk_orders_user", type=ConstraintType.FOREIGN_KEY,
                       table_name="orders", columns=["user_id"],
                       referenced_table="users", referenced_columns=["id"]),
            Constraint(name="chk_status", type=ConstraintType.CHECK,
                       table_name="orders",
                       check_expression="status IN ('new', 'done')"),
        ]
        return t

    def test_default_schema(self):
        t = Table(name="test")
        self.assertEqual(t.schema_name, "public")

    def test_get_primary_key(self):
        t = self._make_table()
        pk = t.get_primary_key()
        self.assertIsNotNone(pk)
        self.assertEqual(pk.name, "pk_orders")
        self.assertEqual(pk.type, ConstraintType.PRIMARY_KEY)

    def test_get_primary_key_none_when_absent(self):
        t = Table(name="no_pk", schema_name="public")
        self.assertIsNone(t.get_primary_key())

    def test_get_foreign_keys(self):
        t = self._make_table()
        fks = t.get_foreign_keys()
        self.assertEqual(len(fks), 1)
        self.assertEqual(fks[0].name, "fk_orders_user")

    def test_get_foreign_keys_empty(self):
        t = Table(name="standalone", schema_name="public")
        self.assertEqual(t.get_foreign_keys(), [])

    def test_get_columns_by_name_found(self):
        t = self._make_table()
        col = t.get_columns_by_name("status")
        self.assertIsNotNone(col)
        self.assertEqual(col.name, "status")
        self.assertEqual(col.data_type, "varchar(50)")

    def test_get_columns_by_name_not_found(self):
        t = self._make_table()
        self.assertIsNone(t.get_columns_by_name("nonexistent"))

    def test_to_dict_structure(self):
        t = self._make_table()
        d = t.to_dict()
        self.assertEqual(d["name"], "orders")
        self.assertEqual(d["schema"], "public")
        self.assertEqual(len(d["columns"]), 3)
        self.assertEqual(len(d["constraints"]), 3)

    def test_to_dict_nested_columns(self):
        t = self._make_table()
        d = t.to_dict()
        names = [c["name"] for c in d["columns"]]
        self.assertIn("id", names)
        self.assertIn("status", names)


class TestBusinessRule(unittest.TestCase):

    def test_creation_with_defaults(self):
        rule = BusinessRule(name="check_age", rule_type="CHECK")
        self.assertTrue(rule.is_active)
        self.assertEqual(rule.metadata, {})
        self.assertIsNone(rule.table_name)

    def test_creation_full(self):
        rule = BusinessRule(
            name="trg_audit",
            rule_type="TRIGGER",
            table_name="users",
            expression="age > 18",
            metadata={"timing": "BEFORE", "event": "INSERT"},
        )
        self.assertEqual(rule.metadata["timing"], "BEFORE")
        self.assertEqual(rule.table_name, "users")


# ─── extractor.py ─────────────────────────────────────────────────────────────

class TestDatabaseExtractor(unittest.TestCase):

    def setUp(self):
        self.extractor = DatabaseExtractor()

    def _cursor(self):
        return MagicMock()

    # extract_tables

    def test_extract_tables_returns_dict(self):
        cursor = self._cursor()
        cursor.fetchall.return_value = [
            ("users", "public", "Пользователи"),
            ("orders", "public", None),
        ]
        cursor.fetchone.return_value = (10,)
        result = self.extractor.extract_tables(cursor)
        self.assertIsInstance(result, dict)
        self.assertIn("users", result)
        self.assertIn("orders", result)

    def test_extract_tables_sets_fields(self):
        cursor = self._cursor()
        cursor.fetchall.return_value = [("users", "public", "Пользователи")]
        cursor.fetchone.return_value = (42,)
        tables = self.extractor.extract_tables(cursor)
        t = tables["users"]
        self.assertEqual(t.name, "users")
        self.assertEqual(t.schema_name, "public")
        self.assertEqual(t.description, "Пользователи")
        self.assertEqual(t.row_count, 42)

    def test_extract_tables_row_count_fallback_on_error(self):
        cursor = self._cursor()
        cursor.fetchall.return_value = [("restricted", "public", None)]
        cursor.fetchone.side_effect = Exception("Permission denied")
        tables = self.extractor.extract_tables(cursor)
        self.assertEqual(tables["restricted"].row_count, 0)

    def test_extract_tables_empty_db(self):
        cursor = self._cursor()
        cursor.fetchall.return_value = []
        self.assertEqual(self.extractor.extract_tables(cursor), {})

    # extract_columns

    def test_extract_columns_adds_to_table(self):
        cursor = self._cursor()
        cursor.fetchall.return_value = [
            ("users", "id",    "integer",      False, None, True,  None, False, None),
            ("users", "email", "varchar(255)", False, None, False, "Email", False, None),
        ]
        tables = {"users": Table(name="users", schema_name="public")}
        self.extractor.extract_columns(cursor, tables)
        self.assertEqual(len(tables["users"].columns), 2)
        self.assertEqual(tables["users"].columns[0].name, "id")
        self.assertEqual(tables["users"].columns[1].name, "email")

    def test_extract_columns_ignores_unknown_table(self):
        cursor = self._cursor()
        cursor.fetchall.return_value = [
            ("ghost", "col", "text", True, None, False, None, False, None),
        ]
        tables = {"users": Table(name="users", schema_name="public")}
        self.extractor.extract_columns(cursor, tables)
        self.assertEqual(len(tables["users"].columns), 0)

    def test_extract_columns_nullable_flag(self):
        cursor = self._cursor()
        cursor.fetchall.return_value = [
            ("users", "name", "text", True,  None, False, None, False, None),
            ("users", "code", "text", False, None, False, None, False, None),
        ]
        tables = {"users": Table(name="users", schema_name="public")}
        self.extractor.extract_columns(cursor, tables)
        self.assertTrue(tables["users"].columns[0].is_nullable)
        self.assertFalse(tables["users"].columns[1].is_nullable)

    def test_extract_columns_computed_field(self):
        cursor = self._cursor()
        cursor.fetchall.return_value = [
            ("users", "full_name", "text", True, None, False, None,
             True, "first_name || ' ' || last_name"),
        ]
        tables = {"users": Table(name="users", schema_name="public")}
        self.extractor.extract_columns(cursor, tables)
        col = tables["users"].columns[0]
        self.assertTrue(col.is_computed)
        self.assertEqual(col.computed_expression, "first_name || ' ' || last_name")

    def test_extract_columns_identity_field(self):
        cursor = self._cursor()
        cursor.fetchall.return_value = [
            ("users", "id", "integer", False, None, True, None, False, None),
        ]
        tables = {"users": Table(name="users", schema_name="public")}
        self.extractor.extract_columns(cursor, tables)
        self.assertTrue(tables["users"].columns[0].is_identity)

    # extract_constraints

    def test_extract_constraints_primary_key(self):
        cursor = self._cursor()
        cursor.fetchall.return_value = [
            ("pk_users", "users", "p", "PRIMARY KEY (id)", False, False),
        ]
        tables = {"users": Table(name="users", schema_name="public")}
        self.extractor._get_constraint_columns = MagicMock(return_value=["id"])
        self.extractor._get_foreign_key_refs = MagicMock(return_value=(None, []))
        self.extractor.extract_constraints(cursor, tables)
        c = tables["users"].constraints[0]
        self.assertEqual(c.type, ConstraintType.PRIMARY_KEY)
        self.assertEqual(c.columns, ["id"])

    def test_extract_constraints_foreign_key(self):
        cursor = self._cursor()
        cursor.fetchall.return_value = [
            ("fk_orders_user", "orders", "f",
             "FOREIGN KEY (user_id) REFERENCES users(id)", False, False),
        ]
        tables = {
            "orders": Table(name="orders", schema_name="public"),
            "users":  Table(name="users",  schema_name="public"),
        }
        self.extractor._get_constraint_columns = MagicMock(return_value=["user_id"])
        self.extractor._get_foreign_key_refs   = MagicMock(return_value=("users", ["id"]))
        self.extractor.extract_constraints(cursor, tables)
        fk = tables["orders"].constraints[0]
        self.assertEqual(fk.type, ConstraintType.FOREIGN_KEY)
        self.assertEqual(fk.referenced_table, "users")
        self.assertEqual(fk.referenced_columns, ["id"])

    def test_extract_constraints_check(self):
        cursor = self._cursor()
        cursor.fetchall.return_value = [
            ("chk_age", "persons", "c", "CHECK ((age > 0))", False, False),
        ]
        tables = {"persons": Table(name="persons", schema_name="public")}
        self.extractor._get_constraint_columns = MagicMock(return_value=[])
        self.extractor._get_foreign_key_refs   = MagicMock(return_value=(None, []))
        self.extractor.extract_constraints(cursor, tables)
        self.assertEqual(tables["persons"].constraints[0].type, ConstraintType.CHECK)

    def test_extract_constraints_unique(self):
        cursor = self._cursor()
        cursor.fetchall.return_value = [
            ("uq_email", "users", "u", "UNIQUE (email)", False, False),
        ]
        tables = {"users": Table(name="users", schema_name="public")}
        self.extractor._get_constraint_columns = MagicMock(return_value=["email"])
        self.extractor._get_foreign_key_refs   = MagicMock(return_value=(None, []))
        self.extractor.extract_constraints(cursor, tables)
        self.assertEqual(tables["users"].constraints[0].type, ConstraintType.UNIQUE)

    def test_extract_constraints_deferrable(self):
        cursor = self._cursor()
        cursor.fetchall.return_value = [
            ("pk_users", "users", "p", "PRIMARY KEY (id)", True, True),
        ]
        tables = {"users": Table(name="users", schema_name="public")}
        self.extractor._get_constraint_columns = MagicMock(return_value=["id"])
        self.extractor._get_foreign_key_refs   = MagicMock(return_value=(None, []))
        self.extractor.extract_constraints(cursor, tables)
        c = tables["users"].constraints[0]
        self.assertTrue(c.is_deferrable)
        self.assertTrue(c.is_deferred)

    def test_extract_constraints_ignores_unknown_table(self):
        cursor = self._cursor()
        cursor.fetchall.return_value = [
            ("pk_ghost", "ghost_table", "p", "PRIMARY KEY (id)", False, False),
        ]
        tables = {"users": Table(name="users", schema_name="public")}
        self.extractor._get_constraint_columns = MagicMock(return_value=["id"])
        self.extractor.extract_constraints(cursor, tables)
        self.assertEqual(len(tables["users"].constraints), 0)

    def test_extract_constraints_table_name_with_schema_prefix(self):
        """'public.users' должен нормализоваться до 'users'"""
        cursor = self._cursor()
        cursor.fetchall.return_value = [
            ("pk_users", "public.users", "p", "PRIMARY KEY (id)", False, False),
        ]
        tables = {"users": Table(name="users", schema_name="public")}
        self.extractor._get_constraint_columns = MagicMock(return_value=["id"])
        self.extractor._get_foreign_key_refs   = MagicMock(return_value=(None, []))
        self.extractor.extract_constraints(cursor, tables)
        self.assertEqual(len(tables["users"].constraints), 1)

    # extract_indexes

    def test_extract_indexes_adds_to_table(self):
        cursor = self._cursor()
        cursor.fetchall.return_value = [
            ("idx_email", "users", False, False, "btree",
             "CREATE INDEX idx_email ON users(email)"),
        ]
        tables = {"users": Table(name="users", schema_name="public")}
        self.extractor._get_index_columns = MagicMock(return_value=["email"])
        self.extractor.extract_indexes(cursor, tables)
        self.assertEqual(len(tables["users"].indexes), 1)
        idx = tables["users"].indexes[0]
        self.assertEqual(idx.name, "idx_email")
        self.assertEqual(idx.index_type, "btree")
        self.assertFalse(idx.is_unique)

    def test_extract_indexes_unique_flag(self):
        cursor = self._cursor()
        cursor.fetchall.return_value = [
            ("uq_email", "users", True, False, "btree", "CREATE UNIQUE INDEX ..."),
        ]
        tables = {"users": Table(name="users", schema_name="public")}
        self.extractor._get_index_columns = MagicMock(return_value=["email"])
        self.extractor.extract_indexes(cursor, tables)
        self.assertTrue(tables["users"].indexes[0].is_unique)

    def test_extract_indexes_primary_flag(self):
        cursor = self._cursor()
        cursor.fetchall.return_value = [
            ("users_pkey", "users", True, True, "btree", "CREATE UNIQUE INDEX ..."),
        ]
        tables = {"users": Table(name="users", schema_name="public")}
        self.extractor._get_index_columns = MagicMock(return_value=["id"])
        self.extractor.extract_indexes(cursor, tables)
        self.assertTrue(tables["users"].indexes[0].is_primary)

    # extract_triggers

    def test_extract_triggers_before_insert(self):
        cursor = self._cursor()
        cursor.fetchall.return_value = [
            ("trg_validate", "users", "validate_fn", "O", "...", "BEFORE", "INSERT"),
        ]
        tables = {"users": Table(name="users", schema_name="public")}
        triggers = self.extractor.extract_triggers(cursor, tables)
        self.assertEqual(len(triggers), 1)
        self.assertEqual(triggers[0].timing, TriggerTiming.BEFORE)
        self.assertEqual(triggers[0].event, TriggerEvent.INSERT)

    def test_extract_triggers_after_update(self):
        cursor = self._cursor()
        cursor.fetchall.return_value = [
            ("trg_audit", "orders", "audit_fn", "O", "...", "AFTER", "UPDATE"),
        ]
        tables = {"orders": Table(name="orders", schema_name="public")}
        triggers = self.extractor.extract_triggers(cursor, tables)
        self.assertEqual(triggers[0].timing, TriggerTiming.AFTER)
        self.assertEqual(triggers[0].event, TriggerEvent.UPDATE)

    def test_extract_triggers_instead_of(self):
        cursor = self._cursor()
        cursor.fetchall.return_value = [
            ("trg_view", "orders_view", "handle_fn", "O", "...", "INSTEAD OF", "INSERT"),
        ]
        tables = {"orders_view": Table(name="orders_view", schema_name="public")}
        triggers = self.extractor.extract_triggers(cursor, tables)
        self.assertEqual(triggers[0].timing, TriggerTiming.INSTEAD_OF)

    def test_extract_triggers_disabled(self):
        cursor = self._cursor()
        cursor.fetchall.return_value = [
            ("trg_off", "users", "fn", "D", "...", "AFTER", "INSERT"),
        ]
        tables = {"users": Table(name="users", schema_name="public")}
        triggers = self.extractor.extract_triggers(cursor, tables)
        self.assertFalse(triggers[0].is_enabled)

    def test_extract_triggers_adds_to_table(self):
        cursor = self._cursor()
        cursor.fetchall.return_value = [
            ("trg_audit", "users", "audit_fn", "O", "...", "AFTER", "DELETE"),
        ]
        tables = {"users": Table(name="users", schema_name="public")}
        self.extractor.extract_triggers(cursor, tables)
        self.assertEqual(len(tables["users"].triggers), 1)

    def test_extract_triggers_delete_event(self):
        cursor = self._cursor()
        cursor.fetchall.return_value = [
            ("trg_del", "users", "fn", "O", "...", "AFTER", "DELETE"),
        ]
        tables = {"users": Table(name="users", schema_name="public")}
        triggers = self.extractor.extract_triggers(cursor, tables)
        self.assertEqual(triggers[0].event, TriggerEvent.DELETE)

    # _parse_function_arguments

    def test_parse_arguments_empty_string(self):
        self.assertEqual(self.extractor._parse_function_arguments(""), [])

    def test_parse_arguments_none(self):
        self.assertEqual(self.extractor._parse_function_arguments(None), [])

    def test_parse_arguments_single_named(self):
        result = self.extractor._parse_function_arguments("p_id integer")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "p_id")
        self.assertEqual(result[0]["type"], "integer")

    def test_parse_arguments_multiple_named(self):
        result = self.extractor._parse_function_arguments("p_name text, p_age integer")
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["name"], "p_name")
        self.assertEqual(result[0]["type"], "text")
        self.assertEqual(result[1]["name"], "p_age")
        self.assertEqual(result[1]["type"], "integer")

    def test_parse_arguments_type_only(self):
        result = self.extractor._parse_function_arguments("integer")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["type"], "integer")
        self.assertEqual(result[0]["name"], "arg1")

    def test_parse_arguments_two_types_only(self):
        result = self.extractor._parse_function_arguments("integer, text")
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["name"], "arg1")
        self.assertEqual(result[1]["name"], "arg2")

    # _analyze_function_rules

    def test_analyze_function_rules_empty(self):
        self.assertEqual(self.extractor._analyze_function_rules(""), [])

    def test_analyze_function_rules_none(self):
        self.assertEqual(self.extractor._analyze_function_rules(None), [])

    def test_analyze_function_rules_detects_if(self):
        code = "IF NEW.age < 0 THEN RAISE EXCEPTION 'Invalid'; END IF;"
        result = self.extractor._analyze_function_rules(code)
        self.assertTrue(any("Условное правило" in r for r in result))

    def test_analyze_function_rules_detects_raise(self):
        code = "RAISE EXCEPTION 'Value out of range';"
        result = self.extractor._analyze_function_rules(code)
        self.assertTrue(any("Проверка с исключением" in r for r in result))

    def test_analyze_function_rules_returns_unique(self):
        code = "IF x>0 THEN NULL; END IF; IF x>0 THEN NULL; END IF;"
        result = self.extractor._analyze_function_rules(code)
        self.assertEqual(len(result), len(set(result)))


# ─── analyzer.py ──────────────────────────────────────────────────────────────

class TestBusinessRuleAnalyzer(unittest.TestCase):

    def _make_analyzer(self):
        conn = MagicMock()
        conn.cursor.return_value = MagicMock()
        return BusinessRuleAnalyzer(conn)

    # _analyze_plpgsql_code

    def test_analyze_empty_code(self):
        analyzer = self._make_analyzer()
        self.assertEqual(analyzer._analyze_plpgsql_code("", "fn"), [])

    def test_analyze_none_code(self):
        analyzer = self._make_analyzer()
        self.assertEqual(analyzer._analyze_plpgsql_code(None, "fn"), [])

    def test_analyze_if_condition(self):
        code = "IF NEW.price < 0 THEN RAISE EXCEPTION 'Negative price'; END IF;"
        result = self._make_analyzer()._analyze_plpgsql_code(code, "check_price")
        self.assertTrue(any("Условное правило" in r for r in result))

    def test_analyze_raise_exception(self):
        code = "RAISE EXCEPTION 'Value out of range';"
        result = self._make_analyzer()._analyze_plpgsql_code(code, "validate")
        self.assertTrue(any("Проверка с исключением" in r for r in result))

    def test_analyze_tg_op(self):
        code = "IF TG_OP = 'INSERT' THEN NULL; END IF;"
        result = self._make_analyzer()._analyze_plpgsql_code(code, "handle_trigger")
        self.assertTrue(any("Операция триггера" in r for r in result))

    def test_analyze_new_old_references(self):
        code = "UPDATE t SET val = NEW.val WHERE id = OLD.id;"
        result = self._make_analyzer()._analyze_plpgsql_code(code, "sync")
        self.assertTrue(any("Доступ к новому значению" in r for r in result))
        self.assertTrue(any("Доступ к старому значению" in r for r in result))

    def test_analyze_trigger_function_marker(self):
        code = "IF TG_OP = 'UPDATE' THEN NEW.updated_at := now(); END IF;"
        result = self._make_analyzer()._analyze_plpgsql_code(code, "set_ts")
        self.assertIn("Триггерная функция", result)

    def test_analyze_validation_marker(self):
        code = "-- This function validates the input"
        result = self._make_analyzer()._analyze_plpgsql_code(code, "do_validate")
        self.assertIn("Валидационная функция", result)

    def test_analyze_audit_marker(self):
        code = "INSERT INTO audit_log VALUES (NEW.id, now());"
        result = self._make_analyzer()._analyze_plpgsql_code(code, "write_audit")
        self.assertIn("Функция аудита/логирования", result)

    def test_analyze_case_when(self):
        code = "result := CASE WHEN status = 'active' THEN 1 ELSE 0 END;"
        result = self._make_analyzer()._analyze_plpgsql_code(code, "get_status")
        self.assertTrue(any("Условная логика" in r for r in result))

    def test_analyze_returns_unique(self):
        code = "IF a>0 THEN NULL; END IF;\nIF a>0 THEN NULL; END IF;"
        result = self._make_analyzer()._analyze_plpgsql_code(code, "test")
        self.assertEqual(len(result), len(set(result)))

    # extract_check_constraints

    def test_extract_check_constraints_basic(self):
        analyzer = self._make_analyzer()
        analyzer.cursor.fetchall.return_value = [
            ("chk_age",   "persons",  "CHECK ((age > 0))"),
            ("chk_price", "products", "CHECK ((price >= 0))"),
        ]
        rules = analyzer.extract_check_constraints()
        self.assertEqual(len(rules), 2)
        self.assertEqual(rules[0].rule_type, "CHECK")
        self.assertEqual(rules[0].name, "chk_age")
        self.assertEqual(rules[0].table_name, "persons")

    def test_extract_check_constraints_normalizes_schema_prefix(self):
        analyzer = self._make_analyzer()
        analyzer.cursor.fetchall.return_value = [
            ("chk_age", "public.persons", "CHECK ((age > 0))"),
        ]
        rules = analyzer.extract_check_constraints()
        self.assertEqual(rules[0].table_name, "persons")

    def test_extract_check_constraints_empty(self):
        analyzer = self._make_analyzer()
        analyzer.cursor.fetchall.return_value = []
        self.assertEqual(analyzer.extract_check_constraints(), [])

    def test_extract_check_constraints_db_error_returns_empty(self):
        analyzer = self._make_analyzer()
        analyzer.cursor.execute.side_effect = Exception("DB error")
        self.assertEqual(analyzer.extract_check_constraints(), [])

    # extract_trigger_rules

    def test_extract_trigger_rules_basic(self):
        analyzer = self._make_analyzer()
        analyzer.cursor.fetchall.return_value = [
            ("trg_audit", "users", "audit_fn", "O", "CREATE TRIGGER ...", "AFTER", "INSERT"),
        ]
        analyzer._get_function_source = MagicMock(return_value="BEGIN RETURN NEW; END;")
        rules = analyzer.extract_trigger_rules()
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0].rule_type, "TRIGGER")
        self.assertEqual(rules[0].name, "trg_audit")
        self.assertEqual(rules[0].metadata["timing"], "AFTER")
        self.assertEqual(rules[0].metadata["event"], "INSERT")

    def test_extract_trigger_rules_disabled_flag(self):
        analyzer = self._make_analyzer()
        analyzer.cursor.fetchall.return_value = [
            ("trg_off", "users", "fn", "D", "...", "BEFORE", "UPDATE"),
        ]
        analyzer._get_function_source = MagicMock(return_value=None)
        rules = analyzer.extract_trigger_rules()
        self.assertFalse(rules[0].metadata["is_enabled"])

    def test_extract_trigger_rules_enabled_flag(self):
        analyzer = self._make_analyzer()
        analyzer.cursor.fetchall.return_value = [
            ("trg_on", "users", "fn", "O", "...", "AFTER", "DELETE"),
        ]
        analyzer._get_function_source = MagicMock(return_value=None)
        rules = analyzer.extract_trigger_rules()
        self.assertTrue(rules[0].metadata["is_enabled"])

    def test_extract_trigger_rules_db_error_returns_empty(self):
        analyzer = self._make_analyzer()
        analyzer.cursor.execute.side_effect = Exception("Connection lost")
        self.assertEqual(analyzer.extract_trigger_rules(), [])

    # analyze_all_rules

    def test_analyze_all_rules_keys(self):
        analyzer = self._make_analyzer()
        analyzer.extract_check_constraints = MagicMock(return_value=[])
        analyzer.extract_trigger_rules     = MagicMock(return_value=[])
        analyzer.extract_function_rules    = MagicMock(return_value=[])
        result = analyzer.analyze_all_rules()
        self.assertIn("check_constraints", result)
        self.assertIn("triggers", result)
        self.assertIn("functions", result)

    def test_analyze_all_rules_calls_each_method(self):
        analyzer = self._make_analyzer()
        analyzer.extract_check_constraints = MagicMock(return_value=[])
        analyzer.extract_trigger_rules     = MagicMock(return_value=[])
        analyzer.extract_function_rules    = MagicMock(return_value=[])
        analyzer.analyze_all_rules()
        analyzer.extract_check_constraints.assert_called_once()
        analyzer.extract_trigger_rules.assert_called_once()
        analyzer.extract_function_rules.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)
