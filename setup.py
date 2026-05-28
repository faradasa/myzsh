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
import argparse

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

def _read_text(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read().strip()
    except OSError:
        return ""

def detect_aws_environment():
    """Best-effort AWS/EC2 detection without requiring privileged access."""
    if os.environ.get("AWS_EXECUTION_ENV"):
        return True, "AWS_EXECUTION_ENV present"

    hypervisor_uuid = _read_text("/sys/hypervisor/uuid").lower()
    if hypervisor_uuid.startswith("ec2"):
        return True, "/sys/hypervisor/uuid starts with ec2"

    dmi_candidates = [
        "/sys/class/dmi/id/sys_vendor",
        "/sys/class/dmi/id/board_vendor",
        "/sys/class/dmi/id/chassis_vendor",
        "/sys/devices/virtual/dmi/id/sys_vendor",
    ]
    for p in dmi_candidates:
        val = _read_text(p).lower()
        if "amazon ec2" in val or val == "amazon":
            return True, f"DMI vendor indicates AWS ({p})"

    # Metadata endpoint check with aggressive timeout to avoid hanging.
    rc, out, _ = run_silent(
        "curl -fsS --connect-timeout 1 --max-time 1 "
        "http://169.254.169.254/latest/meta-data/instance-id"
    )
    if rc == 0 and out.startswith("i-"):
        return True, "instance-id returned from IMDS"

    return False, "no AWS indicators detected"

# ── OS detection ──────────────────────────────────────────────────────────────
OS = platform.system()   # "Linux" or "Darwin"
IS_LINUX = OS == "Linux"
IS_MACOS = OS == "Darwin"

# ─────────────────────────────────────────────────────────────────────────────
# Step 1: Prerequisites
# ─────────────────────────────────────────────────────────────────────────────
_APT_PACKAGES = {"zsh": "zsh", "curl": "curl", "git": "git"}

def _linux_apt_available():
    if not IS_LINUX:
        return False
    rc, _, _ = run_silent("command -v apt-get")
    return rc == 0

def _linux_sudo_noninteractive():
    rc, _, _ = run_silent("sudo -n true")
    return rc == 0

def _try_apt_install(packages):
    """Install Debian/Ubuntu packages when passwordless sudo is available."""
    if not packages or not _linux_apt_available() or not _linux_sudo_noninteractive():
        return False
    pkg_list = " ".join(packages)
    rc, _, err = run_silent(
        "sudo -n env DEBIAN_FRONTEND=noninteractive "
        f"apt-get install -y -qq {pkg_list}"
    )
    if rc != 0 and err:
        print(f"  {YELLOW}apt install note:{RESET} {err.splitlines()[-1] if err else 'failed'}")
    return rc == 0

def _linux_prereq_hint(missing, aws_mode=False):
    hints = []
    apt_names = [_APT_PACKAGES[t] for t in missing if t in _APT_PACKAGES]
    if apt_names and _linux_apt_available():
        hints.append(f"sudo apt install -y {' '.join(apt_names)}")
    if "zsh" in missing and not aws_mode:
        hints.append("optional: chsh -s $(which zsh)   # login shell (needs your password)")
    return hints

def _ohmyzsh_ready():
    return os.path.isfile(home(".oh-my-zsh", "oh-my-zsh.sh"))

def check_prerequisites(aws_mode=False):
    print("\n[1/11] Checking prerequisites...")
    required = ("zsh", "curl", "git")
    missing = [t for t in required if not shutil.which(t)]

    for tool in required:
        if tool not in missing:
            ok(f"{tool} found")

    if missing and IS_LINUX:
        apt_pkgs = [_APT_PACKAGES[t] for t in missing if t in _APT_PACKAGES]
        if apt_pkgs:
            if _linux_sudo_noninteractive():
                print(f"  {YELLOW}→{RESET}  Attempting apt install: {' '.join(apt_pkgs)}")
                if _try_apt_install(apt_pkgs):
                    still_missing = [t for t in missing if not shutil.which(t)]
                    installed = [t for t in missing if t not in still_missing]
                    for tool in installed:
                        ok(f"{tool} installed via apt")
                    missing = still_missing
                else:
                    fail("apt install failed (check sudo / network)")
            else:
                for hint in _linux_prereq_hint(missing, aws_mode=aws_mode):
                    print(f"  {YELLOW}hint:{RESET}  {hint}")

    for tool in missing:
        fail(f"{tool} not found — install it before continuing")
        if IS_LINUX and tool in _APT_PACKAGES:
            print(f"  {YELLOW}hint:{RESET}  sudo apt install -y {_APT_PACKAGES[tool]}")

    all_ok = not missing
    if not all_ok:
        print(f"  {YELLOW}Some prerequisites are missing. Continuing anyway...{RESET}")
    record("prerequisites", "ok" if all_ok else "fail")

# ─────────────────────────────────────────────────────────────────────────────
# Step 2: Oh My Zsh
# ─────────────────────────────────────────────────────────────────────────────
def install_ohmyzsh():
    print("\n[2/11] Installing Oh My Zsh...")
    omz_dir = home(".oh-my-zsh")
    if _ohmyzsh_ready():
        skip("Oh My Zsh already installed")
        record("oh-my-zsh", "skip")
        return
    if os.path.isdir(omz_dir) and not _ohmyzsh_ready():
        print(f"  {YELLOW}→{RESET}  ~/.oh-my-zsh exists but is incomplete — reinstalling")
        shutil.rmtree(omz_dir)
    if not shutil.which("zsh"):
        fail("zsh not in PATH — install zsh before Oh My Zsh")
        record("oh-my-zsh", "fail")
        return
    try:
        run(
            'sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"'
            ' "" --unattended'
        )
        if _ohmyzsh_ready():
            ok("Oh My Zsh installed")
            record("oh-my-zsh", "ok")
        else:
            fail("Oh My Zsh install finished but oh-my-zsh.sh is missing")
            record("oh-my-zsh", "fail")
    except subprocess.CalledProcessError as e:
        fail(f"Oh My Zsh install failed: {e}")
        record("oh-my-zsh", "fail")

# ─────────────────────────────────────────────────────────────────────────────
# Step 3: Powerlevel10k
# ─────────────────────────────────────────────────────────────────────────────
def install_p10k():
    print("\n[3/11] Installing Powerlevel10k...")
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
    print("\n[4/11] Installing Oh My Zsh custom plugins...")
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
def install_brew(aws_mode=False):
    print("\n[5/11] Installing Homebrew...")
    if shutil.which("brew"):
        skip("brew already installed")
        record("homebrew", "skip")
        return
    # Also check common non-PATH locations
    brew_paths = [
        home(".linuxbrew", "bin", "brew"),
        "/home/linuxbrew/.linuxbrew/bin/brew",
        "/opt/homebrew/bin/brew",
        "/usr/local/bin/brew",
    ]
    if any(os.path.isfile(p) for p in brew_paths):
        skip("brew binary found (not in PATH yet — will be activated by zshrc)")
        record("homebrew", "skip")
        return

    if aws_mode and IS_LINUX:
        brew_root = home(".linuxbrew")
        brew_repo = os.path.join(brew_root, "Homebrew")
        brew_bin = os.path.join(brew_root, "bin")
        brew_exe = os.path.join(brew_bin, "brew")
        try:
            os.makedirs(brew_bin, exist_ok=True)
            if not os.path.isdir(brew_repo):
                run(
                    f"git clone --depth=1 https://github.com/Homebrew/brew {brew_repo}"
                )
            if not os.path.exists(brew_exe):
                os.symlink("../Homebrew/bin/brew", brew_exe)
            run(f"{brew_exe} update --force --quiet")
            os.environ["PATH"] = f"{brew_bin}:{os.environ.get('PATH', '')}"
            ok("Homebrew installed in ~/.linuxbrew (AWS no-sudo mode)")
            record("homebrew", "ok")
            return
        except (OSError, subprocess.CalledProcessError) as e:
            fail(f"Homebrew AWS no-sudo install failed: {e}")
            record("homebrew", "fail")
            return

    try:
        run(
            'NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL'
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
# (formula, [fallback formulas], optional on Linux when brew build fails)
BREW_PACKAGE_SPECS = [
    ("eza", [], False),
    ("bat", [], False),
    ("fzf", [], False),
    ("fd", [], False),
    ("ripgrep", [], False),
    ("zoxide", [], False),
    ("lazygit", [], False),
    ("neovim", [], False),
    ("git-delta", [], False),
    ("dust", [], False),
    ("duf", [], False),
    ("bottom", [], False),
    ("jq", [], False),
    # tldr is deprecated; tlrc is the maintained replacement (fewer deps on Linuxbrew).
    ("tlrc", ["tealdeer"], True),
    ("httpie", [], True),
    ("hyperfine", [], True),
]

def _brew_cmd():
    """Return the path to brew, checking common locations."""
    if shutil.which("brew"):
        return "brew"
    for p in [
        home(".linuxbrew", "bin", "brew"),
        "/home/linuxbrew/.linuxbrew/bin/brew",
        "/opt/homebrew/bin/brew",
        "/usr/local/bin/brew",
    ]:
        if os.path.isfile(p):
            return p
    return None

def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Install dependencies for zshrc_best"
    )
    parser.add_argument(
        "--aws",
        action="store_true",
        help="Force AWS/EC2 mode (install Homebrew in ~/.linuxbrew without sudo)",
    )
    return parser.parse_args(argv)

def _brew_install_env():
    """Reduce slow/failed auto-update noise during batch installs (common on EC2)."""
    env = os.environ.copy()
    env.setdefault("HOMEBREW_NO_AUTO_UPDATE", "1")
    env.setdefault("HOMEBREW_NO_INSTALLED_DEPENDENTS_CHECK", "1")
    if IS_LINUX:
        env.setdefault("HOMEBREW_NO_ENV_HINTS", "1")
    return env

def _formula_installed(installed, name):
    """Match brew list names and common aliases (e.g. tldr vs tlrc)."""
    aliases = {name}
    if name == "tlrc":
        aliases.update(("tldr", "tealdeer"))
    elif name == "tldr":
        aliases.update(("tlrc", "tealdeer"))
    return bool(aliases & installed)

def _install_one_brew_formula(brew, formula, env):
    run(f"{brew} install --formula {formula}", env=env)

def install_brew_packages():
    print("\n[6/11] Installing brew packages...")
    brew = _brew_cmd()
    if not brew:
        fail("brew not found — skipping package installs")
        record("brew-packages", "fail")
        return

    env = _brew_install_env()

    # Get already-installed packages once (--formula -1 gives one name per line)
    rc, installed_out, _ = run_silent(f"{brew} list --formula -1")
    installed = set(installed_out.splitlines())

    for spec in BREW_PACKAGE_SPECS:
        formula, fallbacks, optional_on_linux = spec
        optional = optional_on_linux and IS_LINUX

        if _formula_installed(installed, formula):
            skip(f"{formula} already installed")
            record(f"brew:{formula}", "skip")
            continue

        candidates = [formula, *fallbacks]
        last_error = None
        installed_name = None

        for candidate in candidates:
            if candidate in installed:
                skip(f"{candidate} already installed")
                record(f"brew:{formula}", "skip")
                installed_name = candidate
                break
            try:
                _install_one_brew_formula(brew, candidate, env)
                ok(f"{candidate} installed")
                record(f"brew:{formula}", "ok")
                installed.add(candidate)
                installed_name = candidate
                break
            except subprocess.CalledProcessError as e:
                last_error = e
                if candidate != candidates[-1]:
                    print(
                        f"  {YELLOW}→{RESET}  {candidate} failed, trying next option..."
                    )

        if installed_name is not None:
            continue

        msg = f"{formula} install failed"
        if last_error:
            msg += f": {last_error}"
        if optional:
            skip(f"{msg} (optional on Linux — shell works without it)")
            record(f"brew:{formula}", "skip")
        else:
            fail(msg)
            record(f"brew:{formula}", "fail")

def _delta_binary():
    """Resolve delta executable (PATH or Homebrew prefix — setup.py may lack brew in PATH)."""
    w = shutil.which("delta")
    if w:
        return w
    brew = _brew_cmd()
    if not brew:
        return None
    rc, prefix, _ = run_silent(f"{brew} --prefix")
    if rc != 0 or not prefix:
        return None
    candidate = os.path.join(prefix.strip(), "bin", "delta")
    return candidate if os.path.isfile(candidate) else None

def configure_git_delta():
    """Set global git options so delta is used for pager and interactive diff."""
    print("\n       Configuring git to use delta...")
    if not _delta_binary():
        skip("delta not found — skipping git config")
        record("git-delta-config", "skip")
        return
    if not shutil.which("git"):
        skip("git not in PATH — skipping git config")
        record("git-delta-config", "skip")
        return
    configs = [
        ("core.pager", "delta"),
        ("interactive.diffFilter", "delta --color-only"),
        ("merge.conflictStyle", "diff3"),
        ("diff.colorMoved", "default"),
        ("delta.navigate", "true"),
        ("delta.line-numbers", "true"),
    ]
    try:
        for key, value in configs:
            subprocess.run(
                ["git", "config", "--global", key, value],
                check=True,
            )
        ok("git configured to use delta")
        record("git-delta-config", "ok")
    except subprocess.CalledProcessError as e:
        fail(f"git config for delta failed: {e}")
        record("git-delta-config", "fail")

# ─────────────────────────────────────────────────────────────────────────────
# Step 7: NVM
# ─────────────────────────────────────────────────────────────────────────────
def install_nvm():
    print("\n[7/11] Installing NVM...")
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
    print("\n[8/11] Installing Bun...")
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
_BASHRC_ZSH_MARKER = "# zshrc_best: auto-start zsh"

def configure_zsh_launcher(aws_mode=False):
    """Use ~/.bashrc instead of chsh on EC2 (chsh usually asks for a password)."""
    print("\n[10/11] Configuring zsh launcher...")
    zsh_path = shutil.which("zsh")
    if not zsh_path:
        skip("zsh not found — skipping launcher setup")
        record("zsh-launcher", "skip")
        return

    bashrc = home(".bashrc")
    snippet = (
        f"{_BASHRC_ZSH_MARKER}\n"
        f'if [[ -z "${{ZSH_VERSION:-}}" ]] && [[ -x "{zsh_path}" ]]; then\n'
        f"  exec {zsh_path} -l\n"
        "fi\n"
    )

    try:
        existing = ""
        if os.path.isfile(bashrc):
            with open(bashrc, "r", encoding="utf-8", errors="ignore") as f:
                existing = f.read()
        if _BASHRC_ZSH_MARKER in existing:
            skip("~/.bashrc already starts zsh on login")
            record("zsh-launcher", "skip")
            return
        with open(bashrc, "a", encoding="utf-8") as f:
            if existing and not existing.endswith("\n"):
                f.write("\n")
            f.write("\n" + snippet)
        ok("~/.bashrc will exec zsh on SSH login (no chsh password needed)")
        record("zsh-launcher", "ok")
    except OSError as e:
        fail(f"Could not update ~/.bashrc: {e}")
        record("zsh-launcher", "fail")
        return

    if aws_mode or IS_LINUX:
        print(
            f"  {YELLOW}note:{RESET}  EC2: skip chsh — new SSH sessions use zsh automatically"
        )
        print(f"  {YELLOW}note:{RESET}  Current session: run {GREEN}zsh{RESET} or reconnect SSH")

def deploy_zshrc():
    print("\n[9/11] Deploying zshrc_best to ~/.zshrc...")
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
        print(f"\n  {GREEN}All done!{RESET}")
        print(f"  Run {GREEN}zsh{RESET} now, reconnect SSH, or: source ~/.zshrc\n")
    else:
        print(f"\n  {YELLOW}Some steps failed — review output above and re-run if needed.{RESET}\n")

# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
def main():
    args = parse_args(sys.argv[1:])
    auto_aws, aws_reason = detect_aws_environment()
    aws_mode = args.aws or auto_aws

    print(f"{'─'*60}")
    print(f"  zshrc_best setup  ({OS})")
    print(f"{'─'*60}")
    if args.aws:
        print("  AWS mode: forced via --aws")
    elif auto_aws:
        print(f"  AWS mode: auto-detected ({aws_reason})")
    else:
        print("  AWS mode: off (use --aws to force no-sudo Linuxbrew path)")

    check_prerequisites(aws_mode=aws_mode)
    install_ohmyzsh()
    install_p10k()
    install_plugins()
    install_brew(aws_mode=aws_mode)
    install_brew_packages()
    configure_git_delta()
    install_nvm()
    install_bun()
    deploy_zshrc()
    configure_zsh_launcher(aws_mode=aws_mode)
    print_summary()

if __name__ == "__main__":
    main()
