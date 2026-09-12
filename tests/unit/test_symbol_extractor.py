from apps.api.src.models.enums import SymbolType
from apps.api.src.services.parser.symbol_extractor import extract_symbols_from_tree
from apps.api.src.services.parser.tree_sitter_parser import parse_code


def test_python_symbol_extraction():
    code = b"""
class DataProcessor:
    def process_data(self, item):
        return item * 2

def top_level_func(a, b):
    return a + b
"""
    tree = parse_code(code, "Python")
    assert tree is not None
    symbols = extract_symbols_from_tree(tree, code, "Python")

    names = [s.name for s in symbols]
    assert "DataProcessor" in names
    assert "top_level_func" in names

    # Class should have method child
    cls_sym = next(s for s in symbols if s.name == "DataProcessor")
    assert cls_sym.symbol_type == SymbolType.CLASS
    assert len(cls_sym.children) == 1
    assert cls_sym.children[0].name == "process_data"
    assert cls_sym.children[0].symbol_type == SymbolType.METHOD
    assert cls_sym.children[0].qualified_name == "DataProcessor.process_data"


def test_typescript_symbol_extraction():
    code = b"""
export interface UserProfile {
    id: string;
    email: string;
}

export type Role = 'ADMIN' | 'USER';

export class AuthService {
    login(token: string): boolean {
        return true;
    }
}

export function validateEmail(email: string): boolean {
    return email.includes('@');
}
"""
    tree = parse_code(code, "TypeScript")
    assert tree is not None
    symbols = extract_symbols_from_tree(tree, code, "TypeScript")

    names = [s.name for s in symbols]
    assert "UserProfile" in names
    assert "Role" in names
    assert "AuthService" in names
    assert "validateEmail" in names

    cls_sym = next(s for s in symbols if s.name == "AuthService")
    assert len(cls_sym.children) == 1
    assert cls_sym.children[0].name == "login"
    assert cls_sym.children[0].symbol_type == SymbolType.METHOD
