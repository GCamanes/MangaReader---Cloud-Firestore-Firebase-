# HELP LINK
# https://medium.com/@cbrannen/importing-data-into-firestore-using-python-dce2d6d3cd51

# INSTALL virtualenv
# pip3 install virtualenv
	# activate env with : source ./env/bin/activate
# (env) pip install firebase-admin google-cloud-firestore

# IMPORT
import os
import sys
import argparse
import math
from operator import itemgetter
import firebase_admin
import google.cloud
from firebase_admin import credentials, firestore

## WEBSITE URLS
URL_WEBSITE = 'https://manganelo.com'
URL_SEARCH = 'https://manganelo.com/search/'
URL_MANGA = 'https://manganelo.com/manga/'
URL_CHAPTER = 'https://manganelo.com/chapter/'
DB_URL = 'https://mangareader-ef367.firebaseio.com'

# COLLECTION NAMES (CLOUD FIRESTORE)
MANGAS_COLLECTION = u'mangasList'
MANGAS_DOCUMENT = u'mangas'
MANGAS_LIST_FIELD = u'list'
CHAPTERS_COLLECTION = u'mangasChapters'
CHAPTERS_COLLECTION_PARTS = u'parts'

## VARIABLES
PATH = '.'
DICO_MANGAS = {}
NUMBER_OF_CHAPTERS_PER_BATCH = 100

#-----------------------------------------------------------------------------------
# OPERATION ON CHAPTER NAME AND PAGE NAME
#-----------------------------------------------------------------------------------

# Function to get the complete name of a chapter
# Format : [nameOfManga]_[chap num on 4 digit]
# Used in : chap repository and img file
def getChapName(chap):
	chapName = ""
	if (len(chap.split(".")[0]) == 1):
		chapName = "000"+chap
	elif (len(chap.split(".")[0]) == 2):
		chapName = "00"+chap
	elif (len(chap.split(".")[0]) == 3):
		chapName = "0"+chap
	else:
		chapName = chap
	return chapName

# Function to get the string page number (3 digits)
def getPageName(page):
	strPage = str(page)
	if (len(strPage) == 1):
		strPage = "00"+strPage
	elif (len(strPage) == 2):
		strPage = "0"+strPage
	return strPage

#-----------------------------------------------------------------------------------
# WEBSITE PARSING TO RETRIEVE MANGA DATA
#-----------------------------------------------------------------------------------

# Function to search for and show all available manga fiting with a pattern
# Return : void
def searchManga(pattern):
    print('** searching ...')
    pattern = pattern.replace('-', '_')
    
    # Get html content in a file
    os.system("curl -s " + URL_SEARCH+pattern + " | grep '" + pattern + "' > "+PATH+"/searchResults.txt")
    # read the file
    f = open(PATH+'/searchResults.txt', 'r')
    content = f.readlines()
    f.close()
    os.system("rm "+PATH+"/searchResults.txt")

    searchResult = []
    for line in content:
        if (URL_MANGA in line and '</a>' in line):
            url = line.split('href="')[1].split('">')[0]
            manga = line.split('">')[1].split('</a>')[0]
            searchResult.append({'name': manga, 'url': url})

    for result in searchResult:
        print('   ', result['name'])
        print("     '-->", result['url'])

# Function to get information of a manga from url
# Return : dict
def getMangaInfos(mangaUrl):
    # Get html content in a file
    os.system("curl -s " + mangaUrl + " > "+PATH+"/mangasInfos.txt")
    # read the file
    f = open(PATH+'/mangasInfos.txt', 'r')
    content = f.readlines()
    f.close()
    os.system("rm "+PATH+"/mangasInfos.txt")

    mangaDict = {'name': '', 'imgUrl': '', 'url': mangaUrl, 'status': '', 'authors': [], 'lastChapter': 'None'}

    mangaInfoContent = []
    divToClose = 0
    ulToClose = 0
    infoDivFound = False
    for line in content:
        if ('<div class="manga-info-top">' in line or '<div class="manga-info-pic">' in line):
            infoDivFound = True
            divToClose = divToClose + 1
        if (infoDivFound == True and '</div>' in line and '<div>' not in line):
            divToClose = divToClose - 1
        if (infoDivFound):
            mangaInfoContent.append(line)
        if (infoDivFound == True and divToClose == 0):
            break

    inImgDiv = False
    inAuthorLi = False
    for line in mangaInfoContent:
        if ('<h1>' in line and '</h1>' in line):
            mangaDict['name'] = line.split('>')[1].split('<')[0]
        elif ('Status' in line):
            mangaDict['status'] = line.split('<li>Status : ')[-1].split('</li>')[0]
        elif ('<div class="manga-info-pic">' in line):
            inImgDiv = True
        elif ('img' in line and inImgDiv):
            mangaDict['imgUrl'] = line.split('<img src="')[1].split('"')[0]
            inImgDiv = False
        elif ('<li>Author' in line):
            inAuthorLi = True
        elif (inAuthorLi):
            authors = line.split('</a>')
            for author in authors[:-1]:
                if (author[0] != ' '):
                    mangaDict['authors'].append(author.split('>')[-1])
                else:
                    mangaDict['authors'].append(author.split('>')[-1][1:])
            inAuthorLi = False
        
    return mangaDict

