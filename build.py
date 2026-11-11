"""构建脚本 - 打包子衿桌面伴生代理"""
import subprocess
import sys
import os
import shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, "dist")
BUILD = os.path.join(ROOT, "build")


def clean():
    for d in [DIST, BUILD]:
        if os.path.exists(d):
            shutil.rmtree(d)
    print("清理完成")


def build():
    clean()
    cmd = [sys.executable, "-m", "PyInstaller", "ZiJin.spec", "--clean"]
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode == 0:
        print(f"构建成功: {DIST}/ZiJin/")
    else:
        print("构建失败")
        sys.exit(1)


if __name__ == "__main__":
    build()
