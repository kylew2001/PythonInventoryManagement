CREATE TABLE IF NOT EXISTS orders (
    order_id INTEGER PRIMARY KEY AUTOINCREMENT,
    description TEXT,
    lines INTEGER,
    quantity INTEGER,
    clinic_name TEXT,
    clinic_address TEXT,
    finalized_time DATETIME,
    finalized_by TEXT,
    carrier TEXT,
    category TEXT DEFAULT 'unallocated', -- unallocated, misc, on_hold, pick-ups, allocated
    status TEXT, -- new, old, urgent, priority
    allocated_to INTEGER
);

CREATE TABLE IF NOT EXISTS order_items (
    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER,
    item_name TEXT,
    quantity INTEGER,
    FOREIGN KEY (order_id) REFERENCES orders (order_id)
);

CREATE TABLE IF NOT EXISTS carriers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);




CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'Storeworker',
    full_name TEXT
);

CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    address TEXT NOT NULL,
    category TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    product_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name TEXT NOT NULL,
    product_weight REAL NOT NULL,
    weight_type TEXT CHECK(products.weight_type IN ('g', 'Kg', 'mL', 'L')) NOT NULL,
    supplier TEXT NOT NULL,
    price REAL NOT NULL
);


-- TEST RECORDS --

CREATE TABLE IF NOT EXISTS test_records (
    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_name TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL,
    status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS customer_account (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    clinic_name TEXT NOT NULL,
    clinic_address TEXT NOT NULL,
    clinic_username TEXT UNIQUE NOT NULL,
    clinic_password TEXT NOT NULL,
    clinic_category TEXT NOT NULL
);


CREATE TABLE IF NOT EXISTS product_stock (
    product_id INTEGER PRIMARY KEY,
    total_quantity INTEGER NOT NULL,
    primary_quantity INTEGER NOT NULL,
    stock_location TEXT NOT NULL UNIQUE ,
    primary_capacity INTEGER NOT NULL,
    barcode TEXT NOT NULL UNIQUE ,
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

-- BEGIN TRANSACTION;
--
-- -- Generate random records for product_stock
-- INSERT INTO product_stock (product_id, stock_location, total_quantity, primary_capacity, primary_quantity, barcode)
-- SELECT
--     product_id,
--     -- Generate stock location in format e.g., "B06C04"
--     CHAR(65 + ABS(RANDOM() % 6)) || -- Isle: Random letter A-F
--     PRINTF('%02d', 5 + ABS(RANDOM() % 38)) || -- Slot: Random number between 5 and 42
--     CHAR(65 + ABS(RANDOM() % 3)) || -- Location level: Random letter A-C
--     PRINTF('%02d', 1 + ABS(RANDOM() % 6)), -- Location slot: Random number between 01 and 06
--     -- Generate total_quantity based on stock type
--     CASE
--         WHEN product_id % 3 = 0 THEN ABS(RANDOM() % 1901 + 100) -- Higher for cans
--         WHEN product_id % 2 = 0 THEN ABS(RANDOM() % 1401 + 100) -- Medium for sachets
--         ELSE ABS(RANDOM() % 901 + 50) -- Lower for bags
--     END AS total_quantity,
--     -- Generate primary_capacity
--     CASE
--         WHEN product_id % 3 = 0 THEN ABS(RANDOM() % 1501 + 500) -- Higher for cans
--         WHEN product_id % 2 = 0 THEN ABS(RANDOM() % 1201 + 300) -- Medium for sachets
--         ELSE ABS(RANDOM() % 701 + 50) -- Lower for bags
--     END AS primary_capacity,
--     -- Generate primary_quantity less than or equal to primary_capacity
--     CASE
--         WHEN product_id % 3 = 0 THEN ABS(RANDOM() % 1501 + 100) -- Proportional for cans
--         WHEN product_id % 2 = 0 THEN ABS(RANDOM() % 1201 + 50) -- Proportional for sachets
--         ELSE ABS(RANDOM() % 701 + 10) -- Proportional for bags
--     END AS primary_quantity,
--     -- Generate random 9-digit barcode
--     ABS(RANDOM() % 900000000 + 100000000) AS barcode
-- FROM
--     (SELECT product_id FROM products WHERE product_id BETWEEN 3 AND 60);
--
-- COMMIT;



-- INSERT INTO products (product_name, product_weight, weight_type, supplier, price) VALUES
-- -- Dog Biscuits
-- ('Hills Dog Biscuits Chicken Flavor', 2.5, 'Kg', 'Hills', 25.99),
-- ('Royal Canin Dog Biscuits Original', 1.8, 'Kg', 'Royal Canin', 30.50),
-- ('Hills Puppy Biscuits Lamb Flavor', 3.0, 'Kg', 'Hills', 32.99),
-- ('Royal Canin Large Breed Biscuits', 2.2, 'Kg', 'Royal Canin', 35.99),
-- ('Hills Active Dog Biscuits', 1.5, 'Kg', 'Hills', 27.99),
-- ('Royal Canin Hypoallergenic Biscuits', 2.0, 'Kg', 'Royal Canin', 33.50),
-- ('Hills Small Breed Biscuits', 1.2, 'Kg', 'Hills', 22.49),
-- ('Royal Canin Medium Breed Biscuits', 2.5, 'Kg', 'Royal Canin', 29.99),
-- ('Hills Digestive Care Biscuits', 1.7, 'Kg', 'Hills', 31.99),
-- ('Royal Canin High Protein Biscuits', 2.8, 'Kg', 'Royal Canin', 34.99),
--
-- -- Cat Biscuits
-- ('Hills Cat Biscuits Tuna Flavor', 1.5, 'Kg', 'Hills', 23.99),
-- ('Royal Canin Indoor Cat Biscuits', 1.8, 'Kg', 'Royal Canin', 28.99),
-- ('Hills Hairball Control Biscuits', 2.0, 'Kg', 'Hills', 25.50),
-- ('Royal Canin Feline Dental Care', 1.6, 'Kg', 'Royal Canin', 30.99),
-- ('Hills Mature Cat Biscuits', 1.4, 'Kg', 'Hills', 24.50),
-- ('Royal Canin Kitten Biscuits', 1.2, 'Kg', 'Royal Canin', 22.99),
-- ('Hills Grain-Free Cat Biscuits', 2.1, 'Kg', 'Hills', 29.99),
-- ('Royal Canin Feline Protein Biscuits', 2.0, 'Kg', 'Royal Canin', 27.99),
-- ('Hills Weight Management Cat Biscuits', 2.3, 'Kg', 'Hills', 32.50),
-- ('Royal Canin Persian Cat Biscuits', 1.9, 'Kg', 'Royal Canin', 33.99),
--
-- -- Dog Canned Food
-- ('Hills Wet Food Chicken & Rice', 400, 'g', 'Hills', 22.49),
-- ('Royal Canin Gastrointestinal Dog Food', 350, 'g', 'Royal Canin', 25.50),
-- ('Hills Puppy Canned Food Lamb', 500, 'g', 'Hills', 24.99),
-- ('Royal Canin Senior Dog Wet Food', 450, 'g', 'Royal Canin', 28.99),
-- ('Hills Sensitive Stomach Wet Food', 300, 'g', 'Hills', 23.50),
-- ('Royal Canin Weight Control Wet Food', 400, 'g', 'Royal Canin', 26.99),
-- ('Hills High Protein Wet Food', 420, 'g', 'Hills', 27.50),
-- ('Royal Canin Medium Dog Wet Food', 380, 'g', 'Royal Canin', 29.50),
-- ('Hills Grain-Free Dog Wet Food', 400, 'g', 'Hills', 30.99),
-- ('Royal Canin Digestive Care Wet Food', 350, 'g', 'Royal Canin', 25.99),
--
-- -- Cat Canned Food
-- ('Hills Adult Cat Wet Food Tuna', 200, 'g', 'Hills', 21.99),
-- ('Royal Canin Kitten Wet Food', 250, 'g', 'Royal Canin', 22.50),
-- ('Hills Urinary Care Cat Wet Food', 300, 'g', 'Hills', 23.99),
-- ('Royal Canin Persian Cat Wet Food', 350, 'g', 'Royal Canin', 28.50),
-- ('Hills Sensitive Skin Cat Wet Food', 220, 'g', 'Hills', 24.99),
-- ('Royal Canin Indoor Cat Wet Food', 280, 'g', 'Royal Canin', 26.50),
-- ('Hills Kitten Wet Food Chicken', 200, 'g', 'Hills', 21.50),
-- ('Royal Canin Hairball Control Wet Food', 300, 'g', 'Royal Canin', 25.50),
-- ('Hills Grain-Free Cat Wet Food', 350, 'g', 'Hills', 27.99),
-- ('Royal Canin Sterilised Cat Wet Food', 300, 'g', 'Royal Canin', 29.50),
--
-- -- Dog Sachets
-- ('Hills Sachet Lamb & Vegetables', 85, 'g', 'Hills', 24.99),
-- ('Royal Canin Sachet Mini Puppy', 100, 'g', 'Royal Canin', 23.50),
-- ('Hills Senior Dog Sachet', 90, 'g', 'Hills', 25.99),
-- ('Royal Canin Adult Dog Sachet', 95, 'g', 'Royal Canin', 26.50),
-- ('Hills Small Dog Sachet', 80, 'g', 'Hills', 22.50),
-- ('Royal Canin Large Breed Sachet', 110, 'g', 'Royal Canin', 27.99),
-- ('Hills Digestive Care Sachet', 85, 'g', 'Hills', 28.50),
-- ('Royal Canin High Protein Sachet', 100, 'g', 'Royal Canin', 29.50),
-- ('Hills Grain-Free Dog Sachet', 90, 'g', 'Hills', 30.99),
-- ('Royal Canin Weight Control Sachet', 95, 'g', 'Royal Canin', 31.99),
--
-- -- Cat Sachets
-- ('Hills Cat Sachet Tuna & Salmon', 85, 'g', 'Hills', 21.99),
-- ('Royal Canin Kitten Sachet', 80, 'g', 'Royal Canin', 22.50),
-- ('Hills Sterilised Cat Sachet', 90, 'g', 'Hills', 23.50),
-- ('Royal Canin Hairball Care Sachet', 85, 'g', 'Royal Canin', 25.99),
-- ('Hills Indoor Cat Sachet', 80, 'g', 'Hills', 24.50),
-- ('Royal Canin Persian Cat Sachet', 90, 'g', 'Royal Canin', 26.50),
-- ('Hills Grain-Free Cat Sachet', 85, 'g', 'Hills', 28.50),
-- ('Royal Canin Urinary Care Sachet', 100, 'g', 'Royal Canin', 29.50),
-- ('Hills Sensitive Skin Cat Sachet', 90, 'g', 'Hills', 27.50),
-- ('Royal Canin Digestive Care Cat Sachet', 85, 'g', 'Royal Canin', 30.50);
--