# Function to get chapter dico from a manga
# Fill with chapter name as key and chapter url as value
# Return : dictionnary
def getMangaChaptersDico(mangaUrl):
    # Get html content in a file
    os.system("curl -s " + mangaUrl + " | grep '" + URL_CHAPTER + "' > "+PATH+"/mangaChapterslist.txt")
    # read the file
    f = open(PATH+'/mangaChapterslist.txt', 'r')
    content = f.readlines()
    f.close()
    # os.system("rm "+PATH+"/mangaChapterslist.txt")
        
    dico_chapters = {}
    for line in content:
        if ("<span>" in line):
            chapterUrl = line.split('<a href="')[1].split('"')[0]
            chapterNumber = getChapName(chapterUrl.split('_')[-1])
            dico_chapters[chapterNumber] = chapterUrl

    return dico_chapters

#-----------------------------------------------------------------------------------
# CONNECTION AND INTERACTION WITH CLOUD FIRESTORE
#-----------------------------------------------------------------------------------

def getMangasList(store):
    mangasList = []
    try:
        mangasList = store.collection(MANGAS_COLLECTION).document(MANGAS_DOCUMENT).get().to_dict()[MANGAS_LIST_FIELD]
    except:
        print('/!\ ERROR in getting manga list')
        sys.exit()
    return mangasList

def showCollectionMangas(store):
    try:
        mangasList = getMangasList(store)
        print('\n** List of manga on firestore **')
        for (manga, index) in zip(mangasList, range(1, len(mangasList)+1)):
            print('   ', index, ':', manga[u'name'], '  ', manga[u'lastChapter'])
    except google.cloud.exceptions.NotFound:
        print('/!\ Collection ', MANGAS_COLLECTION, "doesn't exist in firestore")

def findMangaInMangasList(mangaName, mangasList):
    mangaToFind = None
    for manga in mangasList:
        if (mangaName == manga[u'name']):
            mangaToFind = manga
            break
    return mangaToFind

def removeMangaFromMangasList(mangaName, mangasList):
    mangaToFind = None
    for manga in mangasList:
        if (mangaName == manga[u'name']):
            mangaToFind = manga
            break
    if (mangaToFind != None):
        mangasList.remove(mangaToFind)

def updateMangaListItem(store, mangasList, mangaDict, strAction):
    removeMangaFromMangasList(mangaDict['name'], mangasList)
    mangasList.append(mangaDict)
    try:
        store.collection(MANGAS_COLLECTION).document(MANGAS_DOCUMENT).set({
            u'list': sorted(mangasList, key=itemgetter('name')),
        })
        print('\nSUCCESS firestore list item', strAction, mangaDict['name'])
    except google.api_core.exceptions.AlreadyExists:
        print('\n/!\ ERROR firestore list item', strAction, mangaDict['name'])

