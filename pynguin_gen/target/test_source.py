'''
Author: longJourney bbl@mails.swust.deu.cn
Date: 2024-09-13 20:37:45
LastEditors: longJourney bbl@mails.swust.deu.cn
LastEditTime: 2024-09-13 22:12:03
FilePath: \mut-project\pynguin_gen\target\test_source.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
import pytest
import sys
import os

# 获取当前脚本所在目录的上一级目录
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# 将上一级目录添加到 sys.path 中
sys.path.append(parent_dir)
from source.source import add
def test_add():
    a = 1
    b = 2
    result = add(a, b)
    assert result == 3  # 测试正确返回值
