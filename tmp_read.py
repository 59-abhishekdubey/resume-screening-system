import csv
with open(r'C:\Users\Lenovo\OneDrive\Desktop\FUTURE_int\resume-screening-system\data\cleaned_resumes.csv') as f:
    reader = csv.reader(f)
    for i, row in enumerate(reader):
        if i < 5:
            print(row)
        else:
            break