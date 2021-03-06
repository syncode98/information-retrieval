#!/usr/bin/python3
import pickle
import re
import nltk
import sys
import getopt

OPERATORS = ["NOT", "AND", "OR"]
PRECEDENCE_DICT = {"NOT": 3, "AND": 2, "OR": 1}  # the precedence order for not, and, or.
PORTER_STEMMER = nltk.stem.porter.PorterStemmer()
STOP_WORDS = set(nltk.corpus.stopwords.words('english') + [".", ",", ";", ":"])
NUMBER_OF_BLOCKS = 10

with open('term_conversion.txt', 'rb') as read_term_converter:
    term_to_term_id = pickle.load(read_term_converter)  # term (str) -> term id (int, 4 bytes)
    term_id_to_term = pickle.load(read_term_converter)  # term id (int, 4 bytes) -> term (str)


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

    def alt_or_merge(self, a, b):
        head_a = a
        while a is not None and a.next is not None:
            print(f'A: {a}, B: {b}')
            if a.doc_id == b.doc_id:
                # in this case, we want to break the tie in favor of the posting that have the
                # lowest numbered next posting

                c = a
                d = b
                tie_broken = False
                while not tie_broken:
                    a_next = c.next.doc_id if c.next is not None else 0
                    b_next = d.next.doc_id if d.next is not None else 0

                    result = a  # does not matter which one of a or b we pick
                    if a_next < b_next:
                        a = a.next  # continue the forward traversal of the lists
                        tie_broken = True
                    elif a_next > b_next:
                        a = b.next  # continue the forward traversal of the lists
                        tie_broken = True
                    else:
                        c = a.next
                        d = b.next

            elif a.doc_id < b.doc_id:

                # if this is the case, then we check if we can use the skip ptr or not.
                if a.skip is not None and b.doc_id - a.skip.doc_id >= 0:
                    prev_skip = a  # if we use the skip pointer, we remember where we skipped from.
                    # "With great power comes great responsibility."
                    a = a.skip  # traverse forward using the skip pointer
                else:
                    a = a.next

            elif a.doc_id > b.doc_id:
                if b.skip is not None and a.doc_id - b.skip.doc_id >= 0:
                    b = b.skip
                else:
                    b = b.next  # traverse forward in b's postings

        return head_a

    def or_merge(self, a, b):
        """
        This is the same as a merge between the two posting lists. We are looking for the union of two linked lists.
        Time Complexity: O(x+y)
        """
        result = None

        # Base cases
        if a is None:
            return b
        elif b is None:
            return a

        # Pick either a or b, and recur
        if a.doc_id < b.doc_id:
            result = a
            result.next = self.or_merge(a.next, b)
        elif a.doc_id > b.doc_id:
            result = b
            result.next = self.or_merge(a, b.next)
        else:
            # if both are the same, we want to set to include only one of the postings and set
            # the next to the smallest of a.next and b.next.
            tie_broken = False
            while not tie_broken:
                a_next = a.next.doc_id if a.next is not None else 0
                b_next = b.next.doc_id if b.next is not None else 0

                result = a  # does not matter which one of a or b we pick
                if a_next < b_next:
                    result.next = self.or_merge(a, a.next)
                elif a_next >= b_next:
                    result.next = self.or_merge(a, b.next)
                else:
                    result.next = self.or_merge(a, b.next)


        return result

    def and_merge(self, a, b):
        """
        This is the same as looking for the intersection of two linked lists.
        Time Complexity: O(x+y)
        """
        result = None

        # Base case. An AND operation always return null if one of the lists are empty
        if a is None or b is None:
            return None

        if a.doc_id == b.doc_id:
            # if the two postings are the same, it should (hopefully) not matter which one we choose to add to our list
            result = a
            result.next = self.and_merge(a.next, b)

        elif a.doc_id < b.doc_id:
            if a.next is None:
                return None
            # we only use the skip ptr if it gets us closer to the larger doc_id of b
            if a.skip is not None and b.doc_id - a.skip.doc_id >= 0:
                result = self.and_merge(a.skip, b)
            else:
                result = self.and_merge(a.next, b)

        elif a.doc_id > b.doc_id:
            if b.next is None:
                return None
            # we only use the skip ptr if it gets us closer to the larger doc_id of a
            if b.skip is not None and a.doc_id - b.skip.doc_id >= 0:
                result = self.and_merge(a, b.skip)
            else:
                result = self.and_merge(a, b.next)

        return result

    def and_not_merge(self, a, b):
        head_a = a
        prev_a = None
        prev_skip = None
        while a is not None and a.next is not None:
            print(f'A: {a}, B: {b}')
            if a.doc_id == b.doc_id:
                if prev_a is None:
                    # this if statement would only apply if the very first postings of both lists match.
                    head_a = a.next

                # If the doc id's are the same, we manipulate the pointer of the
                # previous posting to the node after the current. Deciding the previous posting is a bit
                # tricky because we are using skip pointers, hence the below if-statement.

                # this if statement makes sure no previous skip ptr causes us to delete all
                # nodes between the skip start to the skip end.
                if prev_skip:
                    c = prev_skip
                    d = prev_skip
                    while c is not None and c.next is not None:
                        if c.doc_id == b.doc_id:
                            d.next = c.next  # set the previous posting's next to the current's next posting
                            a = d  # continue traversing from node a (= d (= first node before the collision))
                            break  # we are done with this while-loop within while-loop and break
                        else:
                            d = c
                            c = c.next  # continue traversing and remember last posting with var d.
                else:
                    if prev_a is None:
                        prev_a = a
                        a = head_a
                    else:
                        prev_a.next = a.next  # set the previous posting's next to the current's next posting
                        a = a.next  # continue the forward traversal of the lists

            elif a.doc_id < b.doc_id:
                prev_skip = None
                prev_a = a

                # if this is the case, then we check if we can use the skip ptr or not.
                if a.skip is not None and b.doc_id - a.skip.doc_id >= 0:
                    prev_skip = a   # if we use the skip pointer, we remember where we skipped from.
                                    # "With great power comes great responsibility."
                    a = a.skip  # traverse forward using the skip pointer
                else:
                    a = a.next

            elif a.doc_id > b.doc_id:
                prev_skip = None
                prev_a = a

                if b.next is None:
                    break
                else:
                    b = b.next  # traverse forward in b's postings

        return head_a

    """
    ### LEGACY CODE ###
    def find_first_non_match(self, a, b):
        print(f'Comparing {a} with {b}')
        if b.doc_id > a.doc_id:
            print(f'We settle for {a}')
            return a, a.next
        if b.doc_id < a.doc_id:
            if b.next is None:
                return a, a.next
            else:
                return self.find_first_non_match(a, b.next)
        else:
            return self.find_first_non_match(a.next, b.next)


    def and_not_merge(self, a, b, prev=None):
        
        #The listA And-Not listB operation is the same as taking ListA - {all elements in listB}
        #Time Complexity: O(x+y)

        # base cases
        if b is None:
            return a
        if a is None:
            return None

        result = None

        print(f'A: {a}, B: {b}')

        if a.doc_id == b.doc_id:
            # if the two postings are the same, we do not set this node, instead we set it to the next

            if a.next is None:
                return None

            if prev:
                # our idea is to skip the current node (a) by
                # setting the previous node's next to the node in front of a.
                prev.next, restart_node = self.find_first_non_match(a.next, b)

                result = prev.next

                print(f'We found {prev} -> {result} is safe')
                print(f'TEST {a.next}')
                print(f'Starting process from {result} again, also {b} and {result}')

                result = self.and_not_merge(result, b, prev)

            else:
                # only if this was the very first posting in listA, otherwise we always have a "prev"
                prev, restart_node = self.find_first_non_match(a.next, b)
                result = prev
                result.next = self.and_not_merge(restart_node, b, result)

            # print(f'{prev} is now linked to {result} instead of {a} == {b}')

        elif a.doc_id < b.doc_id:
            if a.next is None:
                return a

            # we only use the skip ptr if it gets us closer to the larger doc_id of b
            if a.skip is not None and b.doc_id - a.skip.doc_id >= 0:
                result = self.and_not_merge(a.skip, b, a)
            else:
                result = self.and_not_merge(a.next, b, a)

        elif a.doc_id > b.doc_id:
            if b.next is None:
                return a
            # we only use the skip ptr if it gets us closer to the larger doc_id of a
            if b.skip is not None and a.doc_id - b.skip.doc_id >= 0:
                result = self.and_not_merge(a, b.skip, a)
            else:
                result = self.and_not_merge(a, b.next, a)

        return result
    """

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
        nodes = []
        while node is not None:
            nodes.append(str(node.doc_id))
            node = node.next
        return " ".join(nodes)


