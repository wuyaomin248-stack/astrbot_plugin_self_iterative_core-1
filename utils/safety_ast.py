import ast
from typing import Tuple, List, Set, Dict

DANGEROUS_CANONICAL_CALLS = {
    "os.system",
    "shutil.rmtree",
    "subprocess.Popen",
    "subprocess.call",
    "subprocess.run",
}

def validate_python_code(code_str: str) -> Tuple[bool, str, List[str]]:
    """
    静态语法、编译规则与危险调用预检 (AST Safety Validator v2)
    由 橙子汐 架构贡献设计
    
    返回: (is_valid: bool, message: str, warnings: List[str])
    """
    try:
        tree = ast.parse(code_str)
    except SyntaxError as e:
        return False, f"AST 语法树解析失败: 第 {e.lineno} 行语法错误 ({e.msg})", []

    try:
        compile(code_str, "<string>", "exec")
    except SyntaxError as e:
        return False, f"Python 字节码编译失败: 第 {e.lineno} 行 ({e.msg})", []
    except Exception as e:
        return False, f"编译预检异常: {str(e)}", []

    warnings: List[str] = []

    alias_map: Dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                asname = alias.asname or alias.name
                alias_map[asname] = alias.name
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            for alias in node.names:
                asname = alias.asname or alias.name
                canonical = f"{mod}.{alias.name}" if mod else alias.name
                alias_map[asname] = canonical

    for node in ast.walk(tree):
        if isinstance(node, ast.While):
            test = node.test
            is_const_true = False
            if isinstance(test, ast.Constant) and bool(test.value) is True:
                is_const_true = True
            elif isinstance(test, ast.NameConstant) and test.value is True:
                is_const_true = True
            
            if is_const_true:
                has_break = any(isinstance(sub, ast.Break) for sub in ast.walk(node))
                if not has_break:
                    warnings.append(f"检测到无退出路径的常真循环 while True (行 {getattr(node, 'lineno', '?')})")

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            canonical_call = ""
            if isinstance(node.func, ast.Name):
                func_id = node.func.id
                canonical_call = alias_map.get(func_id, func_id)
            elif isinstance(node.func, ast.Attribute):
                attr = node.func.attr
                if isinstance(node.func.value, ast.Name):
                    val_id = node.func.value.id
                    mod_canonical = alias_map.get(val_id, val_id)
                    canonical_call = f"{mod_canonical}.{attr}"
            
            if canonical_call in DANGEROUS_CANONICAL_CALLS:
                warnings.append(f"检测到潜在危险系统调用: {canonical_call} (行 {getattr(node, 'lineno', '?')})")

    if warnings:
        return False, f"安全校验未通过: 发现 {len(warnings)} 项潜在风险", warnings

    return True, "AST 语法与安全校验完全通过", []
