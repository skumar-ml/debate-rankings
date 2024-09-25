import glob
import pandas as pd
import numpy as np
import math

elos = {}

with open("Rankings.csv","r") as file:
    for line in file:
        line = line.split(",")
        elos[line[1]] = line[3]


def brier_prelims(tournament, elos):
    '''Finds the Brier Score and Brier Skill Score of the prelims'''
    brierScoreP = 0
    countP = 0
    files = glob.glob(tournament + "/Prelims/*.csv")
    if len(files) == 0:
        raise Exception(f"Error in reading prelims from {tournament}.")
    for file in files:
        file = open(file, "r", encoding="Latin-1")
        for line in file.readlines()[1:]:
            line = line.split(",")
            team1, team2, judge, result = tuple(line[0:4])
            result = result.lower()
            if "bye" in result or "BYE" in team1 or "BYE" in team2 or "BYE" in judge:
                continue
            if result == "neg" or result == "con":
                team1, team2 = team2, team1  # team 1 is the winning team
            try:
                elo1, elo2 = elos[team1], elos[team2]
            except:
                continue

            elo_diff = float(elo1) - float(elo2)
            winProb = 1.0 / (math.pow(10.0, (-elo_diff / 400.0)) + 1.0)
            brierScoreP += (winProb-1)**2
            countP += 1
        file.close()
    bs = brierScoreP / countP
    bss = 1 - bs/.25
    return f"The Brier Score for the {tournament} prelims is {bs}, and the Brier Skill Score is {bss}."





def brier_elims(tournament, elos):
    '''Finds the Brier Score and Brier Skill Score of the elims'''
    brierScoreE = 0
    countE = 0
    files = glob.glob(tournament + "/Elims/*.csv")
    if len(files) == 0:
        raise Exception(f"Error in reading elims from {tournament}.")
    for file in files:
        file = open(file, "r", encoding="Latin-1")
        for line in file.readlines()[1:]:
            line = line.split(",")
            try:
                team1, team2, judge, votes, result = tuple(line[0:5])
            except:
                continue
            result = result.lower()
            try:
                margin, result = tuple(result[1:-2].split())
            except:
                continue
            if "bye" in result or "BYE" in team1 or "BYE" in team2 or "BYE" in judge or "bye" in margin:
                continue
            if result == "neg" or result == "con":
                team1, team2 = team2, team1  # team 1 is the winning team

            try:
                elo1, elo2 = elos[team1], elos[team2]
            except:
                continue

            elo_diff = float(elo1) - float(elo2)
            winProb = 1.0 / (math.pow(10.0, (-elo_diff / 400.0)) + 1.0)
            brierScoreE += (winProb - 1) ** 2
            countE += 1
        file.close()
    bs = brierScoreE / countE
    bss = 1 - bs / .25
    return f"The Brier Score for the {tournament} elims is {bs}, and the Brier Skill Score is {bss}."


print(brier_prelims("Sunvite", elos))
print(brier_elims("Sunvite", elos))
print(brier_prelims("ASU", elos))
print(brier_elims("ASU", elos))






