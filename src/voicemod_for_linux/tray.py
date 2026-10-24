from __future__ import annotations

import subprocess
import sys

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("AyatanaAppIndicator3", "0.1")
from gi.repository import AyatanaAppIndicator3, Gtk


APPLICATION_ID = "io.github.fakerh0g.VoiceFX"


def _activate_action(action: str) -> None:
    try:
        subprocess.run(
            ["gapplication", "action", APPLICATION_ID, action],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except FileNotFoundError:
        print("gapplication is required for the VoiceFX tray menu.", file=sys.stderr)
    except subprocess.TimeoutExpired:
        print("VoiceFX did not respond to the tray action.", file=sys.stderr)
    except subprocess.CalledProcessError as error:
        detail = error.stderr.strip() or error.stdout.strip() or str(error)
        print(f"Could not run VoiceFX tray action: {detail}", file=sys.stderr)


def main() -> int:
    indicator = AyatanaAppIndicator3.Indicator.new(
        "voicefx",
        "voicefx",
        AyatanaAppIndicator3.IndicatorCategory.APPLICATION_STATUS,
    )
    indicator.set_title("VoiceFX")
    indicator.set_status(AyatanaAppIndicator3.IndicatorStatus.ACTIVE)

    menu = Gtk.Menu()
    open_item = Gtk.MenuItem.new_with_label("Open VoiceFX")
    open_item.connect("activate", lambda _item: _activate_action("show"))
    menu.append(open_item)
    menu.append(Gtk.SeparatorMenuItem())
    quit_item = Gtk.MenuItem.new_with_label("Quit VoiceFX")
    quit_item.connect("activate", lambda _item: _activate_action("quit"))
    menu.append(quit_item)
    menu.show_all()
    indicator.set_menu(menu)

    Gtk.main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
