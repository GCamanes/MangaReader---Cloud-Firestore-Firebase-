# HELP LINK
# https://medium.com/@cbrannen/importing-data-into-firestore-using-python-dce2d6d3cd51

# Python 3 script to update firebase database
# install
# need Python 3
# need pip3
# sudo pip3 install firebase-admin
# get credentials : firebase console > project > project parameters > service account > generate new private key > rename file to ServiceAccountKey.json

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
LIST_COLLECTION = u'mangasList'
LIST_DOCUMENT = u'mangas'
LIST_DOCUMENT_FIELD = u'list'

MANGAS_COLLECTION = u'mangasChapters'
MANGAS_LIST_FIELD = u'chaptersList'
CHAPTERS_COLLECTION = u'chapters'
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
    print('SEARCHING ...')
    pattern = pattern.replace('-', '_')

    # Get html content in a file
    os.system("curl -s " + URL_SEARCH+pattern + " | grep '" + URL_MANGA + "' | grep -v '<h3>' > "+PATH+"/searchResults.txt")
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
    os.system("curl -s " + mangaUrl + " > "+PATH+"/mangaInfos.txt")
    # read the file
    f = open(PATH+'/mangaInfos.txt', 'r')
    content = f.readlines()
    f.close()
    os.system("rm "+PATH+"/mangaInfos.txt")

    mangaDict = {'name': '', 'imgUrl': '', 'url': mangaUrl, 'status': '', 'lastChapter': 'None'}

    imageFlag = False
    nameFlag = False
    statusFlag = False

    for line in content:
        if (imageFlag):
            mangaDict['imgUrl'] = line.split('src="')[1].split('"')[0]
            imageFlag = False
        if ('<span class="info-image">' in line):
            imageFlag = True

        if (nameFlag):
            mangaDict['name'] = line.split('<h1>')[1].split('</h1>')[0]
            nameFlag = False
        if ('<div class="story-info-right">' in line):
            nameFlag = True

        if (statusFlag):
            mangaDict['status'] = line.split('<td class="table-value">')[1].split('</td>')[0]
            statusFlag = False
            break
        if ('<td class="table-label"><i class="info-status"></i>Status :</td>' in line):
            statusFlag = True

    return mangaDict

# Function to get chapter dico from a manga
# Fill with chapter name as key and chapter url as value
# Return : dictionnary
def getMangaChaptersDico(mangaName, mangaUrl):
    # Get html content in a file
    os.system("curl -s " + mangaUrl + " | grep '" + URL_CHAPTER + "' > "+PATH+"/mangaChapterslist.txt")
    # read the file
    f = open(PATH+'/mangaChapterslist.txt', 'r')
    content = f.readlines()
    f.close()
    os.system("rm "+PATH+"/mangaChapterslist.txt")

    dico_chapters = {}

    for line in content:
        if (stringToFind in line and 'link_chapter_null' not in line):
            chapterUrl = line.split('href="')[1].split('"')[0]
            chapterNumber = getChapName(chapterUrl.split('chapter_')[1])
            dico_chapters[chapterNumber] = chapterUrl

    return dico_chapters

def getChapter(mangaName, chapter, chapterUrl):

    chapterObj = {u'chapter': chapter, u'pages': [], u'url': chapterUrl}

    # Get html content in a file
    os.system("curl -s " + chapterUrl + " | grep '<img src' | grep 'page' > "+PATH+"/chapterInfos.txt")
    # read the file
    f = open(PATH+'/chapterInfos.txt', 'r')
    content = f.readlines()
    f.close()
    os.system("rm "+PATH+"/chapterInfos.txt")
    if (len(content) != 1):
        print('   ERROR uploading', mangaName, chapter, ' in getting pages')
        sys.exit()

    contentClean = content[0].split('/>')
    for item in contentClean:
        itemClean = item.split('<img src="')[-1]
        if ('</div>' not in itemClean):
            url = itemClean.split('" alt')[0]
            page = getPageName(url.split('/')[-1].split('.')[0])
            chapterObj['pages'].append({u'page': page, u'url': url})

    return chapterObj

#-----------------------------------------------------------------------------------
# CONNECTION AND INTERACTION WITH CLOUD FIRESTORE
#-----------------------------------------------------------------------------------

def getMangasList(store):
    mangasList = []
    try:
        mangasList = store.collection(LIST_COLLECTION).document(LIST_DOCUMENT).get().to_dict()[LIST_DOCUMENT_FIELD]
    except:
        print('/!\ ERROR in getting manga list')
        sys.exit()
    return mangasList

def showCollectionMangas(store):
    try:
        mangasList = getMangasList(store)
        print('\n** List of manga on firestore **')
        if (len(mangasList) == 0):
            print('   No mangas added to firestore')
        else:
            for (manga, index) in zip(mangasList, range(1, len(mangasList)+1)):
                print('   ', index, ':', manga[u'name'], '  ', manga[u'lastChapter'])
    except google.cloud.exceptions.NotFound:
        print('/!\ Collection ', LIST_COLLECTION, "doesn't exist in firestore")
        sys.exit()

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
        store.collection(LIST_COLLECTION).document(LIST_DOCUMENT).set({
            u'list': sorted(mangasList, key=itemgetter('name')),
        })
        print('SUCCESS firestore list item', strAction, mangaDict['name'])
    except google.api_core.exceptions.AlreadyExists:
        print('\n/!\ ERROR firestore list item', strAction, mangaDict['name'])
        sys.exit()

