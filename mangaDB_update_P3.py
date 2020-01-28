# Python 3 script to update firebase database
# install
# need Python 3
# need pip3
# sudo pip3 install firebase-admin
# get credentials : firebase console > project > project parameters > service account > generate new private key

import os
import sys
import argparse
import math
import google.cloud
import firebase_admin
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

#-----------------------------------------------------------------------------------
# CURL METHODS
#-----------------------------------------------------------------------------------

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

def updateAllMangaOnFirestore(store):
    print("\nUPDATING ALL ...")
    mangasList = getMangasList(store)
    if (len(mangasList) > 0):
        for manga in mangasList:
            print(manga)
            # updateMangaOnFirestore(store, manga[u'name'])
    else:
        print("\n/!\ no manga to update on firestore")

#-----------------------------------------------------------------------------------
# MAIN FUNCTION
#-----------------------------------------------------------------------------------
def main():
    print('HELLO WORLD')
    # Cloud Firestore certificate
    cred = credentials.Certificate("./ServiceAccountKey.json")
    app = firebase_admin.initialize_app(cred)
    # Get firestore client to interact with distant database
    store = firestore.client()

    # Definition of argument option
    parser = argparse.ArgumentParser(prog="mangaDB_update_P3.py")
    parser.add_argument('--updateall',
        help='update all mangas in cloud firestore',
        action='store_true')

    # Parsing of command line argument
    args = parser.parse_args(sys.argv[1:])

    elif(args.updateall == True):
        updateAllMangaOnFirestore(store)
        print()
        sys.exit()

if __name__ == "__main__":
    main()
