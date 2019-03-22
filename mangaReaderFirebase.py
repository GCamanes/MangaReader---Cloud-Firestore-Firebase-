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
import firebase_admin
import google.cloud
from firebase_admin import credentials, firestore

## WEBSITE URLS
URL_WEBSITE = "https://www.mangareader.net"
URL_MANGAS_LIST = "/alphabetical"
DB_URL = "https://mangareader-ef367.firebaseio.com"

# COLLECTION NAMES (CLOUD FIRESTORE)
MANGAS_COLLECTION = u'mangas'
CHAPTERS_COLLECTION = u'chapters'
PAGES_COLLECTION = u'pages'

# LIST OF FAVORITE MANGAS
FAVORITE_MANGAS_LIST = []

## VARIABLES
PATH = "."
DICO_MANGAS = {}

#-----------------------------------------------------------------------------------
# OPERATION ON CHAPTER NAME AND PAGE NAME
#-----------------------------------------------------------------------------------

# Function to get the complete name of a chapter
# Format : [nameOfManga]_[chap num on 4 digit]
# Used in : chap repository and img file
def getChapName(manga, chap):
	chapName = ""
	if (len(chap.split(".")[0]) == 1):
		chapName = manga+"_chap000"+chap
	elif (len(chap.split(".")[0]) == 2):
		chapName = manga+"_chap00"+chap
	elif (len(chap.split(".")[0]) == 3):
		chapName = manga+"_chap0"+chap
	else:
		chapName = manga+"_chap"+chap
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

# Function to show all available manga according to a pattern
# Return : void
def showMangaList(pattern):
	for mangaName in sorted(DICO_MANGAS):
		if (pattern in mangaName):
			print("%s" % (mangaName))

#-----------------------------------------------------------------------------------
# CONNECTION AND INTERACTION WITH CLOUD FIRESTORE
#-----------------------------------------------------------------------------------

def getCollectionMangasIDs(store):
	listID = []

	try:
		collection = store.collection(MANGAS_COLLECTION).get()
		for doc in collection :
			listID.append(doc.id)
	except google.cloud.exceptions.NotFound:
		print('/!\ Collection ' + MANGAS_COLLECTION + "doesn't exist in firestore")

	return listID

def getCollectionChaptersIDs(store, mangaName):
	listID = []

	try:
		collection = store.collection(MANGAS_COLLECTION).document(mangaName)\
			.collection(CHAPTERS_COLLECTION).get()
		for doc in collection :
			listID.append(doc.id)
	except google.cloud.exceptions.NotFound:
		print('/!\ Collection ' + CHAPTERS_COLLECTION + "doesn't exist in firestore")

	return listID

def showCollectionMangas(store):
	listID = getCollectionMangasIDs(store)
	print("\n** List of manga on firestore **")
	for id, index in zip(listID, range(1, len(listID)+1)):
		print(" #"+str(index)+" "+id)

def addDocumentManga(store, mangaName):
	if (mangaName in DICO_MANGAS.keys()):
		try:
			store.collection(MANGAS_COLLECTION).add({'url': URL_WEBSITE+DICO_MANGAS[mangaName]}, mangaName)
			print("\nSUCCESS " + mangaName + " added to firestore")
		except google.api_core.exceptions.AlreadyExists:
			print('\n/!\ Manga (document) ' + mangaName + ' already exists')
	else:
		print("\n/!\ no existing manga as " + mangaName+"")

def updateMangaOnFirestore(store, mangaName):
	if (mangaName in getCollectionMangasIDs(store)):
		print("UPDATE ", mangaName, "...")

		dico_chapters = getMangaChaptersDico(mangaName)

		for chapter in sorted(dico_chapters)[:10]:
			store.collection(MANGAS_COLLECTION).document(mangaName)\
				.collection(CHAPTERS_COLLECTION).add({}, chapter)
	else:
		print('\n/!\ Manga (document) ' + mangaName + " doesn't exists in firestore")

def deleteDocumentManga(store, mangaName):
	if (mangaName in DICO_MANGAS.keys()):
		try:
			listChapterIDs = getCollectionChaptersIDs(store, mangaName)
			for chapter in listChapterIDs:
				deleteDocuementChapter(store, mangaName, chapter)
			store.collection(MANGAS_COLLECTION).document(mangaName).delete()
			print("\nSUCCESS " + mangaName + " deleted from firestore")
		except google.api_core.exceptions.AlreadyExists:
			print('\n/!\ Manga (document) ' + mangaName + " doesn't exists")
	else:
		print("\n/!\ no existing manga as " + mangaName+"")

def deleteDocuementChapter(store, mangaName, chapter):
	try:
		store.collection(MANGAS_COLLECTION).document(mangaName)\
			.collection(CHAPTERS_COLLECTION).document(chapter).delete()
	except google.api_core.exceptions.AlreadyExists:
		print('\n/!\ Chapter (document) ' + chapter + " doesn't exists")

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
	parser.add_argument('-s', '--show', nargs=1,
		help='list of all available mangas that include a search pattern',
		action='store', type=str)
	parser.add_argument('-u', '--update', nargs=1,
		help='update all favorite mangas in cloud firestore',
		action='store', type=str)
	parser.add_argument('-m', '--manga', nargs=1,
		help='update one manga from favorite list in cloud firestore',
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
		addDocumentManga(store, args.add[0])
		print()
		sys.exit()

	elif(args.delete != None):
		deleteDocumentManga(store, args.delete[0])
		print()
		sys.exit()

	elif(args.manga != None):
		updateMangaOnFirestore(store, args.manga[0])
		print()
		sys.exit()

if __name__ == "__main__":
    main()
