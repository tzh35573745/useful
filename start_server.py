import json
import os
import platform
import socket
import subprocess
import sys
from importlib.util import find_spec

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
REQUIREMENTS_PATH = os.path.join(BASE_DIR, "requirements.txt")
RECEIVED_DIR = os.path.join(BASE_DIR, "received_files")
SHARED_DIR = os.path.join(BASE_DIR, "shared_files")
REQUIRED_MODULES = [
    ("fastapi", "fastapi"),
    ("uvicorn", "uvicorn"),
    ("jinja2", "jinja2"),
    ("multipart", "python-multipart"),
    ("Crypto", "pycryptodome"),
]
MIN_PYTHON_VERSION = (3, 10)


def wait_before_exit(message="按回车键退出..."):
    try:
        input(message)
    except EOFError:
        pass


def load_config():
    """加载配置文件"""
    default_config = {
        "port": 5000
    }

    if not os.path.exists(CONFIG_PATH):
        print(f"配置文件 {os.path.basename(CONFIG_PATH)} 不存在，创建默认配置...")
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)
        return default_config

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)

        if "port" not in config or not isinstance(config["port"], int):
            print("配置文件格式错误，使用默认配置...")
            return default_config

        if not (1024 <= config["port"] <= 65535):
            print(f"端口号 {config['port']} 不在有效范围内，使用默认端口 5000...")
            config["port"] = default_config["port"]

        return config
    except Exception as e:
        print(f"读取配置文件失败: {e}，使用默认配置...")
        return default_config


def check_python_version():
    print("2. 检查Python版本...")
    print(f"当前Python版本: {sys.version}")
    if sys.version_info < MIN_PYTHON_VERSION:
        required = ".".join(str(part) for part in MIN_PYTHON_VERSION)
        print(f"错误: 需要 Python {required} 或更高版本")
        wait_before_exit()
        return False

    print("Python版本符合要求")
    print()
    return True


def ensure_runtime_directories():
    print("3. 创建必要目录...")
    os.makedirs(RECEIVED_DIR, exist_ok=True)
    os.makedirs(SHARED_DIR, exist_ok=True)
    print("目录创建完成")
    print()


def get_missing_runtime_dependencies():
    missing_packages = []
    for module_name, package_name in REQUIRED_MODULES:
        if find_spec(module_name) is None:
            missing_packages.append(package_name)
    return missing_packages


def install_runtime_dependencies(missing_packages):
    print("4. 检查运行依赖...")
    if not missing_packages:
        print("依赖已安装，跳过安装步骤")
        print()
        return True

    print("检测到缺少依赖:")
    for package_name in missing_packages:
        print(f"- {package_name}")

    print("正在尝试自动安装依赖，请稍候...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", REQUIREMENTS_PATH],
            check=True,
        )
    except subprocess.CalledProcessError as error:
        print(f"依赖安装失败，pip退出码: {error.returncode}")
        print("请确认已安装 pip，并检查网络是否正常。")
        print(f"你也可以手动执行: {sys.executable} -m pip install -r requirements.txt")
        wait_before_exit()
        return False
    except Exception as error:
        print(f"依赖安装失败: {error}")
        print(f"你也可以手动执行: {sys.executable} -m pip install -r requirements.txt")
        wait_before_exit()
        return False

    remaining_missing = get_missing_runtime_dependencies()
    if remaining_missing:
        print("依赖安装后仍缺少以下模块:")
        for package_name in remaining_missing:
            print(f"- {package_name}")
        print("请手动执行安装命令后重试。")
        wait_before_exit()
        return False

    print("依赖安装完成")
    print()
    return True


def get_local_ipv4_addresses():
    addresses = []
    seen = set()

    def add_address(address):
        if not address or address.startswith("127.") or address in seen:
            return
        if address.startswith(("10.", "172.", "192.168.")):
            seen.add(address)
            addresses.append(address)

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            add_address(sock.getsockname()[0])
    except OSError:
        pass

    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, family=socket.AF_INET):
            add_address(info[4][0])
    except OSError:
        pass

    return addresses


def is_port_available(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("0.0.0.0", port))
            return True
        except OSError:
            return False


def find_available_port(start_port, attempts=10):
    for candidate in range(start_port + 1, min(start_port + attempts + 1, 65536)):
        if is_port_available(candidate):
            return candidate
    return None


def show_local_ip_info(port):
    print("本地IP地址信息:")
    addresses = get_local_ipv4_addresses()
    if not addresses:
        system_name = platform.system()
        print(f"未能自动识别局域网IP，请在 {system_name} 的系统网络设置中查看。")
        print(f"手机访问地址格式: http://你的电脑IP:{port}")
        return

    for address in addresses:
        print(f"   {address}")
    print("手机访问地址:")
    for address in addresses:
        print(f"   http://{address}:{port}")


def main():
    print("=" * 50)
    print("局域网安全文件传输系统")
    print("=" * 50)
    print()

    print("1. 加载配置...")
    config = load_config()
    port = config["port"]
    print(f"使用端口: {port}")
    print()

    if not check_python_version():
        return

    ensure_runtime_directories()

    if not is_port_available(port):
        print(f"3.5 端口检查失败: 端口 {port} 已被占用")
        suggested_port = find_available_port(port)
        print("请关闭占用该端口的程序，或修改 config.json 中的端口后重试。")
        if suggested_port:
            print(f"建议可用端口: {suggested_port}")
        wait_before_exit()
        return

    missing_packages = get_missing_runtime_dependencies()
    if not install_runtime_dependencies(missing_packages):
        return

    print()
    print("=" * 50)
    print("服务器即将启动!")
    print("=" * 50)
    print("使用说明:")
    print("1. 将需要分享的文件复制到 shared_files 目录")
    print(f"2. 在手机浏览器访问: http://你的IP地址:{port}")
    print("3. 选择'电脑 → 手机'下载文件，或'手机 → 电脑'上传文件")
    print("4. 按 Ctrl+C 停止服务器")
    print("5. 如需修改端口，请编辑 config.json 文件")
    print("=" * 50)
    show_local_ip_info(port)

    print(f"6. 正在启动服务器，端口: {port}...")
    print()

    try:
        subprocess.run([sys.executable, os.path.join(BASE_DIR, "server_simple.py"), str(port)], check=False)
    except KeyboardInterrupt:
        print()
        print("服务器已停止")
    except Exception as e:
        print(f"服务器启动失败: {e}")
        wait_before_exit()


if __name__ == "__main__":
    main()
