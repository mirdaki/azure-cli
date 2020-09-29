# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------
import json
import os.path

from azure.cli.command_modules.find.Example import Example


def search_examples(index_path, index_name, query, strict):
    examples = []
    number_of_examples = 3
    command_weight = 0.5
    if strict:
        number_of_examples = 5

    results = search(index_path, index_name, query, number_of_examples, command_weight)

    if results:
        call_successful = True
        for result in results:
            examples.append(clean_from_index_result(result))

    return (call_successful, examples)


def search(index_path, index_name, q, n=1, command_weight=0.5):
    full_path = os.path.join(index_path, index_name)
    with open(full_path, 'r') as file:
        index = json.load(file)

    synonym_dict = index['synonym_dict']
    stop_words = index['stopWords']
    index_dict = index['index_dict']
    inverse_index_dict = index['inverse_index_dict']
    inverse_command_index_dict = index['inverse_command_index_dict']
    # strip 
    qt = q.lower().replace('-',' ').replace('/',' ').replace('"','').replace("'",'').strip()
    
    # normalize synonyms
    for key in synonym_dict.keys():
        if key in qt:
            qt = qt.replace(key,synonym_dict[key])
    # remove stop_words
    for t in stop_words:
        tt = ' '+t+' '
        if tt in qt:
            qt = qt.replace(tt,' ')
    qt = qt.replace('az ','')
    # collapse multiple spaces
    qt = qt.replace('   ',' ').replace('  ',' ').strip()
    # split into single terms
    query_terms = qt.split(' ')
    # add 3ple of terms
    for i in range(len(query_terms)-2):
        query_terms.append(' '.join(query_terms[i:i+3]))
    # add 2ple terms in direct and reversed order
    for i in range(len(query_terms)-1):
        query_terms.append(' '.join([query_terms[i],query_terms[i+1]]))
        query_terms.append(' '.join([query_terms[i+1],query_terms[i]]))
    # add whole query itself
    query_terms.append(qt)
    # deduplicate
    query_terms = set(query_terms)
    
    docs = {}
    for t in query_terms:
        if t in inverse_index_dict:
            doc_k = set(inverse_index_dict[t]['doc_ids'])
            idf_k = inverse_index_dict[t]['idf']
        else:
            doc_k = set()
            idf_k = 0
        if t in inverse_command_index_dict:
            doc_c = set(inverse_command_index_dict[t]['doc_ids'])
            idf_c = inverse_command_index_dict[t]['idf']
        else:
            doc_c = set()
            idf_c = 0
        
        for d in doc_k:
            str_d = str(d)
            doc_term_weight_k = index_dict[str_d]['boosting_factor']*idf_k*(1-command_weight)
            if d in docs:
                docs[d]['t'] += doc_term_weight_k
                docs[d]['k'] += doc_term_weight_k
            else:
                docs[d] = {'t':doc_term_weight_k,'k':doc_term_weight_k,'c':0}
                
        for d in doc_c:
            str_c = str(d)
            doc_term_weight_c = index_dict[str(d)]['boosting_factor']*idf_c*(command_weight)
            if d in docs:
                docs[d]['t'] += doc_term_weight_c
                docs[d]['c'] += doc_term_weight_c
            else:
                docs[d] = {'t':doc_term_weight_c,'k':0,'c':doc_term_weight_c}
                
    docs = [(key,val) for key,val in docs.items()]
    docs.sort(key = lambda x:x[1]['t'],reverse=True)
    result = []
    size = 0
    already_present_commands = {}
    for (k,v) in docs:
        r = index_dict[str(k)]
        c = r['command'].split(' -')[0]
        if c in already_present_commands:
            if already_present_commands[c]['score'] == v and already_present_commands[c]['popularity_metric'] < r['popularity_metric']:
                r['score'] = v 
                result[already_present_commands[c]['index']] = r
                already_present_commands[c]['popularity_metric'] = r['popularity_metric']
            
        else:
            already_present_commands[c] = {'index':size,'score':v,'popularity_metric':r['popularity_metric']}
            r['score'] = v
            result.append(r)
            size +=1
            if size >= n:
                break
                
    result.sort(key = lambda x:x['score']['t']+x['popularity_metric']/100000000000,reverse=True) 
    return result


def clean_from_index_result(index_result):
    return Example("", index_result['command'])
