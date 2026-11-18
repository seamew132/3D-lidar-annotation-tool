import os
import sys
import time
import json
import math
import subprocess
import ctypes

# Win32 Constants for background key sending
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
VK_RIGHT = 0x27

USER_PROFILE = os.environ.get("USERPROFILE") or os.path.expanduser("~")
UNITY_SEQUENCE_DIR = os.path.join(USER_PROFILE, "AppData", "LocalLow", "Alchera Inc", "ADO-anntoation-tool", "sequence")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_CACHE_ANN_DIR = os.path.join(BASE_DIR, "cache", "annotations")

def euler_to_quaternion_zyx(roll, pitch, yaw):
    cx = math.cos(roll / 2.0)
    sx = math.sin(roll / 2.0)
    cy = math.cos(pitch / 2.0)
    sy = math.sin(pitch / 2.0)
    cz = math.cos(yaw / 2.0)
    sz = math.sin(yaw / 2.0)

    qx = sx * cy * cz - cx * sy * sz
    qy = cx * sy * cz + sx * cy * sz
    qz = cx * cy * sz - sx * sy * cz
    qw = cx * cy * cz + sx * sy * sz

    return [qx, qy, qz, qw]

def format_obj_for_unity(obj):
    formatted = json.loads(json.dumps(obj))
    loc = formatted.get("pose_in_lidar", {}).get("location", [0, 0, 0])
    sub = formatted.get("sub_class") or formatted.get("subclass") or "adult"
    formatted["sub_class"] = sub
    formatted["subclass"] = sub

    roll, pitch, yaw = 0.0, 0.0, 0.0
    if "pose_in_lidar_target" in formatted and "orientation" in formatted["pose_in_lidar_target"]:
        ori = formatted["pose_in_lidar_target"]["orientation"]
        if isinstance(ori, list) and len(ori) >= 3:
            roll = float(ori[0] or 0.0)
            pitch = float(ori[1] or 0.0)
            yaw = float(ori[2] or 0.0)

    formatted["pose_in_lidar_target"] = {
        "location": loc,
        "orientation": [roll, pitch, yaw],
        "order": "IZYX"
    }

    quat = euler_to_quaternion_zyx(roll, pitch, yaw)

    formatted["pose_in_lidar"] = {
        "location": loc,
        "orientation": quat
    }

    formatted["pose_in_vehicle"] = {
        "location": loc,
        "orientation": [0.0, 0.0, 0.0, 1.0]
    }

    if "cameras" not in formatted or not isinstance(formatted["cameras"], list) or len(formatted["cameras"]) == 0:
        formatted["cameras"] = [{
            "name": "front",
            "box_in_camera": {
                "location": [0.0, 0.0, 0.0],
                "orientation": [0.0, 0.0, 0.0, 1.0]
            },
            "2d_box": [0, 0, 0, 0]
        }]

    return formatted

def sync_cache_moi_to_unity():
    if not os.path.exists(LOCAL_CACHE_ANN_DIR):
        print(f"❌ Không tìm thấy thư mục nhãn cache webtool: '{LOCAL_CACHE_ANN_DIR}'")
        return False

    if not os.path.exists(UNITY_SEQUENCE_DIR):
        print(f"❌ Không tìm thấy thư mục cache sequence Unity: '{UNITY_SEQUENCE_DIR}'")
        return False

    local_ann_files = sorted([f for f in os.listdir(LOCAL_CACHE_ANN_DIR) if f.endswith('.json')])
    if not local_ann_files:
        print("❌ Không có file nhãn nào trong thư mục cache/annotations của Web Tool!")
        return False

    frame_anns = {}
    for fn in local_ann_files:
        idx_str = fn.replace('frame_', '').replace('.json', '')
        if idx_str.isdigit():
            num = int(idx_str)
            fpath = os.path.join(LOCAL_CACHE_ANN_DIR, fn)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    frame_anns[num] = data
                    frame_anns[num - 1] = data
            except Exception:
                pass

    files = os.listdir(UNITY_SEQUENCE_DIR)
    target_cache_files = []
    
    for fn in files:
        fpath = os.path.join(UNITY_SEQUENCE_DIR, fn)
        if os.path.isfile(fpath) and os.path.getsize(fpath) < 2000000:
            try:
                with open(fpath, 'r', encoding='utf-8') as jf:
                    data = json.load(jf)
                    if "object_list" in data and "pcd_filename" in data:
                        pcd_fn = data.get("pcd_filename", "")
                        frame_idx = int(pcd_fn[:4]) if len(pcd_fn) >= 4 and pcd_fn[:4].isdigit() else -1
                        mtime = os.path.getmtime(fpath)
                        target_cache_files.append((fpath, fn, frame_idx, mtime, data))
            except Exception:
                pass

    if not target_cache_files:
        print(f"❌ Không tìm thấy file JSON nhãn phù hợp trong '{UNITY_SEQUENCE_DIR}'")
        return False

    target_cache_files.sort(key=lambda x: x[2] if x[2] >= 0 else x[3])

    synced_count = 0
    for idx, (fpath, fname, f_idx, mtime, orig_data) in enumerate(target_cache_files):
        target_idx = f_idx if f_idx >= 0 else idx
        local_ann = frame_anns.get(target_idx) or frame_anns.get(target_idx + 1)
        if local_ann:
            raw_objs = local_ann.get("object_list", [])

            formatted_objs = [format_obj_for_unity(obj) for obj in raw_objs]
            orig_data["object_list"] = formatted_objs

            with open(fpath, 'w', encoding='utf-8') as jout:
                json.dump(orig_data, jout, indent=2)

            synced_count += 1

    print(f"\n✨ [SYNC THÀNH CÔNG] Đã ghi đè {synced_count} file nhãn sang Unity Sequence!")
    return True

