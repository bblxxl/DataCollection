from github import Github
import requests
import json
import ast
import os
import time
from tqdm import tqdm

# 多个 GitHub 访问令牌
ACCESS_TOKENS = [3
]

# 令牌索引
current_token_index = 0

def switch_token():
    """
    切换到下一个 GitHub 访问令牌
    """
    global current_token_index
    current_token_index = (current_token_index + 1) % len(ACCESS_TOKENS)
    print(f"切换到新的 GitHub 令牌，索引：{current_token_index}")
    return Github(ACCESS_TOKENS[current_token_index])

# 初始化 GitHub 对象
g = switch_token()

PROCESSED_LOG = 'processed_files.log'
DATA_PAIRS_FILE = 'data_pairs.json'

def extract_functions_from_content(file_content):
    """
    从代码内容中提取所有函数定义，忽略非 Python 3 语法的错误
    """
    try:
        tree = ast.parse(file_content)
    except SyntaxError as e:
        print(f"解析代码文件失败，错误：{e}")
        return {}
    functions = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            func_name = node.name
            func_code = ast.get_source_segment(file_content, node)
            functions[func_name] = func_code
    return functions

def get_python_files_in_repo(repo):
    """
    获取仓库中所有的Python文件路径列表
    """
    python_files = []
    contents = repo.get_contents("")
    while contents:
        file_content = contents.pop(0)
        if file_content.type == "dir":
            try:
                contents.extend(repo.get_contents(file_content.path))
            except Exception as e:
                print(f"无法获取目录内容：{file_content.path}, 错误：{e}")
                continue
        elif file_content.type == "file" and file_content.path.endswith('.py'):
            if 'test' not in file_content.path.lower():
                python_files.append(file_content.path)
    return python_files

def load_processed_log():
    """
    加载已处理的文件日志
    """
    if os.path.exists(PROCESSED_LOG):
        with open(PROCESSED_LOG, 'r', encoding='utf-8') as f:
            return set(line.strip() for line in f.readlines())
    return set()

def save_processed_log(processed_files):
    """
    将已处理文件保存到日志
    """
    with open(PROCESSED_LOG, 'a', encoding='utf-8') as f:
        for file_info in processed_files:
            f.write(f"{file_info}\n")

def load_existing_data_pairs():
    """
    加载已保存的数据对
    """
    if os.path.exists(DATA_PAIRS_FILE):
        with open(DATA_PAIRS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_single_data_pair(data_pair):
    """
    保存单个数据对到文件（及时保存）
    """
    existing_data = load_existing_data_pairs()
    existing_data.append(data_pair)
    
    with open(DATA_PAIRS_FILE, 'w', encoding='utf-8') as f:
        json.dump(existing_data, f, ensure_ascii=False, indent=4)

def process_single_repo(github_obj, file_info, processed_log):
    """
    处理单个仓库，提取函数对
    """
    global g
    repo_name = file_info['repository_full_name']
    test_file_path = file_info['file_path']
    download_url = file_info['download_url']
    unique_file_identifier = f"{repo_name}:{test_file_path}"

    # 如果该文件已经处理过，则跳过
    if unique_file_identifier in processed_log:
        print(f"跳过已处理的文件：{repo_name}, {test_file_path}")
        return None

    print(f"\n处理仓库：{repo_name}, 测试文件：{test_file_path}")

    # 下载测试文件内容
    response = requests.get(download_url)
    if response.status_code != 200:
        print(f"无法下载文件：{download_url}")
        return None
    test_file_content = response.text

    # 提取测试函数，捕获并忽略解析失败的文件
    test_functions = extract_functions_from_content(test_file_content)
    test_functions = {name: code for name, code in test_functions.items() if name.startswith('test_')}

    if not test_functions:
        print(f"测试文件 {test_file_path} 中未找到测试函数")
        return None

    # 获取仓库对象
    try:
        repo = github_obj.get_repo(repo_name)
    except Exception as e:
        print(f"无法获取仓库：{repo_name}, 错误：{e}")
        return None

    # 检查 GitHub API 速率限制
    rate_limit = g.get_rate_limit().core
    if rate_limit.remaining < 10:
        print("GitHub API 请求速率接近上限，切换到下一个令牌...")
        g = switch_token()

    # 获取仓库中的Python文件
    python_files = get_python_files_in_repo(repo)

    # 提取仓库中所有的函数
    repo_functions = {}
    for py_file in python_files:
        try:
            file_contents = repo.get_contents(py_file)
            code_content = file_contents.decoded_content.decode('utf-8', errors='ignore')
            funcs = extract_functions_from_content(code_content)
            repo_functions[py_file] = funcs
        except Exception as e:
            print(f"无法处理文件：{py_file}, 错误：{e}")
            continue

    # 对于每个测试函数，查找对应的原始函数
    for test_func_name, test_func_code in test_functions.items():
        original_func_name = test_func_name[5:]  # 去除 test_ 前缀
        found = False
        for code_file, funcs in repo_functions.items():
            if original_func_name in funcs:
                original_func_code = funcs[original_func_name]
                data_pair = {
                    'input_code': original_func_code,
                    'test_code': test_func_code,
                    'repo_name': repo_name,
                    'code_file': code_file,
                    'test_file': test_file_path
                }
                save_single_data_pair(data_pair)  # 及时保存找到的函数对
                print(f"匹配成功：{original_func_name} 在文件 {code_file} 中找到")
                found = True
                break  # 假设一个函数只在一个文件中定义
        if not found:
            print(f"在仓库 {repo_name} 中未找到函数 {original_func_name}")

    return unique_file_identifier

def find_and_save_functions():
    # 从 deduplicated_output.json 中读取测试文件的信息
    with open('deduplicated_output.json', 'r', encoding='utf-8') as f:
        test_code_files = json.load(f)

    processed_log = load_processed_log()
    processed_files = set()

    # 顺序处理所有仓库
    for file_info in tqdm(test_code_files, desc="处理文件"):
        result = process_single_repo(g, file_info, processed_log)
        if result:
            processed_files.add(result)
            save_processed_log([result])  # 及时保存处理日志

if __name__ == "__main__":
    find_and_save_functions()
