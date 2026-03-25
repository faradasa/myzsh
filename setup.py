#!/usr/bin/env python3
"""
setup.py — Install everything needed for zshrc_best to work.
Run with: python3 setup.py
"""

import os
import platform
import shutil
import subprocess
import sys

# ── ANSI color helpers ────────────────────────────────────────────────────────
GREEN  = "\033[32m"
RED    = "\033[31m"
YELLOW = "\033[33m"
RESET  = "\033[0m"

def ok(msg):   print(f"  {GREEN}✓{RESET}  {msg}")
def fail(msg): print(f"  {RED}✗{RESET}  {msg}")
def skip(msg): print(f"  {YELLOW}→{RESET}  {msg}")

# ── Results tracker ───────────────────────────────────────────────────────────
results = []  # list of (label, status)  status: "ok" | "fail" | "skip"

def record(label, status):
    results.append((label, status))

# ── Helpers ───────────────────────────────────────────────────────────────────
def run(cmd, **kwargs):
    """Run a shell command, inheriting stdio by default."""
    kwargs.setdefault("shell", True)
    kwargs.setdefault("check", True)
    return subprocess.run(cmd, **kwargs)

def run_silent(cmd):
    """Run a command, capturing output, returning (returncode, stdout, stderr)."""
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()

def exists(path):
    return os.path.exists(os.path.expanduser(path))

def home(*parts):
    return os.path.join(os.path.expanduser("~"), *parts)

# ── OS detection ──────────────────────────────────────────────────────────────
OS = platform.system()   # "Linux" or "Darwin"
IS_LINUX = OS == "Linux"
IS_MACOS = OS == "Darwin"

# ─────────────────────────────────────────────────────────────────────────────
# Step 1: Prerequisites
# ─────────────────────────────────────────────────────────────────────────────
def check_prerequisites():
    print("\n[1/10] Checking prerequisites...")
    all_ok = True
    for tool in ("zsh", "curl", "git"):
        if shutil.which(tool):
            ok(f"{tool} found")
        else:
            fail(f"{tool} not found — install it before continuing")
            all_ok = False
    if not all_ok:
        print(f"  {YELLOW}Some prerequisites are missing. Continuing anyway...{RESET}")
    record("prerequisites", "ok" if all_ok else "fail")

# ─────────────────────────────────────────────────────────────────────────────
# Step 2: Oh My Zsh
# ─────────────────────────────────────────────────────────────────────────────
def install_ohmyzsh():
    print("\n[2/10] Installing Oh My Zsh...")
    if exists("~/.oh-my-zsh"):
        skip("Oh My Zsh already installed")
        record("oh-my-zsh", "skip")
        return
    try:
        run(
            'sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"'
            ' "" --unattended'
        )
        ok("Oh My Zsh installed")
        record("oh-my-zsh", "ok")
    except subprocess.CalledProcessError as e:
        fail(f"Oh My Zsh install failed: {e}")
        record("oh-my-zsh", "fail")

# ─────────────────────────────────────────────────────────────────────────────
# Step 3: Powerlevel10k
# ─────────────────────────────────────────────────────────────────────────────
def install_p10k():
    print("\n[3/10] Installing Powerlevel10k...")
    zsh_custom = os.environ.get("ZSH_CUSTOM", home(".oh-my-zsh", "custom"))
    dest = os.path.join(zsh_custom, "themes", "powerlevel10k")
    if os.path.exists(dest):
        skip("Powerlevel10k already installed")
        record("powerlevel10k", "skip")
        return
    try:
        run(
            f"git clone --depth=1 https://github.com/romkatv/powerlevel10k.git {dest}"
        )
        ok("Powerlevel10k installed")
        record("powerlevel10k", "ok")
    except subprocess.CalledProcessError as e:
        fail(f"Powerlevel10k install failed: {e}")
        record("powerlevel10k", "fail")

