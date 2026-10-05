import os

# Keep the deterministic offline test suite independent of network availability.
os.environ.setdefault("BAYYIN_LIVE_SOURCES", "off")
