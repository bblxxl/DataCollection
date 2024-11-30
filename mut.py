import ast
import inspect
import astor
import copy

# 为每个节点分配唯一的 ID
def assign_node_ids(tree):
    node_id = 0
    for node in ast.walk(tree):
        node.node_id = node_id
        node_id += 1

# 在 AST 中根据节点 ID 查找节点
def find_node_by_id(tree, node_id):
    for node in ast.walk(tree):
        if getattr(node, 'node_id', None) == node_id:
            return node
    return None

# 定义变异器类
class Mutator:
    def __init__(self):
        self.mutations = []

    def mutate(self, tree):
        assign_node_ids(tree)
        for node in ast.walk(tree):
            original_node_id = node.node_id
            mutations = self.generate_mutations(node)
            for mutated_node in mutations:
                mutated_tree = copy.deepcopy(tree)
                # 在深拷贝的树中找到对应的节点
                target_node = find_node_by_id(mutated_tree, original_node_id)
                if target_node is not None:
                    # 替换节点
                    self.replace_node(mutated_tree, target_node, mutated_node)
                    self.mutations.append(mutated_tree)
        return self.mutations

    def replace_node(self, tree, target_node, new_node):
        class Replacer(ast.NodeTransformer):
            def visit(self, node):
                if node is target_node:
                    return new_node
                else:
                    return self.generic_visit(node)
        replacer = Replacer()
        replacer.visit(tree)

    def generate_mutations(self, node):
        mutations = []
        if isinstance(node, ast.BinOp):
            # AOR - 算术运算符替换
            operators = [ast.Add(), ast.Sub(), ast.Mult(), ast.Div(), ast.Mod(), ast.Pow(), ast.FloorDiv()]
            for op in operators:
                if not isinstance(node.op, type(op)):
                    mutated_node = copy.deepcopy(node)
                    mutated_node.op = op
                    mutations.append(mutated_node)
            # AOD - 算术运算符删除
            mutations.append(node.left)
            mutations.append(node.right)
        elif isinstance(node, ast.AugAssign):
            # ASR - 赋值运算符替换
            operators = [ast.Add(), ast.Sub(), ast.Mult(), ast.Div(), ast.Mod(), ast.Pow(), ast.FloorDiv()]
            for op in operators:
                if not isinstance(node.op, type(op)):
                    mutated_node = copy.deepcopy(node)
                    mutated_node.op = op
                    mutations.append(mutated_node)
        elif isinstance(node, ast.Break):
            # BCR - break continue 替换
            mutations.append(ast.Continue())
        elif isinstance(node, ast.Continue):
            mutations.append(ast.Break())
        elif isinstance(node, ast.BoolOp):
            # LCR - 逻辑连接符替换
            if isinstance(node.op, ast.And):
                mutated_node = copy.deepcopy(node)
                mutated_node.op = ast.Or()
                mutations.append(mutated_node)
            elif isinstance(node.op, ast.Or):
                mutated_node = copy.deepcopy(node)
                mutated_node.op = ast.And()
                mutations.append(mutated_node)
            # LOD - 逻辑运算符删除
            for value in node.values:
                mutations.append(value)
        elif isinstance(node, ast.If):
            # COI - 条件运算符插入
            mutated_node_and = copy.deepcopy(node)
            mutated_node_and.test = ast.BoolOp(op=ast.And(), values=[node.test, ast.Constant(value=True)])
            mutations.append(mutated_node_and)
            mutated_node_or = copy.deepcopy(node)
            mutated_node_or.test = ast.BoolOp(op=ast.Or(), values=[node.test, ast.Constant(value=False)])
            mutations.append(mutated_node_or)
            # COD - 条件运算符删除
            mutations.append(ast.Pass())
        elif isinstance(node, ast.Constant):
            # CRP - 常量替换
            if isinstance(node.value, (int, float)):
                constants = [0, 1, -1, node.value + 1, node.value - 1]
                for c in constants:
                    if node.value != c:
                        mutations.append(ast.Constant(value=c))
            elif isinstance(node.value, str):
                constants = ['', 'mutated', node.value + '_mutated']
                for c in constants:
                    if node.value != c:
                        mutations.append(ast.Constant(value=c))
        elif isinstance(node, ast.FunctionDef):
            # DDL - 装饰器删除
            if node.decorator_list:
                mutated_node = copy.deepcopy(node)
                mutated_node.decorator_list = []
                mutations.append(mutated_node)
            # SCI - super 调用插入
            if node.args.args and node.args.args[0].arg == 'self':
                super_call = ast.Expr(value=ast.Call(
                    func=ast.Attribute(
                        value=ast.Call(func=ast.Name(id='super', ctx=ast.Load()), args=[], keywords=[]),
                        attr=node.name,
                        ctx=ast.Load()
                    ),
                    args=[ast.Name(id=arg.arg, ctx=ast.Load()) for arg in node.args.args[1:]],
                    keywords=[]
                ))
                mutated_node = copy.deepcopy(node)
                mutated_node.body.insert(0, super_call)
                mutations.append(mutated_node)
        elif isinstance(node, ast.Try):
            # EHD - 异常处理器删除
            if node.handlers:
                mutated_node = copy.deepcopy(node)
                mutated_node.handlers = []
                mutations.append(mutated_node)
        elif isinstance(node, ast.ExceptHandler):
            # EXS - 异常吞噬
            mutated_node = copy.deepcopy(node)
            mutated_node.body = []
            mutations.append(mutated_node)
        elif isinstance(node, ast.UnaryOp):
            # LOR - 逻辑运算符替换
            if isinstance(node.op, ast.Not):
                mutations.append(node.operand)
            else:
                mutated_node = copy.deepcopy(node)
                mutated_node.op = ast.Not()
                mutations.append(mutated_node)
        elif isinstance(node, ast.Compare):
            # ROR - 关系运算符替换
            operators = [ast.Eq(), ast.NotEq(), ast.Lt(), ast.LtE(), ast.Gt(), ast.GtE()]
            for op in operators:
                if not isinstance(node.ops[0], type(op)):
                    mutated_node = copy.deepcopy(node)
                    mutated_node.ops = [op]
                    mutations.append(mutated_node)
        elif isinstance(node, ast.Call):
            # SCD - super 调用删除
            if isinstance(node.func, ast.Name) and node.func.id == 'super':
                mutations.append(ast.Constant(value=None))
        elif isinstance(node, ast.Subscript):
            # SIR - 切片索引移除
            if isinstance(node.slice, ast.Slice):
                mutated_node = copy.deepcopy(node)
                mutated_node.slice = ast.Index(value=ast.Constant(value=0))
                mutations.append(mutated_node)
        elif isinstance(node, ast.Assign):
            # ASR - 赋值替换
            mutated_node = copy.deepcopy(node)
            mutated_node.value = ast.Constant(value=None)
            mutations.append(mutated_node)
        elif isinstance(node, ast.Return):
            # COD - 条件运算符删除（在返回中）
            mutations.append(ast.Pass())
        return mutations

# 生成变异函数的源代码
def generate_mutant_codes(func):
    source = inspect.getsource(func)
    tree = ast.parse(source)
    func_def = tree.body[0]

    mutator = Mutator()
    mutations = mutator.mutate(func_def)

    mutant_codes = []
    for idx, mutated_tree in enumerate(mutations):
        module = ast.Module(body=[mutated_tree], type_ignores=[])
        ast.fix_missing_locations(module)
        code = astor.to_source(module)
        mutant_codes.append(code)
    return mutant_codes

# 示例函数
def pre_mutation(context):
    if context.filename == 'foo.py':
        context.skip = True

# 生成变异函数代码列表
mutated_codes = generate_mutant_codes(pre_mutation)

# 输出变异函数的源代码
for i, code in enumerate(mutated_codes):
    print(f"#变异函数 {i}:\n{code}\n#{'-'*40}")
