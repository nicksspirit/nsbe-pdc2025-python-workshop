import re
import subprocess
import time
import urllib
from pathlib import Path

from IPython import get_ipython
from IPython.display import display
from ipywidgets import Button, HBox, Output


class ShowPasswordBtn:
    def __init__(self, output_widget: Output | None = None):
        self.output_widget = Output() if output_widget is None else output_widget

    def render(self):
        show_button = Button(description="Show Localtunnel Password", button_style="info")
        show_button.layout.width = "250px"
        show_button.on_click(self._show_password)

        display(show_button, self.output_widget)

    def _show_password(self, btn):
        with self.output_widget:
            self.output_widget.clear_output()

            try:
                passwd = (
                    urllib.request.urlopen("https://ipv4.icanhazip.com")
                    .read()
                    .decode("utf8")
                    .strip("\n")
                )
                self.output_widget.append_stdout(f"🔑 Localtunnel password: {passwd}")
            except Exception as e:
                self.output_widget.append_stderr(f"❌ Failed to get password: {e}")


class StopStreamlitAppBtn:
    def __init__(self, app_name: str, output_widget: Output | None = None):
        self.app_name = app_name
        self.output_widget = Output() if output_widget is None else output_widget

    def render(self):
        stop_button = Button(description="Stop Streamlit App", button_style="danger")
        stop_button.on_click(self._stop_streamlit)

        display(stop_button, self.output_widget)

    def _stop_streamlit(self, btn):
        with self.output_widget:
            self.output_widget.clear_output()

            try:
                get_ipython().run_cell_magic(
                    "bash", "", f'pkill -f "streamlit run app/{self.app_name}.py"'
                )
                self.output_widget.append_stdout("\n🛑 Streamlit app stopped.")
            except subprocess.CalledProcessError as e:
                if e.returncode == 1:
                    self.output_widget.append_stdout("\nℹ️ No Streamlit app was running.")
                else:
                    self.output_widget.append_stderr(f"\n❌ An error occurred: {e}")


class StartStreamlitAppBtn:
    def __init__(self, app_name: str, output_widget: Output | None = None):
        self.app_name = app_name
        self.output_widget = Output() if output_widget is None else output_widget
        self.port = None  # Will store the port number once extracted
        self.is_running = False  # Track if Streamlit is currently running

    def render(self):
        start_button = Button(description="Start Streamlit App and Tunnel", button_style="success")
        start_button.on_click(self._start_streamlit)

        display(start_button, self.output_widget)

    def _is_streamlit_running(self) -> bool:
        """Check if Streamlit process is currently running for this app."""
        try:
            get_ipython().run_cell_magic(
                "bash", "", f'pgrep -f "streamlit run app/{self.app_name}.py"'
            )
            return True  # If pgrep finds a process, it returns success
        except subprocess.CalledProcessError:
            return False  # If pgrep finds nothing, it returns non-zero exit code

    def _extract_port_from_logs(self, wait_for_logs: bool = True):
        """Extract the port number from the Streamlit log file."""

        log_path = Path(f"./app/logs/{self.app_name}.log")

        if not log_path.exists():
            return None

        try:
            # Only wait if we're expecting new logs (when starting)
            if wait_for_logs:
                time.sleep(2)

            log_content = log_path.read_text()

            # Look for the local URL pattern and extract port
            match = re.search(r"Local URL: http://localhost:(\d+)", log_content)
            if match:
                self.port = int(match.group(1))
                return self.port
            else:
                return None
        except Exception as e:
            self.output_widget.append_stderr(f"\n❌ Failed to extract port: {e}")
            return None

    def _start_streamlit(self, btn):
        with self.output_widget:
            self.output_widget.clear_output()

            # Check if already running
            if self.is_running or self._is_streamlit_running():
                # Try to get the current port
                current_port = self._extract_port_from_logs(wait_for_logs=False)
                if current_port:
                    self.output_widget.append_stdout(
                        f"\n⚠️ Streamlit app '{self.app_name}' is already running on port {current_port}!\n"
                        f"🔗 Local URL: http://localhost:{current_port}"
                    )
                else:
                    self.output_widget.append_stdout(
                        f"\n⚠️ Streamlit app '{self.app_name}' is already running!"
                    )
                self.is_running = True  # Update state in case it was detected via process check
                return

            self.output_widget.append_stdout("\n🚀 Starting Streamlit app...")
            self.is_running = True  # Set state before starting

            streamlit_run_cmd = [
                f"uv run streamlit run app/{self.app_name}.py",
                "--server.headless true",
                f"&>./app/logs/{self.app_name}.log &",
            ]

            try:
                get_ipython().run_cell_magic("bash", "", " ".join(streamlit_run_cmd))
                self.output_widget.append_stdout("\n✅ Streamlit app started in the background.")

                # Give Streamlit a moment to start
                time.sleep(5)

                # Extract and store the port number
                port = self._extract_port_from_logs()
                if port:
                    self.output_widget.append_stdout(f"\n🔌 Streamlit running on port: {port}")
                else:
                    self.output_widget.append_stdout("\n⚠️ Could not determine Streamlit port")

            except subprocess.CalledProcessError as e:
                self.output_widget.append_stderr(f"\n❌ An error occurred: {e}")
                self.is_running = False  # Reset state on failure