def find_unity_hwnd():
    hwnds = []
    def enum_windows_callback(hwnd, extra):
        if ctypes.windll.user32.IsWindowVisible(hwnd):
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
            title = buff.value
            if "ADO-anntoation-tool" in title or "ADO" in title:
                hwnds.append((hwnd, title))
        return True

    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    ctypes.windll.user32.EnumWindows(EnumWindowsProc(enum_windows_callback), 0)
    return hwnds[0][0] if hwnds else None

def send_right_arrow(hwnd):
    if hwnd:
        ctypes.windll.user32.PostMessageW(hwnd, WM_KEYDOWN, VK_RIGHT, 0)
        time.sleep(0.05)
        ctypes.windll.user32.PostMessageW(hwnd, WM_KEYUP, VK_RIGHT, 0)
        return True
    return False

def launch_unity_tool():
    possible_paths = [
        os.path.join(BASE_DIR, "ADO-anntoation-tool.exe"),
        r"C:\Program Files\ADO-anntoation-tool\ADO-anntoation-tool.exe",
        os.path.join(os.path.dirname(BASE_DIR), "ADO-anntoation-tool.exe")
    ]
    
    unity_exe = None
    for p in possible_paths:
        if os.path.exists(p):
            unity_exe = p
            break

    if unity_exe:
        print(f"🚀 Tự động khởi chạy Unity Tool: {unity_exe}")
        subprocess.Popen([unity_exe])
    else:
        print("⚠️ Không tìm thấy ADO-anntoation-tool.exe tự động. Vui lòng bật Unity Tool thủ công nếu chưa bật.")

def main():
    print("==========================================================")
    print("    AUTO-SYNC & SEQUENCE DOWNLOAD MONITOR (STANDALONE)")
    print("==========================================================")
    print(f"📂 Thư mục theo dõi: {UNITY_SEQUENCE_DIR}")
    print("----------------------------------------------------------\n")

    os.makedirs(UNITY_SEQUENCE_DIR, exist_ok=True)
    launch_unity_tool()

    last_file_count = -1
    state = "WAITING"
    downloaded_frames = 0
    next_expected_count = 4

    print("⏳ Đang chờ load file từ Unity Tool...")

    while True:
        try:
            time.sleep(0.5)
            if not os.path.exists(UNITY_SEQUENCE_DIR):
                continue

            current_files = [f for f in os.listdir(UNITY_SEQUENCE_DIR) if os.path.isfile(os.path.join(UNITY_SEQUENCE_DIR, f))]
            count = len(current_files)

            if count < last_file_count and last_file_count > 0:
                print("\n⚡ Cập nhật: Unity Tool vừa xóa file cũ -> Đang ở chế độ LOAD FILE MỚI...")
                state = "LOADING"
                downloaded_frames = 0
                next_expected_count = 4

            if count == 0 and state != "LOADING":
                state = "LOADING"
                downloaded_frames = 0
                next_expected_count = 4

            if state == "LOADING":
                hwnd = find_unity_hwnd()

                if downloaded_frames == 0 and count >= 4:
                    downloaded_frames = 1
                    print(f"📥 [Auto-Sync] Đã download Frame 1 (đạt {count} files) -> ➡️ Đang bấm Right Arrow sang Frame 2...")
                    send_right_arrow(hwnd)
                    next_expected_count = 7
                elif downloaded_frames >= 1 and downloaded_frames < 10 and count >= next_expected_count:
                    downloaded_frames += 1
                    print(f"📥 [Auto-Sync] Đã download Frame {downloaded_frames} (đạt {count} files) -> ➡️ Đang bấm Right Arrow sang Frame {downloaded_frames + 1}...")
                    send_right_arrow(hwnd)
                    next_expected_count += 3

                if count >= 31 or downloaded_frames >= 10:
                    time.sleep(2.0)
                    print(f"\n==========================================================")
                    print(f"✅ ĐÃ DOWNLOAD ĐẦY ĐỦ 10 FRAME ({count} FILES)!")
                    print("==========================================================")
                    
                    ans = input("\n👉 Bạn có muốn SYNC toàn bộ nhãn từ Web Tool sang Unity không? (Y/N): ").strip().upper()
                    if ans == 'Y':
                        print("🔄 Đang tiến hành Sync toàn bộ...")
                        sync_cache_moi_to_unity()
                        print("\n==========================================================")
                        print("⚠️ LƯU Ý QUAN TRỌNG: Hãy chọn Frame 1 bằng chuột trên thanh trượt")
                        print("   của Unity Tool (ADO-anntoation-tool) để làm mới hiển thị")
                        print("   và tránh save đè ảnh hiện tại!")
                        print("==========================================================\n")
                    else:
                        print("🚫 Đã bỏ qua thao tác Sync.")
                    
                    state = "COMPLETED"
                    print("\n⏳ Đang chờ lượt load file sequence mới...")

            last_file_count = count

        except KeyboardInterrupt:
            print("\n👋 Đã thoát Auto-Sync Monitor.")
            break
        except Exception as e:
            time.sleep(1.0)

if __name__ == '__main__':
    main()
