import db_connect
from service import Service

class Menu:
    @staticmethod
    def show_main_menu():
        print("\n" + "="*35)
        print("   HỆ THỐNG QUẢN LÝ KHO & CỬA HÀNG   ")
        print("="*35)
        print("0. Quản lý Danh mục (Category)")
        print("1. Nhập kho (Thêm Sản phẩm / Lô hàng)")
        print("2. Hiển thị danh sách Sản phẩm")
        print("3. Hiển thị tình trạng Kho hàng")
        print("4. Tìm kiếm Sản phẩm theo ID")
        print("5. Xem tồn kho theo ID Sản phẩm")
        print("6. [Cảnh báo] Sản phẩm sắp hết hàng (Low Stock)")
        print("7. [Cảnh báo] Lô hàng sắp HẾT HẠN (Expiring Soon)") 
        print("8. Tìm kiếm Sản phẩm theo Tên (Trie Auto-complete)")
        print("9. Lịch sử Sản phẩm vừa xem (Queue / Deque)") # Thêm tính năng này
        print("10. Thoát chương trình")
        print("="*35)

    @staticmethod
    def show_category_menu():
        print("\n--- QUẢN LÝ DANH MỤC ---")
        print("a. Xem danh sách danh mục")
        print("b. Thêm danh mục mới")
        print("c. Quay lại menu chính")

