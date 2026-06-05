import sqlite3
import re

def main():
    conn = sqlite3.connect("restruct_warp.db")
    cursor = conn.cursor()
    cursor.execute("SELECT output FROM generations ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    if not row:
        print("No generations found.")
        return
    output = row[0]
    
    # Try to find <!DOCTYPE html> or <html> up to </html>
    match = re.search(r'(?i)(<!doctype\s+html|<html)', output)
    if not match:
        print("No HTML tags found.")
        return
    
    html_start = match.start()
    html_end = output.lower().find("</html>")
    if html_end == -1:
        print("No </html> found, taking everything after start.")
        html_content = output[html_start:]
    else:
        html_content = output[html_start:html_end+7]
        
    with open("scratch/preview.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Extracted HTML length: {len(html_content)}. Saved to scratch/preview.html")

if __name__ == "__main__":
    main()