class StartTunnelBtn:
    """Button to start a Cloudflare tunnel using the tunnel.js script."""

    def __init__(self, port: int | None = None, output_widget: Output | None = None):
        self.port = port  # Can be set directly or obtained from a Streamlit app
        self.output_widget = Output() if output_widget is None else output_widget
        self.tunnel_process = None
        self.is_running = False  # Track if tunnel is currently running

    def render(self):
        start_button = Button(description="Start Cloudflare Tunnel", button_style="primary")
        start_button.on_click(self._start_tunnel)

        display(start_button, self.output_widget)

    def _is_tunnel_running(self) -> bool:
        """Check if tunnel process is currently running for this port."""
        try:
            if self.port:
                get_ipython().run_cell_magic("bash", "", f'pgrep -f "node tunnel.js {self.port}"')
            else:
                get_ipython().run_cell_magic("bash", "", 'pgrep -f "node tunnel.js"')
            return True  # If pgrep finds a process, it returns success
        except subprocess.CalledProcessError:
            return False  # If pgrep finds nothing, it returns non-zero exit code

    def _get_existing_tunnel_url(self) -> str | None:
        """Get tunnel URL from existing log file if tunnel is already running."""
        if not self.port:
            return None

        tunnel_log_path = Path(f"./app/logs/tunnel_{self.port}.log")

        if not tunnel_log_path.exists():
            return None

        try:
            log_content = tunnel_log_path.read_text()
            url_match = re.search(r"LINK: (https://.*\.trycloudflare\.com)", log_content)
            return url_match.group(1) if url_match else None
        except Exception:
            return None

    def _poll_for_tunnel_url(self, log_path: str, timeout: int = 30) -> str | None:
        """Poll the log file for the tunnel URL with timeout."""
        start_time = time.time()
        log_file_path = Path(log_path)

        while time.time() - start_time < timeout:
            try:
                if log_file_path.exists():
                    log_content = log_file_path.read_text()
                    url_match = re.search(r"LINK: (https://.*\.trycloudflare\.com)", log_content)

                    if url_match:
                        return url_match.group(1)

                # Wait a bit before checking again
                time.sleep(1)

            except Exception as e:
                self.output_widget.append_stderr(f"\n⚠️ Error reading log file: {e}")
                break

        return None

    def _start_tunnel(self, btn):
        with self.output_widget:
            self.output_widget.clear_output()

            if not self.port:
                self.output_widget.append_stderr("\n❌ No port specified. Cannot start tunnel.")
                return

            # Check if already running
            if self.is_running or self._is_tunnel_running():
                # Try to get the current tunnel URL
                current_url = self._get_existing_tunnel_url()
                if current_url:
                    self.output_widget.append_stdout(
                        f"\n⚠️ Tunnel for port {self.port} is already running!\n"
                        f"🔗 Tunnel URL: {current_url}"
                    )
                else:
                    self.output_widget.append_stdout(
                        f"\n⚠️ Tunnel for port {self.port} is already running!"
                    )
                self.is_running = True  # Update state in case it was detected via process check
                return

            self.output_widget.append_stdout(
                f"\n🚇 Starting Cloudflare tunnel for port {self.port}..."
            )
            self.is_running = True  # Set state before starting

            tunnel_log_path = f"./app/logs/tunnel_{self.port}.log"

            try:
                # Run the tunnel.js script with Node.js
                tunnel_cmd = f"node tunnel.js {self.port} &>{tunnel_log_path} &"
                get_ipython().run_cell_magic("bash", "", tunnel_cmd)

                self.output_widget.append_stdout("\n✅ Tunnel started in the background.")
                self.output_widget.append_stdout(
                    f"\n🔍 Check {tunnel_log_path} for the tunnel URL."
                )

                # Poll the log file for the tunnel URL
                tunnel_url = self._poll_for_tunnel_url(tunnel_log_path)

                if tunnel_url:
                    self.output_widget.append_stdout(f"\n🔗 Tunnel URL: {tunnel_url}")
                else:
                    self.output_widget.append_stdout("\n⚠️ Could not extract tunnel URL from logs.")

            except subprocess.CalledProcessError as e:
                self.output_widget.append_stderr(f"\n❌ An error occurred: {e}")
                self.is_running = False  # Reset state on failure


