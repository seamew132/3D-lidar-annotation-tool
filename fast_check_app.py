import os
import sys
import json
import glob
import io
import shutil
import re
import webbrowser
import threading
import time
from flask import Flask, jsonify, send_file, request, render_template_string

IS_FROZEN = getattr(sys, 'frozen', False)
if IS_FROZEN:
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

LOCAL_CACHE_DIR = os.path.join(BASE_DIR, "cache")
LOCAL_ANNOTATIONS_DIR = os.path.join(LOCAL_CACHE_DIR, "annotations")
LOCAL_IMAGES_DIR = os.path.join(LOCAL_CACHE_DIR, "images")

USER_PROFILE = os.environ.get("USERPROFILE") or os.path.expanduser("~")
UNITY_CACHE_DIR = os.path.join(USER_PROFILE, "AppData", "LocalLow", "Alchera Inc", "ADO-anntoation-tool", "sequence")

app = Flask(__name__)

def get_sequence_data():
    """Reads sequence annotations and calibration strictly READ-ONLY."""
    frames = []
    calibration = None

    # 1. Try reading from web_app/cache first
    if os.path.exists(LOCAL_ANNOTATIONS_DIR):
        cal_path = os.path.join(LOCAL_CACHE_DIR, "calibration.json")
        if os.path.exists(cal_path):
            try:
                with open(cal_path, 'r', encoding='utf-8') as f:
                    calibration = json.load(f)
            except Exception:
                pass

        ann_files = sorted(glob.glob(os.path.join(LOCAL_ANNOTATIONS_DIR, "frame_*.json")))
        for idx, ann_path in enumerate(ann_files):
            try:
                with open(ann_path, 'r', encoding='utf-8') as f:
                    ann_data = json.load(f)
            except Exception:
                ann_data = {"object_list": []}

            # Parse true 1-based frame number from filename (e.g. frame_0001.json -> 1)
            m = re.search(r'frame_(\d+)', os.path.basename(ann_path))
            frame_num = int(m.group(1)) if m else (idx + 1)
            img_name = f"frame_{frame_num:04d}.png"
            pcd_name = f"frame_{frame_num:04d}.pcd"
            img_path = os.path.join(LOCAL_IMAGES_DIR, img_name)

            frames.append({
                "index": idx,
                "frame_number": frame_num,
                "pcd_filename": pcd_name,
                "img_filename": img_name,
                "img_path": img_path if os.path.exists(img_path) else None,
                "annotation": ann_data
            })

    # 2. If local cache is empty, read directly from Unity original sequence cache
    if not frames and os.path.exists(UNITY_CACHE_DIR):
        files = os.listdir(UNITY_CACHE_DIR)
        ann_entries = []
        img_map = {}

        for fname in files:
            fpath = os.path.join(UNITY_CACHE_DIR, fname)
            if not os.path.isfile(fpath):
                continue
            try:
                with open(fpath, 'rb') as f:
                    header = f.read(100)
                if header.startswith(b"{") or header.startswith(b"["):
                    with open(fpath, 'r', encoding='utf-8') as jf:
                        data = json.load(jf)
                    if "cameras" in data and "lidar_to_vehicle" in data:
                        calibration = data
                    elif "object_list" in data:
                        pcd_fn = data.get("pcd_filename", "")
                        m = re.search(r'(\d+)', pcd_fn)
                        frame_idx = int(m.group(1)) if m else len(ann_entries) + 1
                        ann_entries.append({'frame_idx': frame_idx, 'data': data, 'fname': fname})
                elif header.startswith(b"\x89PNG") or header.startswith(b"\xff\xd8"):
                    mtime = os.path.getmtime(fpath)
                    img_map[fname] = (fpath, mtime)
            except Exception:
                pass

        ann_entries.sort(key=lambda x: x['frame_idx'])
        sorted_imgs = sorted(img_map.items(), key=lambda x: x[1][1])

        for idx, entry in enumerate(ann_entries):
            frame_num = entry['frame_idx']
            img_name = f"frame_{frame_num:04d}.png"
            pcd_name = f"frame_{frame_num:04d}.pcd"
            img_path = sorted_imgs[idx][1][0] if idx < len(sorted_imgs) else None
            frames.append({
                "index": idx,
                "frame_number": frame_num,
                "pcd_filename": pcd_name,
                "img_filename": img_name,
                "img_path": img_path,
                "annotation": entry['data']
            })

    return frames, calibration

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ADO Standalone 3D FastCheck Viewer</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; user-select: none; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0b0f19; color: #f8fafc; height: 100vh; display: flex; flex-direction: column; overflow: hidden; }
        header { background: #1e293b; padding: 10px 20px; border-bottom: 1px solid #334155; display: flex; align-items: center; justify-content: space-between; flex-shrink: 0; }
        .title-box { display: flex; align-items: center; gap: 10px; }
        .title { font-size: 17px; font-weight: 700; color: #38bdf8; }
        .badge { background: #0284c7; color: #fff; font-size: 11px; padding: 3px 8px; border-radius: 4px; font-weight: 600; }
        .search-controls { display: flex; align-items: center; gap: 10px; }
        input[type="number"], input[type="text"] { background: #0f172a; border: 1px solid #38bdf8; color: #fff; padding: 6px 12px; border-radius: 6px; font-size: 14px; width: 180px; outline: none; }
        input:focus { border-color: #0ea5e9; box-shadow: 0 0 0 2px rgba(14, 165, 233, 0.3); }
        .btn { background: #0284c7; color: #fff; border: none; padding: 6px 14px; border-radius: 6px; font-size: 13px; font-weight: 600; cursor: pointer; transition: background 0.15s; }
        .btn:hover { background: #0369a1; }
        .nav-bar { background: #182234; padding: 8px 20px; border-bottom: 1px solid #334155; display: flex; align-items: center; justify-content: space-between; flex-shrink: 0; }
        .nav-group { display: flex; align-items: center; gap: 12px; }
        .nav-btn { background: #334155; color: #fff; border: 1px solid #475569; padding: 6px 16px; border-radius: 6px; font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.15s; display: flex; align-items: center; gap: 6px; }
        .nav-btn:hover { background: #0284c7; border-color: #38bdf8; }
        .nav-status { font-size: 14px; font-weight: 600; color: #e2e8f0; }
        .zoom-controls { display: flex; align-items: center; gap: 12px; font-size: 12px; color: #94a3b8; }
        .toggle-label { display: flex; align-items: center; gap: 6px; cursor: pointer; color: #38bdf8; font-weight: 600; }
        .toggle-label input { accent-color: #0284c7; cursor: pointer; }
        main { flex: 1; position: relative; display: flex; align-items: center; justify-content: center; background: #000; overflow: hidden; }
        #camera-canvas { display: block; width: 100%; height: 100%; cursor: grab; }
        #camera-canvas:active { cursor: grabbing; }
        
        /* Info spec overlay matching Unity Tool format */
        #spec-overlay { position: absolute; top: 16px; left: 16px; z-index: 100; font-family: monospace; font-size: 12px; color: #ffffff; background: rgba(0, 0, 0, 0.85); padding: 10px 14px; border-radius: 6px; pointer-events: none; line-height: 1.6; text-shadow: 1px 1px 2px #000; border: 1px solid rgba(255,255,255,0.2); }
        .overlay-title { font-weight: bold; color: #f472b6; margin-bottom: 2px; }
        .empty-msg { text-align: center; color: #94a3b8; font-size: 16px; line-height: 1.8; }
    </style>
</head>
<body>
    <header>
        <div class="title-box">
            <span class="title">🔍 Standalone 3D FastCheck Viewer</span>
            <span class="badge" id="sequence-badge">Sequence: 0 Frames</span>
        </div>
        <div class="search-controls">
            <input type="number" id="id-input" placeholder="Nhập Tracking ID..." min="0">
            <button id="btn-search" class="btn">🔍 FastCheck ID</button>
        </div>
    </header>

    <div class="nav-bar">
        <div class="nav-group">
            <button id="btn-prev" class="nav-btn" title="Chuyển tới Frame trước (Phím ◄ hoặc A)">◀ Frame trước (◄)</button>
            <button id="btn-next" class="nav-btn" title="Chuyển tới Frame tiếp (Phím ► hoặc D)">Frame sau (►) ▶</button>
            <div class="zoom-controls">
                <label class="toggle-label" title="Tự động di chuyển ảnh để Box ID luôn nằm chính giữa khung hình">
                    <input type="checkbox" id="chk-center-box" checked> 🎯 Căn giữa Box
                </label>
                <span id="zoom-info" style="color: #e2e8f0; font-weight: 600;">Zoom: 100%</span>
                <button id="btn-reset-zoom" class="btn" style="padding: 3px 8px; font-size: 11px; background: #475569;">↩ Reset Zoom</button>
            </div>
        </div>
        <div class="nav-status" id="nav-status">Vui lòng nhập Tracking ID để bắt đầu xem</div>
    </div>

    <main id="main-viewport">
        <div id="spec-overlay" style="display: none;">
            <div class="overlay-title">Camera target - Channel 1</div>
            <div id="info-cam-dim">- dimension: (W: 0.00, H: 0.00, L: 0.00)</div>
            <div id="info-cam-loc">- location: (x: 0.00, y: 0.00, z: 0.00)</div>
            <div id="info-cam-ori">- orientation: (I - Z: 0.00, X: 0.00, Y: 0.00)</div>
            <div id="info-cam-bbox">- 2D BBox: (W: 0.00, H: 0.00)</div>
        </div>
        <div class="empty-msg" id="empty-msg">
            👋 Nhập <b>Tracking ID</b> ở trên (ví dụ: <code>1</code> hoặc <code>50</code>) và bấm <b>FastCheck ID</b>!<br>
            Sử dụng phím mũi tên <b>◄ / ►</b> trên bàn phím để chuyển qua các Frame chứa ID đó.<br>
            Cuộn chuột trên ảnh để <b>Zoom In / Zoom Out</b> (Box sẽ luôn nằm ở chính giữa khung hình).
        </div>
        <canvas id="camera-canvas" style="display: none;"></canvas>
    </main>

    <script>
        let calibrationData = null;
        let matchedFrames = [];
        let currentMatchIdx = 0;
        let currentTargetId = null;

        // Viewport Zoom & Centering State
        let imgZoom = 1.0;
        let loadedImage = null;

        // 3D LiDAR to 2D Camera Image Projection Engine (Kannala-Brandt Fisheye Model)
        class CameraProjection {
            constructor(calib) {
                this.calibration = calib;
                this.camera = calib && calib.cameras ? calib.cameras[0] : null;
            }

            // Projects a 3D point in LiDAR space (x, y, z) into 2D camera image coordinates (u, v)
            projectPoint(point3d) {
                if (!this.camera || !this.camera.lidar_to_camera) return null;
                const l2c = this.camera.lidar_to_camera;
                const R = l2c.rotation;
                const T = l2c.translation;
                if (!R || !T) return null;

                // 1. Transform LiDAR point (X,Y,Z) to Camera coordinate (Xc, Yc, Zc)
                const xc = R[0]*point3d.x + R[1]*point3d.y + R[2]*point3d.z + T[0];
                const yc = R[3]*point3d.x + R[4]*point3d.y + R[5]*point3d.z + T[1];
                const zc = R[6]*point3d.x + R[7]*point3d.y + R[8]*point3d.z + T[2];

                if (zc <= 0.1) return null;

                // 2. Normalized camera coordinates
                const x_norm = xc / zc;
                const y_norm = yc / zc;
                const r = Math.sqrt(x_norm * x_norm + y_norm * y_norm);
                let scale = 1.0;

                // 3. Apply Kannala-Brandt Fisheye Lens Distortion (K1..K5)
                if (r > 1e-8) {
                    const dist = this.camera.intrinsic ? this.camera.intrinsic.distortion : null;
                    const k1 = dist ? (dist.K1 !== undefined ? dist.K1 : 1.0) : 1.0;
                    const k2 = dist ? (dist.K2 || 0) : 0;
                    const k3 = dist ? (dist.K3 || 0) : 0;
                    const k4 = dist ? (dist.K4 || 0) : 0;
                    const k5 = dist ? (dist.K5 || 0) : 0;

                    const theta = Math.atan(r);
                    const th2 = theta * theta;
                    const th4 = th2 * th2;
                    const th6 = th4 * th2;
                    const th8 = th4 * th4;
                    const theta_d = theta * (k1 + k2*th2 + k3*th4 + k4*th6 + k5*th8);
                    scale = theta_d / r;
                }

                const x_dist = x_norm * scale;
                const y_dist = y_norm * scale;

                // 4. Convert to pixel coordinates (u, v) using intrinsics
                const intrinsic = this.camera.intrinsic || {};
                const Mu = intrinsic.Mu || 2473.151047;
                const Mv = intrinsic.Mv || 2472.250821;
                const U0 = intrinsic.U0 || 1926.315973;
                const V0 = intrinsic.V0 || 1094.351564;

                const u = Mu * x_dist + U0;
                const v = Mv * y_dist + V0;

                return { u: u, v: v, z: zc };
            }

            // Calculates 8 corners of a 3D cuboid (matching web_app projection.js exactly)
            getCuboidCorners(cuboid) {
                const loc = cuboid.pose_in_lidar ? cuboid.pose_in_lidar.location : [0, 0, 0];
                const w = cuboid.width || 1.8;
                const l = cuboid.length || 4.0;
                const h = cuboid.height || 1.5;

                let roll = 0, pitch = 0, yaw = 0;
                if (cuboid.pose_in_lidar_target && cuboid.pose_in_lidar_target.orientation) {
                    yaw = cuboid.pose_in_lidar_target.orientation[0] || 0;
                    pitch = cuboid.pose_in_lidar_target.orientation[1] || 0;
                    roll = cuboid.pose_in_lidar_target.orientation[2] || 0;
                } else if (cuboid.pose_in_lidar && cuboid.pose_in_lidar.orientation) {
                    yaw = cuboid.pose_in_lidar.orientation[0] || 0;
                    pitch = cuboid.pose_in_lidar.orientation[1] || 0;
                    roll = cuboid.pose_in_lidar.orientation[2] || 0;
                }

                // Bottom center is at loc[2] (z = 0 for bottom, z = h for top)
                const localCorners = [
                    {x:  l/2, y:  w/2, z: 0},
                    {x:  l/2, y: -w/2, z: 0},
                    {x: -l/2, y: -w/2, z: 0},
                    {x: -l/2, y:  w/2, z: 0},
                    {x:  l/2, y:  w/2, z: h},
                    {x:  l/2, y: -w/2, z: h},
                    {x: -l/2, y: -w/2, z: h},
                    {x: -l/2, y:  w/2, z: h}
                ];

                const cz = Math.cos(yaw), sz = Math.sin(yaw);
                const cy = Math.cos(pitch), sy = Math.sin(pitch);
                const cx = Math.cos(roll), sx = Math.sin(roll);

                // Euler ZYX rotation matrix
                const r00 = cz*cy, r01 = cz*sy*sx - sz*cx, r02 = cz*sy*cx + sz*sx;
                const r10 = sz*cy, r11 = sz*sy*sx + cz*cx, r12 = sz*sy*cx - cz*sx;
                const r20 = -sy,   r21 = cy*sx,          r22 = cy*cx;

                const worldCorners = localCorners.map(pt => ({
                    x: loc[0] + (r00*pt.x + r01*pt.y + r02*pt.z),
                    y: loc[1] + (r10*pt.x + r11*pt.y + r12*pt.z),
                    z: loc[2] + (r20*pt.x + r21*pt.y + r22*pt.z)
                }));

                return worldCorners;
            }

            // Projects 3D wireframe corners of a cuboid into 2D camera image
            projectCuboidWireframe(cuboid) {
                const corners3d = this.getCuboidCorners(cuboid);
                const projectedCorners = corners3d.map(pt => this.projectPoint(pt));

                const edges = [
                    [0, 1], [1, 2], [2, 3], [3, 0], // Bottom face
                    [4, 5], [5, 6], [6, 7], [7, 4], // Top face
                    [0, 4], [1, 5], [2, 6], [3, 7]  // Vertical edges
                ];

                return {
                    corners: projectedCorners,
                    edges: edges
                };
            }
        }

        function abbreviateTag(category, subclass) {
            const catMap = {
                'PEDESTRIAN': 'PED', 'PERSON': 'PER', 'ANIMAL': 'ANI', 'VEHICLE': 'CAR',
                'MOTORCYCLE': 'MOT', 'BICYCLE': 'BIC', 'CYCLE': 'CYC', 'MOBILITY': 'MOB',
                'CART': 'CRT', 'PARKING_OBSTACLE': 'OBS'
            };
            const subMap = {
                'adult': 'Adu', 'child': 'Chi', 'rider': 'Rid', 'seated': 'Sea',
                'adult_pedestrian': 'Ped', 'child_pedestrian': 'Chd',
                'car': 'Car', 'van': 'Van', 'truck': 'Tru', 'trailer': 'Tra', 'bus': 'Bus',
                'motorcycle': 'Mot', 'scooter': 'Sco', 'bicycle': 'Bic',
                'no_park_sign_circle': 'Sign-C', 'no_park_sign_square': 'Sign-S',
                'No_parking_sign': 'Sign', 'no_parking_sign': 'Sign',
                'stopper': 'Stp', 'stopper_long': 'Stp-L', 'cone': 'Cone',
                'bollard': 'Bld', 'bollard_u': 'Bld-U', 'pillar': 'Pil', 'pillar_circle': 'Pil-C',
                'speedbump': 'Bmp', 'parking_gate_body': 'Gate'
            };
            const catAbbr = catMap[category] || (category ? category.substring(0, 3).toUpperCase() : 'PED');
            const subAbbr = subMap[subclass] || (subclass ? (subclass.charAt(0).toUpperCase() + subclass.substring(1, 3).toLowerCase()) : 'Adu');
            return `${catAbbr}/${subAbbr}`;
        }

        async function init() {
            const res = await fetch('/api/summary');
            const data = await res.json();
            calibrationData = data.calibration;
            document.getElementById('sequence-badge').innerText = `Sequence: ${data.total_frames} Frames`;

            document.getElementById('btn-search').onclick = () => performFastCheck();
            document.getElementById('id-input').onkeydown = (e) => {
                if (e.key === 'Enter') performFastCheck();
            };

            document.getElementById('btn-prev').onclick = () => prevFrame();
            document.getElementById('btn-next').onclick = () => nextFrame();

            document.getElementById('btn-reset-zoom').onclick = () => {
                imgZoom = 1.0;
                document.getElementById('zoom-info').innerText = `Zoom: 100%`;
                renderCurrentFrame();
            };

            document.getElementById('chk-center-box').onchange = () => renderCurrentFrame();

            const canvas = document.getElementById('camera-canvas');
            canvas.addEventListener('wheel', (e) => {
                e.preventDefault();
                const zoomFactor = e.deltaY < 0 ? 1.15 : 0.85;
                imgZoom = Math.max(0.5, Math.min(10.0, imgZoom * zoomFactor));
                document.getElementById('zoom-info').innerText = `Zoom: ${Math.round(imgZoom * 100)}%`;
                renderCurrentFrame();
            });

            // Keyboard Arrow Key Navigation (Left / Right Arrows & A / D Keys)
            window.addEventListener('keydown', (e) => {
                if (document.activeElement && document.activeElement.tagName === 'INPUT') return;
                if (e.key === 'ArrowLeft' || e.key === 'a' || e.key === 'A') {
                    prevFrame();
                } else if (e.key === 'ArrowRight' || e.key === 'd' || e.key === 'D') {
                    nextFrame();
                }
            });

            window.addEventListener('resize', () => renderCurrentFrame());
        }

        async function performFastCheck() {
            const inputVal = parseInt(document.getElementById('id-input').value);
            if (isNaN(inputVal)) return;

            currentTargetId = inputVal;
            const res = await fetch(`/api/id_frames/${currentTargetId}`);
            const data = await res.json();

            matchedFrames = data.frames || [];
            currentMatchIdx = 0;

            if (matchedFrames.length === 0) {
                document.getElementById('empty-msg').style.display = 'block';
                document.getElementById('empty-msg').innerHTML = `❌ Không tìm thấy Frame nào chứa Tracking ID <b>#${currentTargetId}</b>!`;
                document.getElementById('camera-canvas').style.display = 'none';
                document.getElementById('spec-overlay').style.display = 'none';
                document.getElementById('nav-status').innerText = `Không tìm thấy ID #${currentTargetId}`;
                return;
            }

            renderCurrentFrame();
        }

        function prevFrame() {
            if (matchedFrames.length === 0) return;
            currentMatchIdx = (currentMatchIdx - 1 + matchedFrames.length) % matchedFrames.length;
            renderCurrentFrame();
        }

        function nextFrame() {
            if (matchedFrames.length === 0) return;
            currentMatchIdx = (currentMatchIdx + 1) % matchedFrames.length;
            renderCurrentFrame();
        }

        function renderCurrentFrame() {
            if (matchedFrames.length === 0) return;
            const item = matchedFrames[currentMatchIdx];

            document.getElementById('empty-msg').style.display = 'none';
            const canvas = document.getElementById('camera-canvas');
            canvas.style.display = 'block';

            document.getElementById('nav-status').innerHTML = `Frame <b>${item.frame_number || item.frame_index}</b> (${currentMatchIdx + 1}/${matchedFrames.length} chứa ID #${currentTargetId})`;

            const viewport = document.getElementById('main-viewport');
            const viewW = viewport.clientWidth || 1000;
            const viewH = viewport.clientHeight || 700;
            canvas.width = viewW;
            canvas.height = viewH;

            const img = new Image();
            img.src = `/api/frame/${item.frame_number || item.frame_index}/image`;

            img.onload = () => {
                const imgW = img.naturalWidth || 1920;
                const imgH = img.naturalHeight || 1080;
                const ctx = canvas.getContext('2d');

                ctx.clearRect(0, 0, viewW, viewH);
                ctx.fillStyle = '#000000';
                ctx.fillRect(0, 0, viewW, viewH);

                const cuboid = item.cuboid;
                const camObj = (cuboid.cameras && cuboid.cameras.length > 0) ? cuboid.cameras[0] : null;

                // Project 3D Wireframe Cuboid
                const projection = new CameraProjection(calibrationData);
                const proj = projection.projectCuboidWireframe(cuboid);

                // Calculate center point of target box in 2D image coordinates
                let boxCenterU = imgW / 2;
                let boxCenterV = imgH / 2;

                if (proj && proj.corners) {
                    const validCorners = proj.corners.filter(pt => pt !== null);
                    if (validCorners.length > 0) {
                        boxCenterU = validCorners.reduce((sum, pt) => sum + pt.u, 0) / validCorners.length;
                        boxCenterV = validCorners.reduce((sum, pt) => sum + pt.v, 0) / validCorners.length;
                    }
                }

                // Compute scaling and offsets
                const baseScale = Math.min(viewW / imgW, viewH / imgH);
                const scale = baseScale * imgZoom;

                const isCenterBox = document.getElementById('chk-center-box').checked;
                let drawX = 0, drawY = 0;

                if (isCenterBox) {
                    // Position image so that (boxCenterU, boxCenterV) sits exactly at canvas center (viewW/2, viewH/2)
                    drawX = (viewW / 2) - (boxCenterU * scale);
                    drawY = (viewH / 2) - (boxCenterV * scale);
                } else {
                    // Default centering of whole image
                    const drawW = imgW * scale;
                    const drawH = imgH * scale;
                    drawX = (viewW - drawW) / 2;
                    drawY = (viewH - drawH) / 2;
                }

                // Draw background 2D camera image
                ctx.drawImage(img, drawX, drawY, imgW * scale, imgH * scale);

                // Update Info Spec Overlay
                const overlay = document.getElementById('spec-overlay');
                overlay.style.display = 'block';

                let camW = 0, camH = 0, camL = 0;
                let camX = 0, camY = 0, camZ = 0;
                let camOriX = 0, camOriY = 0, camOriZ = 0;
                let bboxW = 0, bboxH = 0;

                if (camObj) {
                    if (camObj.bbox && camObj.bbox.length === 4) {
                        bboxW = Math.abs(camObj.bbox[2] - camObj.bbox[0]);
                        bboxH = Math.abs(camObj.bbox[3] - camObj.bbox[1]);
                    }
                    if (camObj.pose_in_camera && camObj.pose_in_camera.location) {
                        camX = camObj.pose_in_camera.location[0] || 0;
                        camY = camObj.pose_in_camera.location[1] || 0;
                        camZ = camObj.pose_in_camera.location[2] || 0;
                    }
                    if (camObj.pose_in_camera_target && camObj.pose_in_camera_target.orientation) {
                        camOriZ = camObj.pose_in_camera_target.orientation[0] || 0;
                        camOriX = camObj.pose_in_camera_target.orientation[1] || 0;
                        camOriY = camObj.pose_in_camera_target.orientation[2] || 0;
                    }
                    camW = cuboid.width || 0;
                    camH = cuboid.height || 0;
                    camL = cuboid.length || 0;
                }

                document.getElementById('info-cam-dim').innerText = `- dimension: (W: ${camW.toFixed(6)}, H: ${camH.toFixed(6)}, L: ${camL.toFixed(6)})`;
                document.getElementById('info-cam-loc').innerText = `- location: (x: ${camX.toFixed(6)}, y: ${camY.toFixed(6)}, z: ${camZ.toFixed(6)})`;
                document.getElementById('info-cam-ori').innerText = `- orientation: (I - Z: ${camOriZ.toFixed(6)}, X: ${camOriX.toFixed(6)}, Y: ${camOriY.toFixed(6)})`;
                document.getElementById('info-cam-bbox').innerText = `- 2D BBox: (W: ${bboxW.toFixed(4)}, H: ${bboxH.toFixed(4)})`;

                // Draw 3D Wireframe Cuboid (in Thick Neon Cyan matching Unity tool)
                if (proj && proj.corners) {
                    const canvasCorners = proj.corners.map(pt => {
                        if (!pt) return null;
                        return {
                            x: drawX + pt.u * scale,
                            y: drawY + pt.v * scale
                        };
                    });

                    ctx.lineWidth = Math.max(2, 4 * Math.min(imgZoom, 2.0));
                    ctx.strokeStyle = '#00ffff';

                    proj.edges.forEach(([i1, i2]) => {
                        const pt1 = canvasCorners[i1];
                        const pt2 = canvasCorners[i2];
                        if (pt1 && pt2) {
                            ctx.beginPath();
                            ctx.moveTo(pt1.x, pt1.y);
                            ctx.lineTo(pt2.x, pt2.y);
                            ctx.stroke();
                        }
                    });

                    // Draw ID & Tag Badge
                    const validCanvasCorners = canvasCorners.filter(pt => pt !== null);
                    if (validCanvasCorners.length > 0) {
                        const minX = Math.min(...validCanvasCorners.map(p => p.x));
                        const minY = Math.min(...validCanvasCorners.map(p => p.y));
                        const tag = abbreviateTag(cuboid.category, cuboid.sub_class || cuboid.subclass);

                        ctx.fillStyle = '#00ffff';
                        ctx.font = 'bold 20px monospace';
                        ctx.fillText(`#${currentTargetId} ${tag}`, minX, Math.max(30, minY - 8));
                    }
                }
            };
        }

        window.onload = init;
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/summary')
def api_summary():
    frames, calibration = get_sequence_data()
    return jsonify({
        "total_frames": len(frames),
        "calibration": calibration
    })

@app.route('/api/id_frames/<int:tracking_id>')
def api_id_frames(tracking_id):
    frames, calibration = get_sequence_data()
    result = []

    for f in frames:
        cuboids = f["annotation"].get("object_list", [])
        cuboid = next((c for c in cuboids if c.get("tracking_id") == tracking_id), None)
        if cuboid:
            result.append({
                "frame_index": f.get("frame_number", f["index"]),
                "frame_number": f.get("frame_number", f["index"]),
                "img_filename": f["img_filename"],
                "cuboid": cuboid
            })

    return jsonify({
        "tracking_id": tracking_id,
        "frames": result,
        "calibration": calibration
    })

@app.route('/api/frame/<int:frame_idx>/image')
def api_frame_image(frame_idx):
    frames, _ = get_sequence_data()
    # Find matching frame by 1-based frame_number first, fallback to 0-based index
    target_frame = next((f for f in frames if f.get("frame_number") == frame_idx), None)
    if not target_frame and 0 <= frame_idx < len(frames):
        target_frame = frames[frame_idx]

    if not target_frame:
        return "Invalid frame index", 400

    img_path = target_frame.get("img_path")
    if not img_path or not os.path.exists(img_path):
        return "Image not found", 404

    return send_file(img_path, mimetype='image/png')

def auto_open_browser():
    time.sleep(1.2)
    try:
        webbrowser.open("http://localhost:5050/")
    except Exception:
        pass

if __name__ == '__main__':
    print("=====================================================")
    print("🚀 ADO Standalone 3D FastCheck Viewer (Read-Only)")
    print("Sẵn sàng phục vụ tại: http://localhost:5050/")
    print("=====================================================")
    app.run(host='0.0.0.0', port=5050, debug=False)
