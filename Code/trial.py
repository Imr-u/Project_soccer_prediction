import pandas as pd
source1 = "alpha_source/2026-2027.csv" 
source2 = "alpha_source/2025-2026.csv" 

df1 = pd.read_csv(source1)
df2 = pd.read_csv(source2)

df = pd.concat([df1,df2], join= "inner", ignore_index='True')
df = df.drop_duplicates()
df = df.sort_values(by = ['Date'])


df = df[["Date", "HomeTeam", "AwayTeam", "FTR"]]

def count_head_to_head(df, team1, team2):
    # Create conditions for both home/away scenarios
    match1 = (df['HomeTeam'] == team1) & (df['AwayTeam'] == team2)
    match2 = (df['HomeTeam'] == team2) & (df['AwayTeam'] == team1)

    # Combine conditions using OR (|)
    all_matches = df[match1 | match2]

    # Get total count
    total_matches = len(all_matches)

    # Optional but helpful: breakdown of where the matches happened
    team1_home = len(df[match1])
    team2_home = len(df[match2])

    print(f"Total matches between {team1} and {team2}: {total_matches}")
    print(f" - {team1} was Home: {team1_home} times")
    print(f" - {team2} was Home: {team2_home} times")

    return total_matches
count_head_to_head(df, 'Arsenal', 'Man City')