'''
Author: longJourney bbl@mails.swust.deu.cn
Date: 2024-11-11 12:38:59
LastEditors: longJourney bbl@mails.swust.deu.cn
LastEditTime: 2024-11-11 12:44:31
FilePath: \mut-project-pycharm\trans.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
import json

def transform_data(input_file, output_file):
    # 读取原始 JSON 文件
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 转换数据
    transformed_data = []
    for item in data:
        # 构建新的数据项
        transformed_item = {
            "input": item["function_code"],
            "output": item["test_function_code"]
        }
        transformed_data.append(transformed_item)

    # 将转换后的数据保存为 JSON Lines 格式
    with open(output_file, 'w', encoding='utf-8') as f:
        for item in transformed_data:
            json_line = json.dumps(item, ensure_ascii=False)
            f.write(json_line + '\n')

    print(f"数据转换完成，结果保存在 {output_file}")

# 使用示例
input_file = 'D:\Code\mut-project-pycharm\merged_output.json'   # 替换为您的原始 JSON 文件路径
output_file = 'transformed_data.jsonl'  # 转换后的数据文件

transform_data(input_file, output_file)