# ─────────────────────────────────────────────────────────────────────────────
# Step 4: Oh My Zsh custom plugins
# ─────────────────────────────────────────────────────────────────────────────
PLUGINS = [
    (
        "zsh-autosuggestions",
        "https://github.com/zsh-users/zsh-autosuggestions",
    ),
    (
        "zsh-syntax-highlighting",
        "https://github.com/zsh-users/zsh-syntax-highlighting.git",
    ),
    (
        "zsh-fzf-history-search",
        "https://github.com/joshskidmore/zsh-fzf-history-search",
    ),
    (
        "fzf-tab",
        "https://github.com/Aloxaf/fzf-tab",
    ),
    (
        "you-should-use",
        "https://github.com/MichaelAquilina/zsh-you-should-use.git",
        "you-should-use",  # override dir name if different from slug
    ),
]

def install_plugins():
    print("\n[4/10] Installing Oh My Zsh custom plugins...")
    zsh_custom = os.environ.get("ZSH_CUSTOM", home(".oh-my-zsh", "custom"))
    plugins_dir = os.path.join(zsh_custom, "plugins")

    for entry in PLUGINS:
        name = entry[0]
        url  = entry[1]
        dirname = entry[2] if len(entry) > 2 else name
        dest = os.path.join(plugins_dir, dirname)
        if os.path.exists(dest):
            skip(f"{name} already installed")
            record(f"plugin:{name}", "skip")
            continue
        try:
            run(f"git clone {url} {dest}")
            ok(f"{name} installed")
            record(f"plugin:{name}", "ok")
        except subprocess.CalledProcessError as e:
            fail(f"{name} install failed: {e}")
            record(f"plugin:{name}", "fail")

# ─────────────────────────────────────────────────────────────────────────────
# Step 5: Homebrew / Linuxbrew
# ─────────────────────────────────────────────────────────────────────────────
def install_brew():
    print("\n[5/10] Installing Homebrew...")
    if shutil.which("brew"):
        skip("brew already installed")
        record("homebrew", "skip")
        return
    # Also check common non-PATH locations
    brew_paths = [
        "/home/linuxbrew/.linuxbrew/bin/brew",
        "/opt/homebrew/bin/brew",
        "/usr/local/bin/brew",
    ]
    if any(os.path.isfile(p) for p in brew_paths):
        skip("brew binary found (not in PATH yet — will be activated by zshrc)")
        record("homebrew", "skip")
        return
    try:
        run(
            '/bin/bash -c "$(curl -fsSL'
            ' https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
        )
        ok("Homebrew installed")
        record("homebrew", "ok")
    except subprocess.CalledProcessError as e:
        fail(f"Homebrew install failed: {e}")
        record("homebrew", "fail")

# ─────────────────────────────────────────────────────────────────────────────
# Step 6: Brew packages
# ─────────────────────────────────────────────────────────────────────────────
BREW_PACKAGES = ["eza", "bat", "fzf", "fd", "ripgrep", "zoxide", "lazygit", "neovim"]

def _brew_cmd():
    """Return the path to brew, checking common locations."""
    if shutil.which("brew"):
        return "brew"
    for p in [
        "/home/linuxbrew/.linuxbrew/bin/brew",
        "/opt/homebrew/bin/brew",
        "/usr/local/bin/brew",
    ]:
        if os.path.isfile(p):
            return p
    return None

def install_brew_packages():
    print("\n[6/10] Installing brew packages...")
    brew = _brew_cmd()
    if not brew:
        fail("brew not found — skipping package installs")
        record("brew-packages", "fail")
        return

    # Get already-installed packages once (--formula -1 gives one name per line)
    rc, installed_out, _ = run_silent(f"{brew} list --formula -1")
    installed = set(installed_out.splitlines())

    for pkg in BREW_PACKAGES:
        if pkg in installed:
            skip(f"{pkg} already installed")
            record(f"brew:{pkg}", "skip")
            continue
        try:
            run(f"{brew} install {pkg}")
            ok(f"{pkg} installed")
            record(f"brew:{pkg}", "ok")
        except subprocess.CalledProcessError as e:
            fail(f"{pkg} install failed: {e}")
            record(f"brew:{pkg}", "fail")

