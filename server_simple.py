from fastapi import FastAPI, File, UploadFile, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates
import os
import time
import re

# 预共享密钥（需要在客户端和服务端保持一致）
PRE_SHARED_KEY = b"your_secure_pre_shared_key_here"  # 请更换为强密钥

app = FastAPI()

# 配置模板目录
templates = Jinja2Templates(directory="templates")

# 创建必要的目录
os.makedirs(os.path.join(os.getcwd(), "received_files"), exist_ok=True)
os.makedirs(os.path.join(os.getcwd(), "shared_files"), exist_ok=True)

@app.get('/')
def index(request: Request):
    """主页"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post('/upload')
async def upload(request: Request, file: list[UploadFile] = File(None)):
    """处理文件上传（手机到电脑）"""
    try:
        # 保存文件到received_files目录
        file_path = os.path.join(os.getcwd(), "received_files")
        os.makedirs(file_path, exist_ok=True)
        
        uploaded_count = 0
        
        # 检查file参数是否存在且不为空
        if file is not None and len(file) > 0:
            for f in file:
                try:
                    # 清理文件名，移除不合法字符
                    safe_filename = re.sub(r'[<>:"/\\|?*]', '', f.filename)
                    # 限制文件名长度
                    if len(safe_filename) > 200:
                        name, ext = os.path.splitext(safe_filename)
                        safe_filename = name[:190] + ext
                    
                    # 保存文件
                    file_location = os.path.join(file_path, safe_filename)
                    with open(file_location, "wb") as f_out:
                        f_out.write(await f.read())
                    uploaded_count += 1
                    print(f"[*] 收到文件: {f.filename} -> 保存为: {safe_filename}")
                except Exception as file_error:
                    print(f"[!] 保存文件 {f.filename} 失败: {file_error}")
        
        # 返回成功页面
        result_html = f"<div class=\"success\">成功上传 {uploaded_count} 个文件</div>"
        return templates.TemplateResponse("result.html", {
            "request": request,
            "result_html": result_html
        })
        
    except Exception as e:
        print(f"[!] 处理文件上传时出错: {e}")
        # 返回错误页面
        result_html = f"<div class=\"error\">上传失败: {str(e)}</div>"
        return templates.TemplateResponse("result.html", {
            "request": request,
            "result_html": result_html
        })

@app.post('/upload_shared')
async def upload_shared(file: list[UploadFile] = File(None)):
    """上传文件到共享目录（电脑到手机）"""
    try:
        # 保存文件到shared_files目录
        shared_path = os.path.join(os.getcwd(), "shared_files")
        os.makedirs(shared_path, exist_ok=True)
        
        uploaded_count = 0
        
        # 检查file参数是否存在且不为空
        if file is not None and len(file) > 0:
            for f in file:
                try:
                    # 清理文件名，移除不合法字符
                    safe_filename = re.sub(r'[<>:"/\\|?*]', '', f.filename)
                    # 限制文件名长度
                    if len(safe_filename) > 200:
                        name, ext = os.path.splitext(safe_filename)
                        safe_filename = name[:190] + ext
                    
                    # 保存文件
                    file_location = os.path.join(shared_path, safe_filename)
                    with open(file_location, "wb") as f_out:
                        f_out.write(await f.read())
                    uploaded_count += 1
                    print(f"[*] 共享文件上传: {f.filename} -> 保存为: {safe_filename}")
                except Exception as file_error:
                    print(f"[!] 保存共享文件 {f.filename} 失败: {file_error}")
        
        return JSONResponse(content={
            "success": True,
            "message": f"成功上传 {uploaded_count} 个共享文件"
        })
        
    except Exception as e:
        print(f"[!] 处理共享文件上传时出错: {e}")
        return JSONResponse(content={
            "success": False,
            "message": str(e)
        })

@app.get('/files')
async def get_files():
    """获取共享文件列表"""
    try:
        shared_path = os.path.join(os.getcwd(), "shared_files")
        os.makedirs(shared_path, exist_ok=True)

        files = []
        for filename in os.listdir(shared_path):
            file_path = os.path.join(shared_path, filename)
            if os.path.isfile(file_path):
                file_stats = os.stat(file_path)
                files.append({
                    "id": filename,
                    "name": filename,
                    "size": file_stats.st_size,
                    "mtime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(file_stats.st_mtime))
                })

        # 按修改时间降序排序
        files.sort(key=lambda x: x["mtime"], reverse=True)

        return JSONResponse(content={
            "success": True,
            "files": files
        })

    except Exception as e:
        print(f"[!] 获取文件列表时出错: {e}")
        return JSONResponse(content={
            "success": False,
            "message": str(e)
        })

@app.get('/received_files')
async def get_received_files():
    """获取已上传文件列表（received_files目录）"""
    try:
        received_path = os.path.join(os.getcwd(), "received_files")
        os.makedirs(received_path, exist_ok=True)

        files = []
        for filename in os.listdir(received_path):
            file_path = os.path.join(received_path, filename)
            if os.path.isfile(file_path):
                file_stats = os.stat(file_path)
                files.append({
                    "id": filename,
                    "name": filename,
                    "size": file_stats.st_size,
                    "mtime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(file_stats.st_mtime))
                })

        # 按修改时间降序排序
        files.sort(key=lambda x: x["mtime"], reverse=True)

        return JSONResponse(content={
            "success": True,
            "files": files
        })

    except Exception as e:
        print(f"[!] 获取已上传文件列表时出错: {e}")
        return JSONResponse(content={
            "success": False,
            "message": str(e)
        })

@app.get('/download/{file_id}')
async def download_file(file_id: str):
    """下载共享文件"""
    try:
        shared_path = os.path.join(os.getcwd(), "shared_files")
        file_path = os.path.join(shared_path, file_id)

        if not os.path.exists(file_path):
            return JSONResponse(content={
                "success": False,
                "message": "文件不存在"
            })

        print(f"[*] 文件下载: {file_id}")

        # 使用FileResponse返回文件，自动处理下载
        return FileResponse(
            path=file_path,
            filename=file_id,
            media_type='application/octet-stream'
        )

    except Exception as e:
        print(f"[!] 下载文件时出错: {e}")
        return JSONResponse(content={
            "success": False,
            "message": str(e)
        })

@app.get('/download_received/{file_id}')
async def download_received_file(file_id: str):
    """下载已上传文件（received_files目录）"""
    try:
        received_path = os.path.join(os.getcwd(), "received_files")
        file_path = os.path.join(received_path, file_id)

        if not os.path.exists(file_path):
            return JSONResponse(content={
                "success": False,
                "message": "文件不存在"
            })

        print(f"[*] 文件下载: {file_id}")

        # 使用FileResponse返回文件，自动处理下载
        return FileResponse(
            path=file_path,
            filename=file_id,
            media_type='application/octet-stream'
        )

    except Exception as e:
        print(f"[!] 下载文件时出错: {e}")
        return JSONResponse(content={
            "success": False,
            "message": str(e)
        })

@app.post('/upload_text')
async def upload_text(text: str = Form(...), filename: str = Form(...)):
    """上传文本内容并保存为txt文件"""
    try:
        # 保存文件到shared_files目录
        shared_path = os.path.join(os.getcwd(), "shared_files")
        os.makedirs(shared_path, exist_ok=True)

        # 清理文件名，移除不合法字符
        safe_filename = re.sub(r'[<>:"/\\|?*]', '', filename)

        # 限制文件名长度
        if len(safe_filename) > 200:
            name, ext = os.path.splitext(safe_filename)
            safe_filename = name[:190] + ext

        # 确保文件名不为空
        if not safe_filename:
            safe_filename = 'text_file.txt'

        # 确保有.txt后缀
        if not safe_filename.endswith('.txt'):
            safe_filename += '.txt'

        # 保存文件
        file_location = os.path.join(shared_path, safe_filename)
        with open(file_location, "w", encoding="utf-8") as f:
            f.write(text)

        # 获取文件大小
        file_size = os.path.getsize(file_location)

        print(f"[*] 文本已保存: {safe_filename} ({file_size} 字节)")

        return JSONResponse(content={
            "success": True,
            "message": "文本上传成功",
            "filename": safe_filename,
            "size": file_size
        })

    except Exception as e:
        print(f"[!] 处理文本上传时出错: {e}")
        return JSONResponse(content={
            "success": False,
            "message": str(e)
        })

@app.get('/preview/{file_id}')
async def preview_file(file_id: str):
    """预览文件内容（仅支持小于100KB的文件）"""
    try:
        shared_path = os.path.join(os.getcwd(), "shared_files")
        file_path = os.path.join(shared_path, file_id)

        if not os.path.exists(file_path):
            return JSONResponse(content={
                "success": False,
                "message": "文件不存在"
            })

        # 检查文件大小
        file_size = os.path.getsize(file_path)
        if file_size > 102400:  # 100KB = 102400字节
            return JSONResponse(content={
                "success": False,
                "message": "文件过大，无法预览（超过100KB）"
            })

        # 读取文件内容
        try:
            # 首先尝试以UTF-8编码读取
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            # 如果UTF-8失败，尝试GBK编码
            try:
                with open(file_path, "r", encoding="gbk") as f:
                    content = f.read()
            except UnicodeDecodeError:
                # 如果还是失败，尝试Latin-1编码
                try:
                    with open(file_path, "r", encoding="latin-1") as f:
                        content = f.read()
                except Exception:
                    return JSONResponse(content={
                        "success": False,
                        "message": "文件编码不支持，无法预览"
                    })

        print(f"[*] 文件预览: {file_id} ({file_size} 字节)")

        return JSONResponse(content={
            "success": True,
            "content": content,
            "size": file_size
        })

    except Exception as e:
        print(f"[!] 预览文件时出错: {e}")
        return JSONResponse(content={
            "success": False,
            "message": str(e)
        })

@app.get('/preview_received/{file_id}')
async def preview_received_file(file_id: str):
    """预览已上传文件内容（received_files目录，仅支持小于100KB的文件）"""
    try:
        received_path = os.path.join(os.getcwd(), "received_files")
        file_path = os.path.join(received_path, file_id)

        if not os.path.exists(file_path):
            return JSONResponse(content={
                "success": False,
                "message": "文件不存在"
            })

        # 检查文件大小
        file_size = os.path.getsize(file_path)
        if file_size > 102400:  # 100KB = 102400字节
            return JSONResponse(content={
                "success": False,
                "message": "文件过大，无法预览（超过100KB）"
            })

        # 读取文件内容
        try:
            # 首先尝试以UTF-8编码读取
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            # 如果UTF-8失败，尝试GBK编码
            try:
                with open(file_path, "r", encoding="gbk") as f:
                    content = f.read()
            except UnicodeDecodeError:
                # 如果还是失败，尝试Latin-1编码
                try:
                    with open(file_path, "r", encoding="latin-1") as f:
                        content = f.read()
                except Exception:
                    return JSONResponse(content={
                        "success": False,
                        "message": "文件编码不支持，无法预览"
                    })

        print(f"[*] 文件预览: {file_id} ({file_size} 字节)")

        return JSONResponse(content={
            "success": True,
            "content": content,
            "size": file_size
        })

    except Exception as e:
        print(f"[!] 预览文件时出错: {e}")
        return JSONResponse(content={
            "success": False,
            "message": str(e)
        })

@app.post('/delete_shared/{file_id}')
async def delete_shared_file(file_id: str):
    """删除共享文件（shared_files目录）"""
    try:
        shared_path = os.path.join(os.getcwd(), "shared_files")
        file_path = os.path.join(shared_path, file_id)

        if not os.path.exists(file_path):
            return JSONResponse(content={
                "success": False,
                "message": "文件不存在"
            })

        # 删除文件
        os.remove(file_path)
        print(f"[*] 文件已删除: {file_id}")

        return JSONResponse(content={
            "success": True,
            "message": "文件删除成功"
        })

    except Exception as e:
        print(f"[!] 删除文件时出错: {e}")
        return JSONResponse(content={
            "success": False,
            "message": str(e)
        })

@app.post('/delete_received/{file_id}')
async def delete_received_file(file_id: str):
    """删除已上传文件（received_files目录）"""
    try:
        received_path = os.path.join(os.getcwd(), "received_files")
        file_path = os.path.join(received_path, file_id)

        if not os.path.exists(file_path):
            return JSONResponse(content={
                "success": False,
                "message": "文件不存在"
            })

        # 删除文件
        os.remove(file_path)
        print(f"[*] 文件已删除: {file_id}")

        return JSONResponse(content={
            "success": True,
            "message": "文件删除成功"
        })

    except Exception as e:
        print(f"[!] 删除文件时出错: {e}")
        return JSONResponse(content={
            "success": False,
            "message": str(e)
        })

if __name__ == "__main__":
    import uvicorn
    import sys
    import json
    import os
    
    # 加载配置文件
    def load_config():
        default_config = {
            "port": 5000
        }
        
        config_path = "config.json"
        
        if not os.path.exists(config_path):
            return default_config
        
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            
            if "port" not in config or not isinstance(config["port"], int):
                return default_config
            
            if not (1024 <= config["port"] <= 65535):
                return default_config
            
            return config
        except Exception:
            return default_config
    
    # 解析命令行参数，优先使用命令行参数
    default_port = 5000
    port = default_port
    
    # 先从配置文件加载
    config = load_config()
    port = config["port"]
    
    # 如果有命令行参数，覆盖配置文件
    if len(sys.argv) > 1:
        try:
            cmd_port = int(sys.argv[1])
            if 1024 <= cmd_port <= 65535:
                port = cmd_port
                print(f"使用命令行指定的端口: {port}")
        except ValueError:
            print(f"无效的端口号参数，使用配置文件端口: {port}")
    
    print(f"[*] 服务器启动，访问地址: http://0.0.0.0:{port}")
    print(f"[*] 请确保客户端使用相同的预共享密钥")
    uvicorn.run(app, host="0.0.0.0", port=port, reload=False)