import os
import re

def replace_dollar_in_tags(text):
    def repl(match):
        tag_content = match.group(1)
        # remove all '$' from the tag content
        return f"[{tag_content.replace('$', '')}]"
    return re.sub(r'\[([^\]]+)\]', repl, text)

def main():
    ui_dir = "c:/Users/Parikshit/Desktop/NewGenApps/Sidewinder/sidewinder/ui"
    for root, dirs, files in os.walk(ui_dir):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    new_content = replace_dollar_in_tags(content)
                    if new_content != content:
                        with open(path, "w", encoding="utf-8") as f:
                            f.write(new_content)
                        print(f"Fixed markup in {file}")
                except Exception as e:
                    print(f"Error processing {file}: {e}")

if __name__ == "__main__":
    main()
