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
from pathlib import Path
from typing import Optional

# Set appearance mode and color theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class LighterSigningServiceGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configure window
        self.title("Lighter Signing Service Manager")
        self.geometry("900x700")
        self.minsize(800, 600)

        # Service state
        self.service_process: Optional[subprocess.Popen] = None
        self.service_running = False

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
        self.service_port = 8000

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

        # Title with gradient effect
        title_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        title_frame.grid(row=0, column=0, padx=20, pady=20, sticky="w")

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

        # Service Card - Lighter EdgeX Style
        self.service_card = ctk.CTkFrame(
            self.main_frame,
            corner_radius=15,
            fg_color=("gray95", "gray15"),
            border_width=1,
            border_color=("gray80", "gray25")
        )
        self.service_card.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        self.service_card.grid_columnconfigure(0, weight=1)

        # Card header
        card_header = ctk.CTkFrame(self.service_card, fg_color="transparent")
        card_header.grid(row=0, column=0, sticky="ew", padx=25, pady=(20, 10))
        card_header.grid_columnconfigure(1, weight=1)

        service_title = ctk.CTkLabel(
            card_header,
            text="Lighter - EdgeX[002]",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=("gray10", "white")
        )
        service_title.grid(row=0, column=0, sticky="w")

        self.status_badge = ctk.CTkLabel(
            card_header,
            text="已上线",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="white",
            fg_color=("#818CF8", "#818CF8"),
            corner_radius=12,
            padx=12,
            pady=4
        )
        self.status_badge.grid(row=0, column=1, padx=10, sticky="e")

        # Card description
        service_desc = ctk.CTkLabel(
            self.service_card,
            text="结合两大核心插件优势，提供超低磨损率，是追求稳定高收益的最佳选择。",
            font=ctk.CTkFont(size=13),
            text_color=("gray50", "gray60"),
            wraplength=800,
            justify="left"
        )
        service_desc.grid(row=1, column=0, sticky="w", padx=25, pady=(0, 15))

        # Status info
        status_info_frame = ctk.CTkFrame(self.service_card, fg_color="transparent")
        status_info_frame.grid(row=2, column=0, sticky="ew", padx=25, pady=(0, 20))

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
            text="超低磨损率 0.018%",
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

        self.footer_label = ctk.CTkLabel(
            self.footer_frame,
            text="AlphaAI Labs © 2025 | Lighter Signing Service",
            font=ctk.CTkFont(size=11),
            text_color=("gray50", "gray60")
        )
        self.footer_label.pack(pady=12)

    def log(self, message: str, level: str = "INFO"):
        """Add a message to the log with color coding"""
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

        def start_task():
            try:
                self.log("Starting service...", "INFO")

                # Import and run uvicorn directly
                import sys
                import importlib.util

                # Add service directory to path
                service_path = str(self.service_dir)
                if service_path not in sys.path:
                    sys.path.insert(0, service_path)

                # Import the service main module
                main_file = self.service_dir / "main.py"
                if not main_file.exists():
                    self.log("Service main.py not found", "ERROR")
                    return

                # Load the service module
                spec = importlib.util.spec_from_file_location("service_main", main_file)
                if spec is None or spec.loader is None:
                    self.log("Failed to load service module", "ERROR")
                    return

                service_module = importlib.util.module_from_spec(spec)
                sys.modules["service_main"] = service_module

                self.service_running = True
                self.update_ui_state()
                self.log(f"Service starting on port {self.service_port}...", "INFO")

                # Execute the service module (this will start uvicorn)
                try:
                    spec.loader.exec_module(service_module)
                    self.log(f"Service started on port {self.service_port}", "SUCCESS")
                except Exception as exec_error:
                    self.log(f"Service execution error: {str(exec_error)}", "ERROR")
                    self.service_running = False
                    self.update_ui_state()
                    return

                # Keep the service running
                while self.service_running:
                    time.sleep(0.1)

            except Exception as e:
                self.log(f"Failed to start service: {str(e)}", "ERROR")
                import traceback
                self.log(traceback.format_exc(), "ERROR")
                self.service_running = False
                self.service_process = None
                self.update_ui_state()

        threading.Thread(target=start_task, daemon=True).start()

    def stop_service(self):
        """Stop the HTTP service"""
        if not self.service_running:
            self.log("Service is not running", "WARNING")
            return

        try:
            self.log("Stopping service...", "INFO")
            self.service_running = False
            self.service_process = None
            self.update_ui_state()
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
            self.status_text.configure(text="服务运行中 - 超低磨损率 0.018%")
            self.status_badge.configure(
                text="运行中",
                fg_color=("#52C41A", "#52C41A")
            )
            self.start_button.configure(state="disabled")
            self.stop_button.configure(state="normal")
        else:
            self.status_indicator.configure(
                text="●",
                text_color=("#FF4D4F", "#FF4D4F")
            )
            self.status_text.configure(text="超低磨损率 0.018%")
            self.status_badge.configure(
                text="已上线",
                fg_color=("#818CF8", "#818CF8")
            )
            self.start_button.configure(state="normal")
            self.stop_button.configure(state="disabled")

    def on_closing(self):
        """Handle window closing"""
        if self.service_running:
            self.log("Stopping service before exit...", "INFO")
            self.stop_service()
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
