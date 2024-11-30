import requests
import ast
import time
import json
import logging
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
from datetime import datetime
import threading
from collections import defaultdict
import multiprocessing  # 新增导入

ACCESS_TOKENS = [2
]


GITHUB_API_URL = 'https://api.github.com'
current_token_index = 0
wait_lock = threading.Lock()
token_lock = threading.Lock()
is_waiting = False

def get_headers():
    token_info = ACCESS_TOKENS[current_token_index]
    token = token_info['token']
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    return headers

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def switch_token():
    global current_token_index
    start_index = current_token_index
    while True:
        current_token_index = (current_token_index + 1) % len(ACCESS_TOKENS)
        with token_lock:
            token_info = ACCESS_TOKENS[current_token_index]
            if token_info['available']:
                logging.info(f'切换到下一个令牌，索引为 {current_token_index}')
                return True
        if current_token_index == start_index:
            return False

def check_token_status():
    while True:
        time.sleep(60)
        logging.info("=== 令牌状态 ===")
        for i, token_info in enumerate(ACCESS_TOKENS):
            if token_info['available']:
                remaining = token_info['rate_limit_remaining']
                logging.info(f'令牌 {i} 可用，剩余查询次数: {remaining if remaining is not None else "未知"}')
            else:
                reset_time = token_info['reset_time']
                countdown = max(reset_time - int(time.time()), 0)
                logging.info(f'令牌 {i} 已限速，剩余等待时间: {countdown} 秒')
        logging.info("================")

def send_request(url):
    global current_token_index, is_waiting
    while True:
        headers = get_headers()
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            return response

        elif response.status_code == 403:
            # 获取速率限制相关信息
            rate_limit_remaining = response.headers.get('X-RateLimit-Remaining')
            rate_limit_reset = response.headers.get('X-RateLimit-Reset')

            if rate_limit_remaining is not None and int(rate_limit_remaining) == 0:
                with token_lock:
                    # 标记当前令牌不可用并记录重置时间
                    token_info = ACCESS_TOKENS[current_token_index]
                    reset_time = int(rate_limit_reset)
                    token_info['available'] = False
                    token_info['reset_time'] = reset_time
                    token_info['rate_limit_remaining'] = 0

                # 切换到下一个可用令牌
                if not switch_token():
                    # 如果所有令牌都已用完，等待最早的重置时间
                    with wait_lock:
                        if not is_waiting:
                            is_waiting = True
                            earliest_reset = min([t['reset_time'] for t in ACCESS_TOKENS if t['reset_time'] > 0])
                            sleep_time = max(earliest_reset - int(time.time()), 0) + 10
                            logging.warning(f'所有令牌的 API 速率限制已用完，将等待 {sleep_time} 秒')
                            time.sleep(sleep_time)

                            # 重置所有可用令牌状态
                            with token_lock:
                                for t in ACCESS_TOKENS:
                                    if t['reset_time'] <= int(time.time()):
                                        t['available'] = True
                            current_token_index = 0
                            is_waiting = False
                        else:
                            # 等待其他线程完成等待
                            while is_waiting:
                                time.sleep(1)
                else:
                    continue  # 切换令牌后重试

            elif 'abuse' in response.text.lower():
                # 处理滥用检测
                logging.error(f'滥用检测机制触发：{response.text}')
                time.sleep(60)
                continue  # 等待一段时间后重试

            else:
                # 处理其他 403 错误
                logging.error(f'403 错误：{response.text}')
                time.sleep(10)
                return response

        else:
            # 处理非 403 错误
            logging.error(f'请求错误：{response.status_code}，响应内容：{response.text}')
            time.sleep(10)
            return response

def extract_functions_from_code(code_content):
    functions = {}
    try:
        tree = ast.parse(code_content)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_name = node.name
                func_code = ast.get_source_segment(code_content, node)
                functions[func_name] = func_code
    except SyntaxError:
        pass
    return functions

def download_file(args):
    repo_full_name, file_path = args
    url = f'{GITHUB_API_URL}/repos/{repo_full_name}/contents/{file_path}'
    max_retries = 10
    retries = 0

    while retries < max_retries:
        try:
            response = send_request(url)
            if response.status_code != 200:
                logging.error(f'无法下载文件 {file_path}，仓库 {repo_full_name}：{response.status_code}')
                return '', file_path
            content = response.json().get('content', '')
            if content:
                import base64
                code_content = base64.b64decode(content).decode('utf-8', errors='ignore')
                return code_content, file_path
        except requests.exceptions.SSLError as e:
            logging.error(f'SSL 错误，下载 {file_path} 时出错：{e}')
            retries += 1
            time.sleep(5)  # 等待 5 秒后重试
        except Exception as e:
            logging.error(f'下载文件 {file_path} 时发生未知错误：{e}')
            return '', file_path

    logging.error(f'下载文件 {file_path} 失败，超过最大重试次数 {max_retries}')
    return '', file_path