def addManga(store, mangaUrl):
    print('\n SEARCHING manga linked to', mangaUrl, '...')
    mangaDict = getMangaInfos(mangaUrl)

    isMangaDictOk = True
    if (mangaDict['name'] == ''):
        isMangaDictOk = False
    if (mangaDict['imgUrl'] == ''):
        isMangaDictOk = False
    if (mangaDict['status'] == ''):
        isMangaDictOk = False
    if (mangaDict['authors'] == []):
        isMangaDictOk = False

    if (isMangaDictOk):
        print(' ADDING', mangaDict['name'], 'to firebase...')
        mangasList = getMangasList(store)
        if (findMangaInMangasList(mangaDict['name'], mangasList) == None):
            try:
                updateMangaListItem(store, mangasList, mangaDict, 'ADD MANGA')
                store.collection(CHAPTERS_COLLECTION).document(mangaDict['name']).set({})
                print('\nSUCCESS', mangaDict['name'], 'added to firestore')
            except:
                print('\n/!\ ERROR in adding manga', mangaDict['name'], 'in manga list')
        else:
            print('\n/!\ ERROR manga', mangaName, 'already in manga list')
    else:
        print('  ERROR some information can\'t be retrieved from', mangaUrl)

def deleteManga(store, mangaName):
    try:
        mangasList = getMangasList(store)
        if (findMangaInMangasList(mangaName, mangasList) != None):
            collection = store.collection(CHAPTERS_COLLECTION).document(mangaName)\
                .collection(CHAPTERS_COLLECTION_PARTS).get()

            for doc in collection :
                store.collection(CHAPTERS_COLLECTION).document(mangaName)\
                    .collection(CHAPTERS_COLLECTION_PARTS).document(doc.id).delete()
            store.collection(CHAPTERS_COLLECTION).document(mangaName).delete()

            removeMangaFromMangasList(mangaName, mangasList)
            store.collection(MANGAS_COLLECTION).document(MANGAS_DOCUMENT).set({
                u'list': mangasList,
            })
            print('\nSUCCESS', mangaName, 'deleted from firestore')
        else:
            print('\n/!\ ERROR manga', mangaName, 'not in manga list')
    except:
        print('\n/!\ ERROR in deleting manga', mangaName)

def updateMangaOnFirestore(store, mangaName):
    mangasList = getMangasList(store)
    mangaItem = findMangaInMangasList(mangaName, mangasList)
    if (mangaItem != None):
        print("\nUPDATE ", mangaItem['name'], "...")
        dico_chapters = getMangaChaptersDico(mangaItem['url'])

        for chapter in sorted(dico_chapters):
            print(chapter, dico_chapters[chapter])

        """for chapter in sorted(dico_chapters):
            if (mangaItem['lastChapter'] == 'None' or chapter > mangaItem['lastChapter']):
                updateMangaChapterOnFirestore(store, mangaName, chapter, dico_chapters[chapter], mangasList)
                mangaItem = findMangaInMangasList(mangaName, mangasList)"""

        print("\nSUCCESS " + mangaName + " updated on firestore")
    else:
        print('\n/!\ Manga (document) ' + mangaName + " doesn't exists in firestore")

#-----------------------------------------------------------------------------------
# MAIN FUNCTION
#-----------------------------------------------------------------------------------
def main():

    # Cloud Firestore certificate
    cred = credentials.Certificate("./ServiceAccountKey.json")
    app = firebase_admin.initialize_app(cred)
    # Get firestore client to interact with distant database
    store = firestore.client()

    # Definition of argument option
    parser = argparse.ArgumentParser(prog="mangaReaderFirebase.py")
    parser.add_argument('-s', '--search', nargs=1,
        help='search for all available mangas that include a search pattern',
        action='store', type=str)
    parser.add_argument('-l', '--list',
        help='show list of mangas in firestore',
        action="store_true")
    parser.add_argument('-a', '--add', nargs=1,
        help='add a manga to firestore',
        action='store', type=str)
    parser.add_argument('-d', '--delete', nargs=1,
        help='delete a manga from firestore (use "MangaName")',
        action='store', type=str)
    parser.add_argument('-u', '--update', nargs=1,
        help='update one manga in cloud firestore  (use "MangaName")',
        action='store', type=str)

    # Parsing of command line argument
    args = parser.parse_args(sys.argv[1:])

    if (args.search != None):
        print("\n** List of all available mangas with pattern '"+args.search[0]+"'")
        searchManga(args.search[0])
        print()
        sys.exit()
    
    elif(args.list == True):
        showCollectionMangas(store)
        print()
        sys.exit()

    elif(args.add != None):
        addManga(store, args.add[0])
        print()
        sys.exit()

    elif(args.delete != None):
        deleteManga(store, args.delete[0])
        print()
        sys.exit()

    elif(args.update != None):
        updateMangaOnFirestore(store, args.update[0])
        print()
        sys.exit()

if __name__ == "__main__":
    main()