import sqlite3

def main():
    conn = sqlite3.connect("restruct_warp.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, prompt, type, output FROM generations ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    if not row:
        print("No generations found.")
        return
    gen_id, prompt, gen_type, output = row
    print(f"ID: {gen_id}")
    print(f"Prompt: {prompt}")
    print(f"Type: {gen_type}")
    print(f"Output Length: {len(output)}")
    print("\n--- Output ---")
    print(output[:2000])
    if len(output) > 2000:
        print("...")
        print(output[-1000:])
    conn.close()

if __name__ == "__main__":
    main()
