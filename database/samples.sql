ALTER USER 'root'@'localhost' IDENTIFIED BY '123456';

-- =========================
-- SAMPLE DATA FOR ins_db
-- =========================

USE ins_db;

-- =========================
-- 1. Categories
-- =========================
INSERT INTO categories VALUES
('C001', 'Beverages'),
('C002', 'Snacks'),
('C003', 'Dairy'),
('C004', 'Frozen Food'),
('C005', 'Personal Care'),
('C006', 'Household'),
('C007', 'Instant Food'),
('C008', 'Bakery');

-- =========================
-- 2. Warehouses
-- =========================
INSERT INTO warehouses VALUES
('W001', 'Central Warehouse', 10000),
('W002', 'North Warehouse', 7000),
('W003', 'South Warehouse', 5000);

-- =========================
-- 2.1 Stores
-- =========================
INSERT INTO stores VALUES
('S001', 'District 1 Store', 'District 1, HCM City'),
('S002', 'Thu Duc Store', 'Thu Duc, HCM City'),
('S003', 'Binh Thanh Store', 'Binh Thanh, HCM City'),
('S004', 'Go Vap Store', 'Go Vap, HCM City');

-- =========================
-- 3. Products
-- =========================
INSERT INTO products VALUES
('P001', 'Coca Cola 330ml', 'C001', 10.5, 'ACTIVE'),
('P002', 'Pepsi 330ml', 'C001', 10.0, 'ACTIVE'),
('P003', 'Orange Juice', 'C001', 18.0, 'ACTIVE'),
('P004', 'Potato Chips BBQ', 'C002', 15.0, 'ACTIVE'),
('P005', 'Salted Crackers', 'C002', 12.0, 'ACTIVE'),
('P006', 'Fresh Milk 1L', 'C003', 32.0, 'ACTIVE'),
('P007', 'Yogurt Strawberry', 'C003', 8.0, 'ACTIVE'),
('P008', 'Ice Cream Vanilla', 'C004', 25.0, 'ACTIVE'),
('P009', 'Frozen Dumplings', 'C004', 55.0, 'ACTIVE'),
('P010', 'Shampoo Clear', 'C005', 75.0, 'ACTIVE'),
('P011', 'Toothpaste P/S', 'C005', 28.0, 'ACTIVE'),
('P012', 'Dishwashing Liquid', 'C006', 45.0, 'ACTIVE'),
('P013', 'Laundry Detergent', 'C006', 120.0, 'ACTIVE'),
('P014', 'Instant Noodles Beef', 'C007', 6.5, 'ACTIVE'),
('P015', 'Instant Noodles Chicken', 'C007', 6.5, 'ACTIVE'),
('P016', 'Bread Sandwich', 'C008', 14.0, 'ACTIVE'),
('P017', 'Chocolate Cake', 'C008', 40.0, 'ACTIVE'),
('P018', 'Mineral Water', 'C001', 7.0, 'ACTIVE'),
('P019', 'Energy Drink', 'C001', 15.0, 'ACTIVE'),
('P020', 'Cookies Butter', 'C002', 22.0, 'ACTIVE');

-- =========================
-- 4. Batch
-- =========================
INSERT INTO batch VALUES
-- Warehouse batches
('B001', 'P001', '2026-01-01', '2027-01-01', '2026-01-05', 500, 9.5, 'W001', NULL),
('B002', 'P002', '2026-01-10', '2027-01-10', '2026-01-12', 450, 9.0, 'W001', NULL),
('B003', 'P003', '2026-02-01', '2026-08-01', '2026-02-03', 300, 16.0, 'W002', NULL),
('B004', 'P004', '2026-03-01', '2026-09-01', '2026-03-05', 250, 13.5, 'W002', NULL),
('B005', 'P005', '2026-03-10', '2026-10-10', '2026-03-12', 280, 11.0, 'W003', NULL),
('B006', 'P006', '2026-04-01', '2026-05-15', '2026-04-02', 200, 30.0, 'W001', NULL),
('B007', 'P007', '2026-04-01', '2026-04-25', '2026-04-03', 350, 7.5, 'W001', NULL),
('B008', 'P008', '2026-02-15', '2026-12-15', '2026-02-18', 180, 23.0, 'W003', NULL),
('B009', 'P009', '2026-01-20', '2026-07-20', '2026-01-25', 150, 52.0, 'W002', NULL),
('B010', 'P010', '2026-01-01', '2028-01-01', '2026-01-10', 120, 70.0, 'W001', NULL),

