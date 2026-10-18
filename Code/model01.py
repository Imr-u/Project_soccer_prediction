import pandas as pd
source1 = "alpha_source/2026-2027.csv" 
source2 = "alpha_source/2025-2026.csv"
source3 = "alpha_source/2024-2025.csv"
source4 = "alpha_source/2023-2024.csv"
source5 = "alpha_source/2022-2023.csv"
source6 = "alpha_source/2021-2022.csv"


df1 = pd.read_csv(source1)
df2 = pd.read_csv(source2)
df3 = pd.read_csv(source3)
df4 = pd.read_csv(source4)
df5 = pd.read_csv(source5)
df6 = pd.read_csv(source6)

df = pd.concat([df1,df2,df3,df4,df5,df6], join= "inner", ignore_index='True')
df = df.drop_duplicates()
df = df.sort_values(by = ['Date'])


working_df = df[["Date", "HomeTeam", "AwayTeam", "FTR"]]
unique_teams = df[["HomeTeam"]].nunique()

working_df = working_df.to_dict('records')
def mod_result(wokrking_df, home, away):
    HT = []
    AT = []
    DT = []
     
    for row in working_df:
      if row['HomeTeam'] == home and row['AwayTeam'] == away:
         print(row)
         if row['FTR'] == 'H':
           HT.append('W')
         elif row['FTR'] == 'A':
            AT.append('W')
         elif row['FTR'] == 'D':
            DT.append('W')
    result = [len(HT), len(AT), len(DT)]
    return result

def predict_