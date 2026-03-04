import re
# 1-10 тапсырмалардың шешімі
print('1:', re.fullmatch(r'ab*', 'abbb') is not None)
print('2:', re.fullmatch(r'ab{2,3}', 'abb') is not None)
print('3:', re.findall(r'[a-z]+_[a-z]+', 'hello_world test_case'))
print('4:', re.findall(r'[A-Z][a-z]+', 'Apple Banana'))
print('5:', re.fullmatch(r'a.*b', 'axxxb') is not None)
print('6:', re.sub(r'[ ,.]', ':', 'Hello, world. Python'))
def s2c(s): return re.sub(r'_([a-z])', lambda x: x.group(1).upper(), s)
print('7:', s2c('python_exercises'))
print('8:', re.split(r'(?=[A-Z])', 'SplitAtUpper'))
print('9:', re.sub(r'(?<!^)(?=[A-Z])', ' ', 'InsertSpacesHere'))
def c2s(s): return re.sub(r'(?<!^)(?=[A-Z])', '_', s).lower()
print('10:', c2s('CamelCaseString'))
