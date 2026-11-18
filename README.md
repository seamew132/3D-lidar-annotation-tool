# 3D LiDAR Object Detection — Web Annotation Tool & System Architecture

Comprehensive technical documentation covering system architecture, cache management, data backup pipelines, bidirectional synchronization, and developer guidelines for the 3D LiDAR Web Annotation Suite.

---

## 📑 Table of Contents
1. [System Overview](#1-system-overview)
2. [Directory Structure](#2-directory-structure)
3. [Cache Architecture & Data Integrity](#3-cache-architecture--data-integrity)
   - [3.1. External Host Client Cache](#31-external-host-client-cache)
   - [3.2. Local Web Tool Cache](#32-local-web-tool-cache)
   - [3.3. Invariant Read & Write Rules](#33-invariant-read--write-rules)
4. [Backup & Cloud Synchronization](#4-backup--cloud-synchronization)
5. [Bidirectional Host Synchronization](#5-bidirectional-host-synchronization)
6. [Core Web Interface Features](#6-core-web-interface-features)
   - [6.1. 3D LiDAR Viewport & 2D Camera Projection](#61-3d-lidar-viewport--2d-camera-projection)
   - [6.2. Orthogonal Cross-Section Sub-Views](#62-orthogonal-cross-section-sub-views)
   - [6.3. 2D Top-Down Bounding Box Editor](#63-2d-top-down-bounding-box-editor)
   - [6.4. Kinematic Auto-Box Trajectory Interpolation](#64-kinematic-auto-box-trajectory-interpolation)
   - [6.5. Serverless Cloud Sync via Google Apps Script](#65-serverless-cloud-sync-via-google-apps-script)
7. [Standard Keyboard Shortcuts (Hotkeys)](#7-standard-keyboard-shortcuts-hotkeys)
8. [Installation & Quick Start](#8-installation--quick-start)
9. [Developer & AI Maintainer Guidelines](#9-developer--ai-maintainer-guidelines)

---

## 1. System Overview

This project is a high-throughput 3D spatial annotation suite designed for Autonomous Driving Object Detection (3D-OD) datasets. It bridges a desktop sequence loader with a lightweight, hardware-accelerated web workspace:

1. **External Host Client**: Desktop client responsible for fetching raw multi-frame sensor sequences from remote storage into local disk cache.
2. **Web Annotation Workspace (`localhost:5000`)**: A lightweight web application powered by Python Flask, Three.js (WebGL), and HTML5 Canvas. Built to eliminate heavy engine overhead, it features real-time 3D-to-2D bounding box projection, orthogonal cross-section slicing, kinematic trajectory interpolation (Auto-Box), and serverless cloud backup.
3. **FastCheck QA Viewer (`localhost:5050`)**: A standalone read-only Flask server designed for rapid multi-frame (10-frame) quality assurance and spatial consistency inspection.

---

## 2. Directory Structure

```text
<PROJECT_ROOT>/
├── install.bat                        # Automated Python dependency installer (flask, numpy, requests)
├── start_web_tool.bat                 # Concurrent launcher for Main Tool (5000) & FastCheck (5050)
├── fast_check_app.py                  # Standalone Flask server for FastCheck 3D QA Viewer (5050)
├── cache/                             # PRIMARY LOCAL CACHE DIRECTORY
│   ├── annotations/                   # Annotated cuboids: frame_0001.json -> frame_0010.json
│   ├── images/                        # Synchronized camera frames: frame_0001.png -> frame_0010.png
│   ├── pcd/                           # LiDAR point clouds: frame_0001.pcd -> frame_0010.pcd
│   └── calibration.json               # Intrinsic/extrinsic LiDAR-to-Camera-to-Vehicle matrices
└── web_app/
    ├── server.py                      # Main Flask backend (I/O, coordinate transforms, Auto-Box, sync)
    ├── auto_box.py                    # Kinematic linear/angular velocity trajectory predictor
    ├── drive_sync.py                  # HTTP client communicating with Google Apps Script Web App
    ├── drive_config.json              # Configuration storing Web App endpoint & auto-sync flags
    ├── sync_to_unity.py               # Bidirectional exporter syncing labels back to host client
    ├── google_apps_script_template.js # Serverless backend script for Google Drive integration
    └── static/
        ├── index.html                 # Main Web UI layout
        ├── css/style.css              # Styling for viewports and non-blocking floating windows
        └── js/
            ├── app.js                 # Core state machine, hotkey bindings, and API controller
            ├── pointcloud.js          # Three.js WebGL renderer, orthogonal slicing, cuboid gizmos
            ├── projection.js          # 3D LiDAR-to-2D camera pixel projection math
            ├── OrbitControls.js       # 3D camera navigation controller
            └── three.min.js           # Three.js WebGL library
```

---

## 3. Cache Architecture & Data Integrity

### 3.1. External Host Client Cache
* **Default Path**: `<USER_LOCAL_APPDATA>/<HOST_CLIENT_DIR>/sequence`
* **31-File Sequence Standard**:
  A complete 10-frame sequence consists of exactly **31 files**:
  * 10 Point Cloud files (`.pcd`): `0000_*.pcd` through `0009_*.pcd`
  * 10 Camera Image files (`.png`): `0000_*.png` through `0009_*.png`
  * 10 Annotation files (`.json`): `0000_*.json` through `0009_*.json`
  * 1 Calibration file: `calibration.json`
* **Index Mapping (0-based vs. 1-based)**:
  * The host desktop client uses **0-based indexing** (`0000` to `0009`).
  * The Web Annotation Tool presents **1-based indexing** (**Frame 1 to Frame 10**) for intuitive human labeling:
    * Web Frame 1 $\leftrightarrow$ Host `0000` $\leftrightarrow$ Web Cache `frame_0001`
    * Web Frame 10 $\leftrightarrow$ Host `0009` $\leftrightarrow$ Web Cache `frame_0010`
* **Integrity Verification Guard**:
  When loading from the host cache, the backend verifies the file count in `sequence`:
  * If $\ge 31$ files: Loads immediately into memory.
  * If $< 31$ files: Triggers a confirmation warning modal (`modal-unity-cache-confirm`) to prevent partial sequence corruption.

### 3.2. Local Web Tool Cache
* **Directory Path**: `./cache/`
* Stores normalized frame assets (`annotations/`, `images/`, `pcd/`, and `calibration.json`) decoupled from the external client to prevent accidental overwrites.

### 3.3. Invariant Read & Write Rules
> [!IMPORTANT]
> **CRITICAL DATA SAFETY RULE**:
> Loading data from the external host cache **MUST NEVER OVERWRITE** `./cache/annotations/`. External sequence data is loaded strictly into server RAM for previewing.
> 
> **Local Web Cache (`./cache/annotations/`) is ONLY written when triggered by explicit user actions**:
> 1. Clicking the **Save** button on the toolbar.
> 2. Pressing **`Ctrl + S`**.
> 3. Navigating between frames via **Next / Prev** buttons (or hotkeys `A` / `D`, Arrow keys).
> 4. Directly selecting frame indices **1 through 10**.

---

## 4. Backup & Cloud Synchronization

### 4.1. Local Snapshots
* **Raw Sequence Backup**: Archive the host `sequence` directory (`.zip`) immediately after downloading a new sequence.
* **Annotation Work Backup**: Back up `./cache/` periodically to preserve labeled cuboid states.

### 4.2. Cloud Synchronization (Google Drive via Apps Script)
1. Click **`☁️ Apps Script`** next to the Front View viewport to open the non-blocking floating sync panel.
2. Paste your deployed Google Apps Script Web App URL (ending in `/exec`) and click `🔒 Save`.
3. **Upload to Cloud**:
   * **`☁️ Upload All Frame`**: Pushes all 10 annotation JSON files to Google Drive.
   * **`📤 Upload Current Frame`**: Pushes only the active frame's JSON file.
   * **`Auto-sync Frame` Toggle**: Automatically triggers a background upload thread whenever `Save` or `Ctrl + S` is executed without blocking the UI.
   * *Idempotent Overwrite*: Existing files with matching names on Google Drive are updated in-place to prevent duplicate clutter.
4. **Restore from Cloud**:
   * **`📥 Download All Frame`** / **`📥 Download Current Frame`**: Pulls remote JSON annotations into `./cache/annotations/` and refreshes the active viewport.

---

## 5. Bidirectional Host Synchronization

Once annotation is completed in the Web Tool, labels can be exported back to the external desktop client format:
1. Click **`🔄 Sync to Host`** in the top header bar.
2. `sync_to_unity.py` executes the following pipeline:
   * Reads `./cache/annotations/frame_0001.json` through `frame_0010.json`.
   * Maps each frame back to its corresponding 0-based host JSON file (`0000_*.json` – `0009_*.json`).
   * Preserves original sensor headers, camera names, and calibration matrices while updating the `object_list` array with refined 3D dimensions, coordinates, and yaw angles.

---

## 6. Core Web Interface Features

### 6.1. 3D LiDAR Viewport & 2D Camera Projection
* **3D LiDAR Viewport**: Renders tens of thousands of points via WebGL `BufferGeometry` with smooth `OrbitControls` (rotate, zoom, pan). Includes real-time controls for point brightness, contrast, hue shift, point size, and $Z$-axis ceiling filtering.
* **2D Camera Viewport**: Projects 3D LiDAR cuboids onto the 2D camera image plane in real time using intrinsic/extrinsic calibration matrices.
  * Supports scroll-wheel zooming, left-click panning, and direct click-to-select on projected 2D boxes.
  * **Auto-Focus (`chk-id-check`)**: Automatically centers and zooms the 2D camera viewport onto the currently selected Object ID.

### 6.2. Orthogonal Cross-Section Sub-Views
Three dedicated orthographic slice viewports isolate point clouds around the selected cuboid for centimeter-level precision:
* **Top View**: $XY$-plane projection (bird's-eye view).
* **Side View**: $ZY$-plane projection (profile view).
* **Front View**: $XZ$-plane projection (front/rear view).
* Dragging corner or edge handles allows fine-grained adjustment of Length, Width, Height, and centroid translation.

### 6.3. 2D Top-Down Bounding Box Editor
* Toggled via **`📐 2D Mode`** on the toolbar.
* Locks the 3D camera at a strict $90^\circ$ nadir (top-down) angle looking perpendicular to the ground plane.
* **Left-Click + Drag**: Smoothly translates cuboids across the ground plane without unintended $Z$-axis drift.
* **Right-Click + Drag**: Pans the viewport while maintaining orthographic alignment.

### 6.4. Kinematic Auto-Box Trajectory Interpolation
* Accessible via **`⚡ Auto Box`** (opens a draggable floating window `float-window-autobox`).
* **Kinematic Estimation Model**:
  * **Frame 1 & Frame 2**: Blocked from prediction, as at least **two consecutive historical frames** ($t-2$ and $t-1$) are required to establish a velocity vector.
  * **Frame $t \ge 3$**: Reads object states from Frame $t-1$ and Frame $t-2$. If the target Object ID is missing in Frame $t-1$, execution halts with an explicit diagnostic alert.
  * **State Extrapolation**:
    $$\Delta x = x_{t-1} - x_{t-2}, \quad \Delta y = y_{t-1} - y_{t-2}, \quad \Delta z = z_{t-1} - z_{t-2}$$
    $$\Delta\text{yaw} = \text{normalize}(\text{yaw}_{t-1} - \text{yaw}_{t-2})$$
    Predicted pose at frame $t$:
    $$x_t = x_{t-1} + \Delta x, \quad y_t = y_{t-1} + \Delta y, \quad z_t = z_{t-1} + \Delta z$$
    $$\text{yaw}_t = \text{normalize}(\text{yaw}_{t-1} + \Delta\text{yaw})$$
  * Automatically propagates cuboid dimensions (Length, Width, Height), `category`, and `subclass` from Frame $t-1$.
* **Execution Modes**:
  1. **`🎯 Selected Boxes`**: Predicts poses exclusively for highlighted cuboids.
  2. **`🚀 All Boxes`**: Batch-predicts trajectories for every tracked object in the frame.

### 6.5. Serverless Cloud Sync via Google Apps Script
* Uses a non-blocking floating window (`float-window-appscript`) so users can continue inspecting 3D point clouds during network transfers.
* Dynamically locates the configured target folder on Google Drive via `DriveApp.getFoldersByName(<TARGET_FOLDER>)`, allowing users to organize backup folders anywhere in their Drive hierarchy without breaking sync paths.

---

## 7. Standard Keyboard Shortcuts (Hotkeys)

| Shortcut | Action | Description |
| :--- | :--- | :--- |
| **`Ctrl + S`** | Save Frame | Writes current annotations to `./cache/annotations/` (and triggers Drive sync if enabled). |
| **`A`** or **`←`** | Previous Frame | Auto-saves current frame and steps backward ($t - 1$). |
| **`D`** or **`→`** | Next Frame | Auto-saves current frame and steps forward ($t + 1$). |
| **`O`** | Isolate Selected Box | Hides all unselected boxes on the 2D camera overlay to inspect occlusion. |
| **`H`** | Hide All Boxes | Toggles visibility of all 2D/3D bounding boxes for unobstructed visual inspection. |
| **`Ctrl + C`** | Copy Boxes | Copies selected cuboid parameters to internal clipboard. |
| **`Ctrl + V`** | Paste Boxes | Pastes copied cuboids into the active frame. |
| **`Shift + K`** | Pull from Next Frame | Copies all cuboids from Frame $t+1$ into the current frame. |
| **`Del` / `Backspace`** | Delete Boxes | Removes all currently selected cuboids from the active frame. |
| **`Ctrl + Z`** | Undo | Reverts the last cuboid translation, resize, or deletion operation. |
| **`M`** | Propagate ID Attributes | Synchronizes dimensions (L, W, H) and Class/Subclass of the selected ID across all 10 frames. |

---

## 8. Installation & Quick Start

### Option 1: Standalone Executable (Recommended)
Run the pre-packaged executable directly from `<PROJECT_ROOT>/`:
```text
ADO_Web_Tool.exe
```
* Bundles the Python runtime, dependencies, and static frontend assets.
* Automatically launches both the Main Annotation Server (`5000`) and FastCheck QA Server (`5050`), opening the workspace in your default browser.

### Option 2: Running from Source
1. Run `install.bat` once to install required Python packages (`flask`, `numpy`, `requests`).
2. Run `start_web_tool.bat` to start both local servers.

---

## 9. Developer & AI Maintainer Guidelines

When extending, refactoring, or debugging this codebase, contributors and AI coding assistants must adhere to the following architectural invariants:

1. **Preserve Cache Directory Schema**:
   Both `server.py` and `fast_check_app.py` rely on the exact subdirectory structure under `./cache/` (`annotations/`, `images/`, `pcd/`). Do not rename or restructure these paths.
2. **Enforce RAM-Only External Loading**:
   `scan_original_cache()` in `server.py` must only populate `self.frames[idx]["annotation"]` in memory. Never write directly to `LOCAL_ANNOTATIONS_DIR` during an external cache scan.
3. **Maintain Right-Handed `IZYX` Euler Conventions**:
   LiDAR orientations follow a right-handed coordinate system with rotation order `IZYX` (`orientation: [yaw, pitch, roll]`). Always use `euler_to_quaternion(roll, pitch, yaw)` when converting to Three.js quaternions.
4. **Use Non-Blocking Floating Panels**:
   Any new UI tools (e.g., batch filters, trajectory visualizers) must use `.floating-tool-window` and `makeElementDraggable()`. Avoid full-screen `.modal` backdrops that block 3D viewport interaction.
5. **Preserve Host JSON Schema on Export**:
   When writing back to the host client in `sync_to_unity.py`, retain all native metadata keys (`pcd_filename`, `img_filenames`, and per-camera projection attributes) inside each cuboid object.
