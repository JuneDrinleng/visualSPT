"""
Auto-increment version numbers on each Git commit.
Supports two-part version format (e.g., 2.1, 2.2, 3.0).
Synchronizes FileVersion and ProductVersion.
Uses commit message content to decide major/minor bumps.
"""
import os
import re
import sys


def get_commit_message():
    """Get Git commit message."""
    commit_msg_file = ".git/COMMIT_EDITMSG"
    if os.path.exists(commit_msg_file):
        try:
            with open(commit_msg_file, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            pass
    return ""


def should_bump_major(commit_msg):
    """Return True when commit message indicates a major feature implementation."""
    if not commit_msg:
        return False

    keyword_patterns = [
        r"implement.*feature",
        r"feature.*implement",
        r"new.*feature",
        r"add.*feature",
    ]

    for pattern in keyword_patterns:
        if re.search(pattern, commit_msg, re.IGNORECASE):
            return True
    return False


def increment_version(version_str, is_major=False):
    """Increment version in two-part format."""
    parts = [int(x) for x in version_str.split(".")]
    while len(parts) < 2:
        parts.append(0)

    if is_major:
        parts[0] += 1
        parts[1] = 0
    else:
        parts[1] += 1

    return f"{parts[0]}.{parts[1]}"


def version_to_tuple(version_str):
    """Convert a two-part version to a four-part tuple for filevers/prodvers."""
    parts = [int(x) for x in version_str.split(".")]
    while len(parts) < 4:
        parts.append(0)
    return tuple(parts[:4])


def update_version_file(commit_msg=""):
    """Update version numbers in version_info.txt."""
    file_path = "version_info.txt"

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        file_version_match = re.search(r"StringStruct\(u'FileVersion', u'([\d.]+)'\)", content)
        if not file_version_match:
            print("✗ FileVersion not found")
            return False

        current_version = file_version_match.group(1)
        is_major = should_bump_major(commit_msg)
        new_version = increment_version(current_version, is_major)

        content = re.sub(
            r"(StringStruct\(u'FileVersion', u')([\d.]+)('\))",
            rf"\g<1>{new_version}\3",
            content,
        )
        content = re.sub(
            r"(StringStruct\(u'ProductVersion', u')([\d.]+)('\))",
            rf"\g<1>{new_version}\3",
            content,
        )

        version_tuple = version_to_tuple(new_version)
        content = re.sub(
            r"(filevers=\()\d+,\s*\d+,\s*\d+,\s*\d+(\))",
            rf"\g<1>{version_tuple[0]}, {version_tuple[1]}, {version_tuple[2]}, {version_tuple[3]}\2",
            content,
        )
        content = re.sub(
            r"(prodvers=\()\d+,\s*\d+,\s*\d+,\s*\d+(\))",
            rf"\g<1>{version_tuple[0]}, {version_tuple[1]}, {version_tuple[2]}, {version_tuple[3]}\2",
            content,
        )

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        version_py = os.path.join(os.path.dirname(os.path.abspath(file_path)), "server", "version.py")
        try:
            with open(version_py, "w", encoding="utf-8") as vf:
                vf.write(f'__version__ = "{new_version}"\n')
            print(f"✓ Synced server/version.py to {new_version}")
        except Exception as e:
            print(f"⚠ Failed to sync server/version.py: {e}")

        version_type = "major" if is_major else "minor"
        print(f"✓ Version updated ({version_type}): {current_version} -> {new_version}")
        if is_major and commit_msg:
            print("  Detected feature-implementation keywords, bumped major version")

        return True
    except Exception as e:
        print(f"✗ Version update failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    commit_msg = sys.argv[1] if len(sys.argv) > 1 else get_commit_message()
    update_version_file(commit_msg)
