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
URL_WEBSITE = "https://www.mangareader.net"
URL_MANGAS_LIST = "/alphabetical"
DB_URL = "https://mangareader-ef367.firebaseio.com"

# COLLECTION NAMES (CLOUD FIRESTORE)
MANGAS_COLLECTION = u'mangasList'
MANGAS_DOCUMENT = u'mangas'
MANGAS_LIST_FIELD = u'list'
CHAPTERS_COLLECTION = u'mangasChapters'
CHAPTERS_COLLECTION_PARTS = u'parts'

## VARIABLES
PATH = "."
DICO_MANGAS = {}
NUMBER_OF_CHAPTERS_PER_BATCH = 100

#-----------------------------------------------------------------------------------
# OPERATION ON CHAPTER NAME AND PAGE NAME
#-----------------------------------------------------------------------------------

# Function to get the complete name of a chapter
# Format : [nameOfManga]_[chap num on 4 digit]
# Used in : chap repository and img file
def getChapName(manga, chap):
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

def extractChapterNumber(chapterName):
    return chapterName.split('chap')[1]

def extractPageNumber(pageName):
    return pageName.split('_')[-1]

def getBatchName(chapterName):
    chap = int(chapterName)
    batchNumber = math.ceil(chap/NUMBER_OF_CHAPTERS_PER_BATCH)
    batchName = 'part_'
    if (batchNumber < 10) :
        batchName = batchName + '0' + str(batchNumber)
    else:
        batchName = batchName + str(batchNumber)
    return batchName

#-----------------------------------------------------------------------------------
# WEBSITE PARSING TO RETRIEVE MANGA DATA
#-----------------------------------------------------------------------------------

# Function to get all available mangas
# Fill a dictionnary with manga name as key and manga url as value
# return : void
def getMangasDico():
	# Get html content in a file
	os.system("curl -s " + URL_WEBSITE+URL_MANGAS_LIST+ " > "+PATH+"/mangaslist.txt")
	# read the file
	f = open(PATH+'/mangaslist.txt', 'r')
	content = f.readlines()
	f.close()

	boolInMangaDiv = False
	for line in content:
		if ('<ul class="series_alpha">' in line):
			boolInMangaDiv = True

		if ("</ul>" in line):
			boolInMangaDiv = False
			pass

		if (boolInMangaDiv):
			mangaUrl = line.split('<li><a href="')[1].split('">')[0]
			mangaName = mangaUrl.split('/')[1]
			DICO_MANGAS[mangaName] = mangaUrl

# Function to get chapter dico from a manga
# Fill with chapter name as key and chapter url as value
# Return : dictionnary
def getMangaChaptersDico(mangaName):
	# Get html content in a file
	os.system("curl -s " + URL_WEBSITE+DICO_MANGAS[mangaName]+ " | grep '" + '<a href="/' + mangaName + '/' + "'> "+PATH+"/mangaChapterslist.txt")
	# read the file
	f = open(PATH+'/mangaChapterslist.txt', 'r')
	content = f.readlines()
	f.close()

	dico_chapters = {}

	for line in content:
		if ("</li>" not in line):
			chapterUrl = line.split('<a href="')[1].split('">')[0]
			chapterNumber = getChapName(mangaName, chapterUrl.split('/')[2])
			dico_chapters[chapterNumber] = chapterUrl

	return dico_chapters

# Function to get pages dico from a chapter
# Fill with page name as key and page url as value
# Return : dictionnary
def getMangaChapterPagesDico(chapterUrl):
	dico_pages = {}
	chapterNumber = chapterUrl.split("/")[-1]

	# Get html content in a file
	os.system("curl -s " + URL_WEBSITE+chapterUrl+ " | grep '" + '<option value="' + chapterUrl + "'> "+PATH+"/mangaChapterPageslist.txt")
	# read the file
	f = open(PATH+'/mangaChapterPageslist.txt', 'r')
	content = f.readlines()
	f.close()

	for line in content:
		pageUrl = line.split('<option value="')[1].split('">')[0]
		if ("selected" in pageUrl):
			pageUrl = pageUrl.split('"')[0]
		pageNumber = getPageName(line.split('</option>')[0].split(">")[-1])
		dico_pages[pageNumber] = pageUrl

	return dico_pages

# Function to show all available manga according to a pattern
# Return : void
def showMangaList(pattern):
	for mangaName in sorted(DICO_MANGAS):
		if (pattern in mangaName):
			print("%s" % (mangaName))

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

