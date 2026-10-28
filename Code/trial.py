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

df = pd.concat([df2,df3,df4,df5,df6], join= "inner", ignore_index='True')
df = df.drop_duplicates()
df = df.sort_values(by = ['Date'])


working_df = df[["Date", "HomeTeam", "AwayTeam", "FTR"]]

working_df = working_df.to_dict('records')
#first function returns a result list with the count of how many games were won by each team head on 
# and draw like result = [5,6,2]
def mod_result_face(wokrking_df, home, away):
    HT = [] #Arsenal
    AT = [] #ManCity
    DT = []
     
    for row in working_df:
      if row['HomeTeam'] == home and row['AwayTeam'] == away:  #Arsenal Vs ManCity
         if row['FTR'] == 'H':
           HT.append('W')
         elif row['FTR'] == 'A':
            AT.append('W')
         elif row['FTR'] == 'D':
            DT.append('W')
    result = [len(HT), len(AT), len(DT)]
    return result
#The same function but when the first home team becomes away on this function 
# still returns a list like result = [5,7,2]
def mod_result_back(wokrking_df, home, away):
    HT = [] #ManCity
    AT = [] #Arsenal
    DT = []
     
    for row in working_df:
      if row['HomeTeam'] == away and row['AwayTeam'] == home: #ManCity vs Arsenal
         if row['FTR'] == 'H':
           HT.append('W')
         elif row['FTR'] == 'A':
            AT.append('W')
         elif row['FTR'] == 'D':
            DT.append('W')
    result = [len(HT), len(AT), len(DT)]
    return result


def predict_game(mod_result_face, mod_result_back, home, away):
   points_face = mod_result_face(working_df, home, away) # like [A5,M6,2]
   points_back = mod_result_back(working_df, home, away) # like [M5,A7,2]
  

   sum0 = points_face[0] + points_back[1] #5+7
   sum1 = points_face[1] + points_back[0] #6+5
   sum2 = points_face[2] + points_back[2] #2+2

   points = [sum0, sum1, sum2]
   outcome = ''

   if points[2] >= points[2] and points[1] >= points[0]:
      outcome = 'H'
   elif points[2] >= points[2] and points[1] <= points[0]:
      outcome = 'A'
   else:
      outcome = 'D'
   return outcome

eval_df = df1[["Date", "HomeTeam", "AwayTeam", "FTR"]]
eval_df = eval_df.to_dict('records')
check = []
for row in eval_df:
   eval_home = row["HomeTeam"]
   eval_away = row["AwayTeam"]
   check.append(predict_game(mod_result_face, mod_result_back, eval_home, eval_away))
eval_df = pd.DataFrame(eval_df)
eval_df["pred"] = check
eval_df["correct_sc"] = (eval_df["FTR"] == eval_df["pred"] )|( eval_df["FTR"] == 'D').astype(int)
print(eval_df)


n     = len(eval_df)
ones  = int(eval_df["correct_sc"].sum())

score = ones      # range: -n (all wrong) ... +n (all right)
grade = score / n             # range: -1.0 ... +1.0  (0.0 = random)

print(f"Correct (1s):    {ones}")
print(f"Raw score:       {score} / {n}")
print(f"Grade:           {grade:.2%}  (raw {grade:.3f} of len)")

