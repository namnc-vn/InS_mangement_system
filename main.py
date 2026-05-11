"""CLI entry point for the InS warehouse management system."""

import db_connect
from service import Service
from datetime import date


def print_line():
    print("-" * 80)


def input_int(prompt, default=None):
    value = input(prompt).strip()
    if value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


def print_batches(items):
    if not items:
        print("Không có lô hàng.")
        return
    print(f"{'BATCH ID':<14} | {'SP':<10} | {'QTY':<6} | {'LOC':<18} | {'MFG':<12} | {'EXP':<12}")
    print_line()
    for it in items:
        loc = f"WH:{it.warehouse_id}" if it.warehouse_id else f"ST:{it.store_id}"
        print(f"{it.batch_id:<14} | {it.product_id:<10} | {it.quantity:<6} | {loc:<18} | {it.mfg_date:<12} | {it.exp_date:<12}")


def print_tasks(tasks):
    if not tasks:
        print("Không có task nào.")
        return
    print(f"{'TASK':<6} | {'PID':<10} | {'SOURCE':<10} | {'DEST':<16} | {'QTY':<5} | {'STATUS':<12}")
    print_line()
    for t in tasks:
        print(f"{t.task_id:<6} | {t.product_id:<10} | {t.source_batch_id:<10} | {t.target_location_type}:{t.target_location_id:<10} | {t.quantity:<5} | {t.status:<12}")


def print_menu():
    print("\n" + "=" * 45)
    print(" InS Warehouse Management CLI")
    print("=" * 45)
    print("0. Quản lý danh mục")
    print("1. Quản lý sản phẩm")
    print("2. Nhập kho (thêm batch)")
    print("3. Quản lý kho / cửa hàng")
    print("4. Xem tồn kho / batch")
    print("5. Chuyển hàng / task")
    print("6. Báo cáo và thống kê")
    print("7. Tìm kiếm và lịch sử")
    print("8. Lịch sử giao dịch")
    print("9. Cài đặt ngưỡng")
    print("10. Thoát")
    print("=" * 45)


def category_menu(service):
    while True:
        print("\n--- QUẢN LÝ DANH MỤC ---")
        print("1. Xem danh mục")
        print("2. Thêm danh mục")
        print("3. Quay lại")
        choice = input("Chọn: ").strip()
        if choice == '1':
            cats = service.show_categories()
            if not cats:
                print("Chưa có danh mục nào.")
            else:
                for c in cats:
                    print(c)
        elif choice == '2':
            cat_id = input("Nhập ID danh mục: ").strip()
            name = input("Nhập tên danh mục: ").strip()
            if service.add_category(cat_id, name):
                print("Thêm danh mục thành công.")
            else:
                print("ID danh mục đã tồn tại hoặc bị lỗi.")
        elif choice == '3':
            break
        else:
            print("Lựa chọn không hợp lệ.")


def product_menu(service):
    while True:
        print("\n--- QUẢN LÝ SẢN PHẨM ---")
        print("1. Danh sách sản phẩm")
        print("2. Thêm sản phẩm mới")
        print("3. Xem chi tiết sản phẩm")
        print("4. Tìm theo tên")
        print("5. Quay lại")
        choice = input("Chọn: ").strip()
        if choice == '1':
            products = service.show_products()
            if not products:
                print("Chưa có sản phẩm nào.")
            else:
                print(f"{'ID':<10} | {'Tên':<30} | {'Giá':<10} | {'Danh mục':<10} | {'Trạng thái'}")
                print_line()
                for p in products:
                    print(f"{p.id:<10} | {p.name:<30} | {p.price:<10} | {p.category_id:<10} | {p.status}")
        elif choice == '2':
            prod_id = input("Nhập ID sản phẩm: ").strip()
            name = input("Nhập tên: ").strip()
            category_id = input("Nhập ID danh mục: ").strip()
            try:
                price = float(input("Nhập giá bán: ").strip())
            except ValueError:
                print("Giá bán phải là số.")
                continue
            status = input("Nhập trạng thái: ").strip() or 'Available'
            if service.add_product(prod_id, name, category_id, price, status):
                print("Thêm sản phẩm thành công.")
            else:
                print("Lỗi khi thêm sản phẩm. Kiểm tra ID danh mục hoặc ID sản phẩm.")
        elif choice == '3':
            prod_id = input("Nhập ID sản phẩm: ").strip()
            product = service.find_product_by_id(prod_id)
            if not product:
                print("Không tìm thấy sản phẩm.")
            else:
                print(product)
                batches = service.load_product_batch(prod_id)
                print_batches(batches)
                service.clear_batch_cache()
        elif choice == '4':
            keyword = input("Nhập tên hoặc phần tên: ").strip()
            products = service.search_products_by_name(keyword)
            if not products:
                print("Không tìm thấy sản phẩm nào.")
            else:
                for p in products:
                    print(p)
        elif choice == '5':
            break
        else:
            print("Lựa chọn không hợp lệ.")


