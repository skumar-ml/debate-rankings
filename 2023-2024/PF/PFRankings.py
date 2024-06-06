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
    file_location = \
    glob.glob(tournament + "/*.csv")[0]
    teams = pd.read_csv(file_location, delimiter=",", header=0, usecols=[2, 3])
    teams = teams.to_numpy()
    for team in teams:
        school, names = team[1], team[0]
        print(names)
        names = names.replace("&nbsp;", "")
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
            if result == "neg" or result == "con":
                team1, team2 = team2, team1  # team 1 is the winning team
            try: team1, team2 = teamsDict[team1], teamsDict[team2]
            except: continue
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
with open("23-24-PFCT-Roster.csv", "r") as fp:
    for line in fp:
        # ddTeams += [line.split(",")[0].strip().split()[-1]]
        ddTeams += [line.split(",")[0].strip()]

nsdTeams = []
with open("NSD.csv", "r") as fp:
    for line in fp:
        nsdTeams += [line.split(",")[0].strip().split()[-1]]

nsdLastNames = [string.split()[-1].strip() if string.split() else "" for string in nsdTeams]
nsdTeams = ["JR Masterman CA", "Lexington FJ", "Princeton MB", "Flintridge VZ", "Durham VC", "College Prep CW", "Plano West KL", "Alison Montessori SS"]


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
        if school in ddTeams or ("DebateDrills" in school):
            add += str(counter) + "," + school + "," + names + "," + str(round(elo * 1000) / 1000) + f",Y, " + nsd + ",\n"
        else:
            add += str(counter) + "," + school + "," + names + "," + str(round(elo*1000)/1000) + f",N, " + nsd + ",\n"
    with open("PFRankings.csv","w") as fp:
        fp.write(add[:-1])

add_tournament("SeasonOpener_InPerson", 4)
add_tournament("SeasonOpener_Online", 4)
add_tournament("Grapevine", 4)
add_tournament("JackHowe", 4)
add_tournament("Milpitas", 2)
add_tournament("Valley", 2)
# add_tournament("HolyCross", 1) # Cancelled
add_tournament("Yale", 8)
# add_tournament("StJames", 1) # Cannot find on tab
add_tournament("Georgetown", 1)
add_tournament("NovaTitan", 1)
add_tournament("NanoNagle", 4)
add_tournament("NYC",8)
add_tournament("BlueKey", 8)
# add_tournament("Bellaire", 1) # results not availabile on Tab
add_tournament("AppleValley", 8)
add_tournament("KatyTaylor", 1)
add_tournament("Hockaday", 1)
# # add_tournament("Scarsdale", 2) # results not available on Tab
add_tournament("Roosevelt", 1)
add_tournament("JohnLewis", 4)
add_tournament("Villiger", 2)
add_tournament("Glenbrooks", 8)
add_tournament("Alta", 4)
add_tournament("Princeton", 8)
add_tournament("Longhorn", 2) # TODO
add_tournament("TOCDigital1", 2)
add_tournament("Churchill", 1)
add_tournament("LaCosta", 4)
add_tournament("MillardWest", 1)
add_tournament("Dowling", 4)
add_tournament("IsidoreNewman", 2)
add_tournament("Blake", 8)
add_tournament("Arizona", 8)
add_tournament("PugetSound", 1)
# add_tournament("MyersPark", 1) # Not on Tab? 
add_tournament("Sunvite", 8)
add_tournament("Durham", 4)
add_tournament("MtVernon", 1)
add_tournament("JamesLogan", 4)
add_tournament("Lexington", 4)
add_tournament("Peninsula", 1)
add_tournament("BarkleyForum", 8)
add_tournament("Columbia", 4)
# add_tournament("Ridge", 2) # Not on Tab?
add_tournament("LewisClark", 1)
add_tournament("Pennsbury", 2)
# add_tournament("Puyallup", 1) # Not on Tab?
add_tournament("UNLV", 4)
add_tournament("UPenn", 8)
add_tournament("Stanford", 8)
add_tournament("Berkeley", 8)
add_tournament("MilliardNorth", 4) # Happening 2/23
add_tournament("Bingham", 4)
add_tournament("Harvard", 8)
add_tournament("Lakeland", 1)
add_tournament("TOCDigital2", 2)
add_tournament("TOCDigital3", 4)
add_tournament("TOC", 16)

elos = sorted(elos_dict.items(), key=lambda item: item[1], reverse=True)
write_to_csv(elos)
print(ddTeams)