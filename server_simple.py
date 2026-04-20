from pathlib import Path
import json
import os
import re
import time

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates

# 预共享密钥（需要在客户端和服务端保持一致）
PRE_SHARED_KEY = b"your_secure_pre_shared_key_here"  # 请更换为强密钥

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
RECEIVED_DIR = BASE_DIR / "received_files"
SHARED_DIR = BASE_DIR / "shared_files"
CONFIG_PATH = BASE_DIR / "config.json"
INVALID_FILENAME_PATTERN = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
MAX_FILENAME_LENGTH = 200
DEFAULT_PORT = 5000
HIDDEN_FILE_NAMES = {".DS_Store"}

app = FastAPI()
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
RECEIVED_DIR.mkdir(exist_ok=True)
SHARED_DIR.mkdir(exist_ok=True)


def load_config():
    default_config = {"port": DEFAULT_PORT}
    if not CONFIG_PATH.exists():
        return default_config

    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as config_file:
            config = json.load(config_file)
    except Exception:
        return default_config

    port = config.get("port")
    if isinstance(port, int) and 1024 <= port <= 65535:
        return {"port": port}
    return default_config


def sanitize_filename(filename: str, default_name: str) -> str:
    safe_name = Path(filename or "").name.strip()
    safe_name = INVALID_FILENAME_PATTERN.sub("", safe_name).rstrip(" ")
    if safe_name in {"", ".", ".."}:
        safe_name = default_name

    if len(safe_name) > MAX_FILENAME_LENGTH:
        name, ext = os.path.splitext(safe_name)
        safe_name = name[: MAX_FILENAME_LENGTH - len(ext)] + ext

    return safe_name or default_name


def get_unique_file_path(base_dir: Path, filename: str) -> Path:
    candidate = base_dir / filename
    if not candidate.exists():
        return candidate

    stem = candidate.stem
    suffix = candidate.suffix
    counter = 1
    while True:
        next_candidate = base_dir / f"{stem}_{counter}{suffix}"
        if not next_candidate.exists():
            return next_candidate
        counter += 1


def resolve_existing_file(base_dir: Path, file_id: str) -> Path:
    if not file_id:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    if file_id != Path(file_id).name:
        raise HTTPException(status_code=400, detail="非法文件路径")

    safe_name = sanitize_filename(file_id, "")
    if safe_name != file_id:
        raise HTTPException(status_code=400, detail="非法文件名")

    file_path = (base_dir / safe_name).resolve()
    if file_path.parent != base_dir.resolve() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")
    return file_path


def build_file_info(base_dir: Path):
    files = []
    for file_path in base_dir.iterdir():
        if file_path.name in HIDDEN_FILE_NAMES:
            continue
        if file_path.is_file():
            file_stats = file_path.stat()
            files.append({
                "id": file_path.name,
                "name": file_path.name,
                "size": file_stats.st_size,
                "mtime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(file_stats.st_mtime)),
            })
    files.sort(key=lambda item: item["mtime"], reverse=True)
    return files


def save_upload_files(files: list[UploadFile] | None, target_dir: Path, default_name: str, log_prefix: str):
    uploaded_count = 0
    for upload in files or []:
        try:
            safe_filename = sanitize_filename(upload.filename, default_name)
            file_path = get_unique_file_path(target_dir, safe_filename)
            with file_path.open("wb") as output_file:
                output_file.write(upload.file.read())
            uploaded_count += 1
            print(f"[*] {log_prefix}: {upload.filename} -> 保存为: {file_path.name}")
        except Exception as file_error:
            print(f"[!] 保存文件 {getattr(upload, 'filename', 'unknown')} 失败: {file_error}")
    return uploaded_count


