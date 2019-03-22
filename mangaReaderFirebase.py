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

#-----------------------------------------------------------------------------------
# FAVORITE MANGAS FILE READING
#-----------------------------------------------------------------------------------

def getFavoriteMangas():
	f = open(PATH+'/favoriteMangas.txt', 'r')
	content = f.read().splitlines()
	f.close()
	return content

def showFavoriteMangas():
	fav_list = getFavoriteMangas()
	print()
	if (len(fav_list) > 0):
		for (manga, index) in zip(fav_list, range(1, len(fav_list)+1)):
			print(" #" + str(index) + " : " + manga)
	else:
		print("/!\ no manga in favorite list")

def addFavoriteManga(mangaName):
	if (mangaName in DICO_MANGAS.keys()):
		fav_list = getFavoriteMangas()
		if (mangaName not in fav_list):
			fav_list.append(mangaName)
			with open(PATH+'/favoriteMangas.txt', 'w') as f:
				for item in fav_list:
					f.write("%s\n" % item)
			print("\nSUCCESS " + mangaName + " added to favorite list")
		else:
			print("\n/!\ " + mangaName + " is already in favorite list")
	else:
		print("\n/!\ no existing manga as " + mangaName+"")

def removeFavoriteManga(mangaName):
	if (mangaName in DICO_MANGAS.keys()):
		fav_list = getFavoriteMangas()
		if (mangaName in fav_list):
			fav_list.append(mangaName)
			with open(PATH+'/favoriteMangas.txt', 'w') as f:
				for item in fav_list:
					if (item != mangaName): f.write("%s\n" % item)
			print("\nSUCCESS " + mangaName + " removed from favorite list")
		else:
			print("\n/!\ " + mangaName + " is not in favorite list")
	else:
		print("\n/!\ no existing manga as " + mangaName+"")

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

# Function to show all available manga according to a pattern
# Return : void
def showMangaList(pattern):
	for manga in sorted(DICO_MANGAS):
		if (pattern in manga):
			print("%s" % (manga))

#-----------------------------------------------------------------------------------
# CONNECTION AND INTERACTION WITH CLOUD FIRESTORE
#-----------------------------------------------------------------------------------

def printCollectionDoc(store, collectionName):
	try:
		for doc in store.collection(u'mangas').get():
			print(u'{}'.format(doc.id))
	except google.cloud.exceptions.NotFound:
		print(u'Missing data')

def deleteAllDocumentsFromCollection(store):
	for doc in store.collection(MANGAS_COLLECTION).get():
		store.collection(MANGAS_COLLECTION).document(doc.id).delete()

def addDocumentManga(store, mangaName):
	try:
		store.collection(u'mangas').add({}, mangaName)
	except google.api_core.exceptions.AlreadyExists:
		print(u'\n/!\ Manga collection ' + mangaName + u' already exists')

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
	parser.add_argument('-f', '--favorite',
		help='list of favorite mangas',
		action="store_true")
	parser.add_argument('-a', '--addfav', nargs=1,
		help='add a manga to favorite mangas',
		action='store', type=str)
	parser.add_argument('-r', '--removefav', nargs=1,
		help='remove a manga from favorite mangas',
		action='store', type=str)
	parser.add_argument('-s', '--show', nargs=1,
		help='list of all available mangas that include a search pattern',
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

	elif(args.favorite == True):
		showFavoriteMangas()
		print()
		sys.exit()

	elif(args.addfav != None):
		addFavoriteManga(args.addfav[0])
		print()
		sys.exit()

	elif(args.removefav != None):
		addFavoriteManga(args.removefav[0])
		print()
		sys.exit()


if __name__ == "__main__":
    main()
