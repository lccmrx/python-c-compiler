import re

from core import tokens as tks
from core.errors import CompilerError, Position, Range, error_collector

class Tagged:

    def __init__(self, c, p):
        self.c = c
        self.p = p
        self.r = Range(p, p)


def tokenize(code, filename):
    
    tokens = []
    lines = split_to_tagged_lines(code, filename)
    join_extended_lines(lines)

    in_comment = False
    for line in lines:
        try:
            line_tokens, in_comment = tokenize_line(line, in_comment)
            tokens += line_tokens
        except CompilerError as e:
            error_collector.add(e)

    return process(tokens)


def split_to_tagged_lines(text, filename):
    
    lines = text.splitlines()
    tagged_lines = []
    for line_num, line in enumerate(lines):
        tagged_line = []
        for col, char in enumerate(line):
            p = Position(filename, line_num + 1, col + 1, line)
            tagged_line.append(Tagged(char, p))
        tagged_lines.append(tagged_line)

    return tagged_lines


def join_extended_lines(lines):

    i = 0
    while i < len(lines):
        if lines[i] and lines[i][-1].c == "\\":
            
            if i + 1 < len(lines):
                del lines[i][-1] 
                lines[i] += lines[i + 1]  
                del lines[i + 1]  

                i -= 1

            else:
                del lines[i][-1]  

        i += 1


def tokenize_line(line, in_comment):
    
    tokens = []

    chunk_start = 0
    chunk_end = 0

    
    include_line = False
   
    seen_filename = False
    while chunk_end < len(line):
        symbol_kind = match_symbol_kind_at(line, chunk_end)
        next_symbol_kind = match_symbol_kind_at(line, chunk_end + 1)

       
        if match_include_command(tokens):
            include_line = True

        if in_comment:
            
            if (symbol_kind == tks.star and
                    next_symbol_kind == tks.slash):
                in_comment = False
                chunk_start = chunk_end + 2
                chunk_end = chunk_start
            
            else:
                chunk_start = chunk_end + 1
                chunk_end = chunk_start
       
        elif (symbol_kind == tks.slash and
                next_symbol_kind == tks.star):
            add_chunk(line[chunk_start:chunk_end], tokens)
            in_comment = True

        
        elif (symbol_kind == tks.slash and
                next_symbol_kind == tks.slash):
            break

        
        elif line[chunk_end].c.isspace():
            add_chunk(line[chunk_start:chunk_end], tokens)
            chunk_start = chunk_end + 1
            chunk_end = chunk_start

        
        elif symbol_kind in {tks.dquote, tks.squote}:
            quote_str = '"'
            kind = tks.string
            add_null = True

            chars, end = read_string(line, chunk_end + 1, quote_str, add_null)
            rep = chunk_to_str(line[chunk_end:end + 1])
            r = Range(line[chunk_end].p, line[end].p)

            tokens.append(tks.Token(kind, chars, rep, r=r))

            chunk_start = end + 1
            chunk_end = chunk_start

        elif symbol_kind:
            symbol_start_index = chunk_end
            symbol_end_index = chunk_end + len(symbol_kind.text_repr) - 1

            r = Range(line[symbol_start_index].p, line[symbol_end_index].p)
            symbol_token = tks.Token(symbol_kind, r=r)

            add_chunk(line[chunk_start:chunk_end], tokens)
            tokens.append(symbol_token)

            chunk_start = chunk_end + len(symbol_kind.text_repr)
            chunk_end = chunk_start

        else:
            chunk_end += 1

    add_chunk(line[chunk_start:chunk_end], tokens)

    return tokens, in_comment


def chunk_to_str(chunk):
    return "".join(c.c for c in chunk)


def match_symbol_kind_at(content, start):
    for symbol_kind in tks.symbol_kinds:
        try:
            for i, c in enumerate(symbol_kind.text_repr):
                if content[start + i].c != c:
                    break
            else:
                return symbol_kind
        except IndexError:
            pass

    return None


def match_include_command(tokens):
    return (len(tokens) == 2 and
            tokens[-1].kind == tks.identifier)


def read_string(line, start, delim, null):

    i = start
    chars = []

    escapes = {"'": 39,
               '"': 34,
               "?": 63,
               "\\": 92,
               "a": 7,
               "b": 8,
               "f": 12,
               "n": 10,
               "r": 13,
               "t": 9,
               "v": 11}
    octdigits = "01234567"
    hexdigits = "0123456789abcdefABCDEF"

    while True:
        if i >= len(line):
            descrip = "missing terminating quote"
            raise CompilerError(descrip, line[start - 1].r)
        elif line[i].c == delim:
            if null: chars.append(0)
            return chars, i
        elif (i + 1 < len(line)
              and line[i].c == "\\"
              and line[i + 1].c in escapes):
            chars.append(escapes[line[i + 1].c])
            i += 2
        elif (i + 1 < len(line)
              and line[i].c == "\\"
              and line[i + 1].c in octdigits):
            octal = line[i + 1].c
            i += 2
            while (i < len(line)
                   and len(octal) < 3
                   and line[i].c in octdigits):
                octal += line[i].c
                i += 1
            chars.append(int(octal, 8))
        elif (i + 2 < len(line)
              and line[i].c == "\\"
              and line[i + 1].c == "x"
              and line[i + 2].c in hexdigits):
            hexa = line[i + 2].c
            i += 3
            while i < len(line) and line[i].c in hexdigits:
                hexa += line[i].c
                i += 1
            chars.append(int(hexa, 16))
        else:
            chars.append(ord(line[i].c))
            i += 1

def add_chunk(chunk, tokens):
    if chunk:
        range = Range(chunk[0].p, chunk[-1].p)

        keyword_kind = match_keyword_kind(chunk)
        if keyword_kind:
            tokens.append(tks.Token(keyword_kind, r=range))
            return

        number_string = match_number_string(chunk)
        if number_string:
            tokens.append(tks.Token(tks.number, number_string, r=range))
            return

        identifier_name = match_identifier_name(chunk)
        if identifier_name:
            tokens.append(tks.Token(
                tks.identifier, identifier_name, r=range))
            return

        descrip = f"unrecognized token at '{chunk_to_str(chunk)}'"
        raise CompilerError(descrip, range)


def match_keyword_kind(token_repr):
    token_str = chunk_to_str(token_repr)
    for keyword_kind in tks.keyword_kinds:
        if keyword_kind.text_repr == token_str:
            return keyword_kind
    return None


def match_number_string(token_repr):
    token_str = chunk_to_str(token_repr)
    return token_str if token_str.isdigit() else None


def match_identifier_name(token_repr):
    token_str = chunk_to_str(token_repr)
    if re.match(r"[_a-zA-Z][_a-zA-Z0-9]*$", token_str):
        return token_str
    else:
        return None

def process(tokens):

    processed = []
    i = 0
    while i < len(tokens) - 2:
        processed.append(tokens[i])
        i += 1

    return processed + tokens[i:]
