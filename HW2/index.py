#!/usr/bin/python3
import os
import re
import nltk
import sys
import getopt

"""nltk.download('reuters')
nltk.download('punkt')
nltk.download('stopwords')"""

PORTER_STEMMER = nltk.stem.porter.PorterStemmer()

def usage():
    print("usage: " + sys.argv[0] + " -i directory-of-documents -d dictionary-file -p postings-file")

def build_index(in_dir, out_dict, out_postings):
    """
    build index from documents stored in the input directory,
    then output the dictionary file and postings file
    """
    print('indexing...')

    words_dictionary = {}
    postings = {}

    all_documents = [f for f in os.listdir(in_dir)]

    to_not_go_through_all = 0
    for doc_id in all_documents:
        if to_not_go_through_all >= 50:
            break

        with open(os.path.join(in_dir, doc_id), 'r') as doc_open:
            doc_text = doc_open.read()
            sentences = nltk.sent_tokenize(doc_text)
            sentence_token_lower_sw_ps = []
            for s in sentences:
                words = nltk.word_tokenize(s)

                stop_words = set(nltk.corpus.stopwords.words('english') + [".", ",", ";", ":"])

                # remove stop words and case-fold all word tokens, then porter-stem the word
                sentence_token_lower_sw_ps.append([PORTER_STEMMER.stem(word.lower()) for word in words if word not in stop_words])

        for sentence in sentence_token_lower_sw_ps:
            for processed_word in sentence:
                if processed_word in words_dictionary:
                    if doc_id not in postings[processed_word]:
                        postings[processed_word].append(doc_id)
                    words_dictionary[processed_word] += 1
                else:
                    postings[processed_word] = [doc_id]
                    words_dictionary[processed_word] = 1

        to_not_go_through_all += 1

    print(words_dictionary)
    print("BREAK")
    print(postings)


    # This is an empty method
    # Pls implement your code in below

input_directory = output_file_dictionary = output_file_postings = None

try:
    opts, args = getopt.getopt(sys.argv[1:], 'i:d:p:')
except getopt.GetoptError:
    usage()
    sys.exit(2)

for o, a in opts:
    if o == '-i': # input directory
        input_directory = a
    elif o == '-d': # dictionary file
        output_file_dictionary = a
    elif o == '-p': # postings file
        output_file_postings = a
    else:
        assert False, "unhandled option"

if input_directory == None or output_file_postings == None or output_file_dictionary == None:
    usage()
    sys.exit(2)

build_index(input_directory, output_file_dictionary, output_file_postings)