def showCollectionMangas(store):
    try:
        mangasList = getMangasList(store)
        print('\n** List of manga on firestore **')
        for (manga, index) in zip(mangasList, range(1, len(mangasList)+1)):
            print('   ', index, ':', manga[u'name'], '  ', manga[u'lastChapter'])
    except google.cloud.exceptions.NotFound:
        print('/!\ Collection ', MANGAS_COLLECTION, "doesn't exist in firestore")

def updateMangaListItem(store, mangasList, mangaName, lastChapter, url, strAction):
    removeMangaFromMangasList(mangaName, mangasList)
    mangasList.append({u'name': mangaName, u'lastChapter': lastChapter, u'url': url })
    try:
        store.collection(MANGAS_COLLECTION).document(MANGAS_DOCUMENT).set({
            u'list': sorted(mangasList, key=itemgetter('name')),
        })
        print('\nSUCCESS firestore list item', strAction, mangaName)
    except google.api_core.exceptions.AlreadyExists:
        print('\n/!\ ERROR firestore list item', strAction, mangaName)

def addManga(store, mangaName):
    if (mangaName in DICO_MANGAS.keys()):
        mangasList = getMangasList(store)
        if (findMangaInMangasList(mangaName, mangasList) == None):
            try:
                updateMangaListItem(store, mangasList, mangaName, 'None', URL_WEBSITE+DICO_MANGAS[mangaName], 'ADD MANGA')
                store.collection(CHAPTERS_COLLECTION).document(mangaName).set({})
                print('\nSUCCESS', mangaName, 'added to firestore')
            except google.api_core.exceptions.AlreadyExists:
                print('\n/!\ ERROR in adding manga', mangaName, 'in manga list')
        else:
            print('\n/!\ ERROR manga', mangaName, 'already in manga list')
    else:
        print("\n/!\ no existing manga as ", mangaName)

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
            print('\nSUCCESS', mangaName, 'deletd from firestore')
        else:
            print('\n/!\ ERROR manga', mangaName, 'not in manga list')
    except:
        print('\n/!\ ERROR in deleting manga', mangaName)
            
def updateMangaOnFirestore(store, mangaName):
    mangasList = getMangasList(store)
    mangaItem = findMangaInMangasList(mangaName, mangasList)
    if (mangaItem != None):
        print("\nUPDATE ", mangaName, "...")
        dico_chapters = getMangaChaptersDico(mangaName)

        for chapter in sorted(dico_chapters):
            if (mangaItem['lastChapter'] == 'None' or chapter > mangaItem['lastChapter']):
                updateMangaChapterOnFirestore(store, mangaName, chapter, dico_chapters[chapter], mangasList)
                mangaItem = findMangaInMangasList(mangaName, mangasList)

        print("\nSUCCESS " + mangaName + " updated on firestore")
    else:
        print('\n/!\ Manga (document) ' + mangaName + " doesn't exists in firestore")

def updateMangaChapterOnFirestore(store, mangaName, chapter, chapterUrl, mangasList):
    try:
        chapterBatch = getBatchName(chapter)
        print("  UPDATING", mangaName, chapter, chapterBatch, '...')
        dico_pages = getMangaChapterPagesDico(chapterUrl)
        pages = []
        for page in sorted(dico_pages):
            pages.append(getMangaChapterPageURL(store, mangaName, chapter, chapterUrl, page, dico_pages[page]))

        batch = store.collection(CHAPTERS_COLLECTION).document(mangaName)\
                    .collection(CHAPTERS_COLLECTION_PARTS).document(chapterBatch)

        if (batch.get().to_dict() == None):
            print('No existing batch', chapterBatch)
            chapters = []
        else:
            print('Existing batch', chapterBatch)
            chapters = batch.get().to_dict()[u'chapters']
        
        chapters.append({u'chapter': chapter, u'pages': pages, u'url': chapterUrl})
        batch.set({
            u'chapters': chapters,
        })
        updateMangaListItem(store, mangasList, mangaName, chapter, URL_WEBSITE+DICO_MANGAS[mangaName], 'UPDATE CHAPTER')

    except google.api_core.exceptions.AlreadyExists:
        pass

def getMangaChapterPageURL(store, mangaName, chapter, chapterUrl, page, pageUrl):
	pagename = chapter+"_"+page
	# Get html content in a file
	os.system("curl -s " + URL_WEBSITE+pageUrl+ " | grep '" + chapterUrl + "' | grep 'img' > "+PATH+"/mangaChapterPageUrl.txt")
	# read the file
	f = open(PATH+'/mangaChapterPageUrl.txt', 'r')
	content = f.readlines()
	f.close()

	if (len(content) != 1):
		print("/!\ ERROR page", chapter, chapterUrl, page, pageUrl)
		print(content)
		ferr = open(PATH+'/ERROR_PAGES.txt', 'a+')
		ferr.write("# ERROR"+chapter+" "+chapterUrl+" "+page+" "+pageUrl)
		ferr.write(content)
		ferr.write("\n")
		ferr.close()
		return {u'url': "", u'page': page}
	else:
		fileUrl = content[0].split('src="')[-1].split('"')[0]
		return {u'url': fileUrl, u'page': page}