def addManga(store, mangaUrl):
    print('\nSEARCHING manga linked to', mangaUrl, '...')
    mangaDict = getMangaInfos(mangaUrl)

    isMangaDictOk = True
    if (mangaDict['name'] == ''):
        isMangaDictOk = False
    if (mangaDict['imgUrl'] == ''):
        isMangaDictOk = False
    if (mangaDict['status'] == ''):
        isMangaDictOk = False

    if (isMangaDictOk):
        print('ADDING', mangaDict['name'], 'to firebase...')
        mangasList = getMangasList(store)
        if (findMangaInMangasList(mangaDict['name'], mangasList) == None):
            try:
                updateMangaListItem(store, mangasList, mangaDict, 'ADD MANGA')
                store.collection(MANGAS_COLLECTION).document(mangaDict['name']).set({u'chaptersList': []})
                print('\nSUCCESS', mangaDict['name'], 'added to firestore')
            except:
                print('\n/!\ ERROR in adding manga', mangaDict['name'], 'in manga list')
                sys.exit()
        else:
            print('\n/!\ ERROR manga', mangaDict['name'], 'already in manga list')
            sys.exit()
    else:
        print('  ERROR some information can\'t be retrieved from', mangaUrl)
        sys.exit()

def deleteManga(store, mangaName):
    try:
        mangasList = getMangasList(store)
        if (findMangaInMangasList(mangaName, mangasList) != None):
            collection = store.collection(MANGAS_COLLECTION).document(mangaName)\
                .collection(CHAPTERS_COLLECTION).get()

            for doc in collection :
                store.collection(MANGAS_COLLECTION).document(mangaName)\
                    .collection(CHAPTERS_COLLECTION).document(doc.id).delete()
            store.collection(MANGAS_COLLECTION).document(mangaName).delete()

            removeMangaFromMangasList(mangaName, mangasList)
            store.collection(LIST_COLLECTION).document(LIST_DOCUMENT).set({
                u'list': mangasList,
            })
            print('\nSUCCESS', mangaName, 'deleted from firestore')
        else:
            print('\n/!\ ERROR manga', mangaName, 'not in manga list')
    except:
        print('\n/!\ ERROR in deleting manga', mangaName)
        sys.exit()

def updateMangaOnFirestore(store, mangaName):
    mangasList = getMangasList(store)
    mangaDict = findMangaInMangasList(mangaName, mangasList)
    if (mangaDict != None):
        print("\nUPDATE ", mangaDict['name'], "...")
        dico_chapters = getMangaChaptersDico(mangaDict['name'], mangaDict['url'])

        for chapter in sorted(dico_chapters):
            if (mangaDict['lastChapter'] == 'None' or chapter > mangaDict['lastChapter']):
                updateMangaChapterOnFirestore(store, mangaDict, chapter, dico_chapters[chapter], mangasList)
                mangaDict = findMangaInMangasList(mangaDict['name'], mangasList)

        print("\nSUCCESS " + mangaDict['name'] + " updated on firestore")
    else:
        print('\n/!\ Manga (document) ' + mangaName + " doesn't exists in firestore")
        sys.exit()

def updateMangaChapterOnFirestore(store, mangaDict, chapter, chapterUrl, mangasList):
    try:
        print("\n   UPLOADING", mangaDict['name'], "chapter", chapter, "...")
        chapterObj = getChapter(mangaDict['name'], chapter, chapterUrl)

        mangaDoc = store.collection(MANGAS_COLLECTION).document(mangaDict['name'])

        if (mangaDoc.get().to_dict() == None):
            chaptersList = []
        else:
            chaptersList = mangaDoc.get().to_dict()[u'chaptersList']

        chaptersList.append(mangaDict['name']+'_'+chapterObj['chapter'])
        mangaDoc.set({
            u'chaptersList': chaptersList,
        })

        store.collection(MANGAS_COLLECTION).document(mangaDict['name'])\
            .collection(CHAPTERS_COLLECTION).document(mangaDict['name']+'_'+chapterObj['chapter']).set(chapterObj)

        mangaDict['lastChapter'] = chapterObj['chapter']
        updateMangaListItem(store, mangasList, mangaDict, 'UPDATE CHAPTER')

    except:
        print('/!\ ERROR in UPLOADING', mangaDict['name'], "chapter", chapter)
        sys.exit()

def updateAllMangaOnFirestore(store):
    print("\nUPDATING ALL ...")
    mangasList = getMangasList(store)
    if (len(mangasList) > 0):
        for manga in mangasList:
            updateMangaOnFirestore(store, manga[u'name'])
    else:
        print("\n/!\ no manga to update on firestore")

def deleteAllMangaFromFirestore(store):
    print("\nDELETE ALL ...")
    mangasList = getMangasList(store)
    if (len(mangasList) > 0):
        for manga in mangasList:
            deleteManga(store, manga[u'name'])
    else:
        print("\n/!\ no manga to update on firestore")

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
    parser.add_argument('--updateall',
        help='update all mangas in cloud firestore',
        action='store_true')
    parser.add_argument('--deleteall',
        help='delete all mangas in cloud firestore',
        action='store_true')

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

    elif(args.updateall == True):
        updateAllMangaOnFirestore(store)
        print()
        sys.exit()

    elif(args.deleteall == True):
        deleteAllMangaFromFirestore(store)
        print()
        sys.exit()

if __name__ == "__main__":
    main()
