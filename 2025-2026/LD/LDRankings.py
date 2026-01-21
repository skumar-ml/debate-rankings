import glob
import pandas as pd
import math
import re

"""
Notes:
Must include file with entries in the tournament folder, then two folders
with all of the prelims and elims in order
"""


def entry_dict(tournament):
    """make a dictionary with all of the entries at a  with school and names"""
    outputDict = {}
    file_location = glob.glob(tournament + "/*.csv")[0]
    teams = pd.read_csv(file_location, delimiter=",", header=0, usecols=[2, 3])
    teams = teams.to_numpy()
    for team in teams:
        if team[1] == "Archbishop Mitty AP":
            team[0] = "Andrew Park (Mitty)"
        if (team[1] == "Troy Independent AP") or (team[1] == "Troy AP"):
            team[0] = "Andrew Park (Troy)"
        school, name = team[1], team[0]
        outputDict[school] = [name, school]
    return outputDict


bidList = {}
K = 30


def add_prelims(tournament, teamsDict, elos_dict, bid):
    """adds the prelims of a tournament to the rankings"""
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
                """team1, team2 = team1[:-3] + " " + teamsDict[team1], team2[:-3] + " " + teamsDict[team2]"""  # this line for school names (buggy)
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
            shift = K * (1 - winProb) * ((bid / 8) ** 0.5)
            elo_team1 += shift
            elo_team2 -= shift
            elos_dict[team1[0]] = [elo_team1, team1[1]]
            elos_dict[team2[0]] = [elo_team2, team2[1]]
        file.close()
    return elos_dict


elos_dict = {}


def add_elims(tournament, teamsDict, elos_dict, bid):
    """adds the elims of a tournament to the rankings"""
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
            line = [
                re.sub(r"\t+", " ", item) for item in line
            ]  # Sanitizes test (replaces tabs with spaces)
            line = [item.replace("\n", "") for item in line]  # Strips newlines
            try:
                team1, team2, judge, votes, result = tuple(line[0:5])
            except:
                continue
            result = result.lower()
            try:
                margin, result = tuple(result.split())  # Splits ballots and results
            except:
                continue
            if (
                "bye" in result
                or "BYE" in team1
                or "BYE" in team2
                or "BYE" in judge
                or "bye" in margin
                or "advances" in votes
                or "advances" in result
            ):
                continue

            if "neg" in result or "con" in result:
                team1, team2 = team2, team1  # team 1 is the winning team

            team1, team2 = teamsDict[team1], teamsDict[team2]  # this line for no school names

            """team1, team2 = team1[:-3] + " " + teamsDict[team1], team2[:-3] + " " + teamsDict[team2]"""  # this line for school names (buggy)

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
            shift = K * (1 - winProb) * ((bid / 8) ** 0.5)
            try:
                [bw, bl] = margin.split("-")
                shift *= 1 + (int(bw) - 1) / (int(bl) + 1)
            except:
                continue
            elo_team1 += shift + bid
            elo_team2 -= shift / 2
            elos_dict[team1[0]] = [elo_team1, team1[1]]
            elos_dict[team2[0]] = [elo_team2, team2[1]]
        file.close()
    return elos_dict


def add_tournament(tournament, bid):
    """adds a tournament to the rankings"""
    dictionary = entry_dict(tournament)
    add_prelims(tournament, dictionary, elos_dict, bid)
    add_elims(tournament, dictionary, elos_dict, bid)


ddTeams = []
with open("25-26-LDCT-Roster.csv", "r") as fp:
    for line in fp:
        ddTeams += [line.split(",")[0].strip()]

print(ddTeams)

nsdTeams = []
with open("NSD.csv", "r") as fp:
    for line in fp:
        nsdTeams += [line.split(",")[0].strip().title()]

# print(nsdTeams)


def write_to_csv(elosList):
    """write the rankings to the csv"""
    add = "Rank,School,Name,Elo,Bids,DD Student,NSD Student\n"
    top_500_add = "Rank,School,Name,Elo,Bids,DD Student,NSD Student\n"
    counter = 0
    for team, eloSchool in elosList:
        elo, school = eloSchool[0], eloSchool[1]
        counter += 1
        name = " ".join(team.split())

        if name in ["Ece Eskici"]:  # Remove people from rankings
            continue

        if name in bidList:
            bids = bidList[name]
        else:
            bids = 0

        dd = "Y" if (name in ddTeams) and ("Andrew Park" not in name) else "N"
        nsd = "Y" if name in nsdTeams and ("Andrew Park" not in name) else "N"

        record = (
            str(counter)
            + ","
            + school
            + ","
            + name
            + ","
            + str(round(elo * 1000) / 1000)
            + f",{dd}, "
            + nsd
            + ",\n"
        )

        add += record

        if counter < 501:
            top_500_add += record

    with open("LDRankings.csv", "w") as fp:
        fp.write(add[:-1])

    with open("LDRankings_top500.csv", "w") as fp:
        fp.write(top_500_add[:-1])


# Bid level: Finals (1), Semifinals (2), Quarterfinals (4), Octofinals (8)
add_tournament("Loyola", 4)
add_tournament("NSDSO_Online", 4)
add_tournament("Grapevine", 4)
add_tournament("Greenhill", 8)
add_tournament("JackHowe", 2)
add_tournament("Yale", 4)
add_tournament("MidAmerica", 8)
add_tournament("NanoNagle", 4)
add_tournament("StMarks", 8)
add_tournament("Bronx", 8)
add_tournament("Heritage Hall", 1)
add_tournament("Laird Lewis", 1)
add_tournament("BlueKey", 4)
add_tournament("AppleValley", 8)
add_tournament("Meadows", 4)
add_tournament("Badgerland", 1)
add_tournament("Damus", 2)
add_tournament("Glenbrooks", 8)
add_tournament("DowlingCatholic", 1)
add_tournament("Alta", 2)
add_tournament("LaCosta", 1)
add_tournament("LonghornClassic", 4)
add_tournament("TOCDigital1", 2)
add_tournament("Princeton", 2)
add_tournament("IsidoreNewman", 2)
add_tournament("Blake", 4)
add_tournament("CollegePrep", 4)
add_tournament("Newark", 4)
add_tournament("ChurchillClassic", 2)
add_tournament("ArizonaState", 1)
add_tournament("Sunvite", 1)

elos = sorted(elos_dict.items(), key=lambda item: item[1], reverse=True)
write_to_csv(elos)
