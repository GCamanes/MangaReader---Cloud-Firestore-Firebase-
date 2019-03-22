# IMPORT
import os
import sys
import argparse

# LINK
# https://medium.com/@cbrannen/importing-data-into-firestore-using-python-dce2d6d3cd51

# INSTALL virtualenv
# pip3 install virtualenv
	# activate env with : source ./env/bin/activate
# (env) pip install firebase-admin google-cloud-firestore

import firebase_admin
import google.cloud
from firebase_admin import credentials, firestore

DB_URL = "https://mangareader-ef367.firebaseio.com"

def main():

	cred = credentials.Certificate("./ServiceAccountKey.json")
	app = firebase_admin.initialize_app(cred)

	store = firestore.client()
	doc_ref = store.collection(u'mangas')

	try:
		docs = doc_ref.get()
		for doc in docs:
			print(u'Doc Data:{}'.format(doc.to_dict()))
	except google.cloud.exceptions.NotFound:
		print(u'Missing data')

if __name__ == "__main__":
    main()
