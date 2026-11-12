import sqlite3

def seed_data():
    print("Connecting to database...")
    conn = sqlite3.connect('ngos.db')
    c = conn.cursor()
    
    # --- STEP 1: CREATE TABLES (Fixes the "no such table" error) ---
    print("Checking table structure...")
    
    # 1. NGO Table with 'is_urgent' column
    c.execute('''CREATE TABLE IF NOT EXISTS ngos
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  city TEXT NOT NULL,
                  service TEXT NOT NULL,
                  website_url TEXT NOT NULL,
                  category TEXT NOT NULL,
                  is_urgent INTEGER DEFAULT 0)''')
    
    # 2. Users Table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  password TEXT NOT NULL,
                  role TEXT NOT NULL)''')
    
    # 3. Global Stats Table
    c.execute('''CREATE TABLE IF NOT EXISTS stats
                 (id INTEGER PRIMARY KEY,
                  support_count INTEGER DEFAULT 0)''')
                  
    # 4. Create default admin if missing
    c.execute("SELECT * FROM users WHERE username='admin'")
    if not c.fetchone():
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", ('admin', 'admin123', 'admin'))
        print("✅ Admin user created.")

    # 5. Initialize stats if missing
    c.execute("INSERT OR IGNORE INTO stats (id, support_count) VALUES (1, 142)")

    # --- STEP 2: INSERT DATA ---
    
    # Clear existing NGOs to avoid duplicates if you run this twice
    c.execute("DELETE FROM ngos")
    
    ngos = [
        (
            'The Akshaya Patra Foundation', 
            'Bengaluru', 
            'Mid-day Meals for Schools', 
            'https://www.akshayapatra.org/', 
            'Health',
            0
        ),
        (
            'Goonj', 
            'New Delhi', 
            'Disaster Relief & Clothing', 
            'https://goonj.org/', 
            'Disaster Relief',
            1  # Marked as URGENT
        ),
        (
            'Doctors Without Borders (MSF)', 
            'New Delhi', 
            'Medical Aid in Crisis', 
            'https://www.msf.org/', 
            'Health',
            1 # Marked as URGENT
        ),
        (
            'CRY (Child Rights and You)', 
            'Mumbai', 
            'Child Rights & Safety', 
            'https://www.cry.org/', 
            'Human Rights',
            0
        ),
        (
            'WWF India', 
            'New Delhi', 
            'Wildlife Conservation', 
            'https://www.wwfindia.org/', 
            'Environment',
            0
        ),
        (
            'HelpAge India', 
            'New Delhi', 
            'Elderly Care & Healthcare', 
            'https://www.helpageindia.org/', 
            'Health',
            0
        ),
        (
            'Teach For India', 
            'Mumbai', 
            'Leadership & Education', 
            'https://www.teachforindia.org/', 
            'Education',
            0
        ),
        (
            'Pratham', 
            'Mumbai', 
            'Quality Education for Kids', 
            'https://www.pratham.org/', 
            'Education',
            0
        ),
        (
            'Sewa International', 
            'New Delhi', 
            'Disaster Recovery & Development', 
            'https://www.sewainternational.org/', 
            'Disaster Relief',
            0
        ),
        (
            'Smile Foundation', 
            'New Delhi', 
            'Child Education & Health', 
            'https://www.smilefoundationindia.org', 
            'Education',
            0
        ),
        (
            'GiveIndia', 
            'Bengaluru', 
            'Poverty Alleviation Platform', 
            'https://www.giveindia.org/', 
            'Poverty',
            0
        )
    ]
    
    print(f"Adding {len(ngos)} NGOs...")
    
    try:
        c.executemany("""
            INSERT INTO ngos (name, city, service, website_url, category, is_urgent) 
            VALUES (?, ?, ?, ?, ?, ?)
        """, ngos)
        
        conn.commit()
        print("✅ Success! Tables created and NGOs added.")
        
    except sqlite3.OperationalError as e:
        print(f"❌ Error: {e}")
    
    conn.close()

if __name__ == '__main__':
    seed_data()