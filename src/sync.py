"""Commit + push hasil olahan (data/processed, figures) ke GitHub dari Colab."""
import os
import subprocess


def push_results(base_dir: str, message: str, paths: list[str] | None = None) -> None:
    """
    git add + commit + push untuk file hasil (parquet/json/png), supaya bisa
    dicek dari GitHub tanpa Drive. Aman dipanggil walau tidak ada perubahan
    (git commit akan no-op, push tetap dicoba).

    paths: daftar path relatif ke base_dir yang mau di-add. Default:
    data/processed/ dan figures/.
    """
    if paths is None:
        paths = ["data/processed", "figures"]

    def run(cmd):
        result = subprocess.run(cmd, cwd=base_dir, capture_output=True, text=True)
        print(f"$ {' '.join(cmd)}")
        if result.stdout.strip():
            print(result.stdout)
        if result.returncode != 0 and result.stderr.strip():
            print(result.stderr)
        return result

    run(["git", "add"] + paths)
    status = run(["git", "status", "--porcelain"] + paths)
    if not status.stdout.strip():
        print("Tidak ada perubahan untuk di-push.")
        return

    run(["git", "commit", "-m", message])
    run(["git", "push", "origin", "main"])
