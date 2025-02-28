import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import threading
import os
import requests
import subprocess
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

try:
    from Crypto.Cipher import AES
except ModuleNotFoundError:
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pycryptodome"])
    from Crypto.Cipher import AES

def log_message(message):
    text_log.insert(tk.END, message + "\n")
    text_log.see(tk.END)  # 自动滚动到最新日志

def download_file(m3u8_url, key_url, progress, output_dir, decrypted_dir, output_file):
    try:
        log_message(f"开始处理 m3u8 文件: {m3u8_url}")
        process_m3u8(m3u8_url, key_url, output_dir, decrypted_dir, output_file, progress=progress)
        log_message("处理完成")
    except Exception as e:
        label_status.config(text=f"处理失败: {e}")
        log_message(f"处理失败: {e}")

def start_download():
    global download_thread
    m3u8_url = entry_url.get()
    key_url = entry_key.get()
    output_dir = entry_output_dir.get()
    decrypted_dir = os.path.join(output_dir, 'tmp')  # 修改解密目录为输出目录下的 tmp 目录
    output_file = os.path.join(output_dir, 'output.mp4')
    progress['value'] = 0
    label_status.config(text="处理进度: 0%")
    log_message("开始处理")
    download_thread = threading.Thread(target=download_file, args=(m3u8_url, key_url, progress, output_dir, decrypted_dir, output_file))
    download_thread.start()

def stop_download():
    global download_thread
    if download_thread and download_thread.is_alive():
        download_thread.join(timeout=1)  # 等待线程结束，最多等待1秒
        if download_thread.is_alive():
            download_thread = None  # 强制结束线程
        label_status.config(text="下载已停止")
        log_message("下载已停止")
        # 调用 clean_up 方法清理中间文件
        clean_up([entry_output_dir.get(), os.path.join(entry_output_dir.get(), 'tmp')])
        log_message("中间文件已清理")

def select_output_directory():
    output_dir = filedialog.askdirectory()
    entry_output_dir.delete(0, tk.END)
    entry_output_dir.insert(0, output_dir)

