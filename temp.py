'''
Author: longJourney bbl@mails.swust.deu.cn
Date: 2024-11-03 21:03:15
LastEditors: longJourney bbl@mails.swust.deu.cn
LastEditTime: 2024-11-11 12:35:20
FilePath: \mut-project-pycharm\temp.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
import json

def load_json(file_path):
    """加载 JSON 文件，指定 utf-8 编码"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def merge_and_deduplicate(json_files):
    """合并 JSON 文件并去重"""
    combined_data = []
    seen_functions = set()

    for file_path in json_files:
        data = load_json(file_path)
        for item in data:
            function_name = item['function_name']
            # 去重，保留首次出现的函数
            if function_name not in seen_functions:
                combined_data.append(item)
                seen_functions.add(function_name)

    return combined_data

def save_json(data, output_file):
    """保存合并后的 JSON 数据，指定 utf-8 编码"""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# 合并的文件列表和输出文件
json_files = ['D:\Code\mut-project-pycharm\\result copy\\function_pairs copy.json', 'D:\Code\mut-project-pycharm\\result copy\\function_pairs.json', 'D:\Code\mut-project-pycharm\\function_pairs.json']  # 替换为实际文件路径
output_file = 'merged_output.json'

# 执行合并并保存
merged_data = merge_and_deduplicate(json_files)
save_json(merged_data, output_file)
print("合并完成，结果保存在 merged_output.json")
