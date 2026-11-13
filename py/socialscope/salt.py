"""One hashing salt per project, so the same account keeps the same hash across runs and tools.

Order: an explicit salt argument, then the SOCIALSCOPE_SALT environment variable, then the file
.socialscope_salt in the working directory (created on first use). Keep that file private: with it,
hashed names can be matched back to usernames by anyone holding the username list."""
import os


def get(salt=None, path=".socialscope_salt"):
    if salt:
        return salt
    if os.environ.get("SOCIALSCOPE_SALT"):
        return os.environ["SOCIALSCOPE_SALT"]
    if os.path.exists(path):
        return open(path).read().strip()
    s = os.urandom(8).hex()
    with open(path, "w") as fh:
        fh.write(s)
    return s
