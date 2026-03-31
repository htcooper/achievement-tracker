"""Launch the Achievement Tracker server and open the browser."""

import socket
import sys
import threading
import time
import webbrowser

import uvicorn


def find_free_port() -> int:
    """Find an available port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def open_browser(port: int) -> None:
    """Open the browser after a short delay to let the server start."""
    time.sleep(1.5)
    webbrowser.open(f"http://localhost:{port}")


def main() -> None:
    port = find_free_port()
    print(f"Starting Achievement Tracker on http://localhost:{port}")
    print("Press Ctrl+C to stop.\n")

    threading.Thread(target=open_browser, args=(port,), daemon=True).start()

    try:
        uvicorn.run("src.app:app", host="127.0.0.1", port=port, log_level="info")
    except KeyboardInterrupt:
        print("\nShutting down.")
        sys.exit(0)


if __name__ == "__main__":
    main()
