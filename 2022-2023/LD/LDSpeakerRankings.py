import glob
import pandas as pd
import numpy as np
import sys



def entry_dict(tournament):
    '''make a dictionary with all of the entries at a  with school and names'''
    outputDict = {}
    file_location = glob.glob(tournament + "/*.csv")[0]
    teams = pd.read_csv(file_location, delimiter=",", header=0, usecols=[2, 3])
    teams = teams.to_numpy()
    for team in teams:
        school, name = team[1], team[0]
        outputDict[school] = [name, school]
    return outputDict

scoresDict = {}

def add_error_tournament(tournament):
    file = f"Errors/{tournament}.csv"
    file = open(file, "r", encoding="Latin-1")
    for line in file:
        name = " ".join(line.split(",")[0:2])
        scores = line.split('"')[1].split(",")
        for score in scores:
            score = float(score)
            try:
                scoresDict[name].append(score)
            except:
                scoresDict[name] = [score]



def add_prelims(tournament, teamsDict, bid):
    '''adds the prelims of a tournament to the rankings'''
    files = glob.glob(tournament + "/Prelims/*.csv")
    if len(files) == 0:
        raise Exception(f"Error in reading prelims from {tournament}.")
    tournamentWorks = False
    for file in files:
        file = open(file, "r", encoding="Latin-1")
        for line in file.readlines()[1:]:
            line = line.split(",")
            try:
                team1, team2, judge, result, affSpeaks, negSpeaks = tuple(line[0:6])
            except:
                continue
            if "bye" in result or "BYE" in team1 or "BYE" in team2 or "BYE" in judge:
                continue
            try:
                team1, team2 = teamsDict[team1], teamsDict[team2]
            except:
                continue
            try:
                affSpeaks = float(affSpeaks.strip())
                negSpeaks = float(negSpeaks.strip())
            except:
                try:
                    location1 = affSpeaks.index(".")
                    location2 = negSpeaks.index(".")
                    affSpeaks = float(affSpeaks[location1-2:location1+2])
                    negSpeaks = float(negSpeaks[location2-2:location2+2])
                except:
                    continue
            try:
                scores1 = scoresDict[team1[0]]
            except:
                scores1 = []
            try:
                scores2 = scoresDict[team2[0]]
            except:
                scores2 = []
            count = bid
            if bid == 4:
                count = 3
            if bid == 8:
                count = 4
            for i in range(count):
                scores1.append(affSpeaks)
                scores2.append(negSpeaks)
            scoresDict[team1[0]] = scores1
            scoresDict[team2[0]] = scores2
            tournamentWorks = True
        file.close()
    if not tournamentWorks:
        print(tournament)
        add_error_tournament(tournament)
    return scoresDict

def add_tournament(tournament, bid):
    '''adds a tournament to the rankings'''
    dictionary = entry_dict(tournament)
    add_prelims(tournament, dictionary, bid)

def write_to_csv(scoresDict):
    '''write the rankings to the csv'''
    arr = []
    for student, scores in scoresDict.items():
        score = sum(scores) / (len(scores) + 6) + 2
        mean = np.mean(scores)
        arr.append([student, score, mean])
    arr = sorted(arr, key=lambda item: item[1], reverse=True)
    add = "Rank,School,Name,Elo,Bids,DD Student,NSD Student\n"
    add = "Rank,Name,Adjusted Mean,Mean\n"
    count = 0
    for [student, score, mean] in arr:
        count += 1
        add += f"{count},{student},{np.round(score*1000)/1000},{np.round(mean*1000)/1000}\n"

    with open("LDSpeakerRankings.csv", "w") as fp:
        fp.write(add[:-1])

add_tournament("Loyola", 4)
add_tournament("Grapevine", 4)
add_tournament("UK1", 4)
add_tournament("UK2", 4)
add_tournament("Yale", 4)
add_tournament("Greenhill", 8)
add_tournament("Valley", 8)
add_tournament("JackHowe", 2)
add_tournament("HolyCross", 2)
add_tournament("Duke", 1)
add_tournament("NYC", 8)
#add_tournament("NanoNagle", 4)
add_tournament("HeritageHall", 1)
add_tournament("BlueKey", 4)
add_tournament("Meadows", 4)
add_tournament("UHouston", 2)
# add_tournament("HeartOfTexas", 8)
# add_tournament("Arthur", 1)
# add_tournament("Damus", 2)
add_tournament("AppleValley", 8)
# add_tournament("Badgerland", 1)
add_tournament("Glenbrooks", 8)
# add_tournament("Alta", 2)
add_tournament("Princeton", 2)
add_tournament("Longhorn", 4)
# add_tournament("IsidoreNewman", 2)
# add_tournament("Dowling", 1)
# add_tournament("Ridge", 1)
# add_tournament("Strake", 2)
# add_tournament("Blake", 4)
# add_tournament("ASU", 1)
# add_tournament("PugetSound", 2)
# add_tournament("Churchill", 2)
# add_tournament("Sunvite", 1)
# add_tournament("Lex", 4)
# add_tournament("Durham", 2)
# add_tournament("Houston", 2)
# add_tournament("Peninsula", 4)
# add_tournament("Columbia", 1)
# add_tournament("Emory", 8)
# add_tournament("GoldenDesert", 2)
# add_tournament("Penn", 1)
# add_tournament("Harvard", 8)
# add_tournament("Berkeley", 8)
# add_tournament("Milo", 1)


write_to_csv(scoresDict)