@app.get('/')
def index(request: Request):
    """主页"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post('/upload')
async def upload(file: list[UploadFile] = File(None)):
    """处理文件上传（手机到电脑）"""
    try:
        uploaded_count = save_upload_files(file, RECEIVED_DIR, "uploaded_file", "收到文件")
        return JSONResponse(content={
            "success": True,
            "message": f"成功上传 {uploaded_count} 个文件",
            "uploaded_count": uploaded_count,
        })
    except Exception as error:
        print(f"[!] 处理文件上传时出错: {error}")
        return JSONResponse(content={
            "success": False,
            "message": str(error),
        }, status_code=500)


@app.post('/upload_shared')
async def upload_shared(file: list[UploadFile] = File(None)):
    """上传文件到共享目录（电脑到手机）"""
    try:
        uploaded_count = save_upload_files(file, SHARED_DIR, "shared_file", "共享文件上传")
        return JSONResponse(content={
            "success": True,
            "message": f"成功上传 {uploaded_count} 个共享文件",
            "uploaded_count": uploaded_count,
        })
    except Exception as error:
        print(f"[!] 处理共享文件上传时出错: {error}")
        return JSONResponse(content={
            "success": False,
            "message": str(error),
        }, status_code=500)


@app.get('/files')
async def get_files():
    """获取共享文件列表"""
    try:
        return JSONResponse(content={
            "success": True,
            "files": build_file_info(SHARED_DIR),
        })
    except Exception as error:
        print(f"[!] 获取文件列表时出错: {error}")
        return JSONResponse(content={
            "success": False,
            "message": str(error),
        }, status_code=500)


@app.get('/received_files')
async def get_received_files():
    """获取已上传文件列表（received_files目录）"""
    try:
        return JSONResponse(content={
            "success": True,
            "files": build_file_info(RECEIVED_DIR),
        })
    except Exception as error:
        print(f"[!] 获取已上传文件列表时出错: {error}")
        return JSONResponse(content={
            "success": False,
            "message": str(error),
        }, status_code=500)


@app.get('/download/{file_id}')
async def download_file(file_id: str):
    """下载共享文件"""
    try:
        file_path = resolve_existing_file(SHARED_DIR, file_id)
        print(f"[*] 文件下载: {file_id}")
        return FileResponse(path=str(file_path), filename=file_path.name, media_type='application/octet-stream')
    except HTTPException as error:
        return JSONResponse(content={"success": False, "message": error.detail}, status_code=error.status_code)
    except Exception as error:
        print(f"[!] 下载文件时出错: {error}")
        return JSONResponse(content={"success": False, "message": str(error)}, status_code=500)


@app.get('/download_received/{file_id}')
async def download_received_file(file_id: str):
    """下载已上传文件（received_files目录）"""
    try:
        file_path = resolve_existing_file(RECEIVED_DIR, file_id)
        print(f"[*] 文件下载: {file_id}")
        return FileResponse(path=str(file_path), filename=file_path.name, media_type='application/octet-stream')
    except HTTPException as error:
        return JSONResponse(content={"success": False, "message": error.detail}, status_code=error.status_code)
    except Exception as error:
        print(f"[!] 下载文件时出错: {error}")
        return JSONResponse(content={"success": False, "message": str(error)}, status_code=500)


@app.post('/upload_text')
async def upload_text(text: str = Form(...), filename: str = Form(...)):
    """上传文本内容并保存为txt文件"""
    try:
        safe_filename = sanitize_filename(filename, 'text_file.txt')
        if not safe_filename.endswith('.txt'):
            safe_filename += '.txt'

        file_path = get_unique_file_path(SHARED_DIR, safe_filename)
        with file_path.open("w", encoding="utf-8") as output_file:
            output_file.write(text)

        file_size = file_path.stat().st_size
        print(f"[*] 文本已保存: {file_path.name} ({file_size} 字节)")

        return JSONResponse(content={
            "success": True,
            "message": "文本上传成功",
            "filename": file_path.name,
            "size": file_size,
        })
    except Exception as error:
        print(f"[!] 处理文本上传时出错: {error}")
        return JSONResponse(content={
            "success": False,
            "message": str(error),
        }, status_code=500)


@app.get('/preview/{file_id}')
async def preview_file(file_id: str):
    """预览文件内容（仅支持小于100KB的文件）"""
    try:
        file_path = resolve_existing_file(SHARED_DIR, file_id)
        file_size = file_path.stat().st_size
        if file_size > 102400:
            return JSONResponse(content={
                "success": False,
                "message": "文件过大，无法预览（超过100KB）",
            }, status_code=400)

        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                content = file_path.read_text(encoding="gbk")
            except UnicodeDecodeError:
                try:
                    content = file_path.read_text(encoding="latin-1")
                except Exception:
                    return JSONResponse(content={
                        "success": False,
                        "message": "文件编码不支持，无法预览",
                    }, status_code=400)

        print(f"[*] 文件预览: {file_id} ({file_size} 字节)")
        return JSONResponse(content={"success": True, "content": content, "size": file_size})
    except HTTPException as error:
        return JSONResponse(content={"success": False, "message": error.detail}, status_code=error.status_code)
    except Exception as error:
        print(f"[!] 预览文件时出错: {error}")
        return JSONResponse(content={"success": False, "message": str(error)}, status_code=500)


@app.get('/preview_received/{file_id}')
async def preview_received_file(file_id: str):
    """预览已上传文件内容（received_files目录，仅支持小于100KB的文件）"""
    try:
        file_path = resolve_existing_file(RECEIVED_DIR, file_id)
        file_size = file_path.stat().st_size
        if file_size > 102400:
            return JSONResponse(content={
                "success": False,
                "message": "文件过大，无法预览（超过100KB）",
            }, status_code=400)

        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                content = file_path.read_text(encoding="gbk")
            except UnicodeDecodeError:
                try:
                    content = file_path.read_text(encoding="latin-1")
                except Exception:
                    return JSONResponse(content={
                        "success": False,
                        "message": "文件编码不支持，无法预览",
                    }, status_code=400)

        print(f"[*] 文件预览: {file_id} ({file_size} 字节)")
        return JSONResponse(content={"success": True, "content": content, "size": file_size})
    except HTTPException as error:
        return JSONResponse(content={"success": False, "message": error.detail}, status_code=error.status_code)
    except Exception as error:
        print(f"[!] 预览文件时出错: {error}")
        return JSONResponse(content={"success": False, "message": str(error)}, status_code=500)


@app.post('/delete_shared/{file_id}')
async def delete_shared_file(file_id: str):
    """删除共享文件（shared_files目录）"""
    try:
        file_path = resolve_existing_file(SHARED_DIR, file_id)
        file_path.unlink()
        print(f"[*] 文件已删除: {file_id}")
        return JSONResponse(content={"success": True, "message": "文件删除成功"})
    except HTTPException as error:
        return JSONResponse(content={"success": False, "message": error.detail}, status_code=error.status_code)
    except Exception as error:
        print(f"[!] 删除文件时出错: {error}")
        return JSONResponse(content={"success": False, "message": str(error)}, status_code=500)


@app.post('/delete_received/{file_id}')
async def delete_received_file(file_id: str):
    """删除已上传文件（received_files目录）"""
    try:
        file_path = resolve_existing_file(RECEIVED_DIR, file_id)
        file_path.unlink()
        print(f"[*] 文件已删除: {file_id}")
        return JSONResponse(content={"success": True, "message": "文件删除成功"})
    except HTTPException as error:
        return JSONResponse(content={"success": False, "message": error.detail}, status_code=error.status_code)
    except Exception as error:
        print(f"[!] 删除文件时出错: {error}")
        return JSONResponse(content={"success": False, "message": str(error)}, status_code=500)


if __name__ == "__main__":
    import sys
    import uvicorn

    port = load_config()["port"]
    if len(sys.argv) > 1:
        try:
            cmd_port = int(sys.argv[1])
            if 1024 <= cmd_port <= 65535:
                port = cmd_port
                print(f"使用命令行指定的端口: {port}")
        except ValueError:
            print(f"无效的端口号参数，使用配置文件端口: {port}")

    print(f"[*] 服务器启动，访问地址: http://0.0.0.0:{port}")
    print("[*] 请确保客户端使用相同的预共享密钥")
    uvicorn.run(app, host="0.0.0.0", port=port, reload=False)
