# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------
import json
import os.path

from azure.cli.command_modules.find.Example import Example

# TODO: Get better names of some of these constants, variables, and functions
BOOSTING_FACTOR_KEY = 'boosting_factor'
C_KEY = 'c'
COMMAND_KEY = 'command'
DOC_IDS_KEY = 'doc_ids'
IDF_KEY = 'idf'
INDEX_KEY = 'index'
K_KEY = 'k'
POPULARITY_METRIC_KEY = 'popularity_metric'
SCORE_KEY = 'score'
T_KEY = 't'


def search_examples(index_path, index_name, query, strict):
    examples = []
    call_successful = False
    number_of_examples = 3
    command_weight = 0.5
    if strict:
        number_of_examples = 5

    try:
        results = search(index_path, index_name, query, number_of_examples, command_weight)
        if results:
            call_successful = True
            for result in results:
                examples.append(clean_from_index_result(result))
    except:  # pylint: disable=bare-except
        pass

    return (call_successful, examples)


def search(index_path, index_name, query, number_of_examples=1, command_weight=0.5):
    full_path = os.path.join(index_path, index_name)
    with open(full_path, 'r') as file:
        index = json.load(file)

    synonym_dict = index['synonym_dict']
    stop_words = index['stopWords']
    index_dict = index['index_dict']
    inverse_index_dict = index['inverse_index_dict']
    inverse_command_index_dict = index['inverse_command_index_dict']

    # Strip invalid characters from query
    clean_query = query.lower().replace('-', ' ').replace('/', ' ').replace('"', '').replace("'", '').strip()

    # Normalize synonyms
    for key in synonym_dict.keys():
        if key in clean_query:
            clean_query = clean_query.replace(key, synonym_dict[key])

    # Remove stop_words
    for t in stop_words:
        tt = ' ' + t + ' '
        if tt in clean_query:
            clean_query = clean_query.replace(tt, ' ')
    clean_query = clean_query.replace('az ', '')

    # Collapse multiple spaces
    clean_query = clean_query.replace('   ', ' ').replace('  ', ' ').strip()

    # Split into single terms
    query_terms = clean_query.split(' ')

    # Add 3ple of terms
    for i in range(len(query_terms) - 2):
        query_terms.append(' '.join(query_terms[i:i + 3]))

    # Add 2ple terms in direct and reversed order
    for i in range(len(query_terms) - 1):
        query_terms.append(' '.join([query_terms[i], query_terms[i + 1]]))
        query_terms.append(' '.join([query_terms[i + 1], query_terms[i]]))

    # Add whole query itself
    query_terms.append(clean_query)

    # Deduplicate
    query_terms = set(query_terms)

    docs = get_documents(query_terms, index_dict, inverse_index_dict, inverse_command_index_dict, command_weight)

    return process_documents(docs, index_dict, number_of_examples)


def get_documents(query_terms, index_dict, inverse_index_dict, inverse_command_index_dict, command_weight):
    docs = {}
    for t in query_terms:
        if t in inverse_index_dict:
            doc_k = set(inverse_index_dict[t][DOC_IDS_KEY])
            idf_k = inverse_index_dict[t][IDF_KEY]
        else:
            doc_k = set()
            idf_k = 0
        if t in inverse_command_index_dict:
            doc_c = set(inverse_command_index_dict[t][DOC_IDS_KEY])
            idf_c = inverse_command_index_dict[t][IDF_KEY]
        else:
            doc_c = set()
            idf_c = 0

        for d in doc_k:
            str_d = str(d)
            doc_term_weight_k = index_dict[str_d][BOOSTING_FACTOR_KEY] * idf_k * (1 - command_weight)
            if d in docs:
                docs[d][T_KEY] += doc_term_weight_k
                docs[d][K_KEY] += doc_term_weight_k
            else:
                docs[d] = {T_KEY: doc_term_weight_k, K_KEY: doc_term_weight_k, C_KEY: 0}

        for d in doc_c:
            doc_term_weight_c = index_dict[str(d)][BOOSTING_FACTOR_KEY] * idf_c * (command_weight)
            if d in docs:
                docs[d][T_KEY] += doc_term_weight_c
                docs[d][C_KEY] += doc_term_weight_c
            else:
                docs[d] = {T_KEY: doc_term_weight_c, K_KEY: 0, C_KEY: doc_term_weight_c}

    docs = [(key, val) for key, val in docs.items()]
    docs.sort(key=lambda x: x[1][T_KEY], reverse=True)
    return docs


def process_documents(docs, index_dict, number_of_examples):
    result = []
    size = 0
    already_present_commands = {}
    for (k, v) in docs:
        r = index_dict[str(k)]
        c = r[COMMAND_KEY].split(' -')[0]
        if c in already_present_commands:
            if already_present_commands[c][SCORE_KEY] == v and already_present_commands[c][POPULARITY_METRIC_KEY] < r[POPULARITY_METRIC_KEY]:  # pylint: disable=line-too-long
                r[SCORE_KEY] = v
                result[already_present_commands[c][INDEX_KEY]] = r
                already_present_commands[c][POPULARITY_METRIC_KEY] = r[POPULARITY_METRIC_KEY]
        else:
            already_present_commands[c] = {INDEX_KEY: size, SCORE_KEY: v, POPULARITY_METRIC_KEY: r[POPULARITY_METRIC_KEY]}  # pylint: disable=line-too-long
            r[SCORE_KEY] = v
            result.append(r)
            size += 1
            if size >= number_of_examples:
                break

    result.sort(key=lambda x: x[SCORE_KEY][T_KEY] + x[POPULARITY_METRIC_KEY] / 100000000000, reverse=True)
    return result


def clean_from_index_result(index_result):
    return Example("", index_result[COMMAND_KEY])
