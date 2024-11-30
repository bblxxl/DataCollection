'''
Author: longJourney bbl@mails.swust.deu.cn
Date: 2024-11-11 13:27:49
LastEditors: longJourney bbl@mails.swust.deu.cn
LastEditTime: 2024-11-11 13:28:41
FilePath: \mut-project-pycharm\trans2.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
import json

def transform_data_for_chatglm(input_file, output_file):
    # 读取原始 JSON 文件
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 转换数据
    transformed_data = []
    instruction_text = "为以下 Python 函数编写对应的单元测试代码。"
    for item in data:
        # 检查必要的字段是否存在
        if 'function_code' in item and 'test_function_code' in item:
            # 构建新的数据项，包含 instruction、input 和 output 字段
            transformed_item = {
                "instruction": instruction_text,
                "input": item["function_code"],
                "output": item["test_function_code"]
            }
            transformed_data.append(transformed_item)
        else:
            print(f"数据项缺少必要的字段，已跳过：{item.get('function_name', '未知函数')}")

    # 将转换后的数据保存为 JSON Lines 格式
    with open(output_file, 'w', encoding='utf-8') as f:
        for item in transformed_data:
            json_line = json.dumps(item, ensure_ascii=False)
            f.write(json_line + '\n')

    print(f"数据转换完成，结果保存在 {output_file}，共转换了 {len(transformed_data)} 条数据。")

# 使用示例
input_file = 'D:\Code\mut-project-pycharm\merged_output.json'   # 替换为您的原始 JSON 文件路径
output_file = 'chatglm_finetune_data.jsonl'  # 转换后的数据文件

transform_data_for_chatglm(input_file, output_file)
