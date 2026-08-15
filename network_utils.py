# Copyright (c) 2020-2026 Jess VanDerwalker

def should_retry_with_socket_reset(error):
    """Check whether a runtime error indicates a stale socket connection."""
    if error is None:
        return False

    message = str(error).lower()
    return "existing socket is already connected" in message or (
        "already connected" in message and "socket" in message
    )


def reset_connection_manager():
    """Reset all tracked sockets in the CircuitPython connection manager."""
    try:
        from adafruit_connection_manager import connection_manager_close_all

        connection_manager_close_all()
        return True
    except Exception as exc:  # pragma: no cover - runtime-only fallback
        print("[warn] Unable to reset network sockets:", exc)
        return False
