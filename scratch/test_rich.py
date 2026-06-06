import re

def replace_dollar_in_tags(text):
    def repl(match):
        tag_content = match.group(1)
        return f"[{tag_content.replace('$', '')}]"
    return re.sub(r'\[([^\]]+)\]', repl, text)

def main():
    file_path = "c:/Users/Parikshit/Desktop/NewGenApps/Sidewinder/sidewinder/ui/screens.py"
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Count occurrences of [$ before replacement
    before_count = content.count("[$")
    print("Occurrences of '[$' before:", before_count)
    
    new_content = replace_dollar_in_tags(content)
    
    after_count = new_content.count("[$")
    print("Occurrences of '[$' after:", after_count)
    
    # Print first few differences or matches
    matches = re.findall(r'\[[^\]]*\$[^\]]*\]', content)
    print("Found matches with $:", matches[:10])
    
    if new_content != content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print("File updated successfully!")

if __name__ == "__main__":
    main()