def usage():
    print("usage: " + sys.argv[0] + " -d dictionary-file -p postings-file -q file-of-queries -o output-file-of-results")


def exec_operation(listA, listB, operation):
    resulting_postings = PostingList()

    if operation == 'AND':
        resulting_postings.head = resulting_postings.and_merge(listA.head, listB.head)
    elif operation == 'OR':
        resulting_postings.head = resulting_postings.alt_or_merge(listA.head, listB.head)
    elif operation == 'ANDNOT':
        resulting_postings.head = resulting_postings.and_not_merge(listA.head, listB.head)
    elif operation == 'ORNOT':
        print(f'This operation is not yet implemented')
    elif operation == 'NOT':
        # the query "NOT term" is executed as all_docs AND NOT term. Costly operation!
        resulting_postings.head = resulting_postings.and_not_merge(listA.head, listB.head)
    else:
        print(f'Invalid operation: {operation}')

    return resulting_postings


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
                    and PRECEDENCE_DICT[operator_stack[-1]] >= PRECEDENCE_DICT[token]:
                output_q.append(operator_stack.pop())
            operator_stack.append(token)

        elif token == '(':
            operator_stack.append(token)

        elif token == ')':
            while operator_stack[-1] != '(':
                if len(operator_stack) < 1:
                    raise "MismatchError"
                output_q.append(operator_stack.pop())
            operator_stack.pop()  # pop the left parenthesis from the stack and discard it

        else:  # token must be a search term
            output_q.append(normalize_token(token))

    while len(operator_stack) > 0:
        top_of_stack = operator_stack.pop()
        if top_of_stack == '(' or top_of_stack == ')':
            raise "MismatchError"
        output_q.append(top_of_stack)
    return output_q


