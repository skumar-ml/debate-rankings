import glob
import pandas as pd
import numpy as np
import math

'''
Notes:
Must include file with entries in the tournament folder, then two folders
with all of the prelims and elims in order
'''

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

bidList = {}
K = 30


def add_prelims(tournament, teamsDict, elos_dict, bid):
    '''adds the prelims of a tournament to the rankings'''
    files = glob.glob(tournament + "/Prelims/*.csv")
    if len(files) == 0:
        raise Exception("Error in reading prelims from {}.".format(tournament))
    for file in files:
        file = open(file, "r", encoding="Latin-1")
        for line in file.readlines()[1:]:
            line = line.split(",")
            team1, team2, judge, result = tuple(line[0:4])
            result = result.lower()
            if "bye" in result or "BYE" in team1 or "BYE" in team2 or "BYE" in judge:
                continue
            if "neg" in result or "con" in result:
                team1, team2 = team2, team1  # team 1 is the winning team
            try:
                team1, team2 = teamsDict[team1], teamsDict[team2]  # this line for no school names
                '''team1, team2 = team1[:-3] + " " + teamsDict[team1], team2[:-3] + " " + teamsDict[team2]'''  # this line for school names (buggy)
            except:
                continue
            try:
                elo_team1 = elos_dict[team1[0]][0]
            except:
                elo_team1 = 1500
            try:
                elo_team2 = elos_dict[team2[0]][0]
            except:
                elo_team2 = 1500
            elo_diff = elo_team1 - elo_team2
            winProb = 1.0 / (math.pow(10.0, (-elo_diff / 400.0)) + 1.0)
            shift = K * (1 - winProb) * ((bid / 8) ** .5)
            elo_team1 += shift
            elo_team2 -= shift
            elos_dict[team1[0]] = [elo_team1,team1[1]]
            elos_dict[team2[0]] = [elo_team2,team2[1]]
        file.close()
    return elos_dict


elos_dict = {}


def add_elims(tournament, teamsDict, elos_dict, bid):
    '''adds the elims of a tournament to the rankings'''
    files = glob.glob(tournament + "/Elims/*.csv")
    if len(files) == 0:
        raise Exception("Error in reading elims from {}".format(tournament))
    for file in files:
        file = open(file, "r", encoding="Latin-1")
        lines = file.readlines()[1:]
        for line in lines:
            isBid = False
            if len(lines) == bid:
                isBid = True
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

            if "neg" in result or "con" in result:
                team1, team2 = team2, team1  # team 1 is the winning team

            team1, team2 = teamsDict[team1], teamsDict[team2] #this line for no school names

            '''team1, team2 = team1[:-3] + " " + teamsDict[team1], team2[:-3] + " " + teamsDict[team2]''' #this line for school names (buggy)

            try:
                elo_team1 = elos_dict[team1[0]][0]
            except:
                elo_team1 = 1500
            try:
                elo_team2 = elos_dict[team2[0]][0]
            except:
                elo_team2 = 1500
            if isBid:
                try:
                    bidList[team1[0]] += 1
                except:
                    bidList[team1[0]] = 1
                try:
                    bidList[team2[0]] += 1
                except:
                    bidList[team2[0]] = 1
            elo_diff = elo_team1 - elo_team2
            winProb = 1.0 / (math.pow(10.0, (-elo_diff / 400.0)) + 1.0)
            shift = K * (1 - winProb) * ((bid / 8) ** .5)
            try:
                [bw, bl] = margin.split("-")
                shift *= (1 + (int(bw) - 1) / (int(bl) + 1))
            except:
                continue
            elo_team1 += shift + bid
            elo_team2 -= shift / 2
            elos_dict[team1[0]] = [elo_team1,team1[1]]
            elos_dict[team2[0]] = [elo_team2,team2[1]]
        file.close()
    return elos_dict


def add_tournament(tournament, bid):
    '''adds a tournament to the rankings'''
    dictionary = entry_dict(tournament)
    add_prelims(tournament, dictionary, elos_dict, bid)
    add_elims(tournament, dictionary, elos_dict, bid)


ddTeams = []
with open("23-24-LDCT_Roster.csv", "r") as fp:
    for line in fp:
        ddTeams += [line.split(",")[0].strip()]

print("Test")
print(ddTeams)

nsdTeams = []
with open("NSD.csv", "r") as fp:
    for line in fp:
        nsdTeams += [line.split(",")[0].strip()]


def write_to_csv(elosList):
    '''write the rankings to the csv'''
    add = "Rank,School,Name,Elo,Bids,DD Student,NSD Student\n"
    counter = 0
    print("Test")
    for team, eloSchool in elosList:
        elo, school = eloSchool[0], eloSchool[1]
        counter += 1
        name = " ".join(team.split())
        print(team)
        print("hi")
        if name in bidList:
            bids = bidList[name]
        else:
            bids = 0
        if (name in ddTeams):
            add += str(counter) + "," + school + "," + name + "," + str(round(elo * 1000) / 1000) + ",{},Y".format(bids)
        else:
            add += str(counter) + "," + school + "," + name + "," + str(round(elo*1000)/1000) + ",{},N".format(bids)
            print("No")
        if name in nsdTeams:
            add += ",Y\n"
        else:
            add += ",N\n"

    with open("LDRankings.csv", "w") as fp:
        fp.write(add[:-1])


add_tournament("SeasonOpener", 4)

# add_tournament("Loyola", 4)
# add_tournament("Grapevine", 4)
# add_tournament("UK1", 4)
# add_tournament("UK2", 4)
# add_tournament("Yale", 4)
# add_tournament("Greenhill", 8)
# add_tournament("Valley", 8)
# add_tournament("JackHowe", 2)
# add_tournament("HolyCross", 2)
# add_tournament("Duke", 1)
# add_tournament("NYC", 8)
# add_tournament("NanoNagle", 4)
# add_tournament("HeritageHall", 1)
# add_tournament("BlueKey", 4)
# add_tournament("Meadows", 4)
# add_tournament("UHouston", 2)
# add_tournament("HeartOfTexas", 8)
# # add_tournament("Arthur", 1)
# add_tournament("Damus", 2)
# add_tournament("AppleValley", 8)
# # add_tournament("Badgerland", 1)
# add_tournament("Glenbrooks", 8)
# add_tournament("Alta", 2)
# add_tournament("Princeton", 2)
# add_tournament("Longhorn", 4)
# # add_tournament("IsidoreNewman", 2)
# # add_tournament("Dowling", 1)
# # add_tournament("Ridge", 1) ## NO entries
# add_tournament("Strake", 2)
# add_tournament("Blake", 4)
# add_tournament("ASU", 1)
# add_tournament("PugetSound", 2)
# # add_tournament("Churchill", 2) ## Incomplete results (missing semis/finals)
# add_tournament("Sunvite", 1)
# add_tournament("Lex", 4)
# # add_tournament("Durham", 2)
# # add_tournament("Houston", 2)
# add_tournament("Peninsula", 4)
# add_tournament("Columbia", 1)
# add_tournament("Emory", 8)
# add_tournament("GoldenDesert", 2)
# add_tournament("Pennsbury", 1)
# add_tournament("Stanford", 4)
# add_tournament("Harvard", 8)
# add_tournament("Berkeley", 8)
# add_tournament("HarvardWestlake", 8)
# add_tournament("TOCDigital1", 2)
# add_tournament("TOCDigital2", 4)
# add_tournament("TOCDigital3", 4)

# add_tournament("TOC", 16)


elos = sorted(elos_dict.items(), key=lambda item: item[1], reverse=True)
write_to_csv(elos)