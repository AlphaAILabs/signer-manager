#!/usr/bin/env python3
"""
Lighter Signing Service GUI Client
A beautiful GUI application to manage the lighter-signing-service HTTP server.
"""

import customtkinter as ctk
import os
import sys
import subprocess
import threading
import time
import logging
import io
import traceback
import asyncio
import webbrowser
import socket
from pathlib import Path
from typing import Optional
from PIL import Image

# Set appearance mode and color theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class GUILogHandler(logging.Handler):
    """Custom logging handler that sends logs to the GUI"""
    def __init__(self, gui_log_callback):
        super().__init__()
        self.gui_log_callback = gui_log_callback

    def emit(self, record):
        try:
            msg = self.format(record)
            # Determine log level
            if record.levelno >= logging.ERROR:
                level = "ERROR"
            elif record.levelno >= logging.WARNING:
                level = "WARNING"
            elif record.levelno >= logging.INFO:
                level = "SERVICE"
            else:
                level = "SERVICE"

            # Send to GUI (thread-safe)
            self.gui_log_callback(msg, level)
        except Exception:
            self.handleError(record)


class StreamToLogger:
    """Redirect stdout/stderr to logger"""
    def __init__(self, log_callback, default_level="SERVICE"):
        self.log_callback = log_callback
        self.default_level = default_level
        self.buffer = ""

    def write(self, message):
        try:
            if message and message.strip():
                msg = message.strip()

                # Determine level based on message content
                level = self.default_level
                if "ERROR" in msg or "CRITICAL" in msg or "Exception" in msg or "Traceback" in msg:
                    level = "ERROR"
                elif "WARNING" in msg or "WARN" in msg:
                    level = "WARNING"
                elif "INFO:" in msg or "DEBUG:" in msg:
                    # Remove the INFO: or DEBUG: prefix for cleaner display
                    msg = msg.replace("INFO:", "").replace("DEBUG:", "").strip()
                    level = "SERVICE"
                elif "Started server" in msg or "Uvicorn running" in msg or "Application startup" in msg:
                    level = "SERVICE"
                elif "Shutting down" in msg or "shutdown" in msg.lower():
                    level = "SERVICE"

                self.log_callback(msg, level)
        except Exception:
            # Silently ignore logging errors to prevent infinite loops
            pass

    def flush(self):
        pass

    def isatty(self):
        return False

    def fileno(self):
        return -1


