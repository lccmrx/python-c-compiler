import sys
from core import lexer, error_collector

def main() -> None:
    try:
        if len(sys.argv) <= 1:
            sys.exit('No file specified')

        file = open(sys.argv[1])
        code = file.read()
        
        token_list = lexer.tokenize(code, file)
        
        for token in token_list:
            print(token)
        assert not error_collector.ok()
        
    except Exception as e:
        print(e)
        
        
    finally:
        file.close()
        print(f"""\rRESULTS:
            \r-------------------------
            \r  ['OK'] Lexical Analysis
            \r  ['OK'] Syntatic Analysis
            \r""")
        sys.exit(error_collector.show())
