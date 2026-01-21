import mysql.connector
import sys
import re

# DB CONFIGURATION
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'varrie75',  # <--- UPDATE THIS
    'database': 'job_portal_db'
}


def calculate_score(resume_text, required_skills):
    # Normalize text: lowercase and remove special chars
    resume_clean = re.sub(r'[^a-zA-Z0-9\s]', '', resume_text.lower())
    skills_list = [s.strip().lower() for s in required_skills.split(',')]

    if not skills_list:
        return 0.0

    matches = 0
    for skill in skills_list:
        # Search for skill as a whole word
        if re.search(r'\b' + re.escape(skill) + r'\b', resume_clean):
            matches += 1

    score = (matches / len(skills_list)) * 100
    return round(score, 2)


def analyze_resumes():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        print("Connected to Database...")

        # Fetch candidates joined with job requirements
        query = """
                SELECT c.id, c.resume_text, j.required_skills
                FROM candidates c
                         JOIN jobs j ON c.job_id = j.id \
                """
        cursor.execute(query)
        candidates = cursor.fetchall()

        print(f"Analyzing {len(candidates)} resumes...")

        for cand in candidates:
            cand_id = cand[0]
            resume_text = cand[1]
            required_skills = cand[2]

            score = calculate_score(resume_text, required_skills)

            # Update Score in DB
            update_sql = "UPDATE candidates SET match_score = %s WHERE id = %s"
            cursor.execute(update_sql, (score, cand_id))
            print(f"Candidate ID {cand_id}: Score updated to {score}%")

        conn.commit()
        print("All resumes analyzed successfully.")

    except mysql.connector.Error as err:
        if err.errno == 1045:
            print("AUTH ERROR: Check password in resume_analyzer.py")
        else:
            print(f"Error: {err}")
        sys.exit(1)
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()


if __name__ == "__main__":
    analyze_resumes()