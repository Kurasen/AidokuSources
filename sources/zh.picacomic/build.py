import os
import json
import zipfile
import shutil
import subprocess
import sys
from pathlib import Path


def run_command(cmd, cwd=None):
    """运行命令并返回是否成功"""
    try:
        result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"命令执行失败: {cmd}")
            print(f"错误信息: {result.stderr}")
            return False
        return True
    except Exception as e:
        print(f"执行命令时出错: {e}")
        return False


def package_aidoku_source():
    # 定义项目根目录
    project_root = Path.cwd()
    temp_dir = Path('temp_package')

    # 确保在出错时能清理临时文件
    try:
        # 1. 检查必要文件是否存在
        if not (project_root / 'res' / 'source.json').exists():
            print(f"错误: 未找到 {project_root / 'res' / 'source.json'}")
            return False

        # 2. 编译Rust项目
        print("正在编译Rust项目...")
        if not run_command('cargo build --release --target wasm32-unknown-unknown', cwd=project_root):
            print("编译失败，请检查Rust项目")
            return False

        # 3. 读取source.json获取元数据
        with open(project_root / 'res' / 'source.json', 'r', encoding='utf-8') as f:
            source_info = json.load(f)

        package_id = source_info['info']['id']
        package_version = source_info['info']['version']

        print(f"包ID: {package_id}, 版本: {package_version}")

        # 4. 创建临时目录结构
        payload_dir = temp_dir / 'Payload'

        # 清理已存在的临时目录
        if temp_dir.exists():
            print("清理已存在的临时目录...")
            shutil.rmtree(temp_dir)

        payload_dir.mkdir(parents=True)
        print(f"创建临时目录: {temp_dir}")

        # 5. 复制资源文件
        res_dir = project_root / 'res'
        print(f"复制资源文件从: {res_dir}")
        for item in res_dir.iterdir():
            if item.is_file():
                shutil.copy2(item, payload_dir / item.name)

        # 6. 复制WASM文件
        wasm_dir = project_root / 'target' / 'wasm32-unknown-unknown' / 'release'
        wasm_files = list(wasm_dir.glob('*.wasm'))

        if not wasm_files:
            print("错误：未找到WASM文件")
            # 在返回前清理临时目录
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            return False

        # 使用第一个找到的WASM文件
        shutil.copy2(wasm_files[0], payload_dir / 'main.wasm')

        # 7. 创建ZIP文件（.aix）
        zip_filename = f"{package_id}-v{package_version}.zip"
        aix_filename = f"{package_id}-v{package_version}.aix"

        print(f"正在创建 {zip_filename}...")

        try:
            # 修复：使用正确的ZIP文件路径
            with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        # 在ZIP中保持目录结构
                        arcname = os.path.relpath(file_path, temp_dir.parent)
                        zipf.write(file_path, arcname)

            # 检查ZIP文件是否创建成功
            if os.path.exists(zip_filename):
                file_size = os.path.getsize(zip_filename)
                print(f"ZIP文件创建成功")

                # 8. 重命名为.aix
                if os.path.exists(aix_filename):
                    print(f"删除已存在的AIX文件: {aix_filename}")
                    os.remove(aix_filename)

                os.rename(zip_filename, aix_filename)
                print(f"重命名为: {aix_filename}")
            else:
                print(f"错误: ZIP文件 {zip_filename} 创建后不存在")
                return False

        except Exception as e:
            print(f"创建ZIP文件时出错: {e}")
            return False

        return True

    except Exception as e:
        print(f"处理过程中出错: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # 无论成功还是失败，都清理临时目录
        print("清理临时目录...")
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        wasm_target_dir = project_root / 'target'
        if wasm_target_dir.exists():
            shutil.rmtree(wasm_target_dir)


def main():
    print("开始打包Aidoku源...")

    if package_aidoku_source():
        print("打包完成！")
        sys.exit(0)
    else:
        print("打包失败！")
        sys.exit(1)


if __name__ == "__main__":
    main()
