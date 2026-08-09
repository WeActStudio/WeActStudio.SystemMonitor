import os
import sys
from pathlib import Path
import lib.utils as utils
import shutil
import subprocess
import platform

import argparse
parser = argparse.ArgumentParser(description="Build release package for WeActStudio System Monitor")
parser.add_argument(
    "-s","--subbuild",
    action="store_true",
    help="Sub Module build",
)

parser.add_argument(
    "-sq","--subbuild-quit",
    action="store_true",
    help="Sub Module build and quit",
)

parser.add_argument(
    "-c","--clean",
    action="store_true",
    help="Clean release directory and unless file",
)

args = parser.parse_args()

root_dir = Path(__file__).parent
release_dir = Path(root_dir / "release")

if args.clean:
    if release_dir.exists():
        print("Clean release directory")
        shutil.rmtree(release_dir)
    print("Clean txt file")
    for txt_file in root_dir.glob("*.txt"):
        if txt_file.is_file() and txt_file.name != "requirements.txt":
            txt_file.unlink()
    print("Clean lock file")
    for lock_file in root_dir.glob("*.lock"):
        if lock_file.is_file():
            lock_file.unlink()   
    print("Clean exe file")
    for exe_file in root_dir.glob("*.exe"):
        if exe_file.is_file():
            exe_file.unlink()    
    print("Clean log file")
    for log_file in root_dir.glob("*.log"):
        if log_file.is_file():
            log_file.unlink()

    build_dir = Path(root_dir / "build")
    if build_dir.exists():
        print("Clean build directory")
        shutil.rmtree(build_dir)
    dist_dir = Path(root_dir / "dist")
    if dist_dir.exists():
        print("Clean dist directory")
        shutil.rmtree(dist_dir)

    app = [
        "main",
        "configure",
        "theme-editor",
        "weact_device_setting",
        "image_gif2png_scaler_tool",
        "image_scaler_tool",
        "upgrade",
    ]
    for app_name in app:
        print("Clean",app_name)
        spec_file = Path(root_dir / app_name / str(app_name + ".spec"))
        if spec_file.exists():
            spec_file.unlink()
        build_dir = Path(root_dir / app_name / "build")
        if build_dir.exists():
            shutil.rmtree(build_dir)
        dist_dir = Path(root_dir / app_name / "dist")
        if dist_dir.exists():
            shutil.rmtree(dist_dir)

    if args.subbuild == False and args.subbuild_quit == False:
        sys.exit(0)

if args.subbuild or args.subbuild_quit:
    print("Sub Module build")

    build_dir = Path(root_dir / "build")
    if build_dir.exists():
        print("Clean build directory")
        shutil.rmtree(build_dir)
    dist_dir = Path(root_dir / "dist")
    if dist_dir.exists():
        print("Clean dist directory")
        shutil.rmtree(dist_dir)

    subprocess.run(["pyinstaller", "build.spec"])

    # print("> build main.exe")
    # subprocess.run([root_dir / "main" / "pkg_cmd.bat"])
    # print("> build configure.exe")
    # subprocess.run([root_dir / "configure" / "pkg_cmd.bat"])
    # print("> build theme-editor.exe")
    # subprocess.run([root_dir / "theme-editor" / "pkg_cmd.bat"])
    # print("> build weact_device_setting.exe")
    # subprocess.run([root_dir / "weact_device_setting" / "pkg_cmd.bat"])
    # print("> build image-gif2png-scaler-tool.exe")
    # subprocess.run([root_dir / "image_gif2png_scaler_tool" / "pkg_cmd.bat"])
    # print("> build image-scaler-tool.exe")
    # subprocess.run([root_dir / "image_scaler_tool" / "pkg_cmd.bat"])
    # print("> build upgrade.exe")
    # subprocess.run([root_dir / "upgrade" / "pkg_cmd.bat"])


# 清空release目录
# if release_dir.exists():
#     print("Clear release directory")
#     shutil.rmtree(release_dir)

