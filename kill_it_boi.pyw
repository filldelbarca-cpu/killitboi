"""
Kill it Boi!  -  Cierra de golpe la ventana (proceso) que toques en pantalla.

Solo Windows.  Dependencias:  pip install pillow pystray
Archivos junto al script:
    815221970095488149.jpe                 (logo)
    skull-and-crossbones-free-png.webp     (cursor calavera)

Uso: botón "Kill it!" -> el cursor se vuelve calavera -> clic izquierdo sobre
cualquier ventana = TerminateProcess (sin preguntar).  Clic derecho = cancelar.
"""
import base64
import ctypes
import io
import os
import queue
import struct
import sys
import tempfile
import threading
import atexit
from ctypes import wintypes

import tkinter as tk
from tkinter import messagebox
from PIL import Image

APP_NAME = "Kill it Boi!"
LOGO_NAME = "815221970095488149.jpe"
SKULL_NAME = "skull-and-crossbones-free-png.webp"
CURSOR_SIZE = 48


# ----------------------------------------------------------------- recursos
def _search_dirs():
    dirs = []
    if getattr(sys, "frozen", False):
        dirs.append(getattr(sys, "_MEIPASS", ""))
        dirs.append(os.path.dirname(sys.executable))
    dirs.append(os.path.dirname(os.path.abspath(__file__)))
    return [d for d in dirs if d]


def find_asset(name):
    stem = os.path.splitext(name)[0]
    for d in _search_dirs():
        p = os.path.join(d, name)
        if os.path.isfile(p):
            return p
        for ext in (".jpe", ".jpg", ".jpeg", ".png", ".webp"):
            p = os.path.join(d, stem + ext)
            if os.path.isfile(p):
                return p
    return None


def load_image(name):
    path = find_asset(name)
    if not path:
        return None
    try:
        return Image.open(path).convert("RGBA")
    except Exception:
        return None


def build_cur_bytes(img, size=CURSOR_SIZE):
    """Crea un archivo .cur (32 bpp con alpha) a partir de una imagen."""
    img = img.convert("RGBA")
    img.thumbnail((size, size), Image.LANCZOS)          # conserva proporciones
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.paste(img, ((size - img.width) // 2, (size - img.height) // 2))
    img = canvas
    pixels = img.transpose(Image.FLIP_TOP_BOTTOM).tobytes("raw", "BGRA")
    mask_row = ((size + 31) // 32) * 4
    mask = b"\x00" * (mask_row * size)
    dib_header = struct.pack("<IiiHHIIiiII", 40, size, size * 2, 1, 32, 0,
                             len(pixels) + len(mask), 0, 0, 0, 0)
    data = dib_header + pixels + mask
    hot = size // 2
    icondir = struct.pack("<HHH", 0, 2, 1)
    entry = struct.pack("<BBBBHHII", size, size, 0, 0, hot, hot, len(data), 22)
    return icondir + entry + data


def png_b64(img, max_h=None):
    img = img.copy()
    if max_h:
        img.thumbnail((max_h * 3, max_h), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return base64.b64encode(buf.getvalue()), img


if sys.platform != "win32":
    sys.exit("Kill it Boi! solo funciona en Windows.")

import pystray  # noqa: E402

# ------------------------------------------------------------------- Win32
user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

LRESULT = ctypes.c_ssize_t
HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, ctypes.c_size_t, ctypes.c_ssize_t)


class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [("pt", wintypes.POINT), ("mouseData", wintypes.DWORD),
                ("flags", wintypes.DWORD), ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.c_size_t)]


user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD]
user32.SetWindowsHookExW.restype = ctypes.c_void_p
user32.UnhookWindowsHookEx.argtypes = [ctypes.c_void_p]
user32.CallNextHookEx.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_size_t, ctypes.c_ssize_t]
user32.CallNextHookEx.restype = LRESULT
user32.WindowFromPoint.argtypes = [wintypes.POINT]
user32.WindowFromPoint.restype = wintypes.HWND
user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
user32.GetAncestor.restype = wintypes.HWND
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.LoadImageW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR, wintypes.UINT,
                              ctypes.c_int, ctypes.c_int, wintypes.UINT]
user32.LoadImageW.restype = ctypes.c_void_p
user32.CopyImage.argtypes = [ctypes.c_void_p, wintypes.UINT, ctypes.c_int, ctypes.c_int, wintypes.UINT]
user32.CopyImage.restype = ctypes.c_void_p
user32.SetSystemCursor.argtypes = [ctypes.c_void_p, wintypes.DWORD]
user32.DestroyCursor.argtypes = [ctypes.c_void_p]
user32.SystemParametersInfoW.argtypes = [wintypes.UINT, wintypes.UINT, ctypes.c_void_p, wintypes.UINT]
user32.PostThreadMessageW.argtypes = [wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
user32.PeekMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND,
                                wintypes.UINT, wintypes.UINT, wintypes.UINT]
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD,
                                                wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = wintypes.HMODULE

