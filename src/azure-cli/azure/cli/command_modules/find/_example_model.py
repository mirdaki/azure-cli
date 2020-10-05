# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------
import json

from azure.cli.command_modules.find.Example import Example


_BOOSTING_FACTOR_KEY = 'boosting_factor'
_C_KEY = 'c'
_COMMAND_KEY = 'command'
_DOC_IDS_KEY = 'doc_ids'
_IDF_KEY = 'idf'
_INDEX_KEY = 'index'
_K_KEY = 'k'
_MAX_VERSION_KEY = 'max_version'
_MIN_VERSION_KEY = 'min_version'
_POPULARITY_METRIC_KEY = 'popularity_metric'
_QUESTION_KEY = 'question'
_SCORE_KEY = 'score'
_T_KEY = 't'


def search_examples(model_path, query, cli_version, strict):
    '''Request relevant example commands from Aladdin model. Strict forces all examples to match the query.'''
    examples = []
    call_successful = False
    number_of_examples = 3
    command_weight = 0.5
    query = query.strip()
    if strict:
        number_of_examples = 5

    try:
        results = _search(model_path, query, number_of_examples, _convert_to_model_version(cli_version), command_weight)
        if results:
            call_successful = True
            for result in results:
                example = _clean_from_index_result(result)
                if strict and not (example.snippet.startswith(query) or example.snippet.startswith('az ' + query)):
                    break
                examples.append(_clean_from_index_result(result))
    except:  # pylint: disable=bare-except
        pass

    return (call_successful, examples)


def _search(model_path, query, number_of_examples=1, version=-1, command_weight=0.5):
    with open(model_path, 'r') as file:
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

    docs = _get_documents(query_terms, version, index_dict, inverse_index_dict, inverse_command_index_dict, command_weight)  # pylint: disable=line-too-long

    return _process_documents(docs, index_dict, number_of_examples)


def _get_documents(query_terms, version, index_dict, inverse_index_dict, inverse_command_index_dict, command_weight):
    docs = {}
    for t in query_terms:
        if t in inverse_index_dict:
            doc_k = set(inverse_index_dict[t][_DOC_IDS_KEY])
            idf_k = inverse_index_dict[t][_IDF_KEY]
        else:
            doc_k = set()
            idf_k = 0
        if t in inverse_command_index_dict:
            doc_c = set(inverse_command_index_dict[t][_DOC_IDS_KEY])
            idf_c = inverse_command_index_dict[t][_IDF_KEY]
        else:
            doc_c = set()
            idf_c = 0

        for d in doc_k:
            str_d = str(d)
            if version >= 0:
                if int(index_dict[str_d][_MAX_VERSION_KEY]) > 0:
                    if version < int(index_dict[str_d][_MIN_VERSION_KEY]) or version > int(index_dict[str_d][_MAX_VERSION_KEY]):  # pylint: disable=line-too-long
                        continue

            doc_term_weight_k = index_dict[str_d][_BOOSTING_FACTOR_KEY] * idf_k * (1 - command_weight)
            if d in docs:
                docs[d][_T_KEY] += doc_term_weight_k
                docs[d][_K_KEY] += doc_term_weight_k
            else:
                docs[d] = {_T_KEY: doc_term_weight_k, _K_KEY: doc_term_weight_k, _C_KEY: 0}

        for d in doc_c:
            str_c = str(d)
            if version >= 0:
                if int(index_dict[str_c][_MAX_VERSION_KEY]) > 0:
                    if version < int(index_dict[str_c][_MIN_VERSION_KEY]) or version > int(index_dict[str_c][_MAX_VERSION_KEY]):  # pylint: disable=line-too-long
                        continue

            doc_term_weight_c = index_dict[str(d)][_BOOSTING_FACTOR_KEY] * idf_c * (command_weight)
            if d in docs:
                docs[d][_T_KEY] += doc_term_weight_c
                docs[d][_C_KEY] += doc_term_weight_c
            else:
                docs[d] = {_T_KEY: doc_term_weight_c, _K_KEY: 0, _C_KEY: doc_term_weight_c}

    docs = [(key, val) for key, val in docs.items()]
    docs.sort(key=lambda x: x[1][_T_KEY], reverse=True)
    return docs


def _process_documents(docs, index_dict, number_of_examples):
    result = []
    size = 0
    already_present_commands = {}
    for (k, v) in docs:
        r = index_dict[str(k)]
        c = r[_COMMAND_KEY].split(' -')[0]
        if c in already_present_commands:
            if already_present_commands[c][_SCORE_KEY] == v and already_present_commands[c][_POPULARITY_METRIC_KEY] < r[_POPULARITY_METRIC_KEY]:  # pylint: disable=line-too-long
                r[_SCORE_KEY] = v
                result[already_present_commands[c][_INDEX_KEY]] = r
                already_present_commands[c][_POPULARITY_METRIC_KEY] = r[_POPULARITY_METRIC_KEY]
        else:
            already_present_commands[c] = {_INDEX_KEY: size, _SCORE_KEY: v, _POPULARITY_METRIC_KEY: r[_POPULARITY_METRIC_KEY]}  # pylint: disable=line-too-long
            r[_SCORE_KEY] = v
            result.append(r)
            size += 1
            if size >= number_of_examples:
                break
    result.sort(key=lambda x: x[_SCORE_KEY][_T_KEY] + x[_POPULARITY_METRIC_KEY] / 100000000000, reverse=True)
    return result


def _convert_to_model_version(version):
    version = version.strip('v')
    parts = ['00000000', '00000000', '00000000', '00000000']
    version_break_down = version.split('.')
    for i in range(len(version_break_down)):  # pylint: disable=consider-using-enumerate
        parts[i] = version_break_down[i].zfill(8)
    return int('{}{}{}{}'.format(parts[0], parts[1], parts[2], parts[3]))


def _clean_from_index_result(index_result):
    return Example(index_result[_QUESTION_KEY], index_result[_COMMAND_KEY])
