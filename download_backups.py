import tkinter as tk
from tkinter import filedialog, messagebox
import os
import json
import paramiko
import sys
import threading
from tkinter.ttk import Progressbar

# Tên file cấu hình
CONFIG_FILE_NAME = "servers.json"
SERVERS = {}
FIXED_PASSWORD = 'LvQuy'

def get_resource_path(relative_path):
    """Lấy đường dẫn đến file trong môi trường PyInstaller hoặc mã nguồn gốc."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    else:
        return os.path.join(os.path.dirname(__file__), relative_path)

def get_writable_path(filename):
    """Lấy đường dẫn có thể ghi trong thư mục Documents."""
    return os.path.join(os.path.expanduser('~/Documents'), filename)

def load_servers():
    global SERVERS
    config_path = get_resource_path(CONFIG_FILE_NAME)
    if not os.path.exists(config_path):
        config_path = get_writable_path(CONFIG_FILE_NAME)
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            SERVERS.update(json.load(f))

def save_servers():
    config_path = get_writable_path(CONFIG_FILE_NAME)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(SERVERS, f, indent=4, ensure_ascii=False)

def refresh_server_list():
    server_listbox.delete(0, tk.END)
    for name in SERVERS:
        server_listbox.insert(tk.END, name)

def add_or_update_server():
    name = entry_name.get().strip()
    ip = entry_ip.get().strip()
    user = entry_user.get().strip()
    pem = entry_pem.get().strip()
    remote_path = entry_remote_path.get().strip()
    local_folder = entry_local_folder.get().strip()

    if not name:
        messagebox.showerror("Lỗi", "Tên server không được để trống")
        return

    SERVERS[name] = {
        "ip": ip,
        "username": user,
        "pem": pem,
        "remote_path": remote_path,
        "local_folder": local_folder
    }
    save_servers()
    refresh_server_list()
    clear_inputs()
    messagebox.showinfo("Thành công", f"Đã lưu server '{name}'")

def delete_server():
    selection = server_listbox.curselection()
    if not selection:
        messagebox.showwarning("Cảnh báo", "Chọn server để xóa")
        return
    name = server_listbox.get(selection[0])
    if messagebox.askyesno("Xác nhận", f"Bạn có chắc muốn xóa server '{name}'?"):
        SERVERS.pop(name, None)
        save_servers()
        refresh_server_list()
        clear_inputs()

def on_select(event):
    selection = server_listbox.curselection()
    if selection:
        name = server_listbox.get(selection[0])
        server = SERVERS.get(name, {})
        entry_name.delete(0, tk.END)
        entry_name.insert(0, name)
        entry_ip.delete(0, tk.END)
        entry_ip.insert(0, server.get("ip", ""))
        entry_user.delete(0, tk.END)
        entry_user.insert(0, server.get("username", ""))
        entry_pem.delete(0, tk.END)
        entry_pem.insert(0, server.get("pem", ""))
        entry_remote_path.delete(0, tk.END)
        entry_remote_path.insert(0, server.get("remote_path", ""))
        entry_local_folder.delete(0, tk.END)
        entry_local_folder.insert(0, server.get("local_folder", ""))

        entry_download_ip.delete(0, tk.END)
        entry_download_ip.insert(0, server.get("ip", ""))
        entry_download_user.delete(0, tk.END)
        entry_download_user.insert(0, server.get("username", ""))
        entry_download_pem.delete(0, tk.END)
        entry_download_pem.insert(0, server.get("pem", ""))
        entry_download_remote_path.delete(0, tk.END)
        entry_download_remote_path.insert(0, server.get("remote_path", ""))
        entry_download_local_folder.delete(0, tk.END)
        entry_download_local_folder.insert(0, server.get("local_folder", ""))

def clear_inputs():
    for e in [entry_name, entry_ip, entry_user, entry_pem, entry_remote_path, entry_local_folder]:
        e.delete(0, tk.END)

def update_progress_bar(progress_bar, label, value, server_name=""):
    """Cập nhật giá trị và nhãn của progress bar."""
    progress_bar['value'] = value
    if server_name:
        label.config(text=f"{server_name}: {value:.1f}%")
    else:
        label.config(text=f"Tiến trình: {value:.1f}%")
    root.update_idletasks()

def download_file():
    ip = entry_download_ip.get().strip()
    user = entry_download_user.get().strip()
    pem = entry_download_pem.get().strip()
    remote_path = entry_download_remote_path.get().strip()
    local_folder = entry_download_local_folder.get().strip()

    if not (ip and user and pem and remote_path and local_folder):
        messagebox.showerror("Lỗi", "Điền đầy đủ thông tin")
        return

    # Tạo cửa sổ tiến trình
    progress_window = tk.Toplevel(root)
    progress_window.title("Tiến trình tải file")
    progress_window.geometry("300x100")

    progress_label = tk.Label(progress_window, text="Đang tải file...")
    progress_label.pack(pady=5)

    progress_bar = Progressbar(progress_window, length=200, mode='determinate')
    progress_bar.pack(pady=5)

    def download_task():
        try:
            key = paramiko.RSAKey.from_private_key_file(pem)
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname=ip, username=user, pkey=key)

            sftp = ssh.open_sftp()
            sftp.chdir(remote_path)

            files = sftp.listdir_attr()
            if not files:
                messagebox.showwarning("Không có file", "Thư mục không có file nào")
                sftp.close()
                ssh.close()
                progress_window.destroy()
                return

            newest_file = max(files, key=lambda f: f.st_mtime)
            remote_file_path = os.path.join(remote_path, newest_file.filename)
            local_file_path = os.path.join(local_folder, newest_file.filename)

            file_size = sftp.stat(remote_file_path).st_size
            if file_size == 0:
                update_progress_bar(progress_bar, progress_label, 100)
            else:
                sftp.getfo(remote_file_path, open(local_file_path, 'wb'), callback=lambda size, total=file_size: update_progress_bar(progress_bar, progress_label, (size / total) * 100))

            sftp.close()
            ssh.close()

            messagebox.showinfo("Thành công", f"Đã tải file mới nhất:\n{newest_file.filename}")
        except Exception as e:
            messagebox.showerror("Lỗi tải file", str(e))
        finally:
            progress_window.destroy()

    # Chạy luồng tải file
    download_thread = threading.Thread(target=download_task)
    download_thread.start()

def download_all_servers():
    config_path = get_resource_path(CONFIG_FILE_NAME)
    if not os.path.exists(config_path):
        config_path = get_writable_path(CONFIG_FILE_NAME)

    if not os.path.exists(config_path):
        messagebox.showerror("Lỗi", "Không tìm thấy file servers.json")
        return

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            servers = json.load(f)

        if not servers:
            messagebox.showinfo("Thông báo", "Danh sách server trống")
            return

        # Tạo cửa sổ tiến trình
        progress_window = tk.Toplevel(root)
        progress_window.title("Tiến trình tải tất cả")
        progress_window.geometry("300x100")

        progress_label = tk.Label(progress_window, text="Đang tải...")
        progress_label.pack(pady=5)

        progress_bar = Progressbar(progress_window, length=200, mode='determinate', maximum=len(servers))
        progress_bar.pack(pady=5)

        def download_all_task():
            for idx, (name, info) in enumerate(servers.items()):
                ip = info.get("ip")
                user = info.get("username")
                pem = info.get("pem")
                remote_path = info.get("remote_path")
                local_folder = info.get("local_folder")

                try:
                    key = paramiko.RSAKey.from_private_key_file(pem)
                    ssh = paramiko.SSHClient()
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    ssh.connect(hostname=ip, username=user, pkey=key)

                    sftp = ssh.open_sftp()
                    sftp.chdir(remote_path)

                    files = sftp.listdir_attr()
                    if not files:
                        print(f"[{name}] Không có file nào trong thư mục")
                        sftp.close()
                        ssh.close()
                        update_progress_bar(progress_bar, progress_label, (idx + 1) / len(servers) * 100, name)
                        continue

                    newest_file = max(files, key=lambda f: f.st_mtime)
                    remote_file_path = os.path.join(remote_path, newest_file.filename)
                    local_file_path = os.path.join(local_folder, newest_file.filename)

                    file_size = sftp.stat(remote_file_path).st_size
                    if file_size == 0:
                        sftp.get(remote_file_path, local_file_path)
                        update_progress_bar(progress_bar, progress_label, (idx + 1) / len(servers) * 100, name)
                    else:
                        sftp.getfo(remote_file_path, open(local_file_path, 'wb'), callback=lambda size, total=file_size, i=idx, n=name: update_progress_bar(progress_bar, progress_label, (i + (size / total)) / len(servers) * 100, n))

                    sftp.close()
                    ssh.close()

                except Exception as e:
                    messagebox.showerror("Lỗi", f"[{name}] Lỗi khi tải: {str(e)}")
                    update_progress_bar(progress_bar, progress_label, (idx + 1) / len(servers) * 100, name)

            messagebox.showinfo("Xong", "Đã tải xong tất cả server")
            progress_window.destroy()

        # Chạy luồng tải tất cả
        download_all_thread = threading.Thread(target=download_all_task)
        download_all_thread.start()

    except Exception as e:
        messagebox.showerror("Lỗi chung", str(e))

def show_login_window():
    login_window = tk.Toplevel()
    login_window.title("Đăng nhập")
    login_window.geometry("300x200")
    login_window.resizable(False, False)

    # Đặt cửa sổ đăng nhập ở giữa màn hình
    login_window.update_idletasks()
    width = login_window.winfo_width()
    height = login_window.winfo_height()
    x = (login_window.winfo_screenwidth() // 2) - (width // 2)
    y = (login_window.winfo_screenheight() // 2) - (height // 2)
    login_window.geometry(f"{width}x{height}+{x}+{y}")

    # Vô hiệu hóa cửa sổ chính
    root.withdraw()

    # Thêm nhãn "Bảng Đăng Nhập"
    tk.Label(login_window, text="Backup Rostek", font=("Arial", 14, "bold")).pack(pady=10)

    tk.Label(login_window, text="Mật khẩu:").pack()
    password_entry = tk.Entry(login_window, show="*", width=20)
    password_entry.pack(pady=5)

    # Thêm nhãn "Vào khung login"
    tk.Label(login_window, text="LvQuy").pack(pady=5)

    def check_login():
        password = password_entry.get().strip()
        if password == FIXED_PASSWORD:
            login_window.destroy()
            root.deiconify()  # Hiển thị lại cửa sổ chính
            load_servers()
            refresh_server_list()
        else:
            messagebox.showerror("Lỗi", "Mật khẩu không đúng")
            password_entry.delete(0, tk.END)

    tk.Button(login_window, text="Đăng nhập", command=check_login).pack(pady=10)
    password_entry.focus_set()

    # Xử lý khi nhấn Enter
    password_entry.bind("<Return>", lambda event: check_login())

    # Xử lý khi đóng cửa sổ đăng nhập
    def on_closing():
        login_window.destroy()
        root.destroy()

    login_window.protocol("WM_DELETE_WINDOW", on_closing)

# ==== Giao diện ====
root = tk.Tk()
root.title("Quản lý server & Tải file")

frame_left = tk.LabelFrame(root, text="📋 Quản lý server")
frame_left.pack(side=tk.LEFT, padx=10, pady=10)

server_listbox = tk.Listbox(frame_left, width=30, height=15)
server_listbox.pack()
server_listbox.bind("<<ListboxSelect>>", on_select)

tk.Button(frame_left, text="🗑️ Xóa", command=delete_server).pack(pady=5)

frame_form = tk.Frame(frame_left)
frame_form.pack()

labels = ["Tên:", "IP:", "Username:", "PEM Key:", "Remote Path:", "Local Folder:"]
entries = []
for i, text in enumerate(labels):
    tk.Label(frame_form, text=text).grid(row=i, column=0, sticky="e")
    entry = tk.Entry(frame_form, width=25)
    entry.grid(row=i, column=1)
    entries.append(entry)

entry_name, entry_ip, entry_user, entry_pem, entry_remote_path, entry_local_folder = entries
tk.Button(frame_form, text="💾 Lưu / Cập nhật", command=add_or_update_server).grid(row=6, column=0, columnspan=2, pady=5)

frame_download_all = tk.Frame(root)
frame_download_all.pack(pady=5)

btn_download_all = tk.Button(frame_download_all, text="Tải tất cả", command=download_all_servers, bg="green", fg="white")
btn_download_all.pack()

frame_right = tk.LabelFrame(root, text="⬇️ Tải file từ server")
frame_right.pack(side=tk.RIGHT, padx=10, pady=10)

labels2 = ["IP:", "Username:", "PEM Key:", "Remote Path:", "Local Folder:", "Tên file:"]
entries2 = []
for i, text in enumerate(labels2):
    tk.Label(frame_right, text=text).grid(row=i, column=0, sticky="e")
    entry = tk.Entry(frame_right, width=40)
    entry.grid(row=i, column=1)
    entries2.append(entry)

entry_download_ip, entry_download_user, entry_download_pem, entry_download_remote_path, entry_download_local_folder, entry_download_filename = entries2

tk.Button(frame_right, text="⬇️ Tải file", command=download_file).grid(row=6, column=0, columnspan=2, pady=10)

# Hiển thị cửa sổ đăng nhập trước khi chạy giao diện chính
show_login_window()

root.mainloop()