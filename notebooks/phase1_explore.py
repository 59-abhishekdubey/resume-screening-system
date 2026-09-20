import pandas as pd
import re
import hashlib
import os
import matplotlib.pyplot as plt
import seaborn as sns

#df = pd.read_csv('data/raw/Resume.csv')
df = pd.read_csv(r'C:\Users\Lenovo\OneDrive\Desktop\FUTURE_int\resume-screening-system\data\raw\Resume.csv')
os.makedirs('outputs/figures', exist_ok=True)

# --- Basic info ---
print("=== BASIC INFO ===")
print(f"Shape: {df.shape}")
print(f"Columns: {list(df.columns)}")
print(f"Dtypes:\n{df.dtypes}")
print(f"Null counts:\n{df.isnull().sum()}")

# --- Category distribution ---
print("\n=== CATEGORY DISTRIBUTION ===")
cats = df['Category'].unique()
print(f"Number of categories: {len(cats)}")
cat_counts = df['Category'].value_counts()
for c, n in cat_counts.items():
    print(f"  {c}: {n}")
plt.figure(figsize=(10, 6))
sns.barplot(x=cat_counts.index, y=cat_counts.values)
plt.xticks(rotation=45, ha='right')
plt.title('Category Distribution')
plt.tight_layout()
plt.savefig('outputs/figures/category_distribution.png')
plt.close()

# --- Resume length distribution ---
print("\n=== RESUME LENGTH DISTRIBUTION ===")
char_lens = df['Resume_str'].str.len()
word_lens = df['Resume_str'].str.split().str.len()
print(f"Char length describe:\n{char_lens.describe()}")
print(f"Word length describe:\n{word_lens.describe()}")
plt.figure(figsize=(10, 6))
sns.histplot(char_lens, bins=30, kde=True)
plt.title('Resume Character Length Distribution')
plt.xlabel('Character count')
plt.tight_layout()
plt.savefig('outputs/figures/resume_length_distribution.png')
plt.close()

# --- 3 sample resumes from 3 different categories ---
print("\n=== SAMPLE RESUMES ===")
categories = df['Category'].unique()
for i, cat in enumerate(categories[:3]):
    sample = df[df['Category'] == cat]['Resume_str'].iloc[0]
    print(f"\n--- Category: {cat} ---")
    print(sample[:500])

# --- Duplicate check ---
print("\n=== DUPLICATE CHECK ===")
resumes_normalized = df['Resume_str'].str.strip().str.lower().str.replace(r'\s+', ' ', regex=True)
exact_dups = resumes_normalized[resumes_normalized.duplicated(keep='first')].shape[0]
print(f"Exact duplicate count: {exact_dups}")

# Near-duplicate count (hash of whitespace-normalized text)
hash_to_ids = resumes_normalized.groupby(resumes_normalized).apply(lambda g: g.index.tolist()).to_dict()
near_dups = sum(1 for ids in hash_to_ids.values() if len(ids) > 1)
print(f"Near-duplicate groups (2+ same normalized): {near_dups}")

# --- Presence checks ---
print("\n=== PRESENCE CHECKS ===")

# Emails
email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
df['has_email'] = df['Resume_str'].str.contains(email_pattern, case=False, regex=True, na=False)
print(f"Resumes with email: {df['has_email'].sum()}")

# Phones
phone_pattern = r'(\+\d{1,3}\s?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}'
df['has_phone'] = df['Resume_str'].str.contains(phone_pattern, regex=True, na=False)
print(f"Resumes with phone: {df['has_phone'].sum()}")

# URLs
url_pattern = r'https?://\S+|www\.\S+'
df['has_url'] = df['Resume_str'].str.contains(url_pattern, regex=True, na=False)
print(f"Resumes with URL: {df['has_url'].sum()}")

# Bullet chars
bullet_chars = ['\u2022', '\u2014', '\u2013', '*', '-']
for bc in bullet_chars:
    count = df['Resume_str'].str.contains(re.escape(bc), regex=True, na=False).sum()
    if count > 0:
        print(f'Bullet char {repr(bc)}: {count} resumes')

# Residual HTML tags in Resume_str
html_pattern = r'<[^>]+>'
df['has_html'] = df['Resume_str'].str.contains(html_pattern, regex=True, na=False)
print(f"Resumes with residual HTML in Resume_str: {df['has_html'].sum()}")

# --- Keyword scans ---
print("\n=== KEYWORD SCANS ===")

# Degree terms
degree_terms = ['bachelor', 'master', 'phd', 'b.tech', 'mba']
for term in degree_terms:
    count = df['Resume_str'].str.contains(term, case=False, regex=True, na=False).sum()
    print(f'Resume contains "{term}": {count}')

# Year patterns
year_pattern1 = r'\d\+?\s*years'
year_pattern2 = r'20\d\d[-–]\s*(20\d\d|present)'
for p in [year_pattern1, year_pattern2]:
    count = df['Resume_str'].str.contains(p, regex=True, na=False).sum()
    print(f'Pattern "{p}" matches: {count}')

# Save DECISIONS.md at the end
print("\n=== DECISIONS (to be moved to DECISIONS.md) ===")
print(f"[P1] Dataset has {df.shape[0]} resumes across {len(cats)} categories")
print(f"[P1] Columns: {list(df.columns)}")
print(f"[P1] No null values in any column")
print(f"[P1] Category distribution highly skewed: top categories have ~120 resumes, bottom have ~22")
print(f"[P1] Exact duplicate count: {exact_dups}")
print(f"[P1] Near-duplicate groups: {near_dups}")
print(f"[P1] Resumes with email: {df['has_email'].sum()}")
print(f"[P1] Resumes with phone: {df['has_phone'].sum()}")
print(f"[P1] Resumes with URL: {df['has_url'].sum()}")
print(f"[P1] Degree term presence scans completed")
print(f"[P1] Year pattern scans completed")