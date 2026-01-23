import os
import sys
import subprocess
import time
import json

def load_config():
    """加载配置文件"""
    default_config = {
        "port": 5000
    }
    
    config_path = "config.json"
    
    # 如果配置文件不存在，创建默认配置
    if not os.path.exists(config_path):
        print(f"配置文件 {config_path} 不存在，创建默认配置...")
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)
        return default_config
    
    # 读取配置文件
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        # 验证配置
        if "port" not in config or not isinstance(config["port"], int):
            print("配置文件格式错误，使用默认配置...")
            return default_config
        
        # 验证端口范围
        if not (1024 <= config["port"] <= 65535):
            print(f"端口号 {config['port']} 不在有效范围内，使用默认端口 5000...")
            config["port"] = default_config["port"]
        
        return config
    except Exception as e:
        print(f"读取配置文件失败: {e}，使用默认配置...")
        return default_config

def main():
    print("=" * 50)
    print("局域网安全文件传输系统")
    print("=" * 50)
    print()
    
    # 加载配置
    print("1. 加载配置...")
    config = load_config()
    port = config["port"]
    print(f"使用端口: {port}")
    print()
    
    # 检查Python版本
    print("2. 检查Python版本...")
    print(f"当前Python版本: {sys.version}")
    if sys.version_info < (3, 7):
        print("错误: 需要Python 3.7或更高版本")
        input("按任意键退出...")
        return
    
    print("Python版本符合要求")
    print()
    
    # 创建必要的目录
    print("3. 创建必要目录...")
    os.makedirs("received_files", exist_ok=True)
    os.makedirs("shared_files", exist_ok=True)
    print("目录创建完成")
    print()
    
    # 安装依赖（使用清华镜像）
    print("4. 安装/更新依赖（使用清华镜像）...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-i", "https://pypi.tuna.tsinghua.edu.cn/simple", "-r", "requirements.txt"], 
                     check=False, shell=True)
        print("依赖处理完成")
    except Exception as e:
        print(f"警告: 依赖安装可能不完整 - {e}")
        print("尝试继续...")
    print()
    
    # 显示IP地址
    print("5. 本地IP地址信息:")
    try:
        if sys.platform == "win32":
            result = subprocess.run(["ipconfig"], capture_output=True, text=True, shell=True)
            for line in result.stdout.splitlines():
                if "IPv4" in line:
                    print(f"   {line.strip()}")
        else:
            result = subprocess.run(["ifconfig"], capture_output=True, text=True, shell=True)
            print(result.stdout)
    except Exception as e:
        print(f"无法获取IP地址: {e}")
    
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
    
    # 启动服务器
    print(f"6. 正在启动服务器，端口: {port}...")
    print()
    
    try:
        # 运行server_simple.py并传递端口参数
        subprocess.run([sys.executable, "server_simple.py", str(port)], shell=True)
    except KeyboardInterrupt:
        print()
        print("服务器已停止")
    except Exception as e:
        print(f"服务器启动失败: {e}")
        input("按任意键退出...")

if __name__ == "__main__":
    main()