('B011', 'P011', '2026-01-15', '2028-01-15', '2026-01-18', 140, 26.0, 'W001', NULL),
('B012', 'P012', '2026-02-01', '2028-02-01', '2026-02-05', 160, 42.0, 'W002', NULL),
('B013', 'P013', '2026-03-01', '2028-03-01', '2026-03-04', 110, 115.0, 'W003', NULL),
('B014', 'P014', '2026-04-01', '2026-10-01', '2026-04-02', 1000, 6.0, 'W001', NULL),
('B015', 'P015', '2026-04-01', '2026-10-01', '2026-04-02', 950, 6.0, 'W001', NULL),
('B016', 'P016', '2026-05-01', '2026-05-10', '2026-05-02', 100, 13.0, 'W002', NULL),
('B017', 'P017', '2026-05-01', '2026-05-15', '2026-05-03', 90, 38.0, 'W002', NULL),
('B018', 'P018', '2026-01-01', '2027-01-01', '2026-01-02', 800, 6.5, 'W003', NULL),
('B019', 'P019', '2026-02-01', '2027-02-01', '2026-02-05', 400, 14.0, 'W003', NULL),
('B020', 'P020', '2026-03-01', '2026-12-01', '2026-03-05', 220, 20.0, 'W001', NULL),

-- Store batches
('B021', 'P001', '2026-01-01', '2027-01-01', '2026-04-01', 80, 10.0, NULL, 'S001'),
('B022', 'P002', '2026-01-10', '2027-01-10', '2026-04-01', 75, 10.5, NULL, 'S001'),
('B023', 'P004', '2026-03-01', '2026-09-01', '2026-04-02', 40, 15.5, NULL, 'S001'),
('B024', 'P006', '2026-04-01', '2026-05-15', '2026-04-10', 30, 33.0, NULL, 'S002'),
('B025', 'P007', '2026-04-01', '2026-04-25', '2026-04-11', 50, 8.5, NULL, 'S002'),
('B026', 'P010', '2026-01-01', '2028-01-01', '2026-04-12', 20, 78.0, NULL, 'S003'),
('B027', 'P011', '2026-01-15', '2028-01-15', '2026-04-12', 25, 29.0, NULL, 'S003'),
('B028', 'P014', '2026-04-01', '2026-10-01', '2026-04-15', 200, 7.0, NULL, 'S004'),
('B029', 'P015', '2026-04-01', '2026-10-01', '2026-04-15', 180, 7.0, NULL, 'S004'),
('B030', 'P018', '2026-01-01', '2027-01-01', '2026-04-18', 120, 6.5, NULL, 'S001'),

-- Additional batches for testing sorting/priority
('B031', 'P006', '2026-04-05', '2026-05-10', '2026-04-06', 180, 30.0, 'W001', NULL),
('B032', 'P006', '2026-04-10', '2026-05-20', '2026-04-11', 220, 30.0, 'W001', NULL),
('B033', 'P014', '2026-04-02', '2026-10-02', '2026-04-03', 900, 6.0, 'W002', NULL),
('B034', 'P014', '2026-04-03', '2026-09-28', '2026-04-04', 850, 6.0, 'W003', NULL),
('B035', 'P001', '2026-01-15', '2027-01-15', '2026-01-18', 600, 9.5, 'W002', NULL),
('B036', 'P001', '2026-02-01', '2027-02-01', '2026-02-03', 550, 9.5, 'W003', NULL),
('B037', 'P016', '2026-05-02', '2026-05-09', '2026-05-03', 120, 13.0, NULL, 'S002'),
('B038', 'P017', '2026-05-03', '2026-05-12', '2026-05-04', 70, 38.0, NULL, 'S003'),
('B039', 'P020', '2026-03-10', '2026-12-10', '2026-03-12', 240, 20.0, 'W001', NULL),
('B040', 'P003', '2026-02-10', '2026-08-10', '2026-02-12', 320, 16.0, NULL, 'S004');