def inbound_batch_menu(service):
    print("\n--- NHẬP KHO / THÊM BATCH ---")
    prod_id = input("Nhập ID sản phẩm: ").strip()
    product = service.check_product_exist(prod_id)
    if not product:
        print("Sản phẩm chưa tồn tại. Tạo mới sản phẩm:")
        name = input("Tên sản phẩm: ").strip()
        category_id = input("ID danh mục: ").strip()
        try:
            price = float(input("Giá bán: ").strip())
        except ValueError:
            print("Giá bán phải là số.")
            return
        status = input("Trạng thái: ").strip() or 'Available'
        if not service.add_product(prod_id, name, category_id, price, status):
            print("Thêm sản phẩm thất bại.")
            return
        print("Đã thêm sản phẩm.")
    try:
        quantity = int(input("Số lượng: ").strip())
    except ValueError:
        print("Số lượng phải là số nguyên.")
        return
    batch_id = input("Batch ID: ").strip()
    mfg_date = input("MFG ngày (YYYY-MM-DD): ").strip()
    exp_date = input("EXP ngày (YYYY-MM-DD): ").strip()
    location_type = input("Nhập loại kho (warehouse/store): ").strip().lower()
    warehouse_id = None
    store_id = None
    if location_type == 'store':
        store_id = input("Store ID: ").strip()
    else:
        warehouse_id = input("Warehouse ID: ").strip()
    try:
        unit_price = float(input("Đơn giá: ").strip() or 0)
    except ValueError:
        print("Đơn giá phải là số.")
        return
    try:
        success, saved_batch_id = service.add_batch_item(prod_id, quantity, batch_id, mfg_date, exp_date, date.today(), warehouse_id, store_id=store_id, unit_price=unit_price)
        if success:
            print(f"Đã nhập kho batch {saved_batch_id}.")
        else:
            print("Nhập kho không thành công.")
    except Exception as e:
        print(f"Lỗi: {e}")


def location_menu(service):
    while True:
        print("\n--- QUẢN LÝ KHO / CỬA HÀNG ---")
        print("1. Xem danh sách kho")
        print("2. Thêm kho mới")
        print("3. Xem danh sách cửa hàng")
        print("4. Thêm cửa hàng mới")
        print("5. Quay lại")
        choice = input("Chọn: ").strip()
        if choice == '1':
            if not service.warehouses_map:
                print("Chưa có kho nào.")
            else:
                for wh in service.warehouses_map.values():
                    print(wh)
        elif choice == '2':
            wh_id = input("Warehouse ID: ").strip()
            name = input("Tên kho: ").strip()
            space = input_int("Dung tích kho: ")
            if space is None:
                print("Dung tích phải là số.")
                continue
            if service.add_warehouse(wh_id, name, space):
                print("Đã thêm kho.")
            else:
                print("ID kho tồn tại.")
        elif choice == '3':
            if not service.stores_map:
                print("Chưa có cửa hàng nào.")
            else:
                for st in service.stores_map.values():
                    print(st)
        elif choice == '4':
            store_id = input("Store ID: ").strip()
            name = input("Tên cửa hàng: ").strip()
            location = input("Địa chỉ: ").strip()
            if service.add_store(store_id, name, location):
                print("Đã thêm cửa hàng.")
            else:
                print("ID cửa hàng tồn tại.")
        elif choice == '5':
            break
        else:
            print("Lựa chọn không hợp lệ.")


