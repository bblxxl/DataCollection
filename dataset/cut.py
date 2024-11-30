'''
Author: longJourney bbl@mails.swust.deu.cn
Date: 2024-09-29 19:04:38
LastEditors: longJourney bbl@mails.swust.deu.cn
LastEditTime: 2024-09-29 19:13:57
FilePath: \mut-project-pycharm\dataset\cut.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
import json
import os
import math

def split_json(input_file, output_dir, n):
    """
    将输入的 JSON 文件均匀切分为 n 个大小相同的文件
    """
    # 创建输出目录（如果不存在）
    os.makedirs(output_dir, exist_ok=True)

    # 读取 JSON 文件
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 计算每个文件中的元素数量
    total_items = len(data)
    items_per_file = math.ceil(total_items / n)

    # 分割 JSON 数据
    for i in range(n):
        start_index = i * items_per_file
        end_index = min(start_index + items_per_file, total_items)
        split_data = data[start_index:end_index]

        # 创建输出文件名
        output_file = os.path.join(output_dir, f'split_{i + 1}.json')

        # 保存分割后的 JSON 文件
        with open(output_file, 'w', encoding='utf-8') as out_f:
            json.dump(split_data, out_f, ensure_ascii=False, indent=4)

        print(f"已保存: {output_file}")

if __name__ == "__main__":
    # 输入的 JSON 文件路径
    input_file = 'split_1.json'  # 替换为你的 JSON 文件路径

    # 输出目录
    output_dir = 'splits'  # 分割后的文件保存目录

    # 要分割成的文件数量
    n = 5  # 替换为你想要分割的文件数量

    # 运行分割函数
    split_json(input_file, output_dir, n)
