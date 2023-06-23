from typing import List
import re

FILE = '../public_data/leaders.csv'

def open_csv(file) -> List[List[str]]:
    with open(file, 'r') as fd:
        txt = fd.read()
    lines = [i.strip() for i in txt.split('\n') if i]
    return [line.split(',') for line in lines]

def write_file(file, ls):
    txt = '\n'.join(ls)
    with open(file, 'w') as fd:
        fd.write(txt)

def pascal_to_split(lines):
    result = []
    for line in lines:
        leader_pascal = line[1]
        r = re.sub(r'(?<!^)(?=[A-Z])', ',', leader_pascal)
        result.append(f"{line[0]},{line[1]},{r}")
    return result

def sort_by_civ(lines):
    lines.sort(key=lambda x: x[1])
    return [','.join(line) for line in lines]


lines_ = open_csv('../public_data/leaders.csv')
result = sort_by_civ(lines_)

print('\n'.join(result))
write_file('../public_data/leaders.csv', result)