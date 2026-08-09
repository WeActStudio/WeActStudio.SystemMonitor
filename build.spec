# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main\\main.py', 
    'configure\\configure.py',
    'theme-editor\\theme-editor.py',
    'weact_device_setting\\weact_device_setting.py',
    'upgrade\\upgrade.py',
    'image_gif2png_scaler_tool\\image_gif2png_scaler_tool.py',
    'image_scaler_tool\\image_scaler_tool.py'
    ],
    pathex=['./'],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

def get_single_script(all_script_list, target_file):
    scripts = []
    for item in all_script_list:
        if item[0].startswith('pyi') or target_file in item[0]:
            scripts.append(item)
    return scripts

exe_main = EXE(
    pyz,
    get_single_script(a.scripts,'main'),
    [],
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='main\\version.txt',
    icon=['res\\icons\\logo.ico'],
)

exe_configure = EXE(
    pyz,
    get_single_script(a.scripts,'configure'),
    [],
    name='configure',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='configure\\version.txt',
    icon=['res\\icons\\logo.ico'],
)

exe_theme_editor = EXE(
    pyz,
    get_single_script(a.scripts,'theme-editor'),
    [],
    name='theme-editor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='theme-editor\\version.txt',
    icon=['res\\icons\\logo.ico'],
)

exe_weact_device_setting = EXE(
    pyz,
    get_single_script(a.scripts,'weact_device_setting'),
    [],
    name='weact_device_setting',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='weact_device_setting\\version.txt',
    icon=['res\\icons\\logo.ico'],
)

exe_upgrade = EXE(
    pyz,
    get_single_script(a.scripts,'upgrade'),
    [],
    name='upgrade',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='upgrade\\version.txt',
    icon=['res\\icons\\logo.ico'],
)

exe_image_gif2png_scaler_tool = EXE(
    pyz,
    get_single_script(a.scripts,'image_gif2png_scaler_tool'),
    [],
    name='image_gif2png_scaler_tool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='image_gif2png_scaler_tool\\version.txt',
    icon=['res\\icons\\logo.ico'],
)

exe_image_scaler_tool = EXE(
    pyz,
    get_single_script(a.scripts,'image_scaler_tool'),
    [],
    name='image_scaler_tool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='image_scaler_tool\\version.txt',
    icon=['res\\icons\\logo.ico'],
)

coll = COLLECT(
    exe_main,
    exe_configure,
    exe_theme_editor,
    exe_weact_device_setting,
    exe_upgrade,
    exe_image_gif2png_scaler_tool,
    exe_image_scaler_tool,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="release",  # dist下的文件夹名
)