# # 创建release目录
print("Create release directory")
if not release_dir.exists():
    release_dir.mkdir()

release_dir_build = root_dir / "dist" / "release"
if release_dir_build.exists():
    print("Copy release directory from build directory")
    
    if platform.architecture()[0] == '64bit':
        Path_64bit = release_dir / "64bit"
        if Path_64bit.exists():
            shutil.rmtree(Path_64bit)
        shutil.copytree(release_dir_build, Path_64bit)
    else:
        Path_32bit = release_dir / "32bit"
        if Path_32bit.exists():
            shutil.rmtree(Path_32bit)
        shutil.copytree(release_dir_build, Path_32bit)

if args.subbuild_quit:
    sys.exit(0)

# # 复制main.exe到release目录
# print("Copy main.exe to release directory")
# main_exe = Path(root_dir / "main" / "dist" / "main.exe")
# main_exe.copy(release_dir / "main.exe")

# # 复制configure.exe到release目录
# print("Copy configure.exe to release directory")
# configure_exe = Path(root_dir / "configure" / "dist" / "configure.exe")
# configure_exe.copy(release_dir / "configure.exe")

# # 复制theme-editor.exe到release目录
# print("Copy theme-editor.exe to release directory")
# theme_editor_exe = Path(root_dir / "theme-editor" / "dist" / "theme-editor.exe")
# theme_editor_exe.copy(release_dir / "theme-editor.exe")

# # 复制weact_device_setting.exe到release目录
# print("Copy weact_device_setting.exe to release directory")
# weact_device_setting_exe = Path(root_dir / "weact_device_setting" / "dist" / "weact_device_setting.exe")
# weact_device_setting_exe.copy(release_dir / "weact_device_setting.exe")

# # 复制image-gif2png-scaler-tool.exe到release目录
# print("Copy image-gif2png-scaler-tool.exe to release directory")
# image_gif2png_scaler_tool_exe = Path(root_dir / "image_gif2png_scaler_tool" / "dist" / "image_gif2png_scaler_tool.exe")
# image_gif2png_scaler_tool_exe.copy(release_dir / "image_gif2png_scaler_tool.exe")

# # 复制image-scaler-tool.exe到release目录
# print("Copy image-scaler-tool.exe to release directory")
# image_scaler_tool_exe = Path(root_dir / "image_scaler_tool" / "dist" / "image_scaler_tool.exe")
# image_scaler_tool_exe.copy(release_dir / "image_scaler_tool.exe")

# # 复制upgrade.exe到release目录
# print("Copy upgrade.exe to release directory")
# upgrade_exe = Path(root_dir / "upgrade" / "dist" / "upgrade.exe")
# upgrade_exe.copy(release_dir / "upgrade.exe")

# 复制config.yaml到release目录
print("Copy config.yaml to release directory")
config_yaml = Path(root_dir / "config.yaml")
config_yaml.copy(release_dir / "config.yaml")

# 复制version到release目录
print("Copy version to release directory")
version = Path(root_dir / "version")
version.copy(release_dir / "version")

# 复制LICENSE到release目录
print("Copy LICENSE to release directory")
license = Path(root_dir / "LICENSE")
license.copy(release_dir / "LICENSE")

# 复制res目录到release目录
print("Copy res directory to release directory")
res_dir = Path(root_dir / "res")
shutil.copytree(res_dir, release_dir / "res")

# 复制LibreHardwareMonitor目录到release目录
print("Copy LibreHardwareMonitor directory to release directory")
LibreHardwareMonitor_dir = Path(root_dir / "LibreHardwareMonitor")
shutil.copytree(LibreHardwareMonitor_dir, release_dir / "LibreHardwareMonitor")

# 复制Driver目录到release目录
print("Copy Driver directory to release directory")
Driver_dir = Path(root_dir / "Driver")
shutil.copytree(Driver_dir, release_dir / "Driver")

print("Build release package done")