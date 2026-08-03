"""Commit + push hasil olahan (data/processed, figures) ke GitHub dari Colab."""
import subprocess


def _run(cmd, base_dir):
    result = subprocess.run(cmd, cwd=base_dir, capture_output=True, text=True)
    print(f"$ {' '.join(cmd)}")
    if result.stdout.strip():
        print(result.stdout)
    if result.returncode != 0 and result.stderr.strip():
        print(result.stderr)
    return result


def ensure_git_identity(base_dir: str, email: str = "antoniusbonni@gmail.com",
                         name: str = "Antonius Bonni Febrianto") -> None:
    """Set git user.email/user.name LOKAL ke repo ini saja (bukan --global) kalau
    belum ada -- runtime Colab baru selalu kosong identity-nya, bikin git commit
    gagal dengan 'Author identity unknown'."""
    check = subprocess.run(["git", "config", "user.email"], cwd=base_dir, capture_output=True, text=True)
    if not check.stdout.strip():
        _run(["git", "config", "user.email", email], base_dir)
        _run(["git", "config", "user.name", name], base_dir)
        print(f"Git identity di-set: {name} <{email}>")


def ensure_push_access(base_dir: str, repo: str = "antoniusbonnif/big-data-aol") -> bool:
    """
    Pastikan remote origin punya kredensial push (bukan URL publik read-only).
    Token TIDAK ditulis ke kode -- diambil dari Colab Secrets (ikon kunci di
    sidebar kiri, nama secret GITHUB_TOKEN) kalau tersedia. Kalau remote sudah
    punya token di URL, dibiarkan. Return False kalau tak ada token tersedia
    (push kemungkinan akan gagal 403, pesan sudah cukup jelas dari git sendiri).
    """
    current = subprocess.run(
        ["git", "remote", "get-url", "origin"], cwd=base_dir, capture_output=True, text=True
    ).stdout.strip()

    if "@github.com" in current:
        return True  # sudah ada kredensial di URL

    try:
        from google.colab import userdata
        token = userdata.get("GITHUB_TOKEN")
    except Exception:
        token = None

    if not token:
        print(
            "PERINGATAN: remote origin tidak punya kredensial push, dan secret "
            "GITHUB_TOKEN tidak ditemukan di Colab Secrets. Push kemungkinan gagal 403. "
            "Tambahkan token di ikon kunci sidebar kiri Colab, nama: GITHUB_TOKEN."
        )
        return False

    new_url = f"https://{token}@github.com/{repo}.git"
    _run(["git", "remote", "set-url", "origin", new_url], base_dir)
    print("Remote origin diupdate pakai token dari Colab Secrets.")
    return True


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

    ensure_git_identity(base_dir)
    ensure_push_access(base_dir)

    _run(["git", "add"] + paths, base_dir)
    status = _run(["git", "status", "--porcelain"] + paths, base_dir)
    if not status.stdout.strip():
        print("Tidak ada perubahan untuk di-push.")
        return

    _run(["git", "commit", "-m", message], base_dir)
    _run(["git", "push", "origin", "main"], base_dir)
