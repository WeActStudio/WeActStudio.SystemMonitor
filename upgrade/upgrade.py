import json
import urllib.request
import os
import sys
from pathlib import Path
import py7zr
import shutil
import traceback

if getattr(sys, "frozen", False):
    executable_name = os.path.splitext(os.path.basename(sys.executable))[0]
    executable_dir = Path(sys.executable).parent
else:
    executable_name = os.path.splitext(os.path.basename(__file__))[0]
    executable_dir = Path(__file__).parent

sys.path.append(str(executable_dir.parent))
os.chdir(executable_dir)


def read_file(path: Path = executable_dir / "version"):
    try:
        with open(path, "r") as f:
            data = f.read().strip()
            return data
    except Exception as e:
        print(f"Error reading file: {e}")
        return ""


def get_version(path: Path = executable_dir):
    version_file = path / "version"
    try:
        with open(version_file, "r") as f:
            version = f.read().strip()
            return version
    except Exception as e:
        print(f"Error reading version file: {e}")
        return "V0.0.0.0"


def parse_version(ver_str: str) -> tuple[int, int, int, int]:
    """
    解析 V2.0.0.0 格式版本号为数字元组，方便直接比较
    """
    # 去除开头V/v
    ver = ver_str.lstrip("Vv")
    parts = ver.split(".")
    # 转整数，固定4段，不足补0
    nums = [int(p) for p in parts[:4]]
    while len(nums) < 4:
        nums.append(0)
    return tuple(nums)


def is_newer(ver_a: str, ver_b: str) -> bool:
    """
    判断 ver_a 是否比 ver_b 版本更新
    返回 True: a更新；False: a更旧或相等
    """
    t1 = parse_version(ver_a)
    t2 = parse_version(ver_b)
    return t1 > t2


def download_release_file(
    repo: str, filename_keyword: str, save_dir: str = "./download"
) -> str:
    """
    下载最新Release内匹配关键词的文件
    :param repo: GitHub仓库名 WeActStudio/WeActStudio.SystemMonitor
    :param filename_keyword: 文件名关键词，如 win_x64.zip
    :param save_dir: 本地保存文件夹
    :return: 本地文件路径
    """
    api_url = f"https://api.github.com/repos/{repo}/releases/latest"
    headers = {"User-Agent": "Python-Download"}
    print(f"Request URL: {api_url}")
    req = urllib.request.Request(api_url, headers=headers)

    with urllib.request.urlopen(req) as resp:
        release_info = json.load(resp)

    tag = release_info["tag_name"]
    print(f"Latest Tag: {tag}")

    target_asset = None
    for asset in release_info["assets"]:
        name = asset["name"]
        if filename_keyword in name:
            target_asset = asset
            break

    if not target_asset:
        raise FileNotFoundError(
            f"Release not found file containing [{filename_keyword}]"
        )

    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, target_asset["name"])
    dl_url = target_asset["browser_download_url"]

    print(f"Start download {target_asset['name']} to {save_path}")
    with urllib.request.urlopen(dl_url) as r, open(save_path, "wb") as f:
        f.write(r.read())
    print(f"Download completed: {save_path}")
    return save_path


def extract_py7z(archive_path: str, output_dir: str, password: str = None):
    os.makedirs(output_dir, exist_ok=True)
    with py7zr.SevenZipFile(archive_path, mode="r", password=password) as z:
        z.extractall(path=output_dir)
    print(f"py7zr extract {archive_path} finished")


def list_7z_contents(archive_path: str, password=None):
    """遍历7z压缩包内所有文件，不解压"""
    with py7zr.SevenZipFile(archive_path, mode="r", password=password) as zf:
        # 获取所有文件信息对象
        all_files = zf.getnames()
        print(f"extract {archive_path} files:")
        for name in all_files:
            print("-", name)
    return all_files


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="WeActStudio System Monitor Upgrade")
    parser.add_argument(
        "-l","--local",
        action="store_true",
        help="local upgrade",
    )
    args = parser.parse_args()

    try:
        current_version = get_version(executable_dir)
        print(f"Current version is: {current_version}")
        libHM_version = read_file(executable_dir / "LibreHardwareMonitor" / "version")
        if libHM_version == "":
            libHM_version = "0"
        print(f"Current LibreHardwareMonitor version: {libHM_version}")

        print("Check Software version ...")

        repo = "WeActStudio/WeActStudio.SystemMonitor"
        search_key = "version"
        output_folder = "upgrade_file"

        if not args.local:
            try:
                download_release_file(repo, search_key, output_folder)
            except Exception as err:
                print("Download failed: ", err)
                sys.exit(1)

        latest_version_data = read_file(Path(output_folder) / "version").splitlines()
        latest_version_split = latest_version_data[0].split(",")
        latest_version = latest_version_split[0]
        print(f"Latest version is: {latest_version_split}")
        print(f"Latest version data: {latest_version_data}")

        if len(latest_version_data) > 1:
            libHM_version_split = latest_version_data[1].split(",")
            libHM_version_latest = libHM_version_split[0]
            print(f"LibreHardwareMonitor latest version: {libHM_version_latest}")
            if int(libHM_version_latest) > int(libHM_version):
                print("LibreHardwareMonitor has new version")

                if not args.local:
                    try:
                        download_release_file(repo, libHM_version_split[1], output_folder)
                    except Exception as err:
                        print("Download failed: ", err)
                        sys.exit(1)

                LibreHardwareMonitor_old = Path(executable_dir / "LibreHardwareMonitor_old")
                LibreHardwareMonitor = Path(executable_dir / "LibreHardwareMonitor")
                if LibreHardwareMonitor_old.exists():
                    shutil.rmtree(LibreHardwareMonitor_old)
                Path(executable_dir / "LibreHardwareMonitor").rename(
                    executable_dir / "LibreHardwareMonitor_old"
                )
                print(f"LibreHardwareMonitor is backup to {LibreHardwareMonitor_old}")
                if LibreHardwareMonitor.exists():
                    shutil.rmtree(LibreHardwareMonitor)
                    print(f"{LibreHardwareMonitor} is deleted")
                print(f"Start extract {libHM_version_split[1]}")
                extract_py7z(str(Path(output_folder) / libHM_version_split[1]), "./")
                print("LibreHardwareMonitor upgrade completed.")
            else:
                print("LibreHardwareMonitor no new version")

        if latest_version != "NONE" and is_newer(latest_version, current_version):
            print("Has new version")

            if not args.local:
                try:
                    download_release_file(repo, latest_version_split[1], output_folder)
                except Exception as err:
                    print("Download failed: ", err)
                    sys.exit(1)

            upgrade_files_list = list_7z_contents(
                str(Path(output_folder) / latest_version_split[1])
            )
            if "res" in upgrade_files_list:
                res_path = Path(executable_dir / "res")
                if res_path.exists():
                    shutil.rmtree(res_path)
                    print(f"{res_path} is deleted")

            extract_py7z(str(Path(output_folder) / latest_version_split[1]), "./")
            print("Software upgrade completed.")
        else:
            print("Software no new version")

        if not args.local:
            shutil.rmtree(output_folder)

        print("Finished.")

    except:
        traceback.print_exc()

    print("\nPress Enter to exit...")
    input()
