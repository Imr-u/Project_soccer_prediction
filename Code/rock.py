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


eval_df = df1[["Date", "HomeTeam", "AwayTeam", "FTR"]]
eval_df = eval_df.to_dict('records')
check = []
for n in eval_df:
  check.append('D')
eval_df = pd.DataFrame(eval_df)
eval_df["pred"] = check
eval_df["correct_sc"] = (eval_df["FTR"] == eval_df["pred"] ).astype(int)
print(eval_df)


n     = len(eval_df)
ones  = int(eval_df["correct_sc"].sum())

score = ones      # range: -n (all wrong) ... +n (all right)
grade = score / n             # range: -1.0 ... +1.0  (0.0 = random)

print(f"Correct (1s):    {ones}")
print(f"Raw score:       {score} / {n}")
print(f"Grade:           {grade:.2%}  (raw {grade:.3f} of len)")