def inventory_menu(service):
    while True:
        print("\n--- TỒN KHO / BATCH ---")
        print("1. Xem tất cả batch")
        print("2. Xem batch theo sản phẩm")
        print("3. Xem batch theo warehouse/store")
        print("4. Low stock")
        print("5. Expiring soon")
        print("6. Quay lại")
        choice = input("Chọn: ").strip()
        if choice == '1':
            products = list(service.products_map.keys())
            all_batches = []
            for pid in products:
                all_batches.extend(service.load_product_batch(pid))
            print_batches(all_batches)
            service.clear_batch_cache()
        elif choice == '2':
            pid = input("Nhập ID sản phẩm: ").strip()
            print_batches(service.load_product_batch(pid))
            service.clear_batch_cache()
        elif choice == '3':
            ltype = input("Loại vị trí (warehouse/store): ").strip().lower()
            pid = input("Nhập ID sản phẩm để lọc: ").strip()
            loc_id = input("Nhập location ID hoặc 'All': ").strip()
            if not pid:
                print("Phải nhập product_id.")
                continue
            if loc_id.lower() == 'all':
                loc_id = 'All'
            batches = service.get_product_batches_for_location(pid, ltype, loc_id)
            print_batches(batches)
        elif choice == '4':
            threshold = input_int(f"Ngưỡng low stock hiện tại ({service.settings['low_stock_threshold']}): ", service.settings['low_stock_threshold'])
            if threshold is None:
                threshold = service.settings['low_stock_threshold']
            items = service.get_low_stock_items()
            print_batches(items)
        elif choice == '5':
            exp_items = service.get_expiring_items()
            print_batches(exp_items)
        elif choice == '6':
            break
        else:
            print("Lựa chọn không hợp lệ.")


def task_menu(service):
    while True:
        print("\n--- TASK CHUYỂN HÀNG ---")
        print("1. Xem tất cả task")
        print("2. Tạo task chuyển hàng")
        print("3. Thực hiện task")
        print("4. Hủy task")
        print("5. Quay lại")
        choice = input("Chọn: ").strip()
        if choice == '1':
            print_tasks(service.get_all_tasks())
        elif choice == '2':
            product_id = input("Product ID: ").strip()
            source_batch_id = input("Source batch ID: ").strip()
            target_type = input("Target type (warehouse/store): ").strip().lower()
            target_id = input("Target location ID: ").strip()
            qty = input_int("Số lượng chuyển: ")
            if qty is None:
                print("Số lượng phải là số.")
                continue
            try:
                task = service.create_transfer_task(product_id, target_id, target_type, qty, source_batch_id=source_batch_id)
                print(f"Tạo task thành công: {task.task_id}")
            except Exception as e:
                print(f"Lỗi: {e}")
        elif choice == '3':
            task_id = input("Nhập task ID cần thực hiện: ").strip()
            try:
                service.execute_transfer_task(task_id)
                print("Thực hiện task thành công.")
            except Exception as e:
                print(f"Lỗi: {e}")
        elif choice == '4':
            task_id = input("Nhập task ID cần hủy: ").strip()
            try:
                service.cancel_task(task_id)
                print("Task đã bị hủy.")
            except Exception as e:
                print(f"Lỗi: {e}")
        elif choice == '5':
            break
        else:
            print("Lựa chọn không hợp lệ.")


def report_menu(service):
    while True:
        print("\n--- BÁO CÁO & THỐNG KÊ ---")
        print("1. KPI tổng quan")
        print("2. Báo cáo tồn kho hiện tại")
        print("3. Sản phẩm nhiều hàng tại store")
        print("4. Hàng tồn lâu")
        print("5. Giá trị kho")
        print("6. Quay lại")
        choice = input("Chọn: ").strip()
        if choice == '1':
            stats = service.get_kpi_stats()
            for key, value in stats.items():
                if isinstance(value, dict):
                    print(f"{key}: {value['value']} ({value['trend']})")
                else:
                    print(f"{key}: {value}")
        elif choice == '2':
            report = service.get_current_inventory_report()
            for item in report:
                print(f"{item['product_id']} | {item['name']} | Qty:{item['total_qty']} | Warehouse:{item['warehouse_qty']} | Store:{item['store_qty']} | Batches:{item['batches']}")
        elif choice == '3':
            top = service.get_products_with_highest_store_inventory(10)
            for item in top:
                print(f"{item['product_id']} | {item['name']} | Store Qty:{item['store_qty']}")
        elif choice == '4':
            min_days = input_int(f"Ngày tồn lâu (mặc định {service.settings['aging_days_threshold']}): ", service.settings['aging_days_threshold'])
            if min_days is None:
                min_days = service.settings['aging_days_threshold']
            aging = service.get_aging_inventory(min_days=min_days, limit=50)
            for item in aging:
                print(f"{item['batch_id']} | {item['product_id']} | {item['name']} | Qty:{item['quantity']} | Days:{item['days_in_stock']} | {item['location']}")
        elif choice == '5':
            print(f"Giá trị kho hiện tại: ${service.get_inventory_value():,.2f}")
        elif choice == '6':
            break
        else:
            print("Lựa chọn không hợp lệ.")


