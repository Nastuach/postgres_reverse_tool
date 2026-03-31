-- ============================================
-- ТЕСТОВАЯ БАЗА ДАННЫХ "test"
-- Для PostgreSQL Reverse Engineering Tool
-- ============================================

-- Устанавливаем кодировку
SET client_encoding = 'UTF8';

-- Таблица: Пользователи
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_email_format CHECK (email LIKE '%@%.%'),
    CONSTRAINT chk_username_length CHECK (LENGTH(username) >= 3)
);

COMMENT ON TABLE users IS 'Users table';
COMMENT ON COLUMN users.email IS 'User email address';

-- Таблица: Роли
CREATE TABLE roles (
    role_id SERIAL PRIMARY KEY,
    role_name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE roles IS 'User roles dictionary';

-- Таблица: Связь пользователей и ролей
CREATE TABLE user_roles (
    user_id INTEGER NOT NULL,
    role_id INTEGER NOT NULL,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, role_id),
    CONSTRAINT fk_user_roles_user FOREIGN KEY (user_id) 
        REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_user_roles_role FOREIGN KEY (role_id) 
        REFERENCES roles(role_id) ON DELETE CASCADE
);

-- Таблица: Категории
CREATE TABLE categories (
    category_id SERIAL PRIMARY KEY,
    category_name VARCHAR(100) NOT NULL,
    parent_category_id INTEGER,
    is_active BOOLEAN DEFAULT true,
    CONSTRAINT fk_categories_parent FOREIGN KEY (parent_category_id) 
        REFERENCES categories(category_id) ON DELETE SET NULL
);

-- Таблица: Товары
CREATE TABLE products (
    product_id SERIAL PRIMARY KEY,
    product_name VARCHAR(200) NOT NULL,
    category_id INTEGER NOT NULL,
    price NUMERIC(10, 2) NOT NULL,
    quantity_in_stock INTEGER DEFAULT 0,
    sku VARCHAR(50) UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_products_category FOREIGN KEY (category_id) 
        REFERENCES categories(category_id) ON DELETE RESTRICT,
    CONSTRAINT chk_price_positive CHECK (price > 0),
    CONSTRAINT chk_stock_non_negative CHECK (quantity_in_stock >= 0)
);

COMMENT ON TABLE products IS 'Products catalog';
COMMENT ON COLUMN products.price IS 'Price must be positive';

-- Таблица: Заказы
CREATE TABLE orders (
    order_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'pending',
    total_amount NUMERIC(12, 2),
    CONSTRAINT fk_orders_user FOREIGN KEY (user_id) 
        REFERENCES users(user_id) ON DELETE RESTRICT,
    CONSTRAINT chk_order_status CHECK (status IN ('pending', 'confirmed', 'shipped', 'delivered', 'cancelled'))
);

-- Таблица: Элементы заказа
CREATE TABLE order_items (
    order_item_id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price NUMERIC(10, 2) NOT NULL,
    CONSTRAINT fk_order_items_order FOREIGN KEY (order_id) 
        REFERENCES orders(order_id) ON DELETE CASCADE,
    CONSTRAINT fk_order_items_product FOREIGN KEY (product_id) 
        REFERENCES products(product_id) ON DELETE RESTRICT,
    CONSTRAINT chk_quantity_positive CHECK (quantity > 0)
);

-- Таблица: Логи аудита
CREATE TABLE audit_log (
    log_id SERIAL PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    operation VARCHAR(10) NOT NULL,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- ИНДЕКСЫ
-- ============================================

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_products_category ON products(category_id);
CREATE INDEX idx_orders_user ON orders(user_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_order_items_order ON order_items(order_id);

-- ============================================
-- ФУНКЦИИ
-- ============================================

-- Функция: Обновление timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION update_updated_at_column() IS 'Trigger for updating updated_at';

-- Функция: Подсчёт суммы заказа
CREATE OR REPLACE FUNCTION calculate_order_total(p_order_id INTEGER)
RETURNS NUMERIC AS $$
DECLARE
    v_total NUMERIC;
BEGIN
    SELECT COALESCE(SUM(quantity * unit_price), 0) INTO v_total
    FROM order_items
    WHERE order_id = p_order_id;
    
    UPDATE orders SET total_amount = v_total WHERE order_id = p_order_id;
    
    RETURN v_total;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION calculate_order_total(INTEGER) IS 'Calculate order total amount';

-- Функция: Проверка наличия товара
CREATE OR REPLACE FUNCTION check_product_availability(p_product_id INTEGER, p_quantity INTEGER)
RETURNS BOOLEAN AS $$
DECLARE
    v_stock INTEGER;
BEGIN
    SELECT quantity_in_stock INTO v_stock
    FROM products
    WHERE product_id = p_product_id;
    
    IF v_stock IS NULL THEN
        RETURN false;
    END IF;
    
    RETURN v_stock >= p_quantity;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- ТРИГГЕРЫ
-- ============================================

-- Триггер: Обновление updated_at для products
CREATE TRIGGER trg_products_updated_at
    BEFORE UPDATE ON products
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Триггер: Аудит изменений в заказах
CREATE OR REPLACE FUNCTION audit_order_changes()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO audit_log (table_name, operation) VALUES ('orders', 'INSERT');
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit_log (table_name, operation) VALUES ('orders', 'UPDATE');
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO audit_log (table_name, operation) VALUES ('orders', 'DELETE');
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_audit_orders
    AFTER INSERT OR UPDATE OR DELETE ON orders
    FOR EACH ROW
    EXECUTE FUNCTION audit_order_changes();

-- ============================================
-- ТЕСТОВЫЕ ДАННЫЕ
-- ============================================

-- Пользователи (без русских символов для совместимости)
INSERT INTO users (username, email, password_hash, full_name) VALUES
('admin', 'admin@example.com', 'hash123', 'Administrator'),
('john_doe', 'john@example.com', 'hash456', 'John Doe'),
('jane_smith', 'jane@example.com', 'hash789', 'Jane Smith');

-- Роли
INSERT INTO roles (role_name, description) VALUES
('admin', 'Full access'),
('manager', 'Manage products'),
('customer', 'View and orders');

-- Связь пользователей и ролей (теперь пользователи существуют)
INSERT INTO user_roles (user_id, role_id) VALUES
(1, 1), (1, 2), (2, 2), (2, 3), (3, 3);

-- Категории
INSERT INTO categories (category_name) VALUES
('Electronics'), ('Clothing'), ('Books');

-- Товары
INSERT INTO products (product_name, category_id, price, quantity_in_stock, sku) VALUES
('Laptop Pro', 1, 99990.00, 50, 'LAPTOP-001'),
('Smartphone X12', 1, 59990.00, 100, 'PHONE-001'),
('T-Shirt', 2, 1500.00, 500, 'SHIRT-001');

-- Заказы (теперь пользователи существуют)
INSERT INTO orders (user_id, status) VALUES
(2, 'confirmed'), (3, 'shipped'), (2, 'pending');

-- Элементы заказа (теперь заказы существуют)
INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
(1, 1, 1, 99990.00), (1, 3, 2, 1500.00), (2, 2, 1, 59990.00);

-- ============================================
-- ПРОВЕРКА (ИСПРАВЛЕННЫЙ СИНТАКСИС)
-- ============================================

SELECT 'Database test created successfully!' AS status;
SELECT COUNT(*) AS tables_count FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
SELECT COUNT(*) AS functions_count FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace WHERE n.nspname = 'public' AND p.prokind = 'f';
SELECT COUNT(*) AS triggers_count FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid WHERE NOT t.tgisinternal AND c.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public');