def download_and_extract_functions(file_item):
    repository_full_name = file_item['repository_full_name']
    file_path = file_item['file_path']
    code_content, _ = download_file((repository_full_name, file_path))
    if code_content:
        functions = extract_functions_from_code(code_content)
        function_map = {}
        test_function_map = {}
        for func_name, func_code in functions.items():
            if func_name.startswith('test_'):
                test_function_map[func_name] = {
                    'code': func_code,
                    'file': file_path
                }
            else:
                function_map[func_name] = {
                    'code': func_code,
                    'file': file_path
                }
        return function_map, test_function_map
    else:
        return {}, {}

def process_repository_files(repo_full_name, files):
    logging.info(f'处理仓库：{repo_full_name}')
    function_map = {}
    test_function_map = {}
    all_function_pairs = []

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(download_and_extract_functions, item) for item in files]
        for future in tqdm(as_completed(futures), desc=f'处理 {repo_full_name} 的文件', total=len(futures), leave=False):
            functions, test_functions = future.result()
            function_map.update(functions)
            test_function_map.update(test_functions)

    # 生成函数对
    for test_func_name, test_func_info in test_function_map.items():
        original_func_name = test_func_name[5:]
        if original_func_name in function_map:
            all_function_pairs.append({
                'function_name': original_func_name,
                'function_code': function_map[original_func_name]['code'],
                'function_file': function_map[original_func_name]['file'],
                'test_function_name': test_func_name,
                'test_function_code': test_func_info['code'],
                'test_function_file': test_func_info['file'],
                'repository': repo_full_name
            })

    return all_function_pairs, repo_full_name

def main():
    threading.Thread(target=check_token_status, daemon=True).start()

    processed_repos_file = 'processed_repos.json'
    if os.path.exists(processed_repos_file):
        with open(processed_repos_file, 'r', encoding='utf-8') as f:
            processed_repos = set(json.load(f))
    else:
        processed_repos = set()

    function_pairs_file = 'function_pairs.json'
    if os.path.exists(function_pairs_file):
        with open(function_pairs_file, 'r', encoding='utf-8') as f:
            all_function_pairs = json.load(f)
    else:
        all_function_pairs = []

    repository_stats_file = 'repository_stats.json'
    if os.path.exists(repository_stats_file):
        with open(repository_stats_file, 'r', encoding='utf-8') as f:
            repository_stats = json.load(f)
    else:
        repository_stats = {}

    # 读取提供的 JSON 文件
    with open('deduplicated_output.json', 'r', encoding='utf-8') as f:
        file_list = json.load(f)

    # 检查 file_list 是否为空
    if not file_list:
        logging.error('The file_list.json is empty.')
        return

    # 输出第一个项目的键，供调试
    print('Keys in the first item:', file_list[0].keys())

    # 根据仓库名称对文件进行分组
    files_by_repo = defaultdict(list)
    for idx, item in enumerate(file_list):
        if not isinstance(item, dict):
            logging.error(f'Item at index {idx} is not a dictionary: {item}')
            continue
        repo_full_name = item.get('repository_full_name')
        if not repo_full_name:
            logging.error(f"Missing 'repository_full_name' in item at index {idx}: {item}")
            continue
        files_by_repo[repo_full_name].append(item)

    total_repos = len(files_by_repo)
    repos_processed = len(processed_repos)

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {}
        for repo_full_name, files in files_by_repo.items():
            if repo_full_name in processed_repos:
                logging.info(f'仓库 {repo_full_name} 已处理，跳过')
                continue
            future = executor.submit(process_repository_files, repo_full_name, files)
            futures[future] = repo_full_name

        for future in tqdm(as_completed(futures), desc='处理仓库', total=len(futures)):
            repo_full_name = futures[future]
            try:
                function_pairs, repo_name = future.result()
                all_function_pairs.extend(function_pairs)
                with open('function_pairs.json', 'w', encoding='utf-8') as f:
                    json.dump(all_function_pairs, f, ensure_ascii=False, indent=4)

                num_pairs = len(function_pairs)
                repos_processed += 1
                repository_stats[repo_name] = num_pairs
                with open(repository_stats_file, 'w', encoding='utf-8') as f:
                    json.dump(repository_stats, f, ensure_ascii=False, indent=4)
                logging.info(f'仓库 {repo_name} 收集了 {num_pairs} 个函数对，总共已保存 {len(all_function_pairs)} 个函数对')
                logging.info(f'已处理 {repos_processed} 个仓库')
                processed_repos.add(repo_name)
                with open(processed_repos_file, 'w', encoding='utf-8') as f:
                    json.dump(list(processed_repos), f, ensure_ascii=False, indent=4)
            except Exception as e:
                logging.error(f'处理仓库 {repo_full_name} 时出错：{e}')
                continue

    logging.info(f'总共处理了 {repos_processed} 个仓库')
    logging.info(f'总共保存了 {len(all_function_pairs)} 个函数对到 function_pairs.json')
    logging.info(f'各仓库收集的函数对数量已保存到 repository_stats.json')

if __name__ == '__main__':
    while True:
        start_time = time.time()
        p = multiprocessing.Process(target=main)
        p.start()
        p.join(timeout=300)  # 等待 2 分钟
        if p.is_alive():
            logging.info('已运行两分钟，重新启动脚本')
            p.terminate()
            p.join()
        else:
            logging.info('主函数已完成，退出循环')
            break
        # 您可以根据需要添加等待时间
        time.sleep(20)
