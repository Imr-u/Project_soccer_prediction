import pandas as pd
source_fix = "data/fixtures.csv"
source1 = "alpha_source/2026-2027.csv" 
source2 = "alpha_source/2025-2026.csv"
source3 = "alpha_source/2024-2025.csv"
source4 = "alpha_source/2023-2024.csv"
source5 = "alpha_source/2022-2023.csv"
source6 = "alpha_source/2021-2022.csv"

df0 = pd.read_csv(source_fix)
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

working_df = working_df.to_dict('records')
def mod_result_face(home, away):
    HT = []
    AT = []
    DT = []
     
    for row in working_df:
      if row['HomeTeam'] == home and row['AwayTeam'] == away: #home is the home team and the other is awayteam
         if row['FTR'] == 'H': # HT=['H',...]
           HT.append('W')
         elif row['FTR'] == 'A': #AT=['A',...]
            AT.append('W')
         elif row['FTR'] == 'D':
            DT.append('W')
    result = [len(HT), len(AT), len(DT)] # result = [4, 5, 6]
    return result

def mod_result_back(home, away):
    HT = []
    AT = []
    DT = []
     
    for row in working_df:
      if row['HomeTeam'] == away and row['AwayTeam'] == home: # here home is away awayteam and the other is hometeam
         if row['FTR'] == 'H':
           HT.append('W')
         elif row['FTR'] == 'A':
            AT.append('W')
         elif row['FTR'] == 'D':
            DT.append('W')
    result = [len(HT), len(AT), len(DT)] # result = [6, 7, 8]
    return result


def predict_game(home, away):
   points_face = mod_result_face(home, away) 
   points_back = mod_result_back(home, away)

   sum0 = points_face[0] + points_back[1]
   sum1 = points_face[1] + points_back[0]
   sum2 = points_face[2] + points_back[2]

   sum = sum0 + sum1+ sum2

   points = [sum0, sum1, sum2, sum]
   print(points)

   return points  


eval_df = df0[['HomeTeam','AwayTeam']]
eval_df = eval_df.to_dict('records')

home_chance = []
away_chance = []
draw_chance = []


for row in eval_df:
   home = row['HomeTeam']
   away = row['AwayTeam']
   print_pred = predict_game(home, away)
   if print_pred[3]:
      home_chance.append(print_pred[0] / print_pred[3] * 100)
      away_chance.append(print_pred[1] / print_pred[3] * 100)
      draw_chance.append(print_pred[2] / print_pred[3] * 100)
   else:
      home_chance.append(float('nan'))
      away_chance.append(float('nan'))
      draw_chance.append(float('nan'))

df0['H%'] = home_chance
df0['A%'] = away_chance 
df0['D%'] = draw_chance

print(df0[['HomeTeam', 'AwayTeam', 'H%', 'A%', 'D%']])