def updateAllMangaOnFirestore(store):
    print("\nUPDATE ALL ...")
    mangasList = getMangasList(store)
    if (len(mangasList) > 0):
        for manga in mangasList:
            updateMangaOnFirestore(store, manga[u'name'])
    else:
        print("\n/!\ no manga to update on firestore")

def copyMangaOnFirestore(store, mangaName):
    mangasList = getMangasList(store)
    if (findMangaInMangasList(mangaName, mangasList) != None):
        print('\nCOPYING', mangaName, '...')

        chapters = []
        mangaCollection = store.collection('mangas').get()
        try:
            collection = store.collection('mangas').document(mangaName)\
                .collection('chapters').get()
            for doc in collection :
                chapterDict = doc.to_dict()
                chapter = extractChapterNumber(doc.id)
                pages = chapterDict[u'pages']
                url = chapterDict[u'url']

                for i in range(0, len(pages)):
                    keys = list(pages[i].keys())
                    keys.remove(u'url')
                    pages[i] = {u'page': extractPageNumber(keys[0]), u'url': pages[i][u'url']}

                chapters.append({u'chapter': chapter, u'pages': pages, u'url': url})

            numberOfBatch = math.ceil(len(chapters)/(NUMBER_OF_CHAPTERS_PER_BATCH*1.0))
            batchs = []
            for batchNumber in range(0, numberOfBatch):
                batchs.append([])

            for chapter in chapters:
                batchNumber = math.ceil(int(chapter['chapter'])/NUMBER_OF_CHAPTERS_PER_BATCH)-1
                batchs[batchNumber].append(chapter)

            for batchNumber in range(0, numberOfBatch):
                batchName = 'part_'
                if (batchNumber < 9) :
                    batchName = batchName + '0' + str(batchNumber+1)
                else:
                    batchName = batchName + str(batchNumber+1)

                print(batchName, batchs[batchNumber][0]['chapter'], 'to', batchs[batchNumber][-1]['chapter'], len(batchs[batchNumber]))
                
                store.collection(CHAPTERS_COLLECTION).document(mangaName)\
                    .collection(CHAPTERS_COLLECTION_PARTS).document(batchName).set({
                    u'chapters': batchs[batchNumber],
                })

            updateMangaListItem(store, mangasList, mangaName, batchs[-1][-1]['chapter'], URL_WEBSITE+DICO_MANGAS[mangaName], 'COPY')
            print('\nSUCCESS', mangaName, 'copied in firestore')
        except google.api_core.exceptions.AlreadyExists:
            print('\n/!\ ERROR in copying manga', mangaName, 'in manga list')
        
    else:
        print('\n/!\ Manga ', mangaName, "doesn't exists in firestore")

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
    parser.add_argument('-l', '--list',
        help='show list of mangas in firestore',
        action="store_true")
    parser.add_argument('-a', '--add', nargs=1,
        help='add a manga to firestore',
        action='store', type=str)
    parser.add_argument('-d', '--delete', nargs=1,
        help='remove a manga from firestore',
        action='store', type=str)
    parser.add_argument('-c', '--chap', nargs=1,
        help='specific chapter',
        action='store', type=str)
    parser.add_argument('-s', '--show', nargs=1,
        help='list of all available mangas that include a search pattern',
        action='store', type=str)
    parser.add_argument('--updateall',
        help='update all mangas in cloud firestore',
        action='store_true')
    parser.add_argument('-u', '--update', nargs=1,
        help='update one manga in cloud firestore',
        action='store', type=str)
    parser.add_argument('--copy', nargs=1,
        help='copy one manga in cloud firestore',
        action='store', type=str)

    # Parsing of command line argument
    args = parser.parse_args(sys.argv[1:])

    print("/////////////////////////////////")
    print("//    MANGA READER FIREBASE    //")
    print("/////////////////////////////////\n")
    print("...loading manga list ...")
    # Loading mangas list
    getMangasDico()
    print("SUCCESS manga list loaded !")

    if (args.show != None):
        print("\n** List of all available mangas with pattern '"+args.show[0]+"'")
        showMangaList(args.show[0])
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

    elif(args.copy != None):
        # copyMangaOnFirestore(store, args.copy[0])
        print()
        sys.exit()

if __name__ == "__main__":
    main()