# ─────────────────────────────────────────────────────────────────────────────
# Step 7: NVM
# ─────────────────────────────────────────────────────────────────────────────
def install_nvm():
    print("\n[7/10] Installing NVM...")
    if exists("~/.nvm"):
        skip("NVM already installed")
        record("nvm", "skip")
        return
    try:
        run(
            "curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash"
        )
        ok("NVM installed")
        record("nvm", "ok")
    except subprocess.CalledProcessError as e:
        fail(f"NVM install failed: {e}")
        record("nvm", "fail")

# ─────────────────────────────────────────────────────────────────────────────
# Step 8: Bun
# ─────────────────────────────────────────────────────────────────────────────
def install_bun():
    print("\n[8/10] Installing Bun...")
    if exists("~/.bun/bin/bun"):
        skip("Bun already installed")
        record("bun", "skip")
        return
    try:
        run("curl -fsSL https://bun.sh/install | bash")
        ok("Bun installed")
        record("bun", "ok")
    except subprocess.CalledProcessError as e:
        fail(f"Bun install failed: {e}")
        record("bun", "fail")

# ─────────────────────────────────────────────────────────────────────────────
# Step 9: Deploy zshrc_best
# ─────────────────────────────────────────────────────────────────────────────
def deploy_zshrc():
    print("\n[9/10] Deploying zshrc_best to ~/.zshrc...")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(script_dir, "zshrc_best")
    dst = os.path.expanduser("~/.zshrc")
    bak = os.path.expanduser("~/.zshrc.bak")

    if not os.path.isfile(src):
        fail(f"zshrc_best not found at {src}")
        record("deploy-zshrc", "fail")
        return

    try:
        if os.path.isfile(dst):
            shutil.copy2(dst, bak)
            ok(f"Backed up existing ~/.zshrc to ~/.zshrc.bak")
        shutil.copy2(src, dst)
        ok(f"~/.zshrc deployed from {src}")
        record("deploy-zshrc", "ok")
    except OSError as e:
        fail(f"Failed to deploy zshrc: {e}")
        record("deploy-zshrc", "fail")

# ─────────────────────────────────────────────────────────────────────────────
# Step 9: Summary
# ─────────────────────────────────────────────────────────────────────────────
def print_summary():
    print("\n" + "─" * 60)
    print("Summary")
    print("─" * 60)
    counts = {"ok": 0, "fail": 0, "skip": 0}
    for label, status in results:
        counts[status] += 1
        if status == "ok":
            print(f"  {GREEN}✓{RESET}  {label}")
        elif status == "fail":
            print(f"  {RED}✗{RESET}  {label}")
        else:
            print(f"  {YELLOW}→{RESET}  {label} (already present)")
    print("─" * 60)
    print(
        f"  {GREEN}{counts['ok']} succeeded{RESET}  "
        f"{YELLOW}{counts['skip']} skipped{RESET}  "
        f"{RED}{counts['fail']} failed{RESET}"
    )
    if counts["fail"] == 0:
        print(f"\n  {GREEN}All done! Restart your terminal or run: source ~/.zshrc{RESET}\n")
    else:
        print(f"\n  {YELLOW}Some steps failed — review output above and re-run if needed.{RESET}\n")

# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
def main():
    print(f"{'─'*60}")
    print(f"  zshrc_best setup  ({OS})")
    print(f"{'─'*60}")

    check_prerequisites()
    install_ohmyzsh()
    install_p10k()
    install_plugins()
    install_brew()
    install_brew_packages()
    install_nvm()
    install_bun()
    deploy_zshrc()
    print_summary()

if __name__ == "__main__":
    main()
