##
## Justify.py
# A democratic http front-end for Mopidy
#
# TODO:
# make search field text more clear
# fix no results redirect button
# better logs
# make back arrows
# add refresh button to list view
# make release + 2820.camp branch
# rewrite front page
# write admin panel
# allow more than just spotify results
# add relative paths (especially for static)
# switch away from development server - test w/ multiple people first
# generate results pages dynamically - test w/ multiple people first

from __future__ import unicode_literals
from bottle import route, run, post, request, template, redirect, static_file, auth_basic, parse_auth
from paste import httpserver # not in use atm
from mpd import MPDClient
import time
import configparser
import os.path
from passlib.hash import sha256_crypt

# dictionary of mpd ID : vote counts
votes = {}
# dictionary of mpd ID : vote times, for spoof prevention
timers = {}

###############
# CONFIGURATION
config = configparser.RawConfigParser()
config.read("config.txt")
# http section
host = config.get("http", "host")
port = config.getint("http","port")
# mpd section
mpdhost = config.get("mpd", "host")
mpdport = config.getint("mpd","port")
# other section
delay = config.getint("other","delay")
admin_uri = config.getint("other","admin_uri")

# serve static files, in use only for background image atm
@route('/static/<filename>')
def server_static(filename):
    return static_file(filename, root='./static') #TODO: import path

###########
# INIT MPD STUFF
client = MPDClient()
client.timeout = 100
client.idletimeout = None
client.connect(mpdhost, mpdport)
client.consume(1)

##################
# SORTING FUNCTION
def Sort():
    playlist = client.playlistid() # get nice list of dicts
    swapped = True
    while swapped == True:
        swapped = False
        for i in range(1,len(playlist)-1): #iterate thru playlist, skipping first and last tracks
            song = playlist[i]
            song2 = playlist[i+1]
            if votes[song["id"]] < votes[song2["id"]]:
                client.move(int(song["pos"]),int(song["pos"])+1)
                playlist = client.playlistid() # reload playlist after swap
                swapped = True
                #client.swapid(song["id"],song2["id"])
                #client.swap(song["pos"],song2["pos"])

# Function to add songs from other front-ends to votes / timers databases
def Register(songid):
    votes[songid] = 0
    timers[songid] = time.time()

############
# FRONT PAGE
@route('/')
def Root():
    return template('front',delay=delay)

##############
#PLAYLIST PAGE
#Shows the playlist in the current order, w/ vote buttons
@route('/list')
def List():
    plist = client.playlistid() # get nice list of dicts
    return template('list', plist=plist, votes=votes, timers=timers, delay=delay, time=time, Register=Register)

@post('/list')
def Vote():
    voteid = request.POST.get('voteID')
    votes[voteid] += 1
    timers[voteid] = time.time() # reset timer
    print("votes",votes)
    Sort()
    redirect('/list')

#############
# SEARCH PAGE
# for specific search form
@route('/search')
def SearchForm():
    return template('search')

@post('/search')
def Search():
    global result
    if request.forms.get('searchtype') == "simple":
        print("Doing simple search!")
        searchany = request.forms.get('inputany')
        result = client.search("any",searchany)
    elif request.forms.get('searchtype') == "specific":
        print("Doing specific search!")
        # reset vars to avoid searching for "None"
        searchsong = ""
        searchartist = ""
        searchalbum = ""
        searchsong = request.forms.get('inputsong')
        searchartist = request.forms.get('inputartist')
        searchalbum = request.forms.get('inputalbum')
        result = client.search("title",searchsong,"artist",searchartist,"album",searchalbum)
    else:
        "Something went wrong!"
    redirect('/search/result')

#####################
# SEARCH RESULTS PAGE
@route('/search/result')
def SearchResults():
    return template('result', result=result)

@post('/search/result')
def Add(uri=None):
    if uri is None:
        uri = request.POST.get('URI')
    songid = client.addid(uri)
    votes[songid] = 1
    timers[songid] = time.time() - delay
    # play song if paused
    status = client.status()
    if status["state"] != "play":
        client.play()
    print("ADDED:", songid)
    redirect('/list')

############
# ADMIN PAGE totally incomplete
def Delete(id="None"):
    if not id == "None":
        client.deleteid(id)

@route('/secretadminpanel')
def AdminPanel():
    return template('list', plist=plist, votes=votes, timers=timers, delay=delay, time=time, Register=Register)

run(host=host, port=port)