WH_MOUSE_LL = 14
WM_QUIT = 0x0012
WM_LBUTTONDOWN, WM_LBUTTONUP = 0x0201, 0x0202
WM_RBUTTONDOWN, WM_RBUTTONUP = 0x0204, 0x0205
GA_ROOT = 2
PROCESS_TERMINATE = 0x0001
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
WM_CLOSE = 0x0010
IMAGE_CURSOR, LR_LOADFROMFILE = 2, 0x0010
SPI_SETCURSORS = 0x0057
# Cursores del sistema que se reemplazan (flecha, texto, mano, espera, etc.)
SYSTEM_CURSORS = [32512, 32513, 32514, 32515, 32516, 32640, 32641, 32642, 32643,
                  32644, 32645, 32646, 32648, 32649, 32650, 32651]
PROTECTED_CLASSES = {"Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd"}


def restore_cursors():
    user32.SystemParametersInfoW(SPI_SETCURSORS, 0, None, 0)


def enable_dpi_awareness():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            user32.SetProcessDPIAware()
        except Exception:
            pass


# --------------------------------------------------------------------- app
class KillItBoi:
    def __init__(self):
        enable_dpi_awareness()
        atexit.register(restore_cursors)

        self.events = queue.Queue()
        self.armed = False
        self.finished = False
        self.hook_tid = None
        self.was_visible = True
        self._cb = HOOKPROC(self._hook_proc)

        self.logo_img = load_image(LOGO_NAME)
        self.skull_img = load_image(SKULL_NAME)
        self.cur_path = None
        if self.skull_img is not None:
            fd, self.cur_path = tempfile.mkstemp(suffix=".cur")
            with os.fdopen(fd, "wb") as f:
                f.write(build_cur_bytes(self.skull_img))

        self._build_ui()
        self._build_tray()
        self.root.after(80, self._poll)

    # ---- interfaz
    def _build_ui(self):
        bg = "#1b1b1f"
        self.root = tk.Tk()
        self.root.title(APP_NAME)
        self.root.configure(bg=bg)
        self.root.geometry("320x380")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)

        self._photo = None
        if self.logo_img is not None:
            data, _ = png_b64(self.logo_img, max_h=130)
            self._photo = tk.PhotoImage(data=data)
            self.root.iconphoto(True, self._photo)
            tk.Label(self.root, image=self._photo, bg=bg).pack(pady=(18, 6))
        else:
            tk.Label(self.root, text="(falta " + LOGO_NAME + ")", fg="#888",
                     bg=bg).pack(pady=(40, 6))

        tk.Label(self.root, text=APP_NAME, font=("Segoe UI", 20, "bold"),
                 fg="#ffffff", bg=bg).pack()

        tk.Button(self.root, text="Kill it!", font=("Segoe UI", 18, "bold"),
                  fg="#ffffff", bg="#d62828", activebackground="#9d1c1c",
                  activeforeground="#ffffff", relief="flat", cursor="hand2",
                  width=12, command=self.arm).pack(expand=True)

        tk.Label(self.root, text="Clic izquierdo: matar  |  Clic derecho: cancelar",
                 font=("Segoe UI", 8), fg="#777", bg=bg).pack(pady=(0, 10))

    def _build_tray(self):
        if self.logo_img is not None:
            icon_img = self.logo_img.resize((64, 64), Image.LANCZOS)
        else:
            icon_img = Image.new("RGBA", (64, 64), (214, 40, 40, 255))
        menu = pystray.Menu(
            pystray.MenuItem("Mostrar", lambda: self.events.put(("show",)), default=True),
            pystray.MenuItem("Kill it!", lambda: self.events.put(("arm",))),
            pystray.MenuItem("Salir", lambda: self.events.put(("quit",))),
        )
        self.tray = pystray.Icon("kill_it_boi", icon_img, APP_NAME, menu)
        self.tray.run_detached()

    # ---- ventana / bandeja
    def hide_window(self):
        self.root.withdraw()

    def show_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def notify(self, msg):
        try:
            self.tray.notify(msg, APP_NAME)
        except Exception:
            pass

    def _poll(self):
        try:
            while True:
                ev = self.events.get_nowait()
                kind = ev[0]
                if kind == "show":
                    self.show_window()
                elif kind == "arm":
                    self.arm()
                elif kind == "quit":
                    self.quit()
                    return
                elif kind in ("done", "cancel"):
                    self.disarm()
                    if kind == "done" and len(ev) > 1 and ev[1]:
                        self.notify(ev[1])
        except queue.Empty:
            pass
        self.root.after(80, self._poll)

    # ---- modo matar
    def arm(self):
        if self.armed:
            return
        if self.cur_path is None:
            self.show_window()
            messagebox.showerror(APP_NAME, "No encuentro " + SKULL_NAME)
            return
        self.armed = True
        self.finished = False
        self.was_visible = self.root.state() != "withdrawn"
        self.root.withdraw()

        base = user32.LoadImageW(None, self.cur_path, IMAGE_CURSOR, 0, 0, LR_LOADFROMFILE)
        if base:
            for cid in SYSTEM_CURSORS:
                user32.SetSystemCursor(user32.CopyImage(base, IMAGE_CURSOR, 0, 0, 0), cid)
            user32.DestroyCursor(base)

        ready = threading.Event()
        threading.Thread(target=self._hook_thread, args=(ready,), daemon=True).start()
        ready.wait(2)

    def disarm(self):
        if not self.armed:
            return
        self.armed = False
        restore_cursors()
        if self.hook_tid:
            user32.PostThreadMessageW(self.hook_tid, WM_QUIT, 0, 0)
        if self.was_visible:
            self.show_window()

    def _hook_thread(self, ready):
        self.hook_tid = kernel32.GetCurrentThreadId()
        msg = wintypes.MSG()
        user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0)  # crea la cola de mensajes
        hook = user32.SetWindowsHookExW(WH_MOUSE_LL, self._cb,
                                        kernel32.GetModuleHandleW(None), 0)
        ready.set()
        if not hook:
            self.events.put(("cancel",))
            return
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            pass
        user32.UnhookWindowsHookEx(hook)
        self.hook_tid = None

    def _hook_proc(self, nCode, wParam, lParam):
        if nCode == 0 and wParam in (WM_LBUTTONDOWN, WM_LBUTTONUP,
                                     WM_RBUTTONDOWN, WM_RBUTTONUP):
            if not self.finished:
                if wParam == WM_LBUTTONDOWN:
                    info = ctypes.cast(lParam, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
                    result = self._kill_at(wintypes.POINT(info.pt.x, info.pt.y))
                    if result is not None:  # None = ventana protegida, sigue armado
                        self.finished = True
                        self.events.put(("done", result))
                elif wParam == WM_RBUTTONDOWN:
                    self.finished = True
                    self.events.put(("cancel",))
            return 1  # traga el clic: la ventana de abajo no lo recibe
        return user32.CallNextHookEx(None, nCode, wParam, lParam)

    def _kill_at(self, pt):
        hwnd = user32.WindowFromPoint(pt)
        if not hwnd:
            return None
        root = user32.GetAncestor(hwnd, GA_ROOT) or hwnd
        cls = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(root, cls, 256)
        if cls.value in PROTECTED_CLASSES:
            return None
        title = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(root, title, 256)
        pid = wintypes.DWORD(0)
        user32.GetWindowThreadProcessId(root, ctypes.byref(pid))
        if not pid.value or pid.value == os.getpid():
            return None
        name = title.value or cls.value
        h = kernel32.OpenProcess(PROCESS_TERMINATE | PROCESS_QUERY_LIMITED_INFORMATION,
                                 False, pid.value)
        if not h:
            h = kernel32.OpenProcess(PROCESS_TERMINATE, False, pid.value)
        if not h:
            return "Sin permiso para cerrar '%s'. Prueba ejecutando como administrador." % name

        # explorer.exe aloja el escritorio, la barra de tareas Y las carpetas:
        # matarlo borra el fondo. Para sus ventanas solo se cierra esa ventana.
        buf = ctypes.create_unicode_buffer(520)
        size = wintypes.DWORD(520)
        exe = ""
        if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
            exe = os.path.basename(buf.value).lower()
        if exe == "explorer.exe":
            kernel32.CloseHandle(h)
            if cls.value in ("CabinetWClass", "ExploreWClass"):
                user32.PostMessageW(root, WM_CLOSE, 0, 0)
                return "Carpeta cerrada: %s" % name
            return None  # otra ventana del shell: se ignora y sigue armado

        ok = kernel32.TerminateProcess(h, 1)
        kernel32.CloseHandle(h)
        if ok:
            return "Proceso terminado: %s (PID %d)" % (name, pid.value)
        return "No se pudo terminar '%s'." % name

    # ---- salida
    def quit(self):
        self.disarm()
        restore_cursors()
        try:
            self.tray.stop()
        except Exception:
            pass
        if self.cur_path and os.path.exists(self.cur_path):
            try:
                os.remove(self.cur_path)
            except OSError:
                pass
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    KillItBoi().run()
