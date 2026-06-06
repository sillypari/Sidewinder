import re

def remove_compose_prompt(content):
    # Match compose_prompt with its body
    # We match:
    # 4 spaces indentation + def compose_prompt(self) ... :
    # followed by lines that are indented by at least 8 spaces, or empty lines.
    pattern = r"    def compose_prompt\(self\)[^:]*:\n(^[ \t]*\n|        [^\n]*\n)*"
    # Wait, let's make it more robust. A method ends when a line with 4 or fewer spaces starts
    # (unless it's an empty line).
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
        
    new_content, count = remove_compose_prompt(content)
    print(f"Removed {count} compose_prompt methods.")
    
    # Also verify if any compose_prompt remains
    remaining = [line for line in new_content.splitlines() if "def compose_prompt" in line]
    print("Remaining definitions:", remaining)

if __name__ == "__main__":
    main()
