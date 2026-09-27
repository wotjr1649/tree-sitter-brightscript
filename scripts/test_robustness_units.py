"""Check the POSIX peak-memory units used by V10."""

from check_robustness import maxrss_bytes


assert maxrss_bytes(4096, "linux") == 4096 * 1024
assert maxrss_bytes(4096, "darwin") == 4096
try:
    maxrss_bytes(4096, "freebsd")
except RuntimeError:
    pass
else:
    raise AssertionError("unknown RSS units must fail")
