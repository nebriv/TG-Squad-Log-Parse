import logging
import sys
import io
import datetime
import unicodecsv as csv
import re

# OPTIONS
logfile = "C:\\Users\\ben\\Desktop\\SquadData\\logfile.txt"
active_player_lines = []
max_players = 80
output_date_format = "%m/%d/%y %H:%M"

# Logging shit.
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
# create a stdout handler
handler1 = logging.StreamHandler(sys.stderr)
handler1.setLevel(logging.DEBUG)
# create a logging format
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler1.setFormatter(formatter)
logger.addHandler(handler1)

# Support functions
def extract_date(line):
    date_string = line.split("[")[1].split("]")[0]
    date_string = datetime.datetime.strptime(date_string,"%Y.%m.%d-%H.%M.%S:%f")
    return (date_string)


logger.debug("Opening %s" % logfile)
f = io.open(logfile, mode="r", encoding="utf-8")
lines = f.read().splitlines()
logger.debug("Done reading file")

#[2018.08.31-01.20.58:817][208]LogSquad: SQGameRallyPoint BP_SquadRallyPoint_C_8 for team 1 at X=41738.789 Y=-11442.620 Z=-4991.473 destroyed by enemy SQPlayerState_84.
#[2018.08.31 - 01.21.03: 574][395]LogSquad: SQGameRallyPoint BP_SquadRallyPoint_C_26 for team 1 at X=24749.859 Y=-48580.563 Z=-6371.964 created.

# Get rally point
rally_line = "SQGameRallyPoint"
created = " created."
destroyed = " destroyed by enemy "

outdata = []
for line in lines:
    if rally_line in line:

        date_val = extract_date(line)
        status = None
        location = None

        if created in line:
            status = "Created"
        elif destroyed in line:
            status = "Destroyed"

        if status == "Created":
            location = line.split(" at ")[1].split(" created")[0]
        elif status == "Destroyed":
            location = line.split(" at ")[1].split(" destroyed ")[0]

        rally = {"Datetime": date_val, "Location": location, "Status": status}
        outdata.append(rally)
        #print(current_map)


keys = outdata[0].keys()

with open('rally_point_location.csv', 'wb') as out_file:
    dict_writer = csv.DictWriter(out_file, keys)
    dict_writer.writeheader()
    dict_writer.writerows(outdata)




# Get player kill info

#[2018.08.31-04.55.10:064][730]LogSquad: Player:[LLJK] ☢Riyott.exe☢ ActualDamage=186.000015 from oldstastic2011 caused by BP_M4_M68_C_20
#[2018.08.31-04.55.35:645][  2]LogSquad: ScorePoints: Points: -1.000000 ScoreEvent: TeamKilled Jordan Reagan

regex = r"(Player:.*) (ActualDamage=.*) from (.*) caused by (.*)"

kill_logs = []

for indx,line in enumerate(lines):

    if ("ActualDamage=" in line) and ("caused by" in line):
        dateline = extract_date(line)

        # TARGET AND SHOOTER MIGHT BE BACKWARDS.

        # Lets just not talk about this...
        log_data = line.split("LogSquad: ")[1]
        target = log_data.split("Player:")[1].split(" ActualDamage")[0]
        damage = log_data.split("ActualDamage=")[1].split(" from")[0]
        shooter = log_data.split(" from ")[1].split(" caused by ")[0]
        weapon = log_data.split(" caused by ")[1]

        # Sometimes the TK lines are 1 or two lines below the log entry we're parsing
        i = 1
        max_lines = 4
        no_tk = True
        tk_line = False
        while (i < max_lines) and no_tk:
            if "TeamKill" in lines[indx+i]:
                if lines[indx+i].split("TeamKilled ")[1] == target:
                    no_tk = False
                    tk_line = lines[indx+i]
            i += 1

        if tk_line:
            kill_log = {"Timestamp": dateline.strftime(output_date_format), "Shooter": shooter, "Target": target, "Damage": damage, "Weapon": weapon, "TeamKill": True}
        else:
            kill_log = {"Timestamp": dateline.strftime(output_date_format), "Shooter": shooter, "Target": target, "Damage": damage, "Weapon": weapon, "TeamKill": False}

        if kill_log['Shooter'] == "nullptr":
            kill_log['Suicide'] = True
        else:
            kill_log['Suicide'] = False

        kill_logs.append(kill_log)

keys = kill_logs[0].keys()

with open('damage_log.csv', 'wb') as out_file:
    dict_writer = csv.DictWriter(out_file, keys)
    dict_writer.writeheader()
    dict_writer.writerows(kill_logs)


# Get map data
map_line = "Message returned: Current map is"

outdata = []
for line in lines:
    if map_line in line:
        current_map = line.split("Current map is ")[1].split(",")[0]
        outdata.append([extract_date(line).strftime(output_date_format), current_map])
        #print(current_map)

with open('map_data.csv', 'w', newline='') as out:
    csv_out=csv.writer(out)
    csv_out.writerow(['Date', "Map"])
    for row in outdata:
        csv_out.writerow(row)

# Get active players

logger.debug("Looking for active player listing")
start = "RCONOutputDevice::Serialize(): Message returned: ----- Active Players -----"
end = "SendOutboundMessage(): Successfully sent SERVERDATA_RESPONSE_VALUE"
log = False
buffer = []
dates = []

for line in lines:
    if start in line:
        dates.append(extract_date(line))
        log = True
    elif end in line and log:
        log = False
        active_player_lines.append(buffer)
        buffer = []
    elif log:
        if line.startswith("["):
            # Maybe we'll handle this later
            pass
        else:
            buffer.append(line)

# Clean up the data since I can't parse it right in the first place...
new_active_player_list = []
for group in active_player_lines:
    lists = []
    for each in group:
        if "" == each:
            new_active_player_list.append(lists)
            lists=[]
            break
        else:
            lists.append(each)
active_player_lines = new_active_player_list

out_data = []
logger.debug("Sanity check... Date entries (%s) - Player count (%s)" % (len(dates), len(active_player_lines)))
print("Date,Player Count")

for indx, each in enumerate(active_player_lines):
    print("%s,%s" % (dates[indx].strftime(output_date_format),int(len(each))))
    out_data.append([dates[indx].strftime(output_date_format),int(len(each))])

with open('playercount.csv', 'w', newline='') as playerout:
    csv_out=csv.writer(playerout)
    csv_out.writerow(['Date', "Playercount"])
    for row in out_data:
        csv_out.writerow(row)


# User gets in vehicle ?
#[2018.08.31-01.40.13:857][814]LogSquadTrace: [DedicatedServer]ASQPlayerController::Possess(): PC=|TG-95th| Treefingers6 Pawn=BP_BTR80_turret_Militia_C_0 FullPath=BP_BTR80_turret_Militia_C /Game/Maps/Logar_Valley/LogarValley_AAS_v1.LogarValley_AAS_v1:PersistentLevel.BP_BTR80_turret_Militia_C_0