"""科目归一化工具。

考研 11408 常见科目存在多种写法（高数/高等数学/线代…），统一映射到
标准科目名，便于后续统计与筛选。解析器与创建接口共用，保证一致性。
"""
# 标准科目 -> 别名集合
_ALIASES = {
    '数学': ['数学', '高数', '高等数学', '线代', '线性代数', '概率', '概率论', '概率统计'],
    '英语': ['英语', '英语一', '英语二', '考研英语'],
    '政治': ['政治', '政治理论', '马原', '毛中特', '史纲', '思修', '近代史'],
    '408': [
        '408', '计算机综合', '计算机专业基础', '数据结构', '计组', '计算机组成',
        '计算机组成原理', '操作系统', '计网', '计算机网络',
    ],
}

# 别名 -> 标准科目（反向查表）
_ALIAS_MAP = {alias: std for std, aliases in _ALIASES.items() for alias in aliases}


def normalize_subject(raw):
    """将任意写法归一为标准科目名；无法识别时原样返回（去空格）。"""
    if not raw:
        return ''
    s = str(raw).strip()
    if not s:
        return ''
    return _ALIAS_MAP.get(s, s)


def is_known_subject(raw):
    """是否为系统已知标准科目（含别名）。"""
    return normalize_subject(raw) in _ALIASES