def process_query(q):
    postix_q = shunting_yard(q)
    return postix_q


def retrieve_postings_list(dictionary, term_id):
    with open(postings_file, 'rb') as read_postings:
        reader_offset = dictionary[term_id][1]
        read_postings.seek(reader_offset)
        return pickle.load(read_postings)


def search_term(term_to_search, dictionary):
    searched_term = normalize_token(term_to_search) if term_to_search != 'all_documents_combined' else term_to_search
    try:
        term_id = term_to_term_id[searched_term]
    except KeyError:
        return None

    return retrieve_postings_list(dictionary, term_id)


def run_search(dict_file, postings_file, queries_file, results_file):
    """
    using the given dictionary file and postings file,
    perform searching on the given queries file and output the results to a file
    """
    print('running search on the queries...')

    with open(dict_file, 'rb') as read_dict:
        # We are able to read the full dictionary into memory
        # The dictionary is structured as - term_id : (doc_freq, file_offset)
        dictionary = pickle.load(read_dict)

    # create / wipe the results file before we start handling the queries
    open(results_file, 'w').close()

    with open(queries_file, 'r') as queries:
        for query in queries:
            RPN = process_query(query)  # Process this query
            print(f'Searching for query: {query} which is translated to RPN: {RPN}')

            prev_list = None
            exec_queue = []

            i = 0
            while i < len(RPN):
                print(exec_queue)
                term = RPN[i]
                print(f'Current term: {term}')
                if term in OPERATORS:
                    # this should only be called for first iteration, then we do accumulating runs
                    if prev_list is None:
                        prev_list = search_term(exec_queue.pop(0), dictionary)

                    if term == 'NOT':
                        on_last_index = i + 1 == len(RPN)
                        if not on_last_index:
                            if RPN[i + 1] == 'AND':
                                # exec "term1 AND NOT term2"
                                second_list = search_term(exec_queue.pop(0), dictionary)
                                prev_list = exec_operation(prev_list, second_list, 'ANDNOT')
                                i += 1
                            elif RPN[i + 1] == 'OR':
                                # exec "term1 OR NOT term2"
                                all_docs_list = search_term('all_documents_combined', dictionary)
                                prev_list = exec_operation(all_docs_list, prev_list, 'NOT')
                            else:
                                # exec "NOT term1"
                                all_docs_list = search_term('all_documents_combined', dictionary)
                                prev_list = exec_operation(all_docs_list, prev_list, 'NOT')
                        else:
                            # exec "NOT term1"
                            print("EXECUTING QUERY")
                            print(f'exec q {exec_queue}')
                            all_docs_list = search_term('all_documents_combined', dictionary)
                            prev_list = exec_operation(all_docs_list, prev_list, 'NOT')
                    elif term == 'AND':
                        second_list = search_term(exec_queue.pop(0), dictionary)
                        prev_list = exec_operation(prev_list, second_list, 'AND')
                    elif term == 'OR':
                        second_list = search_term(exec_queue.pop(0), dictionary)
                        prev_list = exec_operation(prev_list, second_list, 'OR')
                else:
                    exec_queue.append(term)
                i += 1

            if exec_queue:
                prev_list = search_term(exec_queue.pop(0), dictionary)

            with open(results_file, 'a') as write_res:
                write_res.write(str(prev_list) + '\n')


dictionary_file = postings_file = file_of_queries = output_file_of_results = None

try:
    opts, args = getopt.getopt(sys.argv[1:], 'd:p:q:o:')
except getopt.GetoptError:
    usage()
    sys.exit(2)

for o, a in opts:
    if o == '-d':
        dictionary_file = a
    elif o == '-p':
        postings_file = a
    elif o == '-q':
        file_of_queries = a
    elif o == '-o':
        file_of_output = a
    else:
        assert False, "unhandled option"

if dictionary_file == None or postings_file == None or file_of_queries == None or file_of_output == None:
    usage()
    sys.exit(2)

run_search(dictionary_file, postings_file, file_of_queries, file_of_output)
