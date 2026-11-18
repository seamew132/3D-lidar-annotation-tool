@echo off
title ADO 3D OD Web Tool - Full Dependencies Installer (Core + AI Models)
color 0B

echo ==============================================================================
echo       ADO 3D OD Web Tool - CAI DAT TOAN BO THU VIEN PYTHON (CORE + AI)
echo ==============================================================================
echo.

:: Tim Python executable
set "PYTHON_EXE=python"
where python >nul 2>nul
if %errorlevel% neq 0 (
    if exist "C:\Users\Administrator\AppData\Local\Programs\Python\Python314\python.exe" (
        set "PYTHON_EXE=C:\Users\Administrator\AppData\Local\Programs\Python\Python314\python.exe"
    ) else (
        color 0C
        echo [LOI] Khong tim thay Python tren may tinh!
        echo Vui long cai dat Python 3.10 tro len va tich vao "Add Python to PATH".
        echo.
        pause
        exit /b 1
    )
)

echo Dang su dung: %PYTHON_EXE%
%PYTHON_EXE% --version
echo.

echo [1/4] Nang cap cong cu quan ly thu vien pip, setuptools, wheel...
%PYTHON_EXE% -m pip install --upgrade pip setuptools wheel
echo.

echo [2/4] Dang cai dat cac thu vien Web Tool Core (Flask, NumPy, Requests, SciPy)...
%PYTHON_EXE% -m pip install flask numpy requests scipy
echo.

echo [3/4] Dang cai dat cac thu vien AI (YOLOv8, SAM, PyTorch, OpenCV, Pillow)...
%PYTHON_EXE% -m pip install ultralytics opencv-python pillow
echo.

echo [4/4] Dang cai dat thu vien tang toc suy luan ONNX Runtime...
%PYTHON_EXE% -m pip install onnx onnxruntime
echo.

echo ==============================================================================
echo   DANG KIEM TRA XAC THUC CAC THU VIEN DA CAI DAT...
echo ==============================================================================
%PYTHON_EXE% -c "
import sys

def check_mod(name, pkg=None):
    try:
        __import__(pkg or name)
        print(f'  [OK] Thu vien {name:<15} : Hoat dong tot!')
        return True
    except Exception as e:
        print(f'  [FAIL] Thu vien {name:<15} : {e}')
        return False

print('')
c1 = check_mod('Flask', 'flask')
c2 = check_mod('NumPy', 'numpy')
c3 = check_mod('Requests', 'requests')
c4 = check_mod('SciPy', 'scipy')
c5 = check_mod('Ultralytics (YOLO/SAM)', 'ultralytics')
c6 = check_mod('PyTorch', 'torch')
c7 = check_mod('OpenCV', 'cv2')
c8 = check_mod('ONNX Runtime', 'onnxruntime')
print('')

if all([c1, c2, c3, c5]):
    print('>>> TAT CA CAC THU VIEN QUAN TRONG DA SAN SANG 100%! <<<')
else:
    print('>>> Co mot so thu vien chua cai duoc, vui long kiem tra lai ket noi mang! <<<')
"

echo.
echo ==============================================================================
echo   HOAN TAT! He thong da san sang chay ca Web Tool va 2 model AI (YOLO + SAM).
echo   Ban co the:
echo     1. Chay file 'start_web_tool.bat' (Chay bang Python truc tiep)
echo     2. Hoac chay truc tiep 'PJT64.exe' (File dong goi doc lap)
echo ==============================================================================
echo.
pause