class StopTunnelBtn:
    """Button to stop a Cloudflare tunnel."""

    def __init__(self, port: int | None = None, output_widget: Output | None = None):
        self.output_widget = Output() if output_widget is None else output_widget
        self.port = port

    def render(self):
        stop_button = Button(description="Stop Cloudflare Tunnel", button_style="danger")
        stop_button.on_click(self._stop_tunnel)

        display(stop_button, self.output_widget)

    def _stop_tunnel(self, btn):
        with self.output_widget:
            self.output_widget.clear_output()

            try:
                # Kill any processes running the tunnel.js script
                get_ipython().run_cell_magic("bash", "", f"pkill -f node tunnel.js {self.port}")
                self.output_widget.append_stdout("\n🛑 Cloudflare tunnel stopped.")
            except subprocess.CalledProcessError as e:
                if e.returncode == 1:
                    self.output_widget.append_stdout("\nℹ️ No tunnel was running.")
                else:
                    self.output_widget.append_stderr(f"\n❌ An error occurred: {e}")


class StreamlitControlBtn:
    """A widget that displays both Start and Stop Streamlit buttons side by side by reusing existing button classes."""

    def __init__(self, app_name: str):
        self.output_widget = Output()
        self.app_name = app_name

        # Create instances of existing button classes
        self.start_app = StartStreamlitAppBtn(self.app_name, self.output_widget)
        self.stop_app = StopStreamlitAppBtn(self.app_name, self.output_widget)

    def render(self):
        # Create buttons using the existing button classes
        start_button = Button(description="Start Streamlit App", button_style="success")
        stop_button = Button(description="Stop Streamlit App", button_style="danger")

        # Configure buttons to use methods from existing classes
        start_button.on_click(self.start_app._start_streamlit)
        stop_button.on_click(self._stop_streamlit_wrapper)

        # Create an HBox to place buttons side by side
        buttons = HBox([start_button, stop_button])

        display(buttons, self.output_widget)

    def _stop_streamlit_wrapper(self, btn):
        """Wrapper to coordinate state between start and stop buttons."""
        # Call the original stop method
        self.stop_app._stop_streamlit(btn)
        # Reset the start button's running state
        self.start_app.is_running = False


class TunnelControlBtn:
    """A widget that displays both Start and Stop Tunnel buttons side by side."""

    def __init__(self, port: int | None = None):
        self.output_widget = Output()
        self.port = port

        # Create instances of tunnel button classes
        self.start_tunnel = StartTunnelBtn(self.port, self.output_widget)
        self.stop_tunnel = StopTunnelBtn(self.port, self.output_widget)

    def render(self):
        # Create buttons for tunnel control
        start_button = Button(description="Start Tunnel", button_style="primary")
        stop_button = Button(description="Stop Tunnel", button_style="danger")

        # Configure buttons to use methods from tunnel classes
        start_button.on_click(self.start_tunnel._start_tunnel)
        stop_button.on_click(self._stop_tunnel_wrapper)

        # Create an HBox to place buttons side by side
        buttons = HBox([start_button, stop_button])

        display(buttons, self.output_widget)

    def _stop_tunnel_wrapper(self, btn):
        """Wrapper to coordinate state between start and stop buttons."""
        # Call the original stop method
        self.stop_tunnel._stop_tunnel(btn)
        # Reset the start button's running state
        self.start_tunnel.is_running = False