def history_menu(service):
    while True:
        print("\n--- TÌM KIẾM & LỊCH SỬ ---")
        print("1. Recent products")
        print("2. Tìm sản phẩm theo tên")
        print("3. Lịch sử giao dịch")
        print("4. Quay lại")
        choice = input("Chọn: ").strip()
        if choice == '1':
            recent = service.get_recently_viewed_products()
            if not recent:
                print("Chưa có sản phẩm nào vừa xem.")
            else:
                for p in recent:
                    print(p)
        elif choice == '2':
            keyword = input("Nhập tên hoặc phần tên: ").strip()
            products = service.search_products_by_name(keyword)
            if not products:
                print("Không tìm thấy.")
            else:
                for p in products:
                    print(p)
        elif choice == '3':
            start = input("Ngày bắt đầu (YYYY-MM-DD, để trống): ").strip() or None
            end = input("Ngày kết thúc (YYYY-MM-DD, để trống): ").strip() or None
            pid = input("Lọc theo product_id (để trống không lọc): ").strip() or None
            wh = input("Lọc theo warehouse_id (để trống không lọc): ").strip() or None
            history = service.get_transaction_history(start_date=start, end_date=end, product_id=pid, warehouse_id=wh)
            if not history:
                print("Không có bản ghi.")
            else:
                for rec in history:
                    print(f"{rec['created_at']} | {rec['operation_type']} | PID:{rec['product_id']} | Batch:{rec['batch_id']} | Qty:{rec['quantity']} | Notes:{rec['notes']}")
        elif choice == '4':
            break
        else:
            print("Lựa chọn không hợp lệ.")


def setting_menu(service):
    print("\n--- CÀI ĐẶT NGƯỠNG ---")
    low = input_int(f"Ngưỡng low stock [{service.settings['low_stock_threshold']}]: ", service.settings['low_stock_threshold'])
    exp = input_int(f"Ngưỡng expiring days [{service.settings['expiring_days_threshold']}]: ", service.settings['expiring_days_threshold'])
    aging = input_int(f"Ngưỡng aging days [{service.settings['aging_days_threshold']}]: ", service.settings['aging_days_threshold'])
    service.settings['low_stock_threshold'] = low if low is not None else service.settings['low_stock_threshold']
    service.settings['expiring_days_threshold'] = exp if exp is not None else service.settings['expiring_days_threshold']
    service.settings['aging_days_threshold'] = aging if aging is not None else service.settings['aging_days_threshold']
    service.load_data()
    print("Đã cập nhật ngưỡng và reload dữ liệu.")


def main():
    """Khởi động ứng dụng ở chế độ console và điều khiển luồng chính."""
    try:
        conn = db_connect.get_connection()
    except Exception as e:
        print(f"Lỗi kết nối cơ sở dữ liệu: {e}")
        return

    service = Service(conn)
    print("Đang tải dữ liệu hệ thống...")
    service.load_data()
    print("Tải dữ liệu hoàn tất!")

    while True:
        print_menu()
        choice = str(input("Chọn chức năng: ").strip())
        if choice == '0':
            category_menu(service)
        elif choice == '1':
            product_menu(service)
        elif choice == '2':
            inbound_batch_menu(service)
        elif choice == '3':
            location_menu(service)
        elif choice == '4':
            inventory_menu(service)
        elif choice == '5':
            task_menu(service)
        elif choice == '6':
            report_menu(service)
        elif choice == '7':
            history_menu(service)
        elif choice == '8':
            history_menu(service)
        elif choice == '9':
            setting_menu(service)
        elif choice == '10':
            print("Thoát chương trình.")
            conn.close()
            break
        else:
            print("Lựa chọn không hợp lệ.")


if __name__ == "__main__":
    main()
