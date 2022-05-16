import sys
from pprint import pprint
from core import lexer, error_collector
from core.parser import parser

def main() -> None:
    try:
        if len(sys.argv) <= 1:
            sys.exit('No file specified')

        file = open(sys.argv[1])
        code = file.read()
        
        token_list = lexer.tokenize(code, file)
        tokenize_ok = 'OK' if error_collector.ok() else 'NOK'
        ast_root = parser.parse(token_list)
        ast_ok = 'OK' if error_collector.ok() else 'NOK'
        pprint(ast_root)
        
        assert not error_collector.ok()
        
    except Exception as e:
        print(e)
        
        
    finally:
        file.close()
        print(f"""\rRESULTS:
            \r-------------------------
            \r  [{tokenize_ok}] Lexical Analysis
            \r  [{ast_ok}] Syntatic Analysis
            \r""")
        sys.exit(error_collector.show())
