def remove_compose_prompt(content):
    new_lines = []
    lines = content.splitlines()
    i = 0
    removed_count = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("    def compose_prompt("):
            removed_count += 1
            i += 1
            while i < len(lines) and (lines[i].startswith("        ") or lines[i].strip() == ""):
                i += 1
        else:
            new_lines.append(line)
            i += 1
    return "\n".join(new_lines), removed_count

def main():
    file_path = "c:/Users/Parikshit/Desktop/NewGenApps/Sidewinder/sidewinder/ui/screens.py"
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Remove all compose_prompt methods
    content, count = remove_compose_prompt(content)
    print(f"Removed {count} compose_prompt methods.")

    # 2. Replace the base class compose method
    target_compose = """    def compose(self) -> ComposeResult:
        with Horizontal(id="screen-layout"):
            with Vertical(id="left-container"):
                with ScrollableContainer(id="main-content"):
                    yield from self.compose_main()
                with Vertical(id="prompt-area"):
                    yield Static("", id="leader-overlay", classes="leader-overlay")
                    yield InlineConfirm(id="inline-confirm")
                    yield from self.compose_prompt()
            yield Static("█", id="sidebar-sep")
            with Vertical(id="right-sidebar"):
                yield from self.compose_sidebar()
        yield Footer()"""

    replacement_compose = """    def compose(self) -> ComposeResult:
        from .components import BottomNavBar
        with Horizontal(id="screen-layout"):
            with Vertical(id="left-container"):
                with ScrollableContainer(id="main-content"):
                    yield from self.compose_main()
                with Vertical(id="prompt-area"):
                    yield Static("", id="leader-overlay", classes="leader-overlay")
                    yield InlineConfirm(id="inline-confirm")
            yield Static("█", id="sidebar-sep")
            with Vertical(id="right-sidebar"):
                yield from self.compose_sidebar()
        yield BottomNavBar()"""

    if target_compose in content:
        content = content.replace(target_compose, replacement_compose)
        print("Replaced base class compose method.")
    else:
        # Let's search with different line endings if any
        target_compose_lf = target_compose.replace("\r\n", "\n")
        replacement_compose_lf = replacement_compose.replace("\r\n", "\n")
        if target_compose_lf in content:
            content = content.replace(target_compose_lf, replacement_compose_lf)
            print("Replaced base class compose method (LF).")
        else:
            print("WARNING: Base class compose method NOT found in screens.py!")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("screens.py written successfully.")

if __name__ == "__main__":
    main()
