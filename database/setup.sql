ALTER USER 'root'@'localhost' IDENTIFIED BY '123456';

-- Xóa database cũ để làm mới hoàn toàn cấu trúc
DROP DATABASE IF EXISTS ins_db;
CREATE DATABASE ins_db;
USE ins_db;

-- 1. Danh mục sản phẩm
CREATE TABLE categories (
    id VARCHAR(10) PRIMARY KEY,
    name VARCHAR(100) NOT NULL
);

-- 2. Kho chứa hàng
CREATE TABLE warehouses (
    id VARCHAR(10) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    space INT DEFAULT 0
);

-- 2.1. Cửa hàng
CREATE TABLE stores (
    id VARCHAR(10) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    location VARCHAR(255)
);

-- 3. Sản phẩm
CREATE TABLE products (
    id VARCHAR(10) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    category_id VARCHAR(10),
    price FLOAT,
    status VARCHAR(20),
    CONSTRAINT fk_product_category FOREIGN KEY (category_id) REFERENCES categories(id)
);

-- 4. Tồn kho (liên kết products, warehouses & stores)
CREATE TABLE inventory (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id VARCHAR(10),
    batch_id VARCHAR(20),
    mfg_date DATE,
    exp_date DATE,
    quantity INT,
    warehouse_id VARCHAR(10) NULL,
    store_id VARCHAR(10) NULL,
    CONSTRAINT fk_inventory_product FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    CONSTRAINT fk_inventory_warehouse FOREIGN KEY (warehouse_id) REFERENCES warehouses(id),
    CONSTRAINT fk_inventory_store FOREIGN KEY (store_id) REFERENCES stores(id)
);
