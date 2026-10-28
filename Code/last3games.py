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
df = df.sort_values('Date').reset_index(drop = True)

# Function 1 filter the table by the input team

def last_home_games(team):
 subset_home = df[(df['HomeTeam']== team)].sort_values('Date', ascending = False).reset_index(drop = True)
 #subset_home = subset_home[['Date', 'HomeTeam', 'AwayTeam', 'FTR']]
 
 home_result = subset_home[['FTR']].to_dict('Records')
 record_home = []
 for row in home_result:
  record_home.append(row['FTR'])

 record_home = record_home[0:3]

 num_home= []
 for n in record_home:
  if n == 'H':
   num_home.append(1)
  elif n == 'A':
   num_home.append(-1)
  elif n == 'D':
   num_home.append(0)
 print(num_home)
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
 print(num_away)
 return num_away


def eval_winner(home, away):
 sum_of_home = 0
 sum_of_away = 0
 for n in last_home_games(home):
  sum_of_home = sum_of_home + n
 for n in last_away_games(away):
  sum_of_away = sum_of_away + n

 sum = sum_of_home - sum_of_away
 return sum
 

prediction = eval_winner('Arsenal','Fulham')
print(prediction)

 