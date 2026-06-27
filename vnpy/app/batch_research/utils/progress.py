"""
Progress bar utility for batch backtesting.

Uses Unicode block characters when stdout supports UTF-8,
falls back to ASCII '#'/'.' on GBK / other narrow encodings.
"""

import sys


def _stdout_supports_unicode() -> bool:
    """Return True if stdout can encode the block characters we use."""
    enc = getattr(sys.stdout, "encoding", None) or ""
    try:
        "\u2588\u2591".encode(enc)
        return True
    except (UnicodeEncodeError, LookupError):
        return False


class ProgressBar:
    """
    Simple text progress bar, pure Python, no third-party deps.

    Usage::

        bar = ProgressBar(total=500, label="Backtesting")
        for i, symbol in enumerate(symbols):
            bar.update(i + 1, suffix=symbol)
        bar.finish()
    """

    def __init__(
        self,
        total: int,
        label: str = "",
        width: int = 40,
    ) -> None:
        self.total = total
        self.label = label
        self.width = width
        self._current = 0
        self._unicode = _stdout_supports_unicode()

    def update(self, current: int, suffix: str = "") -> None:
        """Redraw the progress bar in place."""
        self._current = current
        filled = int(self.width * current / max(self.total, 1))
        if self._unicode:
            bar = "\u2588" * filled + "\u2591" * (self.width - filled)
        else:
            bar = "#" * filled + "." * (self.width - filled)
        pct = current / max(self.total, 1) * 100
        prefix = f"{self.label} " if self.label else ""
        line = f"\r{prefix}[{bar}] {pct:5.1f}%  {current}/{self.total}"
        if suffix:
            line += f"  {suffix}"
        try:
            sys.stdout.write(line)
            sys.stdout.flush()
        except UnicodeEncodeError:
            # Last-resort fallback: strip non-ASCII and retry
            safe = line.encode("ascii", errors="replace").decode("ascii")
            sys.stdout.write(safe)
            sys.stdout.flush()

    def finish(self) -> None:
        """Print a newline to end the progress bar."""
        self.update(self.total)
        sys.stdout.write("\n")
        sys.stdout.flush()
