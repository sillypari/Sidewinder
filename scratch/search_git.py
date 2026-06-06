import subprocess
import os

symbols = ["🏠", "🔍", "📡", "⚙️", "🗑️", "❓", "❌", "→", "←", "▣", "■", "⬝", "●", "△", "✓", "✗", "↻", "⊕", "⊖", "★", "⚡", "⚙"]

def main():
    # Find all commits
    commits = subprocess.check_output(["git", "log", "--format=%H"], text=True).strip().split('\n')
    
    seen_lines = set()
    for commit in commits:
        # Get list of files in ui
        try:
            files_data = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", commit], text=True)
            ui_files = [f for f in files_data.splitlines() if f.startswith("sidewinder/ui/") and f.endswith(".py")]
        except Exception:
            continue
            
        for f in ui_files:
            try:
                content = subprocess.check_output(["git", "show", f"{commit}:{f}"], text=True, encoding="utf-8")
                for line in content.splitlines():
                    if any(sym in line for sym in symbols):
                        trimmed = line.strip()
                        if trimmed not in seen_lines:
                            seen_lines.add(trimmed)
                            print(f"{commit[:8]} {f}: {trimmed}")
            except Exception:
                pass

if __name__ == "__main__":
    main()