def main():
    # 创建主窗口
    global root, progress, label_status, entry_url, entry_key, entry_output_dir, text_log
    root = tk.Tk()
    root.title("下载器应用")
    root.geometry("600x400")  # 调整窗口大小

    # 使窗口在屏幕中间显示
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width - 600) // 2
    y = (screen_height - 400) // 2
    root.geometry(f"+{x}+{y}")

    # 添加下载地址输入框
    label_url = tk.Label(root, text="下载地址:", font=("Arial", 12))
    label_url.grid(row=0, column=0, padx=10, pady=5, sticky="w")
    entry_url = tk.Entry(root, width=50, font=("Arial", 12))
    entry_url.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

    # 添加密钥文件地址输入框
    label_key = tk.Label(root, text="密钥文件地址:", font=("Arial", 12))
    label_key.grid(row=1, column=0, padx=10, pady=5, sticky="w")
    entry_key = tk.Entry(root, width=50, font=("Arial", 12))
    entry_key.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

    # 添加输出目录输入框
    label_output_dir = tk.Label(root, text="输出目录:", font=("Arial", 12))
    label_output_dir.grid(row=2, column=0, padx=10, pady=5, sticky="w")
    entry_output_dir = tk.Entry(root, width=50, font=("Arial", 12))
    entry_output_dir.grid(row=2, column=1, padx=10, pady=5, sticky="ew")

    # 添加选择输出目录按钮
    button_select_output_dir = tk.Button(root, text="选择目录", command=select_output_directory, font=("Arial", 12))
    button_select_output_dir.grid(row=2, column=2, padx=10, pady=5, sticky="w")

    # 添加下载按钮
    button_download = tk.Button(root, text="开始下载", command=start_download, font=("Arial", 12))
    button_download.grid(row=4, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

    # 添加停止下载按钮
    button_stop_download = tk.Button(root, text="停止下载", command=stop_download, font=("Arial", 12))
    button_stop_download.grid(row=4, column=2, padx=10, pady=10, sticky="w")

    # 添加进度条
    progress = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate")
    progress.grid(row=5, column=0, columnspan=3, padx=10, pady=10, sticky="ew")

    # 添加状态标签
    label_status = tk.Label(root, text="下载进度: 0%", font=("Arial", 12))
    label_status.grid(row=6, column=0, columnspan=3, padx=10, pady=5, sticky="w")

    # 添加日志文本框
    text_log = tk.Text(root, height=10, width=60, font=("Arial", 10))
    text_log.grid(row=7, column=0, columnspan=3, padx=10, pady=10, sticky="ew")

    # 设置焦点到 entry_url 输入框
    entry_url.focus_set()

    # 运行主循环
    root.mainloop()

def download_m3u8(m3u8_url, output_dir):
    response = requests.get(m3u8_url)
    response.raise_for_status()
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    m3u8_path = os.path.join(output_dir, 'playlist.m3u8')
    with open(m3u8_path, 'w') as f:
        f.write(response.text)
    
    return m3u8_path, response.text

def download_key(key_url):
    response = requests.get(key_url)
    response.raise_for_status()
    return response.content

def download_ts_file(ts_url, output_dir):
    ts_filename = os.path.join(output_dir, os.path.basename(ts_url))
    try:
        response = requests.get(ts_url, timeout=10)
        response.raise_for_status()
        with open(ts_filename, 'wb') as f:
            f.write(response.content)
    except requests.exceptions.RequestException as e:
        print(f"Error downloading {ts_url}: {e}")

def download_ts_files(m3u8_content, base_url, output_dir, progress=None, max_workers=5):
    ts_urls = [urljoin(base_url, line) for line in m3u8_content.splitlines() if line and not line.startswith("#")]
    
    if progress:
        progress['value'] = 0
        progress.update()
    
    print("开始下载 .ts 文件...")
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {executor.submit(download_ts_file, ts_url, output_dir): ts_url for ts_url in ts_urls}
        for future in tqdm(as_completed(future_to_url), total=len(ts_urls), desc="Downloading"):
            ts_url = future_to_url[future]
            try:
                future.result()
                if progress:
                    progress['value'] += 100 / len(ts_urls)
                    progress.update()
                    label_status.config(text=f"下载进度: {int(progress['value'])}%")  # 更新进度百分比到 label_status
            except Exception as e:
                print(f"Error downloading {ts_url}: {e}")
    print("所有 .ts 文件下载完成。")
    label_status.config(text=f"下载进度: 100%")

def decrypt_ts_file(ts_file_path, key, iv, output_dir):
    try:
        with open(ts_file_path, 'rb') as f:
            encrypted_data = f.read()
        
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted_data = cipher.decrypt(encrypted_data)
        
        padding_length = decrypted_data[-1]
        decrypted_data = decrypted_data[:-padding_length]
        
        decrypted_file_path = os.path.join(output_dir, os.path.basename(ts_file_path))
        with open(decrypted_file_path, 'wb') as f:
            f.write(decrypted_data)
    except FileNotFoundError:
        print(f"File not found, skipping: {ts_file_path}")

def decrypt_all_ts_files(m3u8_file, key_url, output_dir):
    with open(m3u8_file, 'r') as f:
        lines = f.readlines()
    
    iv = None
    ts_files = []
    for line in lines:
        if line.startswith('#EXT-X-KEY'):
            iv_str = line.split('IV=')[1].strip()
            iv = bytes.fromhex(iv_str[2:])
        elif line.endswith('.ts\n'):
            ts_files.append(line.strip())
    
    key = download_key(key_url)
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    for ts_file in ts_files:
        ts_file_path = os.path.join(os.path.dirname(m3u8_file), ts_file)
        decrypt_ts_file(ts_file_path, key, iv, output_dir)

def create_file_list(ts_dir, file_list_path):
    with open(file_list_path, 'w') as file_list:
        for ts_file in sorted(os.listdir(ts_dir)):
            if ts_file.endswith('.ts'):
                abs_path = os.path.abspath(os.path.join(ts_dir, ts_file))
                file_list.write(f"file '{abs_path}'\n")

def convert_to_mp4(ts_dir, output_file):
    file_list_path = os.path.join(ts_dir, 'file_list.txt')
    create_file_list(ts_dir, file_list_path)
    
    command = [
        'ffmpeg',
        '-f', 'concat',
        '-safe', '0',
        '-i', file_list_path,
        '-c', 'copy',
        output_file
    ]
    
    try:
        subprocess.run(command, check=True)
        print(f'转换完成，视频已保存为 {output_file}')
    except subprocess.CalledProcessError as e:
        print(f"Error occurred: {e}")

def clean_up(dirs):
    for dir_path in dirs:
        for file in os.listdir(dir_path):
            file_path = os.path.join(dir_path, file)
            try:
                if os.path.isfile(file_path) and not file_path.endswith('.mp4'):
                    os.unlink(file_path)
            except Exception as e:
                print(f"Error deleting file {file_path}: {e}")

def process_m3u8(m3u8_url, key_url, output_dir, decrypted_dir, output_file, progress=None, max_workers=10):
    log_message("下载开始")
    log_message("m3u8文件下载开始")  # 添加开始处理日志
    # 下载 m3u8 文件
    m3u8_path, m3u8_content = download_m3u8(m3u8_url, output_dir)
    log_message("m3u8文件下载完成")
    log_message("ts文件下载开始")
    # 下载所有 .ts 文件
    download_ts_files(m3u8_content, m3u8_url, output_dir, progress=progress, max_workers=max_workers)
    log_message("ts文件下载完成")
    log_message("ts文件解密开始")
    # 解密所有 .ts 文件
    decrypt_all_ts_files(m3u8_path, key_url, decrypted_dir)
    log_message("ts文件解密完成")
    # 合并并转换为 mp4
    log_message("MP4文件转换开始")
    convert_to_mp4(decrypted_dir, output_file)
    log_message("MP4文件转换完成")
    # 清理中间文件
    clean_up([output_dir, decrypted_dir])
    log_message("下载完成")  # 添加处理完成日志

if __name__ == "__main__":
    main()