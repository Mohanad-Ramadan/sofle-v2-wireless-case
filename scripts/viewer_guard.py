"""Refuse to claim a part was sent to the OCP CAD Viewer when no viewer is listening.

``ocp_vscode.show()`` does NOT raise when the viewer is gone. It swallows the failed websocket
connect into a ``CommsWarning`` and returns normally, so any caller that prints "sent to the
viewer" afterwards prints it whether or not anything arrived.

That cost real time once: three sends were reported as successful against a dead viewer while the
panel kept showing a months-old encoder plateau, and the stale image was read as the build being
wrong rather than the send having failed.

``~/.ocpvscode`` lists ports the extension has *registered*. Those entries outlive the session that
wrote them, so their presence proves nothing — ``port_check`` is what actually tests one.
"""
from __future__ import annotations


def require_live_viewer() -> str:
    """Return the port of a live viewer, or exit(1) with instructions if there is none."""
    try:
        from ocp_vscode import set_port
        from ocp_vscode.comms import get_ports, port_check
    except ImportError:
        raise SystemExit("ocp_vscode is not installed — nothing to show")

    registered = get_ports()
    live = [p for p in registered if port_check(int(p))]
    if not live:
        raise SystemExit(
            f"\nNO OCP VIEWER IS LISTENING — nothing was sent.\n"
            f"  registered ports: {', '.join(registered) or 'none'} "
            f"(stale; none of them answered)\n"
            f"  start one with:   VS Code command palette -> 'OCP CAD Viewer: Open viewer'\n"
            f"                    or standalone: .venv/bin/python -m ocp_vscode\n"
            f"  then re-run.\n"
            f"Anything currently on screen is left over from an earlier session.")
    set_port(int(live[0]))
    return live[0]
