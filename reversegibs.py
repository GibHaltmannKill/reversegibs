
###################################################
### WARNING: THIS DEMANGLER IS STILL INCOMPLETE ###
###################################################

import re
import sys

def get_qual_len(mangled_info):
    qual_len_match = re.search(r'[0-9]+', ''.join(mangled_info))
    qual_len_str = qual_len_match.string[qual_len_match.start():qual_len_match.end()]
    del mangled_info[:len(qual_len_str):]
    return int(qual_len_str)


def get_qual_name(namespace_count, mangled_info):
    qual_name = list()
    for i in range(0, namespace_count):
        qual_len = get_qual_len(mangled_info)
        qual_name.append(mangled_info[:qual_len:])
        del mangled_info[:qual_len:]
    return qual_name

CONST_MASK = 1
VOLATILE_MASK = 2

def demangle_type_quals(mangled_info):
    mask = str()
    if mangled_info[0] == 'C':
        mask += 'const '
        del mangled_info[:1:]
    if mangled_info[0] == 'V':
        mask += 'volatile '
        del mangled_info[:1:]
    return mask

REF_DICT = {
    'P': 'pointer',
    'R': 'reference',
    'M': 'pointer-to-member' # TODO
}

FUND_DICT = {
    'b': 'bool',
    'c': 'char',
    's': 'short',
    'i': 'int',
    'l': 'long',
    'x': 'long long',
    'f': 'float',
    'd': 'double',
    'r': 'long double',
    'v': 'void'
}

SIGN_DICT = {
    'U': 'unsigned ',
    'S': 'signed '
}

def demangle_type(mangled_info):
    type = dict()
    type['type-qualifiers'] = demangle_type_quals(mangled_info)
    if mangled_info[0] in REF_DICT:
        type['type'] = REF_DICT[mangled_info[0]]
        del mangled_info[:1:]
        type['reference'] = demangle_type(mangled_info)
    elif mangled_info[0] == 'A':
        type['type'] = 'array'
        del mangled_info[:1:]
        type['length'] = get_qual_len(mangled_info)
        del mangled_info[:1:]
        type['element'] = demangle_type(mangled_info)
    elif mangled_info[0] == 'Q' or mangled_info[0].isnumeric():
        type['type'] = 'class'
        type['qualified-name'] = demangle_name_quals(mangled_info)
    elif mangled_info[0] == 'F':
        type['type'] = 'function'
        type['parameters'] = demangle_arguments(mangled_info)
        type['return-type'] = demangle_return_type(mangled_info)
    else:
        type['type'] = 'fundamental'
        type['fundamental'] = str()
        if mangled_info[0] in SIGN_DICT:
            type['fundamental'] += SIGN_DICT[mangled_info[0]]
            del mangled_info[:1:]
        type['fundamental'] += FUND_DICT[mangled_info[0]]
        del mangled_info[:1:]
    return type


def demangle_arguments(mangled_info):
    if mangled_info[0] != 'F':
        print(mangled_info)
        raise Exception("Invalid function symbol")
    del mangled_info[:1:]
    arg_list = list()
    while mangled_info and mangled_info[0] != '_':
        arg_list.append(demangle_type(mangled_info))
    return arg_list

def demangle_return_type(mangled_info):
    del mangled_info[:1:]
    return demangle_type(mangled_info)


def demangle_name_quals(mangled_info):
    if mangled_info[0] == 'Q':
        namespace_count = int(mangled_info[1]) # CAVEAT: maximal amount of namespaces is 10
        del mangled_info[:2:]
        return get_qual_name(namespace_count, mangled_info)
    if mangled_info[0].isnumeric():
        return get_qual_name(1, mangled_info)
    return list()


def get_mangled_dictionary(mangled_name):
    mangled_dictionary = dict()
    # names may begin with 2 underscores, in which case they are not 'delimiters'
    prim_delim_index = mangled_name[1::].find('__')+1
    mangled_dictionary['name'] = mangled_name[:prim_delim_index:]
    mangled_info = list(mangled_name[prim_delim_index+2::])
    mangled_dictionary['qualified-name'] = demangle_name_quals(mangled_info)
    if mangled_info:
        mangled_dictionary['type-qualifiers'] = demangle_type_quals(mangled_info)
        mangled_dictionary['parameters'] = demangle_arguments(mangled_info)
        if mangled_info:
            mangled_dictionary['return-type'] = demangle_return_type(mangled_info)
    return mangled_dictionary


def demangle_obj_dict(obj_dict, prev_str, is_referred):
    return obj_dict['type-qualifiers'] + demangle_qual_dict(obj_dict) + prev_str


def demangle_fund_dict(fund_dict, prev_str, is_referred):
    return fund_dict['type-qualifiers'] + fund_dict['fundamental'] + prev_str


def demangle_ptr_dict(ptr_dict, prev_str, is_referred):
    return demangle_type_dict(ptr_dict['reference'], '*' + ptr_dict['type-qualifiers'] + prev_str, True)


def demangle_ref_dict(ref_dict, prev_str, is_referred):
    return demangle_type_dict(ref_dict['reference'], '&' + ref_dict['type-qualifiers'] + prev_str, True)


DEMANGLE_FUNC_DICT = {
    'fundamental': demangle_fund_dict,
    'pointer': demangle_ptr_dict,
    'reference': demangle_ref_dict,
    'class': demangle_obj_dict
}


def demangle_type_dict(mangled_dictionary, prev_str, is_referred):
    if mangled_dictionary['type'] in DEMANGLE_FUNC_DICT:
        return DEMANGLE_FUNC_DICT[mangled_dictionary['type']](mangled_dictionary, prev_str, is_referred)
    return mangled_dictionary['type'] #TODO


def demangle_param_dict(mangled_dictionary):
    type_list = [demangle_type_dict(type_dict, "", False) for type_dict in mangled_dictionary['parameters']]
    
    return "(" + ", ".join(type_list)+ ")"


def demangle_qual_dict(mangled_dictionary):
    return '::'.join([''.join(qual) for qual in mangled_dictionary['qualified-name']])


def demangle_dictionary(mangled_dictionary):
    return demangle_qual_dict(mangled_dictionary) + '::' + mangled_dictionary['name'] + demangle_param_dict(mangled_dictionary)

def demangle_name(mangled_name):
    return demangle_dictionary(get_mangled_dictionary(mangled_name))


def main():
    for mangled_name in sys.argv[1::]:
        print(demangle_name(mangled_name))


if __name__ == '__main__':
    main()
