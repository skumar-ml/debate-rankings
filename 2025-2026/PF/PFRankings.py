import glob
import pandas as pd
import numpy as np
import math
import re

'''
Notes:
Must include file with entries in the tournament folder, then two folders
with all of the prelims and elims in order
'''

def entry_dict(tournament):
    '''make a dictionary with all of the entries at a  with school and names'''
    outputDict = {}
    file_location = \
    glob.glob(tournament + "/*.csv")[0]
    teams = pd.read_csv(file_location, delimiter=",", header=0, usecols=[2, 3])
    teams = teams.to_numpy()
    for team in teams:
        school, names = team[1], team[0]
        names = names.replace("&nbsp;", "")
        print("Names:", names)
        if names.split()[0] < names.split()[2]:
            outputDict[school] = [names, school]
        else:
            names_mod = names.split()
            names_mod[0], names_mod[2] = names_mod[2], names_mod[0]
            names_mod = ' '.join(names_mod)
            outputDict[school] = [names_mod, school]
    return outputDict


K = 30


def add_prelims(tournament, teamsDict, elos_dict, bid):
    '''adds the prelims of a tournament to the rankings'''
    files = glob.glob(tournament + "/Prelims/*.csv")
    if len(files) == 0:
        raise Exception(f"Error in reading prelims from {tournament}.")
    for file in files:
        file = open(file, "r")
        for line in file.readlines()[1:]:
            line = line.split(",")
            team1, team2, judge, result = tuple(line[0:4])
            result = result.strip().lower()
            if "bye" in result or "BYE" in team1 or "BYE" in team2 or "BYE" in judge:
                continue
            if result == "neg" or result == "con":
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
            shift = K * (1 - winProb) * bid / 8 #(bid/8)^1/2
            elo_team1 += shift
            elo_team2 -= shift
            elos_dict[team1[0]] = [elo_team1,team1[1]]
            elos_dict[team2[0]] = [elo_team2,team2[1]]
        file.close()
    return elos_dict


elos_dict = {}
bidList = {}


def add_elims(tournament, teamsDict, elos_dict, bid):
    '''adds the elims of a tournament to the rankings'''
    files = glob.glob(tournament + "/Elims/*.csv")
    if len(files) == 0:
        raise Exception(f"Error in reading elims from {tournament}.")
    for file in files:
        file = open(file, "r")
        lines = file.readlines()[1:]
        for line in lines:
            isBid = False
            if len(lines) == bid:
                isBid = True
            line = line.split(",")
            line = [re.sub(r'\t+', ' ', item) for item in line] # Sanitizes test (replaces tabs with spaces)
            line = [item.replace("\n", "") for item in line] # Strips newlines
            print(line)
            try:
                team1, team2, judge, votes, result = tuple(line[0:5])
            except:
                continue
            result = result.strip().lower()
            if isBid:
                if team1 in bidList:
                    bidList[team1] += 1
                else:
                    bidList[team1] = 1
                if team2 in bidList:
                    bidList[team2] += 1
                else:
                    bidList[team2] = 1
            try:
                margin, result = tuple(result.strip()[1:-1].split())
            except:
                continue
            if "bye" in result or "BYE" in team1 or "BYE" in team2 or "BYE" in judge or "bye" in margin:
                continue
            if "neg" in result or "con" in result:
                team1, team2 = team2, team1  # team 1 is the winning team
            try: team1, team2 = teamsDict[team1], teamsDict[team2]
            except: continue
            # print(line)
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
            shift = K * (1 - winProb) * bid / 8
            try:
                [bw, bl] = margin.split("-")
                shift *= (1 + (int(bw)-1)/(int(bl)+1))
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
    print(tournament)
    dictionary = entry_dict(tournament)
    add_prelims(tournament, dictionary, elos_dict, bid)
    add_elims(tournament, dictionary, elos_dict, bid)

ddTeams = []
with open("25-26-PFCT-Roster.csv", "r") as fp:
    for line in fp:
        # ddTeams += [line.split(",")[0].strip().split()[-1]]
        ddTeams += [line.split(",")[0].strip()]

nsdTeams = []
# with open("NSD.csv", "r") as fp:
#     for line in fp:
#         nsdTeams += [line.split(",")[0].strip().split()[-1]]

nsdLastNames = [string.split()[-1].strip() if string.split() else "" for string in nsdTeams]
# nsdTeams = ["East Ridge MV", "FW CB", "Avenues: The World CB"]


def write_to_csv(elosList):
    '''write the rankings to the csv'''
    add = "Rank,School,Name,Elo,DD Student,NSD Student\n"
    counter = 0
    for team, eloSchool in elosList:
        elo, school = eloSchool[0],eloSchool[1]
        counter += 1
        names = " ".join(team.split())
        members = names.split('&')
        # print(members[0].strip())
        if (members[0].strip() in nsdLastNames and members[1].strip() in nsdLastNames) or (school in nsdTeams):
            nsd = "Y"
        else:
            nsd = "N"

        if school in bidList:
            bids = bidList[school]
        else:
            bids = 0

        if school == "FW CB":
            school = "Avenues: The World CB"

        if school in ddTeams or ("DebateDrills" in school):
            add += str(counter) + "," + school + "," + names + "," + str(round(elo * 1000) / 1000) + f",Y, " + nsd + ",\n"
        else:
            add += str(counter) + "," + school + "," + names + "," + str(round(elo*1000)/1000) + f",N, " + nsd + ",\n"
    with open("PFRankings.csv","w") as fp:
        fp.write(add[:-1])

# Bid level: Finals (1), Semifinals (2), Quarterfinals (4), Octofinals (8)
add_tournament("NSDSO_Inperson", 4)
add_tournament("NSDSO_Online", 4)
add_tournament("Grapevine", 4)
add_tournament("JackHowe", 4)
add_tournament("Yale", 8)
add_tournament("MidAmerica", 2)
add_tournament("StephenStewart", 4)
add_tournament("MaristIvy", 1)
add_tournament("NSDATaiwan", 0)
add_tournament("GeorgetownFall", 1)
add_tournament("NanoNagle1", 4)
add_tournament("NovaTitan", 2)
add_tournament("Bronx", 8)
add_tournament("CSUFullerton", 1)
add_tournament("Tim Averill", 2)
# add_tournament("Jon Schamber", 1)
add_tournament("Laird Lewis", 2)
add_tournament("BlueKey", 8)
add_tournament("AppleValley", 8)
add_tournament("QuarryLane", 1)
add_tournament("Michigan", 1)
add_tournament("Hockaday", 1)
add_tournament("Badgerland", 2)
add_tournament("Lincoln-Southwest", 1)
add_tournament("Katy_Taylor", 1)
add_tournament("Carrollton", 2)
add_tournament("Harvard_ISDI_1", 1)
add_tournament("JohnLewis", 4)
add_tournament("Glenbrooks", 8)
add_tournament("Villeger", 2)
add_tournament("LaCosta", 4)
add_tournament("TOCDigital1", 2)
add_tournament("DowlingCatholic", 4)
#add_tournament("BigGump", 2) //No Results Available
add_tournament("Alta", 4)
add_tournament("LonghornClassic", 4)
add_tournament("Princeton", 8)

elos = sorted(elos_dict.items(), key=lambda item: item[1], reverse=True)
write_to_csv(elos)
print(ddTeams)