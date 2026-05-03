ALTER USER 'root'@'localhost' IDENTIFIED BY '123456';

USE ins_db;

-- ==========================================
-- 1. INSERT CATEGORIES (5 Categories)
-- ==========================================
INSERT INTO categories (id, name) VALUES 
('C01', 'Electronics'),
('C02', 'Groceries'),
('C03', 'Clothing & Apparel'),
('C04', 'Home Appliances'),
('C05', 'Toys & Games');

-- ==========================================
-- 2. INSERT WAREHOUSES (3 Warehouses)
-- Phải INSERT trước inventory vì có FK constraint
-- ==========================================
INSERT INTO warehouses (id, name, space) VALUES
('WH-A', 'Main Warehouse A',  5000),
('WH-B', 'Warehouse B',       3000),
('WH-C', 'Cold Storage C',    1500);

-- ==========================================
-- 2.1. INSERT STORES (2 Stores)
-- ==========================================
INSERT INTO stores (id, name, location) VALUES
('ST-01', 'Store Downtown', '123 Main St, City Center'),
('ST-02', 'Store Uptown', '456 High St, North District');

-- ==========================================
-- 3. INSERT PRODUCTS (20 Products)
-- ==========================================
INSERT INTO products (id, name, category_id, price, status) VALUES 
-- Electronics (C01)
('P001', 'Smartphone Pro Max',              'C01', 999.99, 'Available'),
('P002', 'Gaming Laptop 15"',               'C01', 1499.50, 'Available'),
('P003', 'Wireless Noise-Canceling Earbuds','C01', 199.00, 'Available'),
('P004', 'Smartwatch Series 8',             'C01', 399.00, 'Out of Stock'),

-- Groceries (C02)
('P005', 'Organic Whole Milk 1L',    'C02', 3.50,  'Available'),
('P006', 'Whole Wheat Bread',         'C02', 2.99,  'Available'),
('P007', 'Fresh Apples (1kg)',        'C02', 4.50,  'Available'),
('P008', '100% Orange Juice 2L',      'C02', 5.20,  'Available'),
('P009', 'Arabica Coffee Beans 500g', 'C02', 12.99, 'Available'),

-- Clothing & Apparel (C03)
('P010', 'Men Classic Cotton T-Shirt',  'C03', 15.00, 'Available'),
('P011', 'Women Slim Fit Denim Jeans',  'C03', 45.00, 'Available'),
('P012', 'Unisex Winter Jacket',        'C03', 89.99, 'Available'),
('P013', 'Running Sneakers',            'C03', 65.50, 'Available'),

-- Home Appliances (C04)
('P014', 'Microwave Oven 800W',    'C04', 120.00, 'Available'),
('P015', 'Robot Vacuum Cleaner',   'C04', 250.00, 'Available'),
('P016', 'Air Purifier HEPA',      'C04', 180.00, 'Available'),
('P017', 'High-Speed Blender',     'C04', 95.00,  'Out of Stock'),

-- Toys & Games (C05)
('P018', 'Lego Star Wars Millennium Falcon', 'C05', 159.99, 'Available'),
('P019', 'Marvel Action Figure Set',         'C05', 35.00,  'Available'),
('P020', 'Monopoly Classic Board Game',      'C05', 20.00,  'Available');

-- ==========================================
-- 4. INSERT INVENTORY (30 Batches)
-- ==========================================
INSERT INTO inventory (product_id, batch_id, mfg_date, exp_date, quantity, warehouse_id, store_id) VALUES 
-- Electronics
('P001', 'BATCH-E01', '2023-10-01', '2028-10-01',  50, 'WH-A', NULL),
('P001', 'BATCH-E02', '2023-11-15', '2028-11-15',  30, 'WH-B', NULL),
('P002', 'BATCH-E01', '2023-09-20', '2028-09-20',  20, 'WH-A', NULL),
('P003', 'BATCH-E03', '2023-12-05', '2026-12-05', 100, 'WH-A', NULL),

-- Groceries (hạn ngắn)
('P005', 'BATCH-G01', '2024-03-01', '2024-03-15', 200, 'WH-C', NULL),
('P005', 'BATCH-G02', '2024-03-10', '2024-03-25', 150, 'WH-C', NULL),
('P006', 'BATCH-G01', '2024-03-12', '2024-03-19',  80, 'WH-C', NULL),
('P007', 'BATCH-G03', '2024-03-05', '2024-03-20', 300, 'WH-C', NULL),
('P008', 'BATCH-G04', '2023-10-10', '2024-10-10', 120, 'WH-C', NULL),
('P009', 'BATCH-G05', '2024-01-15', '2025-01-15',  60, 'WH-A', NULL),
('P009', 'BATCH-G06', '2024-02-01', '2025-02-01',  40, 'WH-B', NULL),

-- Clothing (hạn dài)
('P010', 'BATCH-C01', '2023-05-10', '2030-05-10', 500, 'WH-B', NULL),
('P010', 'BATCH-C02', '2023-08-15', '2030-08-15', 200, 'WH-A', NULL),
('P011', 'BATCH-C01', '2023-06-20', '2030-06-20', 150, 'WH-B', NULL),
('P012', 'BATCH-C03', '2023-09-01', '2030-09-01',  50, 'WH-B', NULL),
('P013', 'BATCH-C04', '2023-11-11', '2028-11-11', 120, 'WH-A', NULL),

-- Home Appliances
('P014', 'BATCH-H01', '2023-04-12', '2033-04-12',  40, 'WH-A', NULL),
('P014', 'BATCH-H02', '2023-10-22', '2033-10-22',  25, 'WH-B', NULL),
('P015', 'BATCH-H03', '2023-07-30', '2033-07-30',  30, 'WH-A', NULL),
('P016', 'BATCH-H04', '2023-08-15', '2028-08-15',  45, 'WH-A', NULL),
('P016', 'BATCH-H05', '2023-12-01', '2028-12-01',  60, 'WH-B', NULL),

-- Toys (hạn rất dài)
('P018', 'BATCH-T01', '2023-01-10', '2035-01-10',  20, 'WH-A', NULL),
('P018', 'BATCH-T02', '2023-06-15', '2035-06-15',  15, 'WH-B', NULL),
('P019', 'BATCH-T03', '2023-09-05', '2030-09-05',  80, 'WH-B', NULL),
('P020', 'BATCH-T04', '2023-02-20', '2035-02-20', 100, 'WH-A', NULL),

-- Lô hàng bổ sung
('P002', 'BATCH-E05', '2024-01-10', '2029-01-10',  15, 'WH-C', NULL),
('P006', 'BATCH-G08', '2024-03-14', '2024-03-21',  50, 'WH-A', NULL),
('P011', 'BATCH-C09', '2024-01-05', '2031-01-05',  80, 'WH-A', NULL),
('P015', 'BATCH-H09', '2024-02-18', '2034-02-18',  10, 'WH-C', NULL),
('P019', 'BATCH-T09', '2024-03-01', '2031-03-01',  40, 'WH-A', NULL),

-- Lô hàng mẫu ở STORES
('P001', 'BATCH-E01', '2023-10-01', '2028-10-01',  15, NULL, 'ST-01'),
('P005', 'BATCH-G01', '2024-03-01', '2024-03-15',  20, NULL, 'ST-02');