#!/usr/bin/python3
import os
import pickle
import re
import nltk
import sys
import getopt

"""nltk.download('reuters')
nltk.download('punkt')
nltk.download('stopwords')"""

PORTER_STEMMER = nltk.stem.porter.PorterStemmer()
STOP_WORDS = set(nltk.corpus.stopwords.words('english') + [".", ",", ";", ":"])


def usage():
    print("usage: " + sys.argv[0] + " -i directory-of-documents -d dictionary-file -p postings-file")


def normalize_token(token):
    token = token.lower()  # case folding
    token = PORTER_STEMMER.stem(token)  # porter-stemming
    return token


def build_index(in_dir, out_dict, out_postings):
    """
    build index from documents stored in the input directory,
    then output the dictionary file and postings file
    """
    print('indexing...')

    list_of_spimis_to_be_merged = []
    list_of_sorted_terms_to_be_merged = []
    spimi_dict = {}

    all_documents = [int(f) for f in os.listdir(in_dir)]
    all_documents.sort()

    to_not_go_through_all = 0
    for doc_id in all_documents:

        if to_not_go_through_all >= 50:
            break

        to_not_go_through_all += 1

        with open(os.path.join(in_dir, str(doc_id)), 'r') as doc_open:  # TODO: Make this something more blocky
            doc_text = doc_open.read()

        sentences = nltk.sent_tokenize(doc_text)

        sentence_token_lower_sw_ps = []
        for s in sentences:
            words = nltk.word_tokenize(s)

            # remove stop words and case-fold all word tokens, then porter-stem the word
            sentence_token_lower_sw_ps.append([normalize_token(token) for token in words if token not in STOP_WORDS])

        # spimi_dict = {}  # create a new dictionary for every block, no global dictionary
        for sentence in sentence_token_lower_sw_ps:
            for token in sentence:
                if token not in spimi_dict:
                    spimi_dict[token] = [0]
                    postings_list = spimi_dict[token]
                else:
                    postings_list = spimi_dict[token]

                if doc_id not in postings_list:
                    spimi_dict[token][0] += 1  # increase doc frequency, the first int at index 0 of the dictionary
                    postings_list.append(doc_id)

    print("... writing dictionary")
    sorted_terms = sorted(spimi_dict, key=lambda x: x[0])

    with open(out_dict, 'wb') as write_dict:
        pickle.dump(sorted_terms, write_dict)

    print("... writing positings")

    with open(out_postings, 'wb') as write_postings:
        pickle.dump(spimi_dict, write_postings)

    print("... DONE!")


input_directory = output_file_dictionary = output_file_postings = None

try:
    opts, args = getopt.getopt(sys.argv[1:], 'i:d:p:')
except getopt.GetoptError:
    usage()
    sys.exit(2)

for o, a in opts:
    if o == '-i':  # input directory
        input_directory = a
    elif o == '-d':  # dictionary file
        output_file_dictionary = a
    elif o == '-p':  # postings file
        output_file_postings = a
    else:
        assert False, "unhandled option"

if input_directory == None or output_file_postings == None or output_file_dictionary == None:
    usage()
    sys.exit(2)

build_index(input_directory, output_file_dictionary, output_file_postings)
