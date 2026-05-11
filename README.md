# InS Management System

Ứng dụng quản lý kho hàng và cửa hàng đơn giản bằng Python với giao diện GUI.

## Tổng quan

Dự án này là một hệ thống quản lý kho và bán hàng nhỏ dùng để:
- Quản lý sản phẩm, danh mục, kho và cửa hàng
- Nhập kho, quản lý lô hàng (batch)
- Theo dõi tồn kho, cảnh báo low stock và hạn dùng
- Chuyển hàng giữa kho và cửa hàng bằng task
- Ghi lại lịch sử giao dịch và lịch sử chuyển hàng
- Hiển thị báo cáo và thống kê cơ bản

## Tính năng chính

- GUI bằng `customtkinter` + `tkcalendar`
- DB MySQL với các bảng: `products`, `categories`, `batch`, `warehouses`, `stores`, `transaction_history`, `transfer_tasks`
- Lọc, tìm kiếm, autocomplete và hiển thị trạng thái sản phẩm
- Quản lý lịch sử xem sản phẩm gần nhất
- Undo / Redo cho một số thao tác thêm/sửa

## Công nghệ

- Python 3
- customtkinter
- tkinter
- tkcalendar
- mysql-connector-python
- MySQL

## Chuẩn bị môi trường

1. Cài Python 3
2. Cài MySQL và tạo user/credential phù hợp
3. Cài thư viện Python:

```bash
pip install -r requirements.txt
```

## Cấu hình cơ sở dữ liệu

1. Mở `db_connect.py` và cập nhật thông tin kết nối MySQL nếu cần:
   - `host`
   - `user`
   - `password`
   - `database`

2. Chạy file `run_setup_db.bat` trên Windows để tạo database và nạp schema + dữ liệu mẫu:

```bat
run_setup_db.bat
```

Nếu bạn dùng môi trường khác, có thể chạy thủ công:

```bash
mysql -u root -p123456 -e "CREATE DATABASE IF NOT EXISTS ins_db;"
mysql -u root -p123456 ins_db < database/setup.sql
mysql -u root -p123456 ins_db < database/samples.sql
```

> Lưu ý: Cập nhật `root` và `123456` thành thông tin MySQL của bạn.

## Cách chạy

### Chạy GUI

Chạy file `run.py`:

```bash
python run.py
```

Hoặc trực tiếp:

```bash
python app.py
```

### Chạy CLI

Chạy file `main.py`:

```bash
python main.py
```

## Cấu trúc thư mục

- `app.py` - Ứng dụng GUI chính
- `service.py` - Lớp nghiệp vụ và truy cập database
- `db_connect.py` - Kết nối MySQL
- `main.py` - Giao diện dòng lệnh
- `batch_item.py`, `product.py`, `category.py`, `warehouse.py`, `store.py`, `transfer_task.py` - các model dữ liệu
- `history.py` - Command pattern cho Undo / Redo
- `database/setup.sql` - Schema database
- `database/samples.sql` - Dữ liệu mẫu
- `requirements.txt` - Thư viện cần cài
- `run_setup_db.bat` - Script tạo DB và nạp dữ liệu mẫu
- `run.py` - Script khởi chạy GUI

## Hướng dẫn sử dụng nhanh

1. Mở phần mềm, chọn `History` để xem lịch sử giao dịch.
2. Dùng `New Batch` để thêm lô hàng mới.
3. Vào `Cài đặt` để cấu hình ngưỡng `low stock`, `expiring` và `aging`.
4. Dùng `Tasks` để quản lý chuyển hàng giữa nguồn và đích.

## Ghi chú

- Thông tin cài đặt low stock nằm trong `self.service.settings["low_stock_threshold"]`.
- Dữ liệu mẫu đã được lưu trong `database/samples.sql`.
- Nếu gặp lỗi format số, kiểm tra dữ liệu giá trị có phải là kiểu string không và convert sang float.

## Phát triển thêm

Bạn có thể mở rộng dự án bằng cách:
- Thêm trang quản lý người dùng / quyền truy cập
- Thêm báo cáo chi tiết theo thời gian
- Hoàn thiện chức năng chuyển hàng và tracking task
- Tối ưu hóa truy vấn DB và xử lý dữ liệu lớn

---

Nếu bạn muốn mở rộng hoặc thêm tính năng nào, cứ đóng góp, tôi sẽ tiến hành bổ sung.