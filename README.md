# ADO 3D Object Detection - Web Annotation Tool & System Documentation

Tài liệu hướng dẫn toàn diện về kiến trúc, cơ chế hoạt động, cấu trúc Cache, cách sao lưu dữ liệu và hướng dẫn vận hành/nâng cấp hệ thống dành cho người dùng và các trợ lý AI kế thừa dự án.

---

## 📑 Mục Lục
1. [Tổng Quan Hệ Thống](#1-tổng-quan-hệ-thống)
2. [Cấu Trúc Thư Mục & Các Tệp Tin Quan Trọng](#2-cấu-trúc-thư-mục--các-tệp-tin-quan-trọng)
3. [Cơ Chế Cache Của Tool Gốc Unity và Web Tool](#3-cơ-chế-cache-của-tool-gốc-unity-và-web-tool)
   - [3.1. Cache Gốc Unity (Alchera ADO Tool)](#31-cache-gốc-unity-alchera-ado-tool)
   - [3.2. Cache Web Tool (Local Cache H:\a\cache)](#32-cache-web-tool-local-cache-hacache)
   - [3.3. Quy Tắc Bất Biến Khi Đọc & Ghi Cache](#33-quy-tắc-bất-biến-khi-đọc--ghi-cache)
4. [Hướng Dẫn Sao Lưu (Backup) & Phục Hồi Dữ Liệu](#4-hướng-dẫn-sao-lưu-backup--phục-hồi-dữ-liệu)
5. [Cơ Chế Đồng Bộ Ngược Lại Tool Gốc Unity](#5-cơ-chế-đồng-bộ-ngược-lại-tool-gốc-unity)
6. [Chi Tiết Toàn Bộ Tính Năng Trên Giao Diện Web](#6-chi-tiết-toàn-bộ-tính-năng-trên-giao-diện-web)
   - [6.1. Không Gian 3D LiDAR & 2D Camera](#61-không-gian-3d-lidar--2d-camera)
   - [6.2. 3 Khung Chiếu Trực Giao Cắt Lớp (Sub-Views)](#62-3-khung-chiếu-trực-giao-cắt-lớp-sub-views)
   - [6.3. Chế Độ 2D Mode (Top-Down Bounding Box Editor)](#63-chế-độ-2d-mode-top-down-bounding-box-editor)
   - [6.4. Tính Năng Auto Box (Dự Đoán Quỹ Đạo Chuyển Động)](#64-tính-năng-auto-box-dự-đoán-quỹ-đạo-chuyển-động)
   - [6.5. Tính Năng Google Drive Sync Qua Apps Script](#65-tính-năng-google-drive-sync-qua-apps-script)
7. [Bảng Phím Tắt Tiêu Chuẩn (Hotkeys)](#7-bảng-phím-tắt-tiêu-chuẩn-hotkeys)
8. [Hướng Dẫn Cài Đặt & Khởi Động](#8-hướng-dẫn-cài-đặt--khởi-động)
9. [Lưu Ý Sống Còn Dành Cho AI Kế Thừa (Developer Notes)](#9-lưu-ý-sống-còn-dành-cho-ai-kế-thừa-developer-notes)

---

## 1. Tổng Quan Hệ Thống

Dự án này là bộ công cụ gán nhãn dữ liệu xe tự hành (Autonomous Driving Object Detection - ADO 3D) kết hợp giữa:
1. **Tool Gốc Unity (`ADO-anntoation-tool`)**: Ứng dụng chạy trên nền Unity của hãng Alchera Inc, dùng để load chuỗi dữ liệu (Sequence) từ server công ty về máy cục bộ.
2. **Tool Web Nội Bộ (`Web Annotation Tool`)**: Ứng dụng web chạy trên nền Python Flask (`localhost:5000`) và Three.js / Canvas HTML5. Công cụ này được xây dựng để khắc phục các hạn chế của Unity (nhanh hơn, nhẹ hơn, có tính năng Auto Box nội suy quỹ đạo, chỉnh sửa 2D/3D đồng thời, và sao lưu dữ liệu lên Google Drive).
3. **Công cụ Kiểm Tra Nhanh (`FastCheck App`)**: Ứng dụng phụ chạy tại `localhost:5050` dùng để review nhanh dữ liệu 10 frame cùng lúc ở chế độ Read-Only.

---

## 2. Cấu Trúc Thư Mục & Các Tệp Tin Quan Trọng

```text
H:\a\
├── install.bat                     # Script tự động cài thư viện Python (flask, numpy, requests)
├── start_web_tool.bat              # Script khởi động cùng lúc Web Tool (5000) & FastCheck (5050)
├── fast_check_app.py               # Standalone Flask server phục vụ FastCheck 3D Viewer (5050)
├── cache/                          # THƯ MỤC CHÍNH CHỨA CACHE WEB TOOL
│   ├── annotations/                # Chứa frame_0001.json -> frame_0010.json
│   ├── images/                     # Chứa frame_0001.png -> frame_0010.png
│   ├── pcd/                        # Chứa frame_0001.pcd -> frame_0010.pcd
│   └── calibration.json            # Ma trận hiệu chuẩn LiDAR - Camera - Xe
├── web_app/
│   ├── server.py                   # Backend Flask chính (API nạp, lưu, convert, auto-box, drive)
│   ├── auto_box.py                 # Module thuật toán vật lý dự đoán quỹ đạo box
│   ├── drive_sync.py               # Module giao tiếp HTTP gửi/nhận JSON với Google Apps Script
│   ├── drive_config.json           # File lưu URL Web App Google Apps Script và cấu hình auto-sync
│   ├── sync_to_unity.py            # Module đồng bộ nhãn từ Web Cache ngược lại Unity Tool
│   ├── google_apps_script_template.js # Mã nguồn JavaScript để dán vào Google Apps Script
│   └── static/
│       ├── index.html              # Giao diện người dùng Web Tool
│       ├── css/style.css           # Toàn bộ CSS giao diện, floating windows, viewport
│       └── js/
│           ├── app.js              # Controller chính xử lý sự kiện, hotkeys, state, API
│           ├── pointcloud.js       # Quản lý Three.js, LiDAR 3D, cắt trực giao, render Box
│           ├── projection.js       # Chiếu tọa độ 3D LiDAR sang tọa độ Pixel 2D Camera
│           ├── OrbitControls.js    # Thư viện điều khiển góc xoay camera 3D
│           └── three.min.js        # Thư viện đồ họa WebGL Three.js
```

---

## 3. Cơ Chế Cache Của Tool Gốc Unity và Web Tool

### 3.1. Cache Gốc Unity (Alchera ADO Tool)
* **Đường dẫn thư mục**:
  `C:\Users\Administrator\AppData\LocalLow\Alchera Inc\ADO-anntoation-tool\sequence`
* **Quy chuẩn 31 File**:
  Một sequence đầy đủ gồm đúng **31 file**:
  * 10 file Point Cloud PCD: `0000_MCAM_....pcd` đến `0009_MCAM_....pcd`
  * 10 file Ảnh Camera PNG: `0000_IMG_Camera1_....png` đến `0009_IMG_Camera1_....png`
  * 10 file Nhãn Annotations JSON: `0000_MCAM_....json` đến `0009_MCAM_....json`
  * 1 file Ma trận hiệu chuẩn: `calibration.json`
* **Quy tắc đếm Index (0-based vs 1-based)**:
  * Trong Unity, các file bắt đầu từ số **0** (`0000` đến `0009`).
  * Trong Web Tool, để người dùng không bị nhầm lẫn, giao diện hiển thị từ **Frame 1 đến Frame 10**. Tương ứng:
    * Frame 1 web $\leftrightarrow$ File `0000` Unity $\leftrightarrow$ File `frame_0001` Web Cache.
    * Frame 10 web $\leftrightarrow$ File `0009` Unity $\leftrightarrow$ File `frame_0010` Web Cache.
* **Cơ chế kiểm tra 31 file an toàn**:
  Khi người dùng bấm nút **🎮 Cache Unity**, server sẽ kiểm tra số lượng file trong thư mục `sequence`.
  * Nếu $\ge 31$ file: Tự động load ngay không hỏi.
  * Nếu $< 31$ file: Hiện modal cảnh báo thiếu dữ liệu (`modal-unity-cache-confirm`). Người dùng bấm *Có* mới nạp, bấm *Không* sẽ hủy bỏ.

### 3.2. Cache Web Tool (Local Cache H:\a\cache)
* **Đường dẫn thư mục**: `H:\a\cache`
* **Cấu trúc**:
  * `annotations/frame_0001.json` ... `frame_0010.json`: Chứa các object cuboid đã gán nhãn.
  * `images/frame_0001.png` ... `frame_0010.png`: Ảnh trích xuất từ camera.
  * `pcd/frame_0001.pcd` ... `frame_0010.pcd`: Dữ liệu đám mây điểm.
  * `calibration.json`: Thông số nội tại, ngoại tại camera và ma trận biến đổi LiDAR sang Vehicle.

### 3.3. Quy Tắc Bất Biến Khi Đọc & Ghi Cache
> [!IMPORTANT]
> **QUY TẮC SỐNG CÒN**:
> Khi người dùng bấm **🎮 Cache Unity**, Web Tool **TUYỆT ĐỐI KHÔNG ĐƯỢC GHI ĐÈ** vào `H:\a\cache\annotations\`.
> Dữ liệu Unity chỉ được đọc vào bộ nhớ RAM của Server để người dùng xem.
> 
> **Cache Web (`H:\a\cache\annotations\`) CHỈ ĐƯỢC PHÉP GHI trong các trường hợp sau**:
> 1. Người dùng bấm nút **Save** trên thanh công cụ.
> 2. Người dùng nhấn tổ hợp phím **`Ctrl + S`**.
> 3. Người dùng chuyển frame bằng nút Next / Prev (hoặc hotkey `A`/`D`, phím mũi tên).
> 4. Người dùng click trực tiếp vào các nút số frame **1 đến 10**.

---

## 4. Hướng Dẫn Sao Lưu (Backup) & Phục Hồi Dữ Liệu

### 4.1. Sao Lưu Cache Gốc Unity
* Khi tool Unity tải xong một sequence mới, copy toàn bộ thư mục:
  `C:\Users\Administrator\AppData\LocalLow\Alchera Inc\ADO-anntoation-tool\sequence`
  sang một nơi an toàn hoặc nén thành file `.zip`.

### 4.2. Sao Lưu Cache Web Cục Bộ
* Sao chép toàn bộ thư mục `H:\a\cache` sang vị trí lưu trữ khác. Thư mục này chứa toàn bộ công sức bạn đã vẽ box.

### 4.3. Sao Lưu Lên Google Drive Qua Apps Script (Đám Mây)
Hệ thống đã tích hợp chức năng Cloud Sync thông qua Google Apps Script Web App:
1. Bấm nút **`☁️ Apps Script`** ở cạnh Front View để mở cửa sổ di động.
2. Dán link Web App (kết thúc bằng `/exec`) vào ô cấu hình và bấm `🔒 Lưu`.
3. **Upload lên Drive**:
   * Bấm **`☁️ Upload All Frame`**: Tải toàn bộ 10 file JSON lên Google Drive.
   * Bấm **`📤 Upload Frame Này`**: Tải riêng file JSON của frame hiện tại lên Drive.
   * Tick vào **`Tự động sync Frame`**: Mỗi khi bạn bấm Save hoặc `Ctrl + S`, hệ thống tự động chạy luồng ngầm đẩy file JSON lên Drive mà không gây khựng giao diện.
   * *Đặc tính an toàn*: Nếu file đã có sẵn trên Drive, hệ thống sẽ **ghi đè nội dung mới**, tuyệt đối không tạo thêm file trùng lặp.
4. **Download từ Drive về Web Tool**:
   * Bấm **`📥 Download All Frame`**: Tải toàn bộ JSON từ Drive về ghi đè vào `H:\a\cache\annotations\` và làm mới lại web.
   * Bấm **`📥 Download Frame Này`**: Tải riêng frame hiện tại về đè vào máy.

---

## 5. Cơ Chế Đồng Bộ Ngược Lại Tool Gốc Unity

Khi bạn đã hoàn thành công việc trên Web Tool và muốn nộp kết quả qua Tool Unity:
1. Trên giao diện Web Tool, bấm nút **`🔄 Đồng bộ Unity`** trên thanh Header.
2. Module `sync_to_unity.py` sẽ thực hiện:
   * Quét toàn bộ `H:\a\cache\annotations\frame_0001.json` đến `frame_0010.json`.
   * Khớp từng frame tương ứng với file gốc trong thư mục Unity (`0000_MCAM_...json` đến `0009_MCAM_...json`).
   * Giữ nguyên cấu trúc ma trận camera, tên camera, header của Unity, chỉ thay thế mảng `object_list` với tọa độ, kích thước, yaw chuẩn xác.
   * Ghi đè vào thư mục `sequence` của Unity Tool.
3. Mở Tool Unity lên, toàn bộ box đã xuất hiện chuẩn xác 100%.

---

## 6. Chi Tiết Toàn Bộ Tính Năng Trên Giao Diện Web

### 6.1. Không Gian 3D LiDAR & 2D Camera
* **Khung 3D LiDAR**: Render hàng chục nghìn điểm point cloud bằng WebGL BufferGeometry. Cho phép xoay tự do (OrbitControls), zoom, pan. Có thanh điều chỉnh độ sáng (brightness), tương phản (contrast), đổi tông màu (hue), chỉnh kích thước hạt điểm và lọc độ cao trần $Z$.
* **Khung 2D Camera**: Chiếu ảnh thực tế từ xe. Toàn bộ Box 3D LiDAR được ma trận nội suy chiếu thành bounding box 3D trên ảnh 2D theo thời gian thực.
  * Hỗ trợ zoom chuột cuộn, kéo chuột trái để di chuyển ảnh.
  * Hỗ trợ click trực tiếp vào Box trên ảnh 2D để chọn đối tượng.
  * Checkbox **`chk-id-check`**: Khi chọn 1 ID, camera 2D tự động zoom và căn giữa màn hình vào đúng đối tượng đó.

### 6.2. 3 Khung Chiếu Trực Giao Cắt Lớp (Sub-Views)
Nằm ở góc dưới màn hình, cắt độc lập không gian điểm quanh Box đang chọn:
* **Top View**: Nhìn từ trên xuống (mặt phẳng $XY$).
* **Side View**: Nhìn từ bên sườn (mặt phẳng $ZY$).
* **Front View**: Nhìn từ phía trước/sau (mặt phẳng $XZ$).
* Cho phép rê chuột vào 4 góc hoặc các cạnh chấm vàng để kéo giãn kích thước (Resize Length, Width, Height) và dời tâm box cực kỳ chuẩn xác đến từng centimet.

### 6.3. Chế Độ 2D Mode (Top-Down Bounding Box Editor)
* Nhấn nút **`📐 2D Mode`** trên thanh công cụ.
* Camera 3D sẽ tự động xoay vuông góc $90^\circ$ từ trên trời nhìn thẳng xuống mặt đất.
* **Chuột trái**: Bấm và kéo bất kỳ Box nào để di chuyển vị trí mượt mà trên mặt phẳng đất.
* **Chuột phải**: Dùng để cuộn/pan khung nhìn mà không làm lệch góc chiếu.

### 6.4. Tính Năng Auto Box (Dự Đoán Quỹ Đạo Chuyển Động)
* Nút bấm **`⚡ Auto Box`** nằm cạnh Front View, mở ra một cửa sổ di động kéo thả được (`float-window-autobox`).
* **Nguyên lý hoạt động nghiêm ngặt**:
  * **Frame 1**: Báo lỗi vì là frame đầu tiên, chưa có dữ liệu quá khứ.
  * **Frame 2**: Báo lỗi vì chỉ mới có Frame 1. Thuật toán vật lý cần ít nhất **2 frame liên tiếp có box** trước đó để tính vector vận tốc $\vec{v}$.
  * **Từ Frame 3 trở đi**:
    * Đang ở Frame 3 $\rightarrow$ đọc Frame 2 và Frame 1.
    * Đang ở Frame 4 $\rightarrow$ đọc Frame 3 và Frame 2.
    * Nếu Frame $t-1$ chưa có dữ liệu hoặc không có ID của box cần tính, hệ thống lập tức chặn lại và thông báo:
      `❌ Không thể Auto Box vì Frame trước (Frame X) chưa có ID: #...`
  * **Tính toán nội suy**:
    $$\Delta x = x_{t-1} - x_{t-2}, \quad \Delta y = y_{t-1} - y_{t-2}, \quad \Delta z = z_{t-1} - z_{t-2}$$
    $$\Delta\text{yaw} = \text{normalize}(\text{yaw}_{t-1} - \text{yaw}_{t-2})$$
    Vị trí mới:
    $$x_t = x_{t-1} + \Delta x, \quad y_t = y_{t-1} + \Delta y, \quad z_t = z_{t-1} + \Delta z$$
    $$\text{yaw}_t = \text{normalize}(\text{yaw}_{t-1} + \Delta\text{yaw})$$
  * Tự động đồng bộ kích thước (Dài, Rộng, Cao), `category`, `subclass` từ frame trước.
* **2 Chế độ chạy**:
  1. **`🎯 Auto Box Đang Chọn`**: Cho phép chọn 1 hoặc nhiều Box mong muốn, chỉ tính toán và dời các Box đó.
  2. **`🚀 Auto Box Toàn Bộ`**: Tự động duyệt qua tất cả các Box hiện có trong frame để dời vị trí theo quỹ đạo.

### 6.5. Tính Năng Google Drive Sync Qua Apps Script
* Cửa sổ di động kéo thả được (`float-window-appscript`), không có nền tối (backdrop) che màn hình, vừa mở cửa sổ vừa làm việc bình thường.
* **Khả năng tự động dò tìm thư mục**:
  Mã nguồn Apps Script sử dụng hàm `DriveApp.getFoldersByName("PED")` quét toàn bộ Google Drive. **Bạn có thể di chuyển thư mục `PED` vào bất kỳ thư mục con nào trên Google Drive**, script vẫn tự động tìm thấy và lưu/tải file bình thường.

---

## 7. Bảng Phím Tắt Tiêu Chuẩn (Hotkeys)

| Phím Tắt | Chức Năng | Chi Tiết |
| :--- | :--- | :--- |
| **`Ctrl + S`** | Lưu dữ liệu Frame | Lưu vào Cache Web (`H:\a\cache\annotations\`). Tự sync Drive nếu bật. |
| **`A`** hoặc **`←`** | Frame Trước | Tự động lưu frame hiện tại trước khi lùi frame. |
| **`D`** hoặc **`→`** | Frame Kế Tiếp | Tự động lưu frame hiện tại trước khi tiến frame. |
| **`O`** | Isolate Box Đang Chọn | Ẩn toàn bộ các box khác trên ảnh 2D, chỉ giữ lại duy nhất box đang chọn. |
| **`H`** | Ẩn Toàn Bộ Box | Ẩn sạch tất cả các box trên ảnh 2D để quan sát vật thể rõ nét. |
| **`Ctrl + C`** | Copy Box | Sao chép thông số các Box đang chọn vào bộ nhớ đệm. |
| **`Ctrl + V`** | Paste Box | Dán các Box đã copy sang Frame hiện tại. |
| **`Shift + K`** | Copy Từ Frame Sau | Lấy toàn bộ Box của frame kế tiếp dán vào frame này. |
| **`Del` / `Backspace`** | Xóa Box | Xóa các Cuboid đang được chọn trong frame. |
| **`Ctrl + Z`** | Hoàn Tác (Undo) | Quay lại thao tác chỉnh sửa hoặc xóa box trước đó. |
| **`M`** | Đồng Bộ ID Toàn Sequence | Đồng bộ kích thước (Dài, Rộng, Cao) và Class/Subclass của ID này cho toàn bộ 10 Frame. |

---

## 8. Hướng Dẫn Cài Đặt & Khởi Động

### Cách 1: Khởi động bằng file thực thi EXE (Khuyên dùng - Nhanh nhất)
Nhấp đúp chuột trực tiếp vào file:
```text
H:\a\ADO_Web_Tool.exe
```
* File `.exe` độc lập đã tích hợp sẵn toàn bộ môi trường và dữ liệu giao diện tĩnh.
* Tự động khởi chạy song song cả 2 Server (Main Tool `5000` & FastCheck `5050`) và tự động mở trình duyệt!

### Cách 2: Khởi động bằng Script Batch
1. Chạy `H:\a\install.bat` để cài thư viện Python (chỉ làm lần đầu).
2. Nhấp đúp chuột vào `H:\a\start_web_tool.bat` để khởi chạy.

---

## 9. Lưu Ý Sống Còn Dành Cho AI Kế Thừa (Developer Notes)

Khi được yêu cầu nâng cấp, sửa đổi hoặc mở rộng tính năng cho codebase này, AI cần nắm rõ các nguyên tắc kỹ thuật sau:

1. **Không can thiệp vào cách tổ chức thư mục Cache**:
   Thư mục `H:\a\cache` là chuẩn định dạng mà cả `server.py` và `fast_check_app.py` cùng đọc. Không tự ý đổi tên thư mục con `annotations`, `images`, `pcd`.
2. **Luôn bảo toàn nguyên tắc không ghi đè khi Load Unity**:
   Hàm `scan_original_cache()` trong `server.py` chỉ được phép đọc dữ liệu vào `self.frames[idx]["annotation"]` trên RAM, **không bao giờ** được ghi vào `LOCAL_ANNOTATIONS_DIR`.
3. **Giữ nguyên quy tắc xoay góc Euler & Quaternion**:
   Tọa độ LiDAR sử dụng hệ trục phải với thứ tự quay `IZYX` (`orientation: [yaw, pitch, roll]`). Khi chuyển sang Quaternion cần dùng hàm `euler_to_quaternion(roll, pitch, yaw)`.
4. **Giữ giao diện Non-blocking cho các Floating Windows**:
   Các cửa sổ chức năng mới (như Auto Box, Drive Sync, YouTube Player, Properties) phải dùng class `.floating-tool-window` và hàm `makeElementDraggable()`, **tuyệt đối không dùng class `.modal` có backdrop đen che màn hình** làm cản trở thao tác 3D/2D của người dùng.
5. **Đồng bộ hóa 2 chiều Unity**:
   Khi ghi dữ liệu ngược về Unity trong `sync_to_unity.py`, cấu trúc JSON phải giữ đúng các key gốc của Unity: `pcd_filename`, `img_filenames`, và các key camera bên trong từng object cuboid.
