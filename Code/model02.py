# Im going to try and make a logic that compares that last 3 games of the teams facing and determine the wining probablity


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

df = pd.concat([df2,df3,df4,df5,df6], join= "inner")
df = df.drop_duplicates()
df['Date'] = pd.to_datetime(df['Date'], format= "%d/%m/%Y")
df = df[df["Date"] < '4/11/2026' ]
df = df.sort_values('Date').reset_index(drop = True)

# Function 1 filter the table by the input team

def last_home_games(team):

 subset_home = df[(df['HomeTeam']== team)].sort_values('Date', ascending = False).reset_index(drop = True)
 #subset_home = subset_home[['Date', 'HomeTeam', 'AwayTeam', 'FTR']]
 
 home_result = subset_home[['FTR']].to_dict('Records')
 record_home = [] # ['H', 'A', 'A', 'D'....]
 for row in home_result:
  record_home.append(row['FTR'])

 record_home = record_home[0:3]  # only the last three home game results

 num_home= []
 for n in record_home:
  if n == 'H':
   num_home.append(1)
  elif n == 'A':
   num_home.append(-1)
  elif n == 'D':
   num_home.append(0)
 # given "Arsenal" it will print arsenal's last 3 home games as a list
 return num_home

  

def last_away_games(team):
 
 subset_away = df[(df['AwayTeam']== team)].sort_values('Date', ascending = False).reset_index(drop = True)
 # subset_away = subset_away[['Date', 'HomeTeam', 'AwayTeam', 'FTR']]

 away_result = subset_away[['FTR']].to_dict('Records')

 record_away = []
 for row in away_result:
  record_away.append(row['FTR'])

 record_away = record_away[0:3]

 num_away= []
 for n in record_away:
  if n == 'H':
   num_away.append(1)
  elif n == 'A':
   num_away.append(-1)
  elif n == 'D':
   num_away.append(0)
   # Given "Arsenal" it will return last 3 games of arsenal
 return num_away


def eval_winner(home, away):
 sum_of_home = 0
 sum_of_away = 0
 for n in last_home_games(home): # let home is arsenal, last_home_games is a list with 3 entries [1, 1 ,0] w, w, D
  sum_of_home = sum_of_home + n  # where arsenal played on home

 for n in last_away_games(away): # and this is the away teams result were they played there much on away, just the last 3 away games
  sum_of_away = sum_of_away + n

 sum = sum_of_home - sum_of_away # last three arsenal's  home games sum - last three rival teams away games sum

 if sum < 0:
  return 'A'
 elif sum > 0:
  return 'H'
 elif sum == 0:
  return 'D'


eval_df = df1[["Date","HomeTeam", "AwayTeam", "FTR"]]
eval_df = eval_df.to_dict('Records')
check = []
for row in eval_df: # row {Date: xxx, HomeTeam: "Arsenal", ....}
 eval_home = row["HomeTeam"]
 eval_away = row["AwayTeam"]

 check.append(eval_winner(eval_home, eval_away))

eval_df = pd.DataFrame(eval_df)
eval_df["pred"] = check
eval_df["correct_sc"] = (eval_df["FTR"] == eval_df["pred"]).astype(int)

eval_df["no_history"] = (eval_df["pred"] == "nan").astype(int) #it assigns 1 for nan predicitons and 0 otherwise 

n     = len(eval_df)
ones  = int(eval_df["correct_sc"].sum())


score = ones      
grade = score / n            

# print(eval_df ,'/n',check )
print(f"Correct (1s):    {ones}")
print(f"Raw score:       {score} / {n}")
print(f"Grade:           {grade:.2%}  (raw {grade:.3f} of len)")