def is_port_in_use(port: int) -> bool:
    """Check if a port is in use"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('0.0.0.0', port))
            return False
        except OSError:
            return True


def get_process_using_port(port: int) -> Optional[int]:
    """Get PID of process using the specified port (Windows only)"""
    if sys.platform != 'win32':
        return None

    try:
        import subprocess
        result = subprocess.run(
            ['netstat', '-ano'],
            capture_output=True,
            text=True,
            timeout=5
        )

        for line in result.stdout.splitlines():
            if f':{port}' in line and 'LISTENING' in line:
                parts = line.split()
                if len(parts) >= 5:
                    try:
                        return int(parts[-1])
                    except ValueError:
                        pass
    except Exception:
        pass
    return None


def kill_process_on_port(port: int) -> bool:
    """Kill the process using the specified port (Windows only)"""
    if sys.platform != 'win32':
        return False

    pid = get_process_using_port(port)
    if pid:
        try:
            subprocess.run(['taskkill', '/F', '/PID', str(pid)],
                         capture_output=True, timeout=10)
            time.sleep(1)  # Wait for process to die
            return True
        except Exception:
            pass
    return False


class LighterSigningServiceGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configure window
        self.title("AlphaLabs Signer Manager")
        self.geometry("900x700")
        self.minsize(800, 600)

        # Set window icon
        try:
            if getattr(sys, 'frozen', False):
                # Running as compiled executable
                if hasattr(sys, '_MEIPASS'):
                    icon_path = Path(sys._MEIPASS) / "logo.png"
                else:
                    icon_path = Path(sys.executable).parent / "logo.png"
            else:
                # Running as script
                icon_path = Path(__file__).parent / "logo.png"

            if icon_path.exists():
                self.iconphoto(True, ctk.CTkImage(Image.open(icon_path), size=(32, 32))._light_image)
        except Exception as e:
            print(f"Could not load icon: {e}")

        # Service state
        self.service_process: Optional[subprocess.Popen] = None
        self.service_running = False
        self.uvicorn_server = None

        # Service directory is bundled with the application
        if getattr(sys, 'frozen', False):
            # Running as compiled executable (PyInstaller)
            # PyInstaller extracts files to sys._MEIPASS
            if hasattr(sys, '_MEIPASS'):
                application_path = Path(sys._MEIPASS)
            else:
                application_path = Path(sys.executable).parent
        else:
            # Running as script
            application_path = Path(__file__).parent

        self.service_dir = application_path / "service"
        self.service_port = 10000

        # Theme state
        self.current_theme = "dark"

        # Create UI
        self.create_widgets()

        # Check if service directory exists
        self.after(100, self.check_service)

    def create_widgets(self):
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header Frame
        self.header_frame = ctk.CTkFrame(self, corner_radius=0, fg_color=("gray90", "gray10"))
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        self.header_frame.grid_columnconfigure(0, weight=1)
        self.header_frame.grid_columnconfigure(1, weight=0)

        # Logo and Title
        title_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        title_frame.grid(row=0, column=0, padx=20, pady=20, sticky="w")

        # Load and display logo
        try:
            if getattr(sys, 'frozen', False):
                if hasattr(sys, '_MEIPASS'):
                    logo_path = Path(sys._MEIPASS) / "logo.png"
                else:
                    logo_path = Path(sys.executable).parent / "logo.png"
            else:
                logo_path = Path(__file__).parent / "logo.png"

            if logo_path.exists():
                logo_image = ctk.CTkImage(
                    light_image=Image.open(logo_path),
                    dark_image=Image.open(logo_path),
                    size=(48, 48)
                )
                logo_label = ctk.CTkLabel(title_frame, image=logo_image, text="")
                logo_label.pack(side="left", padx=(0, 15))
        except Exception as e:
            print(f"Could not load logo: {e}")

        self.title_label = ctk.CTkLabel(
            title_frame,
            text="专业交易 ",
            font=ctk.CTkFont(size=32, weight="bold"),
            text_color=("gray10", "white")
        )
        self.title_label.pack(side="left")

        self.title_label_accent = ctk.CTkLabel(
            title_frame,
            text="插件套件",
            font=ctk.CTkFont(size=32, weight="bold"),
            text_color=("#818CF8", "#818CF8")
        )
        self.title_label_accent.pack(side="left")

        self.subtitle_label = ctk.CTkLabel(
            self.header_frame,
            text="选择适合您的交易策略插件，开启智能化交易之旅",
            font=ctk.CTkFont(size=14),
            text_color=("gray60", "gray60")
        )
        self.subtitle_label.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="w")

        # Theme toggle button
        self.theme_button = ctk.CTkButton(
            self.header_frame,
            text="☀️ Light",
            command=self.toggle_theme,
            font=ctk.CTkFont(size=14),
            width=100,
            height=35,
            fg_color="transparent",
            border_width=2,
            border_color=("#818CF8", "#818CF8"),
            text_color=("#818CF8", "#818CF8"),
            hover_color=("gray85", "gray20")
        )
        self.theme_button.grid(row=0, column=1, padx=20, pady=20, sticky="e")



        # Main Content Frame
        self.main_frame = ctk.CTkFrame(self, corner_radius=10)
        self.main_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(2, weight=1)

        # Service Cards Container - Horizontal Layout
        self.service_cards_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.service_cards_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        # Configure 3 columns with equal weight
        self.service_cards_frame.grid_columnconfigure((0, 1, 2), weight=1)

        # Strategy configurations - all with same badge color
        strategies = [
            {
                "name": "Lighter-EdgeX [002]",
                "desc": "结合两大核心插件优势，提供超低磨损率，是追求稳定高收益的最佳选择",
                "wear_rate": "磨损率 0.023% - 0.025%",
                "badge": "已上线",
                "badge_color": ("#52C41A", "#52C41A")  # Green for all
            },
            {
                "name": "Lighter-Based [003]",
                "desc": "基于 Based 协议的策略，平衡收益与风险，支持大部分 token",
                "wear_rate": "磨损率 0.02% - 0.023%",
                "badge": "已上线",
                "badge_color": ("#52C41A", "#52C41A")  # Green for all
            },
            {
                "name": "Lighter-Backpack [005]",
                "desc": "集成 Backpack 生态，灵活的磨损率范围适应不同市场环境，支持大部分 token",
                "wear_rate": "磨损率 0.014% - 0.035%",
                "badge": "已上线",
                "badge_color": ("#52C41A", "#52C41A")  # Green for all
            }
        ]

        # Create cards for each strategy in horizontal layout
        for idx, strategy in enumerate(strategies):
            self.create_strategy_card(self.service_cards_frame, strategy, idx, column=idx)

        # Status indicator at bottom (shared across all strategies) - span all columns
        status_info_frame = ctk.CTkFrame(self.service_cards_frame, fg_color="transparent")
        status_info_frame.grid(row=1, column=0, columnspan=3, sticky="ew", padx=0, pady=(10, 0))

        status_icon_frame = ctk.CTkFrame(status_info_frame, fg_color="transparent")
        status_icon_frame.pack(side="left")

        self.status_indicator = ctk.CTkLabel(
            status_icon_frame,
            text="●",
            font=ctk.CTkFont(size=20),
            text_color=("#FF4D4F", "#FF4D4F")
        )
        self.status_indicator.pack(side="left", padx=(0, 8))

        self.status_text = ctk.CTkLabel(
            status_info_frame,
            text="服务未运行",
            font=ctk.CTkFont(size=14),
            text_color=("gray40", "gray70")
        )
        self.status_text.pack(side="left")

        self.port_label = ctk.CTkLabel(
            status_info_frame,
            text=f"Port: {self.service_port}",
            font=ctk.CTkFont(size=13),
            text_color=("gray50", "gray60")
        )
        self.port_label.pack(side="right", padx=10)

        # Control Buttons Section
        self.control_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.control_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        self.control_frame.grid_columnconfigure((0, 1), weight=1)

        # Start Button - Modern style
        self.start_button = ctk.CTkButton(
            self.control_frame,
            text="▶  启动服务",
            command=self.start_service,
            font=ctk.CTkFont(size=16, weight="bold"),
            height=50,
            corner_radius=10,
            fg_color=("#52C41A", "#52C41A"),
            hover_color=("#389E0D", "#389E0D"),
            border_width=0
        )
        self.start_button.grid(row=0, column=0, padx=10, pady=20, sticky="ew")

        # Stop Button - Modern style
        self.stop_button = ctk.CTkButton(
            self.control_frame,
            text="■  停止服务",
            command=self.stop_service,
            font=ctk.CTkFont(size=16, weight="bold"),
            height=50,
            corner_radius=10,
            fg_color=("#FF4D4F", "#FF4D4F"),
            hover_color=("#CF1322", "#CF1322"),
            border_width=0,
            state="disabled"
        )
        self.stop_button.grid(row=0, column=1, padx=10, pady=20, sticky="ew")



        # Log Section - Modern style
        self.log_frame = ctk.CTkFrame(
            self.main_frame,
            corner_radius=15,
            fg_color=("gray95", "gray15"),
            border_width=1,
            border_color=("gray80", "gray25")
        )
        self.log_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=(10, 20))
        self.log_frame.grid_columnconfigure(0, weight=1)
        self.log_frame.grid_rowconfigure(1, weight=1)

        log_header_frame = ctk.CTkFrame(self.log_frame, fg_color="transparent")
        log_header_frame.grid(row=0, column=0, sticky="ew", padx=25, pady=(20, 10))
        log_header_frame.grid_columnconfigure(0, weight=1)

        self.log_title = ctk.CTkLabel(
            log_header_frame,
            text="📋 服务日志",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=("gray10", "white")
        )
        self.log_title.pack(side="left")

        self.clear_log_button = ctk.CTkButton(
            log_header_frame,
            text="清除日志",
            command=self.clear_log,
            font=ctk.CTkFont(size=12),
            width=80,
            height=28,
            corner_radius=8,
            fg_color="transparent",
            border_width=1,
            border_color=("gray70", "gray40"),
            text_color=("gray40", "gray70"),
            hover_color=("gray85", "gray25")
        )
        self.clear_log_button.pack(side="right")

        self.log_text = ctk.CTkTextbox(
            self.log_frame,
            font=ctk.CTkFont(size=11),
            wrap="word",
            fg_color=("white", "gray20"),
            border_width=0
        )
        self.log_text.grid(row=1, column=0, padx=25, pady=(5, 25), sticky="nsew")

        # Footer
        self.footer_frame = ctk.CTkFrame(self, corner_radius=0, fg_color=("gray90", "gray10"))
        self.footer_frame.grid(row=2, column=0, sticky="ew", padx=0, pady=0)

        # Footer with social links
        footer_content = ctk.CTkFrame(self.footer_frame, fg_color="transparent")
        footer_content.pack(pady=12)

        self.footer_label = ctk.CTkLabel(
            footer_content,
            text="AlphaLabs © 2025 | Signer Manager",
            font=ctk.CTkFont(size=11),
            text_color=("gray50", "gray60")
        )
        self.footer_label.pack(side="left", padx=20)

        # Social links
        social_links_frame = ctk.CTkFrame(footer_content, fg_color="transparent")
        social_links_frame.pack(side="left")

        links = [
            ("🌐 官网", "https://alphalabs.app"),
            ("𝕏", "https://x.com/Alpha_alabs"),
            ("📱 Telegram", "https://t.me/+DYoJd7HuN1kyNGE1")
        ]

        for text, url in links:
            link_btn = ctk.CTkButton(
                social_links_frame,
                text=text,
                font=ctk.CTkFont(size=10),
                width=80,
                height=24,
                corner_radius=6,
                fg_color="transparent",
                border_width=1,
                border_color=("gray70", "gray40"),
                text_color=("gray40", "gray70"),
                hover_color=("gray85", "gray25"),
                command=lambda u=url: self.open_link(u)
            )
            link_btn.pack(side="left", padx=5)

    def create_strategy_card(self, parent, strategy, index, column=0):
        """Create a strategy information card"""
        card = ctk.CTkFrame(
            parent,
            corner_radius=15,
            fg_color=("gray95", "gray15"),
            border_width=1,
            border_color=("gray80", "gray25")
        )
        # Place in row 0, different columns for horizontal layout
        card.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 5, 0 if column == 2 else 5), pady=0)
        card.grid_columnconfigure(0, weight=1)

        # Card header
        card_header = ctk.CTkFrame(card, fg_color="transparent")
        card_header.grid(row=0, column=0, sticky="ew", padx=25, pady=(15, 8))
        card_header.grid_columnconfigure(1, weight=1)

        service_title = ctk.CTkLabel(
            card_header,
            text=strategy["name"],
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=("gray10", "white")
        )
        service_title.grid(row=0, column=0, sticky="w")

        status_badge = ctk.CTkLabel(
            card_header,
            text=strategy["badge"],
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="white",
            fg_color=strategy["badge_color"],
            corner_radius=10,
            padx=10,
            pady=3
        )
        status_badge.grid(row=0, column=1, padx=10, sticky="e")

        # Card description
        service_desc = ctk.CTkLabel(
            card,
            text=strategy["desc"],
            font=ctk.CTkFont(size=11),
            text_color=("gray50", "gray60"),
            wraplength=250,  # Reduced for horizontal layout
            justify="left"
        )
        service_desc.grid(row=1, column=0, sticky="w", padx=20, pady=(0, 8))

        # Wear rate
        wear_rate_label = ctk.CTkLabel(
            card,
            text=strategy["wear_rate"],
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("gray30", "gray80")
        )
        wear_rate_label.grid(row=2, column=0, sticky="w", padx=25, pady=(0, 15))

    def open_link(self, url):
        """Open URL in default browser"""
        webbrowser.open(url)

    def log(self, message: str, level: str = "INFO"):
        """Add a message to the log with color coding (thread-safe)"""
        # If called from a different thread, schedule on main thread
        if threading.current_thread() != threading.main_thread():
            self.after(0, lambda: self.log(message, level))
            return

        timestamp = time.strftime("%H:%M:%S")

        # Define colors for different log levels (light mode, dark mode)
        color_map = {
            "INFO": ("#666666", "#999999"),
            "SUCCESS": ("#52C41A", "#52C41A"),
            "WARNING": ("#FAAD14", "#FAAD14"),
            "ERROR": ("#FF4D4F", "#FF4D4F"),
            "SERVICE": ("#818CF8", "#818CF8")  # Purple color
        }

        # Get current theme
        current_mode = ctk.get_appearance_mode()
        color = color_map.get(level, ("#666666", "#999999"))
        text_color = color[1] if current_mode == "Dark" else color[0]
        timestamp_color = "#999999" if current_mode == "Dark" else "#999999"

        # Insert timestamp
        self.log_text.insert("end", f"[{timestamp}] ", "timestamp")

        # Insert level with color
        self.log_text.insert("end", f"[{level}] ", level)

        # Insert message
        self.log_text.insert("end", f"{message}\n", level)

        # Configure tags for colors
        self.log_text.tag_config("timestamp", foreground=timestamp_color)
        self.log_text.tag_config(level, foreground=text_color)

        # Auto-scroll to bottom
        self.log_text.see("end")

        # Limit log size (keep last 1000 lines)
        lines = self.log_text.get("1.0", "end").split("\n")
        if len(lines) > 1000:
            self.log_text.delete("1.0", f"{len(lines) - 1000}.0")

    def clear_log(self):
        """Clear all log messages"""
        self.log_text.delete("1.0", "end")
        self.log("Log cleared", "INFO")

    def check_service(self):
        """Check if the service directory exists"""
        if self.service_dir.exists() and (self.service_dir / "main.py").exists():
            self.log("Service found and ready", "SUCCESS")
            self.log(f"Service location: {self.service_dir}", "INFO")
        else:
            self.log("ERROR: Service files not found!", "ERROR")
            self.log(f"Expected location: {self.service_dir}", "ERROR")
            self.start_button.configure(state="disabled")

    def start_service(self):
        """Start the HTTP service"""
        if self.service_running:
            self.log("Service is already running", "WARNING")
            return

        # Update UI immediately to show we're starting
        self.log("Starting service...", "INFO")
        self.start_button.configure(state="disabled", text="启动中...")

        def start_task():
            try:
                # Check and clean up port before starting
                self.log(f"Checking port {self.service_port}...", "INFO")

                if is_port_in_use(self.service_port):
                    self.log(f"Port {self.service_port} is in use, attempting to clean up...", "WARNING")

                    if sys.platform == 'win32':
                        pid = get_process_using_port(self.service_port)
                        if pid:
                            self.log(f"Found process {pid} using port {self.service_port}", "INFO")
                            if kill_process_on_port(self.service_port):
                                self.log("Old process terminated successfully", "SUCCESS")
                                # Wait a bit more to ensure port is released
                                time.sleep(2)
                            else:
                                self.log("Failed to terminate old process", "ERROR")
                                self.log("Please manually close the application using port 10000", "ERROR")
                                self.start_button.configure(state="normal", text="启动服务")
                                return

                    # Double check port is now free
                    if is_port_in_use(self.service_port):
                        self.log(f"Port {self.service_port} is still in use!", "ERROR")
                        self.log("Please wait 2 minutes or restart your computer", "ERROR")
                        self.start_button.configure(state="normal", text="启动服务")
                        return
                    else:
                        self.log(f"Port {self.service_port} is now available", "SUCCESS")
                else:
                    self.log(f"Port {self.service_port} is available", "SUCCESS")

                # Import uvicorn and the service app
                import importlib.util
                import uvicorn

                # Add service directory to path
                service_path = str(self.service_dir)
                if service_path not in sys.path:
                    sys.path.insert(0, service_path)

                # Import the service main module
                main_file = self.service_dir / "main.py"
                if not main_file.exists():
                    self.log("Service main.py not found", "ERROR")
                    self.start_button.configure(state="normal", text="启动服务")
                    return

                self.log("Loading service dependencies (this may take a moment on first run)...", "INFO")

                # Load the service module
                spec = importlib.util.spec_from_file_location("service_main", main_file)
                if spec is None or spec.loader is None:
                    self.log("Failed to load service module", "ERROR")
                    self.start_button.configure(state="normal", text="启动服务")
                    return

                service_module = importlib.util.module_from_spec(spec)
                sys.modules["service_main"] = service_module

                # Execute the service module to get the FastAPI app (this is slow on first run)
                try:
                    spec.loader.exec_module(service_module)
                except Exception as exec_error:
                    self.log(f"Service module load error: {str(exec_error)}", "ERROR")
                    self.log(traceback.format_exc(), "ERROR")
                    self.start_button.configure(state="normal", text="启动服务")
                    return

                # Get the FastAPI app from the module
                if not hasattr(service_module, 'app'):
                    self.log("Service module does not have 'app' attribute", "ERROR")
                    self.start_button.configure(state="normal", text="启动服务")
                    return

                app = service_module.app

                self.service_running = True
                self.update_ui_state()
                self.log(f"Service starting on port {self.service_port}...", "INFO")

                # Start uvicorn server
                try:
                    # Configure logging before redirecting stdout/stderr
                    # This prevents "AttributeError: 'NoneType' object has no attribute 'write'" on Windows
                    logging.getLogger('asyncio').setLevel(logging.WARNING)

                    # Ensure root logger handlers are configured
                    for handler in logging.root.handlers[:]:
                        logging.root.removeHandler(handler)

                    # Redirect stdout/stderr to capture all output
                    old_stdout = sys.stdout
                    old_stderr = sys.stderr

                    stream_logger = StreamToLogger(self.log, "SERVICE")
                    sys.stdout = stream_logger
                    sys.stderr = stream_logger

                    try:
                        # On Windows, we need to set the event loop policy explicitly
                        # to avoid issues with ProactorEventLoop in packaged apps
                        if sys.platform == 'win32':
                            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

                        config = uvicorn.Config(
                            app=app,
                            host="0.0.0.0",
                            port=self.service_port,
                            log_level="info",
                            access_log=True,
                            timeout_graceful_shutdown=1,  # Fast shutdown to release port quickly
                            limit_concurrency=100,
                            backlog=50
                        )
                        self.uvicorn_server = uvicorn.Server(config)

                        self.log(f"Service started on port {self.service_port}", "SUCCESS")

                        # Create and run event loop manually for better Windows compatibility
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            loop.run_until_complete(self.uvicorn_server.serve())
                        finally:
                            loop.close()
                    finally:
                        # Restore stdout/stderr
                        sys.stdout = old_stdout
                        sys.stderr = old_stderr

                except Exception as server_error:
                    self.log(f"Server error: {str(server_error)}", "ERROR")
                    self.log(traceback.format_exc(), "ERROR")
                finally:
                    self.service_running = False
                    self.update_ui_state()
                    self.log("Service stopped", "INFO")

            except Exception as e:
                self.log(f"Failed to start service: {str(e)}", "ERROR")
                self.log(traceback.format_exc(), "ERROR")
                self.service_running = False
                self.service_process = None
                self.start_button.configure(state="normal", text="启动服务")
                self.update_ui_state()

        threading.Thread(target=start_task, daemon=True).start()

    def stop_service(self):
        """Stop the HTTP service"""
        if not self.service_running:
            self.log("Service is not running", "WARNING")
            return

        try:
            self.log("Stopping service...", "INFO")

            # Signal the server to stop
            if self.uvicorn_server:
                self.uvicorn_server.should_exit = True

                # Wait for server to gracefully shutdown
                max_wait = 5  # seconds
                waited = 0
                while waited < max_wait:
                    if not is_port_in_use(self.service_port):
                        break
                    time.sleep(0.5)
                    waited += 0.5

            self.service_running = False
            self.service_process = None
            self.uvicorn_server = None
            self.update_ui_state()

            # Verify port is released
            if is_port_in_use(self.service_port):
                self.log(f"Warning: Port {self.service_port} may still be in use", "WARNING")
                self.log("Please wait a moment before restarting", "WARNING")
            else:
                self.log("Service stopped successfully", "SUCCESS")

        except Exception as e:
            self.log(f"Error stopping service: {str(e)}", "ERROR")

    def update_ui_state(self):
        """Update UI elements based on service state"""
        if self.service_running:
            self.status_indicator.configure(
                text="●",
                text_color=("#52C41A", "#52C41A")
            )
            self.status_text.configure(text="服务运行中")
            self.start_button.configure(state="disabled")
            self.stop_button.configure(state="normal")
        else:
            self.status_indicator.configure(
                text="●",
                text_color=("#FF4D4F", "#FF4D4F")
            )
            self.status_text.configure(text="服务未运行")
            self.start_button.configure(state="normal")
            self.stop_button.configure(state="disabled")

    def on_closing(self):
        """Handle window closing"""
        if self.service_running:
            self.log("Stopping service before exit...", "INFO")
            self.stop_service()
            # Give more time for graceful shutdown
            time.sleep(2)

            # Force kill if still running (Windows only)
            if sys.platform == 'win32' and is_port_in_use(self.service_port):
                self.log("Force terminating service...", "WARNING")
                kill_process_on_port(self.service_port)
                time.sleep(1)

        self.destroy()

    def toggle_theme(self):
        """Toggle between light and dark theme"""
        if self.current_theme == "dark":
            self.current_theme = "light"
            ctk.set_appearance_mode("light")
            self.theme_button.configure(text="🌙 Dark")
            self.log("Switched to light theme", "INFO")
        else:
            self.current_theme = "dark"
            ctk.set_appearance_mode("dark")
            self.theme_button.configure(text="☀️ Light")
            self.log("Switched to dark theme", "INFO")


def main():
    """Main entry point"""
    app = LighterSigningServiceGUI()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()


if __name__ == "__main__":
    main()