-- =========================
-- 5. Transaction History
-- =========================
INSERT INTO transaction_history (operation_type, product_id, batch_id, target_batch_id, quantity, unit_price, source_location_type, source_location_id, target_location_type, target_location_id, notes, created_at) VALUES
-- Warehouse inbound - matching entry_date
('inbound', 'P001', 'B001', NULL, 500, 9.5, NULL, NULL, 'warehouse', 'W001', 'Inbound batch B001', '2026-01-05 10:00:00'),
('inbound', 'P002', 'B002', NULL, 450, 9.0, NULL, NULL, 'warehouse', 'W001', 'Inbound batch B002', '2026-01-12 10:00:00'),
('inbound', 'P003', 'B003', NULL, 300, 16.0, NULL, NULL, 'warehouse', 'W002', 'Inbound batch B003', '2026-02-03 10:00:00'),
('inbound', 'P004', 'B004', NULL, 250, 13.5, NULL, NULL, 'warehouse', 'W002', 'Inbound batch B004', '2026-03-05 10:00:00'),
('inbound', 'P005', 'B005', NULL, 280, 11.0, NULL, NULL, 'warehouse', 'W003', 'Inbound batch B005', '2026-03-12 10:00:00'),
('inbound', 'P006', 'B006', NULL, 200, 30.0, NULL, NULL, 'warehouse', 'W001', 'Inbound batch B006', '2026-04-02 10:00:00'),
('inbound', 'P007', 'B007', NULL, 350, 7.5, NULL, NULL, 'warehouse', 'W001', 'Inbound batch B007', '2026-04-03 10:00:00'),
('inbound', 'P008', 'B008', NULL, 180, 23.0, NULL, NULL, 'warehouse', 'W003', 'Inbound batch B008', '2026-02-18 10:00:00'),
('inbound', 'P009', 'B009', NULL, 150, 52.0, NULL, NULL, 'warehouse', 'W002', 'Inbound batch B009', '2026-01-25 10:00:00'),
('inbound', 'P010', 'B010', NULL, 120, 70.0, NULL, NULL, 'warehouse', 'W001', 'Inbound batch B010', '2026-01-10 10:00:00'),
('inbound', 'P011', 'B011', NULL, 140, 26.0, NULL, NULL, 'warehouse', 'W001', 'Inbound batch B011', '2026-01-18 10:00:00'),
('inbound', 'P012', 'B012', NULL, 160, 42.0, NULL, NULL, 'warehouse', 'W002', 'Inbound batch B012', '2026-02-05 10:00:00'),
('inbound', 'P013', 'B013', NULL, 110, 115.0, NULL, NULL, 'warehouse', 'W003', 'Inbound batch B013', '2026-03-04 10:00:00'),
('inbound', 'P014', 'B014', NULL, 1000, 6.0, NULL, NULL, 'warehouse', 'W001', 'Inbound batch B014', '2026-04-02 10:00:00'),
('inbound', 'P015', 'B015', NULL, 950, 6.0, NULL, NULL, 'warehouse', 'W001', 'Inbound batch B015', '2026-04-02 10:00:00'),
('inbound', 'P016', 'B016', NULL, 100, 13.0, NULL, NULL, 'warehouse', 'W002', 'Inbound batch B016', '2026-05-02 10:00:00'),
('inbound', 'P017', 'B017', NULL, 90, 38.0, NULL, NULL, 'warehouse', 'W002', 'Inbound batch B017', '2026-05-03 10:00:00'),
('inbound', 'P018', 'B018', NULL, 800, 6.5, NULL, NULL, 'warehouse', 'W003', 'Inbound batch B018', '2026-01-02 10:00:00'),
('inbound', 'P019', 'B019', NULL, 400, 14.0, NULL, NULL, 'warehouse', 'W003', 'Inbound batch B019', '2026-02-05 10:00:00'),
('inbound', 'P020', 'B020', NULL, 220, 20.0, NULL, NULL, 'warehouse', 'W001', 'Inbound batch B020', '2026-03-05 10:00:00'),
('inbound', 'P006', 'B031', NULL, 180, 30.0, NULL, NULL, 'warehouse', 'W001', 'Inbound batch B031', '2026-04-06 10:00:00'),
('inbound', 'P006', 'B032', NULL, 220, 30.0, NULL, NULL, 'warehouse', 'W001', 'Inbound batch B032', '2026-04-11 10:00:00'),
('inbound', 'P014', 'B033', NULL, 900, 6.0, NULL, NULL, 'warehouse', 'W002', 'Inbound batch B033', '2026-04-03 10:00:00'),
('inbound', 'P014', 'B034', NULL, 850, 6.0, NULL, NULL, 'warehouse', 'W003', 'Inbound batch B034', '2026-04-04 10:00:00'),
('inbound', 'P001', 'B035', NULL, 600, 9.5, NULL, NULL, 'warehouse', 'W002', 'Inbound batch B035', '2026-01-18 10:00:00'),
('inbound', 'P001', 'B036', NULL, 550, 9.5, NULL, NULL, 'warehouse', 'W003', 'Inbound batch B036', '2026-02-03 10:00:00'),
('inbound', 'P020', 'B039', NULL, 240, 20.0, NULL, NULL, 'warehouse', 'W001', 'Inbound batch B039', '2026-03-12 10:00:00'),
-- Store inbound - direct inbound to stores
('inbound', 'P001', 'B021', NULL, 80, 10.0, NULL, NULL, 'store', 'S001', 'Inbound batch B021 to District 1 Store', '2026-04-01 10:00:00'),
('inbound', 'P002', 'B022', NULL, 75, 10.5, NULL, NULL, 'store', 'S001', 'Inbound batch B022 to District 1 Store', '2026-04-01 10:00:00'),
('inbound', 'P004', 'B023', NULL, 40, 15.5, NULL, NULL, 'store', 'S001', 'Inbound batch B023 to District 1 Store', '2026-04-02 10:00:00'),
('inbound', 'P006', 'B024', NULL, 30, 33.0, NULL, NULL, 'store', 'S002', 'Inbound batch B024 to Thu Duc Store', '2026-04-10 10:00:00'),
('inbound', 'P007', 'B025', NULL, 50, 8.5, NULL, NULL, 'store', 'S002', 'Inbound batch B025 to Thu Duc Store', '2026-04-11 10:00:00'),
('inbound', 'P010', 'B026', NULL, 20, 78.0, NULL, NULL, 'store', 'S003', 'Inbound batch B026 to Binh Thanh Store', '2026-04-12 10:00:00'),
('inbound', 'P011', 'B027', NULL, 25, 29.0, NULL, NULL, 'store', 'S003', 'Inbound batch B027 to Binh Thanh Store', '2026-04-12 10:00:00'),
('inbound', 'P014', 'B028', NULL, 200, 7.0, NULL, NULL, 'store', 'S004', 'Inbound batch B028 to Go Vap Store', '2026-04-15 10:00:00'),
('inbound', 'P015', 'B029', NULL, 180, 7.0, NULL, NULL, 'store', 'S004', 'Inbound batch B029 to Go Vap Store', '2026-04-15 10:00:00'),
('inbound', 'P018', 'B030', NULL, 120, 6.5, NULL, NULL, 'store', 'S001', 'Inbound batch B030 to District 1 Store', '2026-04-18 10:00:00'),
('inbound', 'P016', 'B037', NULL, 120, 13.0, NULL, NULL, 'store', 'S002', 'Inbound batch B037 to Thu Duc Store', '2026-05-03 10:00:00'),
('inbound', 'P017', 'B038', NULL, 70, 38.0, NULL, NULL, 'store', 'S003', 'Inbound batch B038 to Binh Thanh Store', '2026-05-04 10:00:00'),
('inbound', 'P003', 'B040', NULL, 320, 16.0, NULL, NULL, 'store', 'S004', 'Inbound batch B040 to Go Vap Store', '2026-02-12 10:00:00');


-- =========================
-- 6. Transfer Tasks
-- =========================
INSERT INTO transfer_tasks (task_id, product_id, source_batch_id, target_location_id, target_location_type, quantity, priority, strategy, status, created_at, completed_at) VALUES
('T001', 'P001', 'B001', 'S001', 'store', 80, 'normal', 'fefo', 'completed', '2026-01-20 08:00:00', '2026-01-20 08:15:00'),
('T002', 'P002', 'B002', 'S001', 'store', 75, 'normal', 'fefo', 'completed', '2026-01-27 09:00:00', '2026-01-27 09:10:00'),
('T003', 'P006', 'B006', 'S002', 'store', 30, 'normal', 'fefo', 'completed', '2026-04-17 10:30:00', '2026-04-17 10:40:00'),
('T004', 'P014', 'B014', 'S004', 'store', 200, 'normal', 'fefo', 'in_progress', '2026-04-22 14:00:00', NULL);