def main():
    # 1. Khởi tạo kết nối DB và Service
    try:
        conn = db_connect.get_connection()
        cursor = conn.cursor()
    except Exception as e:
        print(f"Lỗi kết nối cơ sở dữ liệu: {e}")
        return

    service = Service()
    
    # 2. Tải toàn bộ dữ liệu từ MySQL lên RAM (Cache)
    print("Đang tải dữ liệu hệ thống...")
    service.load_data(cursor)
    print("Tải dữ liệu hoàn tất!")

    # 3. Vòng lặp chính của chương trình
    while True:
        Menu.show_main_menu()
        choice = input("Vui lòng chọn chức năng (0-6): ").strip()

        if choice == '0':
            while True:
                Menu.show_category_menu()
                sub_choice = input("Chọn thao tác (a/b/c): ").strip().lower()
                
                if sub_choice == 'a':
                    cats = service.show_categories()
                    if not cats:
                        print("Chưa có danh mục nào trong hệ thống.")
                    else:
                        for c in cats:
                            print(c)
                
                elif sub_choice == 'b':
                    c_id = input("Nhập ID danh mục mới: ").strip()
                    c_name = input("Nhập tên danh mục: ").strip()
                    if service.add_category(c_id, c_name, cursor, conn):
                        print(f"-> Đã thêm danh mục '{c_name}' thành công!")
                    else:
                        print(f"-> Lỗi: ID danh mục '{c_id}' đã tồn tại!")
                
                elif sub_choice == 'c':
                    break
                else:
                    print("Lựa chọn không hợp lệ!")

        elif choice == '1':
            print("\n--- NHẬP KHO HÀNG HÓA ---")
            prod_id = input("Nhập ID Sản phẩm: ").strip()
            product = service.check_product_exist(prod_id)
            
            # Xử lý thông tin Sản phẩm
            if product:
                print(f"Sản phẩm '{product.name}' đã có trong hệ thống. Tiếp tục nhập thông tin lô hàng.")
            else:
                print("Sản phẩm chưa tồn tại. Vui lòng tạo sản phẩm mới:")
                name = input(" Tên sản phẩm: ").strip()
                category_id = input(" ID Danh mục: ").strip()
                
                try:
                    price = float(input(" Giá bán: "))
                except ValueError:
                    print("-> Lỗi: Giá bán phải là một số! Hủy thao tác.")
                    continue
                
                status = input(" Trạng thái (VD: Available): ").strip()
                
                # Thử thêm sản phẩm (hàm này sẽ kiểm tra xem category_id có hợp lệ không)
                if service.add_product(prod_id, name, category_id, price, status, cursor, conn):
                    print("-> Đã tạo sản phẩm mới thành công!")
                else:
                    print("-> Thêm sản phẩm thất bại. Vui lòng kiểm tra lại ID danh mục hoặc ID sản phẩm.")
                    continue # Quay lại menu chính nếu lỗi

            # Xử lý thông tin Lô hàng (Inventory)
            print("\n-- Thông tin lô hàng nhập kho --")
            try:
                quantity = int(input(" Số lượng: "))
            except ValueError:
                print("-> Lỗi: Số lượng phải là số nguyên! Hủy thao tác.")
                continue
                
            batch_id = input(" Mã lô (batch_id): ").strip()
            mfg_date = input(" Ngày sản xuất (YYYY-MM-DD): ").strip()
            exp_date = input(" Hạn sử dụng (YYYY-MM-DD): ").strip()
            warehouse_id = input(" Mã kho: ").strip()
            
            if service.add_inventory_item(prod_id, quantity, batch_id, mfg_date, exp_date, warehouse_id, cursor, conn):
                print("-> Nhập kho thành công!")
            else:
                print("-> Đã xảy ra lỗi khi nhập kho.")

        elif choice == '2':
            print("\n--- DANH SÁCH SẢN PHẨM ---")
            products = service.show_products()
            if not products:
                print("Hệ thống chưa có sản phẩm nào.")
            for p in products:
                print(p)
                
        elif choice == '3':
            print("\n--- TÌNH TRẠNG KHO HÀNG ---")
            inventory = service.show_inventory()
            if not inventory:
                print("Kho hàng đang trống.")
            for item in inventory:
                print(item)
                
        elif choice == '4':
            k = input("\nNhập ID sản phẩm cần tìm: ").strip()
            product = service.find_product_by_id(k)
            if product:
                print("-> Kết quả tìm kiếm:")
                print(product)
            else:
                print("-> Không tìm thấy sản phẩm với ID này!")
                
        elif choice == '5':
            k = input("\nNhập ID sản phẩm để xem các lô tồn kho: ").strip()
            items = service.find_inventory_by_product_id(k)
            if items:
                print(f"-> Các lô hàng của sản phẩm ID '{k}':")
                for item in items:
                    print(item)
            else:
                print("-> Không có hàng trong kho cho sản phẩm này!")
                
        elif choice == '6':
            print("\n--- CẢNH BÁO SẢN PHẨM SẮP HẾT HÀNG ---")
            try:
                threshold = int(input("Nhập ngưỡng số lượng báo động (Mặc định 50): ") or 50)
            except ValueError:
                threshold = 50
                
            warnings = service.get_low_stock_warnings(threshold)
            
            if not warnings:
                print(f"-> Tuyệt vời! Không có sản phẩm nào có tổng tồn kho dưới {threshold}.")
            else:
                print(f"-> CẢNH BÁO: Có {len(warnings)} sản phẩm sắp hết hàng (<= {threshold}):")
                print(f"{'ID':<10} | {'TÊN SẢN PHẨM':<35} | {'TỔNG TỒN KHO'}")
                print("-" * 65)
                for w in warnings:
                    print(f"{w['id']:<10} | {w['name']:<35} | {w['total_quantity']} SP")

        elif choice == '7':
            print("\n--- CẢNH BÁO LÔ HÀNG SẮP HẾT HẠN ---")
            try:
                days_th = int(input("Nhập số ngày báo động trước (Mặc định 30 ngày): ") or 30)
            except ValueError:
                days_th = 30
                
            exp_warnings = service.get_expiring_soon_warnings(days_th)
            
            if not exp_warnings:
                print(f"-> An toàn! Không có lô hàng nào hết hạn trong {days_th} ngày tới.")
            else:
                print(f"-> CẢNH BÁO: Phát hiện {len(exp_warnings)} lô hàng cần chú ý:")
                
                # Đổi MÃ SP thành INV ID (ID của bảng inventory)
                print(f"{'INV ID':<8} | {'MÃ LÔ':<12} | {'TÊN SẢN PHẨM':<25} | {'HẠN SỬ DỤNG':<12} | {'TÌNH TRẠNG':<15} | {'SỐ LƯỢNG'}")
                print("-" * 90) 
                
                for w in exp_warnings:
                    days_left = w['days_left']
                    
                    if days_left < 0:
                        status = f"ĐÃ QUÁ HẠN {-days_left} ngày!"
                    elif days_left == 0:
                        status = "HẾT HẠN HÔM NAY!"
                    else:
                        status = f"Còn {days_left} ngày"
                        
                    # Lấy w['inv_id'] để in ra
                    print(f"{w['inv_id']:<8} | {w['batch_id']:<12} | {w['product_name'][:22] + '...' if len(w['product_name']) > 22 else w['product_name']:<25} | {str(w['exp_date']):<12} | {status:<15} | {w['quantity']}")
        elif choice == '8':
            print("\n--- TÌM KIẾM SẢN PHẨM THEO TÊN (AUTO-COMPLETE) ---")
            prefix = input("Nhập tên (hoặc một phần tên) sản phẩm: ").strip()
            
            results = service.search_products_by_name(prefix)
            
            if not results:
                print(f"-> Không tìm thấy sản phẩm nào bắt đầu bằng '{prefix}'.")
            else:
                print(f"-> Tìm thấy {len(results)} sản phẩm:")
                print(f"{'MÃ SP':<10} | {'TÊN SẢN PHẨM':<35} | {'GIÁ BÁN':<10} | {'TRẠNG THÁI'}")
                print("-" * 75)
                for p in results:
                    print(f"{p.id:<10} | {p.name:<35} | ${p.price:<9} | {p.status}")
        elif choice == '9':
            print("\n--- LỊCH SỬ 5 SẢN PHẨM VỪA XEM ---")
            recent = service.get_recently_viewed_products()
            
            if not recent:
                print("-> Bạn chưa xem chi tiết sản phẩm nào (Hãy dùng tính năng số 4 để xem).")
            else:
                print(f"{'MÃ SP':<10} | {'TÊN SẢN PHẨM':<35} | {'GIÁ BÁN':<10}")
                print("-" * 60)
                for p in recent:
                    if p:
                        print(f"{p.id:<10} | {p.name:<35} | ${p.price:<9}")
        elif choice == '10':
            print("\nĐang đóng kết nối dữ liệu...")
            cursor.close()
            conn.close()
            print("Thoát chương trình. Tạm biệt!")
            break
        else:
            print("Lựa chọn không hợp lệ, vui lòng thử lại!")

if __name__ == "__main__":
    main()