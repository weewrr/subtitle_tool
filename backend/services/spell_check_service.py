import os
import re

from backend.config.settings import Config


class SpellCheckService:
    def __init__(self):
        pass
    
    def check_spelling(self, text):
        """检查文本拼写 - 现在使用大模型，此方法返回空列表"""
        return []
    
    def get_suggestions(self, word):
        """获取拼写建议 - 现在使用大模型，此方法返回空列表"""
        return []
    
    def get_user_dictionary(self):
        """获取用户词典 - 已弃用"""
        return []
    
    def get_name_list(self):
        """获取人名列表 - 已弃用"""
        return []
