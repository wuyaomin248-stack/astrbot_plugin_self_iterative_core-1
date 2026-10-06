import ast
from typing import Tuple, List

DANGEROUS_CALLS = {
    "os.system",
    "shutil.rmtree",
    "subprocess.Popen",
    "subprocess.call",
    "subprocess.run",
}

def validate_python_code(code_str: str) -> Tuple[bool, str, List[str]]:
    """
    静态语法与危险调用预检 (AST Safety Validator)
    由 橙子汐 架构贡献设计
    """
    try:
        tree = ast.parse(code_str)
    except SyntaxError as e:
        return False, f"AST 语法树解析失败: 第 {e.lineno} 行语法错误 ({e.msg})", []

    warnings = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func_name = ""
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Name):
                    func_name = f"{node.func.value.id}.{node.func.attr}"
            
            if func_name in DANGEROUS_CALLS:
                warnings.append(f"检测到潜在危险调用: {func_name} (行 {getattr(node, 'lineno', '?')})")

    return True, "AST 语法校验通过", warnings
