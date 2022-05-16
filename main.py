import sys
from core import lexer, error_collector
from core.parser import parser

def main() -> None:
    try:
        lexer_ok = 'NOK'
        parser_ok = 'NOK'
        
        if len(sys.argv) <= 1:
            sys.exit('No file specified')

        file = open(sys.argv[1])
        code = file.read()
        
        token_list = lexer.tokenize(code, file)
        lexer_ok = 'OK' if error_collector.ok() else 'NOK'

        ast_root = parser.parse(token_list)
        parser_ok = 'OK' if error_collector.ok() else 'NOK'
        
        assert not error_collector.ok()
        
    except Exception as e:
        print(e)
        
        
    finally:
        file.close()
        print(f"""\rRESULTS:
            \r-------------------------
            \r  [{lexer_ok}] Lexical Analysis
            \r  [{parser_ok}] Syntatic Analysis
            \r""")
        sys.exit(error_collector.show())
