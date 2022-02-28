#!/usr/bin/python3
import pickle
import re
import nltk
import sys
import getopt

OPERATORS = ["NOT", "AND", "OR"]
PRECEDENCE_DICT = {"NOT":3, "AND":2, "OR":1}  # the precedence order for not, and, or.
PORTER_STEMMER = nltk.stem.porter.PorterStemmer()
STOP_WORDS = set(nltk.corpus.stopwords.words('english') + [".", ",", ";", ":"])
NUMBER_OF_BLOCKS = 10


class Posting:
    def __init__(self, data):
        self.doc_id = data
        self.next = None
        self.skip = None

    def __repr__(self):
        return str(self.doc_id) + str(f' ({self.skip.doc_id})') if self.skip is not None else str(self.doc_id)


class PostingList:
    def __init__(self):
        self.head = None
        self.length = 1

    def add_first(self, node):
        node.next = self.head
        self.head = node

    def convert_to_linked_list(self, list_of_postings, number_of_postings):
        self.length = number_of_postings
        current_node = self.head
        for posting_doc_id in list_of_postings:
            current_node.next = Posting(posting_doc_id)
            current_node = current_node.next

    def sortedMerge(self, a, b):
        result = None

        # Base cases
        if a is None:
            return b
        elif b is None:
            return a

        # Pick either a or b, and recur
        if a.doc_id <= b.doc_id:
            result = a
            result.next = self.sortedMerge(a.next, b)
        else:
            result = b
            result.next = self.sortedMerge(a, b.next)

        return result

    def add_skip_ptr(self, curr_node, skip_distance, curr_idx=0, looking_for_next=False):

        result = curr_node

        if looking_for_next:
            # if curr_idx is evenly divided by skip_distance, we want to add a skip pointer to this node
            if curr_idx % skip_distance == 0:
                return result
            else:
                if result is None or result.next is None:
                    return None
                else:
                    # iterate deeper (if not and end of list) to find where to put the pointer
                    return self.add_skip_ptr(result.next, skip_distance, curr_idx + 1, looking_for_next)
        else:
            if curr_idx % skip_distance == 0:
                looking_for_next = True
                result.skip = self.add_skip_ptr(result.next, skip_distance, curr_idx + 1, looking_for_next)

        # main loop
        if result.next is not None:
            self.add_skip_ptr(result.next, skip_distance, curr_idx + 1, False)

    def __iter__(self):
        node = self.head
        while node is not None:
            yield node
            node = node.next

    def __repr__(self):
        node = self.head
        nodes = ['len' + str(self.length)]
        while node is not None:
            nodes.append(str(node))
            node = node.next
        nodes.append("None")
        return " -> ".join(nodes)

def usage():
    print("usage: " + sys.argv[0] + " -d dictionary-file -p postings-file -q file-of-queries -o output-file-of-results")

def normalize_token(token):
    token = token.lower()  # case folding
    token = PORTER_STEMMER.stem(token)  # porter-stemming
    return token

def shunting_yard(q):
    # while there are tokens to read

    q = q.replace('(', '( ')
    q = q.replace(')', ' )')

    tokens = q.split()

    output_q = []
    operator_stack = []  # stack implementation, use stack.append() and stack.pop() for add/remove

    for token in tokens:
        if token in OPERATORS:
            while len(operator_stack) > 0 and operator_stack[-1] != '(' \
                    and PRECEDENCE_DICT[operator_stack[-1]] > PRECEDENCE_DICT[token]:
                output_q.append(operator_stack.pop())
            operator_stack.append(token)

        elif token == '(':
            operator_stack.append(token)

        elif token == ')':
            while operator_stack[-1] != '(':
                if len(operator_stack) < 1:
                    raise "MismatchError"
                output_q.append(operator_stack.pop())
            operator_stack.pop()    # pop the left parenthesis from the stack and discard it

        else:   # token must be a search term
            output_q.append(normalize_token(token))

    while len(operator_stack) > 0:
        top_of_stack = operator_stack.pop()
        if top_of_stack == '(' or top_of_stack == ')':
            raise "MismatchError"
        output_q.append(top_of_stack)
    return output_q


def process_query(q):
    postix_q = shunting_yard(q)
    print(postix_q)


def run_search(dict_file, postings_file, queries_file, results_file):
    """
    using the given dictionary file and postings file,
    perform searching on the given queries file and output the results to a file
    """

    ##########
    with open(queries_file, 'r') as queries:
        for query in queries:
            process_query(query)    # Process this query

    ##########

    with open('term_conversion.txt', 'rb') as read_term_converter:
        term_to_term_id = pickle.load(read_term_converter)    # term (str) -> term id (int, 4 bytes)
        #term_id_to_term = pickle.load(read_term_converter)    # term id (int, 4 bytes) -> term (str)


    with open(dict_file, 'rb') as read_dict:
        # We are able to read the full dictionary into memory
        dictionary = pickle.load(read_dict)

    print(len(dictionary.keys()))

    # This is not correct code, we should not read everything, instead, rely on pointers.
    with open(postings_file, 'rb') as read_postings:
        postings = pickle.load(read_postings)

    print(postings[term_to_term_id['said']])

    print('running search on the queries...')
    # This is an empty method
    # Pls implement your code in below

dictionary_file = postings_file = file_of_queries = output_file_of_results = None

try:
    opts, args = getopt.getopt(sys.argv[1:], 'd:p:q:o:')
except getopt.GetoptError:
    usage()
    sys.exit(2)

for o, a in opts:
    if o == '-d':
        dictionary_file  = a
    elif o == '-p':
        postings_file = a
    elif o == '-q':
        file_of_queries = a
    elif o == '-o':
        file_of_output = a
    else:
        assert False, "unhandled option"

if dictionary_file == None or postings_file == None or file_of_queries == None or file_of_output == None :
    usage()
    sys.exit(2)

run_search(dictionary_file, postings_file, file_of_queries, file_of_output)
